#!/usr/bin/env python3
"""Propagate a new reference tag of the shared components to a wrapper checkout.

Usage: python3 -I tools/propagate.py <target> <old-tag> <new-tag> [--apply]

Reference-only: this tool lives in claude-container and is never copied.
It reads the tags from this checkout, verifies that the target is a clean,
unforked adopter of <old-tag>, and prints (dry run) or applies the changes:
shared files, the tests/test_reference_copy.py manifest and the tag/commit
references in current-state documents. It never runs suites, commits, merges,
tags or pushes. See docs/propagation.md.
"""
import argparse
import ast
import datetime
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

REFERENCE = Path(__file__).resolve().parents[1]
MANIFEST_FILE = 'tests/test_reference_copy.py'
ALIGNMENT_FILE = 'tests/test_alignment.py'
# Current-state documents; history (docs/validation.md, CHANGELOG.md, todo.md,
# openspec/) is never rewritten.
DOCUMENTS = ('README.md', 'AGENTS.md', 'CONTRIBUTING.md', 'docs/setup.md', 'docs/network-contract.md')
SKIPPED_PARTS = ('__pycache__', 'bin')
TAG_LINE = re.compile(r"^REFERENCE_TAG = '([^']+)'$", re.M)
COMMIT_LINE = re.compile(r"^REFERENCE_COMMIT = '([0-9a-f]{40})'$", re.M)
ENTRY = re.compile(r"^    '([^']+)': '([0-9a-f]{64})',$")


class PropagationError(Exception):
    pass


def git(repo, *args, data=False):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if result.returncode:
        raise PropagationError('git ' + ' '.join(args) + ' failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout if data else result.stdout.decode()


def commit_of(tag):
    try:
        return git(REFERENCE, 'rev-parse', '--verify', '-q', tag + '^{commit}').strip()
    except PropagationError:
        raise PropagationError(f'tag {tag} does not exist in {REFERENCE}') from None


def tree(tag):
    """{path: (mode, blob)} for every file at the tag."""
    files = {}
    for line in git(REFERENCE, 'ls-tree', '-r', tag).splitlines():
        meta, path = line.split('\t', 1)
        mode, kind, blob = meta.split()
        if kind == 'blob':
            files[path] = (mode, blob)
    return files


def shared_set(tag, files):
    """Shared paths at the tag, as listed by its tests/test_alignment.py."""
    source = git(REFERENCE, 'show', f'{tag}:{ALIGNMENT_FILE}')
    values = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in ('SHARED_DIRECTORIES', 'SHARED_TESTS'):
            values[node.targets[0].id] = ast.literal_eval(node.value)
    if set(values) != {'SHARED_DIRECTORIES', 'SHARED_TESTS'}:
        raise PropagationError(f'{tag}:{ALIGNMENT_FILE} does not declare SHARED_DIRECTORIES and SHARED_TESTS')
    directories = tuple(values['SHARED_DIRECTORIES'])
    shared = {path for path in files if path.split('/', 1)[0] in directories
              and not any(part in SKIPPED_PARTS for part in path.split('/'))}
    tests = {path for path in values['SHARED_TESTS'] if path in files}
    return directories, shared | tests, tests


def read_manifest(target):
    path = target / MANIFEST_FILE
    if not path.is_file():
        raise PropagationError(f'{MANIFEST_FILE} is missing in {target}')
    text = path.read_text()
    tags, commits = TAG_LINE.findall(text), COMMIT_LINE.findall(text)
    if len(tags) != 1 or len(commits) != 1:
        raise PropagationError(f'{MANIFEST_FILE}: expected one REFERENCE_TAG and one REFERENCE_COMMIT line')
    lines = text.splitlines(keepends=True)
    try:
        start = next(i for i, line in enumerate(lines) if line.rstrip('\n') == 'MANIFEST = {')
        end = next(i for i in range(start + 1, len(lines)) if lines[i].rstrip('\n') == '}')
    except StopIteration:
        raise PropagationError(f'{MANIFEST_FILE}: cannot find the MANIFEST = {{ ... }} block') from None
    entries = {}
    for line in lines[start + 1:end]:
        match = ENTRY.match(line.rstrip('\n'))
        if not match:
            raise PropagationError(f'{MANIFEST_FILE}: unreadable manifest line: {line.strip()}')
        if match[1] in entries:
            raise PropagationError(f'{MANIFEST_FILE}: duplicate manifest entry {match[1]}')
        entries[match[1]] = match[2]
    return text, lines, (start, end), tags[0], commits[0], entries


def plan(target, old, new):
    target = Path(target).resolve()
    if not (target / '.git').exists():
        raise PropagationError(f'{target} is not a git checkout')
    old_commit, new_commit = commit_of(old), commit_of(new)
    if git(target, 'status', '--porcelain').strip():
        raise PropagationError(f'{target} has uncommitted changes; commit or stash them first')
    _, _, _, tag, commit, adopted = read_manifest(target)
    if (tag, commit) != (old, old_commit):
        raise PropagationError(f'{target} adopts {tag} ({commit}), not {old} ({old_commit})')
    branch = 'adopt-' + new
    if git(target, 'branch', '--list', branch).strip():
        raise PropagationError(f'branch {branch} already exists in {target}')
    old_files, new_files = tree(old), tree(new)
    directories, old_shared, old_tests = shared_set(old, old_files)
    _, new_shared, _ = shared_set(new, new_files)
    for path in sorted(adopted):
        if path not in old_files:
            raise PropagationError(f'manifest entry {path} is not in {old}')
        expected = git(REFERENCE, 'show', f'{old}:{path}', data=True)
        local = target / path
        if not local.is_file() or local.read_bytes() != expected:
            raise PropagationError(f'{path} differs from {old} in {target}; a fork must be fixed in claude-container first')
    complete_directories = {d for d in directories
                            if {p for p in old_shared if p.startswith(d + '/')} <= set(adopted)}
    complete_tests = old_tests <= set(adopted)
    modified = sorted(p for p in adopted if p in new_files and new_files[p][1] != old_files[p][1])
    removed = sorted(p for p in adopted if p not in new_files)
    added, not_adopted = [], []
    for path in sorted(new_shared - old_shared):
        top = path.split('/', 1)[0]
        if top in complete_directories or (path.startswith('tests/') and top not in directories and complete_tests):
            added.append(path)
        else:
            not_adopted.append(path)
    changed = {p for p in (old_shared | new_shared) if old_files.get(p) != new_files.get(p)}
    not_adopted += sorted(changed - set(adopted) - set(added) - set(not_adopted))
    documents = {}
    for name in DOCUMENTS if old != new else ():
        path = target / name
        if path.is_file():
            text = path.read_text()
            count = len(tag_pattern(old).findall(text)) + text.count(old_commit)
            if count:
                documents[name] = count
    return dict(target=target, old=old, new=new, old_commit=old_commit, new_commit=new_commit, branch=branch,
                modified=modified, added=added, removed=removed, not_adopted=sorted(not_adopted),
                documents=documents, modes=checklist(target, modified + added + removed), new_files=new_files)


def tag_pattern(tag):
    # Whole word: sandbox-ref-1 must not match sandbox-ref-10.
    return re.compile(r'(?<![\w-])' + re.escape(tag) + r'(?![\w-])')


def runner_modes(target):
    path = target / 'tests/run-runtime.sh'
    if not path.is_file():
        return set()
    text = path.read_text()
    labels = re.findall(r'^\s*(--[a-z][a-z-]*)(?:\|[^)]*)?\)', text, re.M)
    labels += re.findall(r'\|(--[a-z][a-z-]*)\)', text)
    labels += re.findall(r'==\s*(--[a-z][a-z-]*)\s*\]\]', text)
    return set(labels)


def checklist(target, changed):
    offered = runner_modes(target)
    modes = ['--shared'] if '--shared' in offered else ['python3 -m unittest tests.test_reference_copy tests.test_alignment']
    def any_changed(*prefixes):
        return any(path.startswith(prefixes) for path in changed)
    if any_changed('setup/', 'tests/test_setup.py'):
        modes += [m for m in ('--setup', '--setup-runtime') if m in offered]
    if any_changed('network/qualif', 'network/platform_check.py', 'network/release_acceptance.json',
                   'tests/test_qualification.py', 'tests/test_platform.py'):
        modes += [m for m in ('--qualification',) if m in offered]
    if any_changed('network/guard', 'network/build-guard.sh', 'network/proxy', 'network/relay.py', 'network/mux.py',
                   'network/session.py', 'network/control.py', 'network/tls_client_hello.py', 'network/policy.py',
                   'tests/test_guard.py', 'tests/guard_', 'tests/test_session.py', 'tests/test_mux.py'):
        modes += [m for m in ('--guard', '--network') if m in offered]
    if any_changed('network/agent_profile.py'):
        modes += [m for m in ('--wrapper',) if m in offered]
    return list(dict.fromkeys(modes))


def write_atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name + '.')
    try:
        with os.fdopen(handle, 'wb') as output:
            output.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def apply(result):
    target, new = result['target'], result['new']
    git(target, 'switch', '-q', '-c', result['branch'])
    written = []
    try:
        for path in result['modified'] + result['added']:
            mode = 0o755 if result['new_files'][path][0] == '100755' else 0o644
            write_atomic(target / path, git(REFERENCE, 'show', f'{new}:{path}', data=True), mode)
            written.append(path)
        for path in result['removed']:
            (target / path).unlink()
            written.append(path)
        text, lines, (start, end), _, _, entries = read_manifest(target)
        for path in result['removed']:
            entries.pop(path)
        for path in result['modified'] + result['added']:
            entries[path] = hashlib.sha256((target / path).read_bytes()).hexdigest()
        block = [f"    '{path}': '{digest}',\n" for path, digest in sorted(entries.items())]
        text = ''.join(lines[:start + 1] + block + lines[end:])
        text = TAG_LINE.sub(f"REFERENCE_TAG = '{new}'", text)
        text = COMMIT_LINE.sub(f"REFERENCE_COMMIT = '{result['new_commit']}'", text)
        manifest = target / MANIFEST_FILE
        write_atomic(manifest, text.encode(), manifest.stat().st_mode & 0o7777)
        written.append(MANIFEST_FILE)
        for name in result['documents']:
            path = target / name
            text = tag_pattern(result['old']).sub(new, path.read_text()).replace(result['old_commit'], result['new_commit'])
            write_atomic(path, text.encode(), path.stat().st_mode & 0o7777)
            written.append(name)
    except BaseException as error:
        raise PropagationError(f'apply stopped after writing {written}: {error}; '
                               f'reset with git -C {target} checkout -- . and switch back') from error


def report(result, applied):
    out = [f"{'Applied' if applied else 'Dry run'}: {result['old']} -> {result['new']} in {result['target']}"]
    if applied:
        out.append(f"Branch: {result['branch']} (uncommitted; review with git diff)")
    for label in ('modified', 'added', 'removed', 'not_adopted'):
        out.append(f"{label.replace('_', ' ')}: " + (', '.join(result[label]) or 'none'))
    out.append('documents: ' + (', '.join(f'{n} ({c})' for n, c in result['documents'].items()) or 'none'))
    out.append('manifest: ' + MANIFEST_FILE + f" -> {result['new']} ({result['new_commit']})")
    out.append('Run in the target: ' + '; '.join(
        m if m.startswith('python3') else 'bash tests/run-runtime.sh ' + m for m in result['modes']))
    copied = result['modified'] + result['added']
    out += ['', 'Validation record template (docs/validation.md):', '',
            f"## Adoption of `{result['new']}`: {datetime.date.today().isoformat()}", '',
            f"Copied from `claude-container` tag `{result['new']}` (commit `{result['new_commit'][:7]}`): "
            + (', '.join(f'`{p}`' for p in copied) or 'no files') + '.'
            + (' Removed: ' + ', '.join(f'`{p}`' for p in result['removed']) + '.' if result['removed'] else ''),
            'The `tests/test_reference_copy.py` manifest moved to the tag.', '',
            '| Check | Result |', '| --- | --- |']
    out += [f"| `{m if m.startswith('python3') else 'bash tests/run-runtime.sh ' + m}` | <fill in> |" for m in result['modes']]
    out += ['', 'Commit message:', '', f"Adopt {result['new']}", '',
            f"Copy the changed shared files from claude-container {result['new']} and move",
            'the reference manifest and the current-state references to the tag.']
    print('\n'.join(out))


def main(argv=None):
    global REFERENCE
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('target')
    parser.add_argument('old')
    parser.add_argument('new')
    parser.add_argument('--apply', action='store_true', help='write the changes on a new adopt-<new> branch')
    parser.add_argument('--reference', default=str(REFERENCE), help=argparse.SUPPRESS)  # tests only
    args = parser.parse_args(argv)
    REFERENCE = Path(args.reference).resolve()
    try:
        result = plan(args.target, args.old, args.new)
        if args.apply:
            apply(result)
        report(result, args.apply)
    except PropagationError as error:
        print('propagate: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
