"""Credential-free checks for tools/propagate.py on disposable git repositories."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/propagate.py'

ALIGNMENT = """SHARED_DIRECTORIES = ('network', 'setup')
SHARED_TESTS = ('tests/test_alignment.py', 'tests/test_shared.py'{extra})
"""
# Same structure as a wrapper's tests/test_reference_copy.py.
MANIFEST_HEAD = '''"""Per-agent check that the shared components equal the Claude reference copy."""
import hashlib
REFERENCE_TAG = '{tag}'
REFERENCE_COMMIT = '{commit}'
CLOSED_DIRECTORIES = ('network', 'setup')
SKIPPED_PARTS = ('__pycache__', 'bin')
MANIFEST = {{
{entries}}}


def differences(root):
    return []
'''
RUNNER = """case "${1:-}" in
    --wrapper) pattern=test_wrapper.py ;;
    --shared) pattern='' ;;
    --setup) pattern=test_setup.py ;;
    --guard|--guard-idle) pattern=test_guard.py ;;
    --network) pattern=test_network_runtime.py ;;
esac
"""


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout


def write(root, files):
    for name, text in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


class Propagation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='propagate-')
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.reference = base / 'reference'
        self.target = base / 'target'
        for repo in (self.reference, self.target):
            repo.mkdir()
            git(repo, 'init', '-q', '-b', 'main')
            git(repo, 'config', 'user.email', 'test@example.invalid')
            git(repo, 'config', 'user.name', 'Test')
        old = {'network/a.py': 'a = 1\n', 'network/b.py': 'b = 1\n', 'network/gone.py': 'gone\n',
               'setup/diagnostics.py': 'diagnostics = 1\n', 'setup/common.py': 'common = 1\n',
               'tests/test_alignment.py': ALIGNMENT.format(extra=''), 'tests/test_shared.py': 'shared = 1\n',
               'tests/test_reference_only.py': 'not shared\n'}
        self.commit_tag(old, 'sandbox-ref-1')
        new = dict(old, **{'network/a.py': 'a = 2\n', 'network/c.py': 'c = 1\n', 'setup/common.py': 'common = 2\n',
                           'tests/test_alignment.py': ALIGNMENT.format(extra=", 'tests/test_new.py'"),
                           'tests/test_new.py': 'new = 1\n', 'tests/test_reference_only.py': 'changed\n'})
        del new['network/gone.py']
        self.commit_tag(new, 'sandbox-ref-2')
        self.old_commit = git(self.reference, 'rev-parse', 'sandbox-ref-1^{commit}').strip()
        self.new_commit = git(self.reference, 'rev-parse', 'sandbox-ref-2^{commit}').strip()
        # Target adopts network/ and the shared tests, but only setup/diagnostics.py.
        adopted = {name: old[name] for name in ('network/a.py', 'network/b.py', 'network/gone.py',
                                                 'setup/diagnostics.py', 'tests/test_alignment.py', 'tests/test_shared.py')}
        write(self.target, adopted)
        write(self.target, {
            'tests/test_reference_copy.py': self.manifest('sandbox-ref-1', self.old_commit, adopted),
            'tests/run-runtime.sh': RUNNER,
            'README.md': 'Copied from tag `sandbox-ref-1`; see sandbox-ref-10 and sandbox-ref-1x.\n',
            'docs/network-contract.md': f'Reference `sandbox-ref-1` (commit `{self.old_commit}`).\n'
                                        '| Pi | Ported from `sandbox-ref-1`; shared files unchanged |\n',
            'docs/validation.md': 'Adoption of `sandbox-ref-1`.\n',
            'CHANGELOG.md': 'Shared files now come from `sandbox-ref-1`.\n',
            'openspec/changes/archive/x/design.md': 'Copy from `sandbox-ref-1`.\n'})
        git(self.target, 'add', '-A')
        git(self.target, 'commit', '-q', '-m', 'adopt ref-1')

    def commit_tag(self, files, tag):
        for path in list(self.reference.rglob('*')):
            if path.is_file() and '.git' not in path.parts:
                path.unlink()
        write(self.reference, files)
        git(self.reference, 'add', '-A')
        git(self.reference, 'commit', '-q', '-m', tag)
        git(self.reference, 'tag', '-a', tag, '-m', tag)

    @staticmethod
    def manifest(tag, commit, files):
        entries = ''.join(f"    '{name}': '{hashlib.sha256(text.encode()).hexdigest()}',\n"
                          for name, text in sorted(files.items()))
        return MANIFEST_HEAD.format(tag=tag, commit=commit, entries=entries)

    def run_tool(self, *args, old='sandbox-ref-1', new='sandbox-ref-2'):
        return subprocess.run([sys.executable, '-I', str(TOOL), str(self.target), old, new,
                               '--reference', str(self.reference), *args], capture_output=True, text=True)

    def snapshot(self):
        return {p.relative_to(self.target): p.read_bytes() for p in self.target.rglob('*')
                if p.is_file() and '.git' not in p.parts}

    def test_dry_run_plans_without_writing(self):
        before = self.snapshot()
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('modified: network/a.py, tests/test_alignment.py\n', result.stdout)
        self.assertIn('added: network/c.py, tests/test_new.py\n', result.stdout)
        self.assertIn('removed: network/gone.py\n', result.stdout)
        self.assertIn('not adopted: setup/common.py\n', result.stdout)
        self.assertIn('documents: README.md (1), docs/network-contract.md (3)', result.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'main')

    def test_apply_copies_rewrites_and_keeps_history(self):
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'adopt-sandbox-ref-2')
        for name in ('network/a.py', 'network/c.py', 'tests/test_new.py', 'tests/test_alignment.py'):
            expected = git(self.reference, 'show', f'sandbox-ref-2:{name}')
            self.assertEqual((self.target / name).read_text(), expected, name)
        self.assertFalse((self.target / 'network/gone.py').exists())
        self.assertFalse((self.target / 'setup/common.py').exists())
        manifest = (self.target / 'tests/test_reference_copy.py').read_text()
        self.assertIn("REFERENCE_TAG = 'sandbox-ref-2'", manifest)
        self.assertIn(f"REFERENCE_COMMIT = '{self.new_commit}'", manifest)
        self.assertNotIn('network/gone.py', manifest)
        for name in ('network/a.py', 'network/b.py', 'network/c.py', 'setup/diagnostics.py', 'tests/test_new.py'):
            digest = hashlib.sha256((self.target / name).read_bytes()).hexdigest()
            self.assertIn(f"    '{name}': '{digest}',\n", manifest)
        self.assertTrue(manifest.endswith("def differences(root):\n    return []\n"))
        readme = (self.target / 'README.md').read_text()
        self.assertEqual(readme, 'Copied from tag `sandbox-ref-2`; see sandbox-ref-10 and sandbox-ref-1x.\n')
        contract = (self.target / 'docs/network-contract.md').read_text()
        self.assertIn(f'`sandbox-ref-2` (commit `{self.new_commit}`)', contract)
        self.assertIn('Ported from `sandbox-ref-2`', contract)
        for name in ('docs/validation.md', 'CHANGELOG.md', 'openspec/changes/archive/x/design.md'):
            self.assertIn('sandbox-ref-1`', (self.target / name).read_text(), name)
        # No version-control side effects beyond the branch.
        self.assertEqual(git(self.target, 'log', '--oneline').count('\n'), 1)
        self.assertTrue(git(self.target, 'status', '--porcelain').strip())

    def test_checklist_follows_the_changed_files_and_runner(self):
        result = self.run_tool()
        line = next(l for l in result.stdout.splitlines() if l.startswith('Run in the target: '))
        self.assertEqual(line, 'Run in the target: bash tests/run-runtime.sh --shared')
        self.assertIn('## Adoption of `sandbox-ref-2`:', result.stdout)
        self.assertIn('Adopt sandbox-ref-2', result.stdout)
        # A setup change selects the setup modes the runner offers; guard sources the guard/network modes.
        new = {'network/a.py': 'a = 2\n', 'network/b.py': 'b = 1\n', 'network/c.py': 'c = 1\n',
               'network/proxy.py': 'proxy\n', 'setup/diagnostics.py': 'diagnostics = 2\n',
               'setup/common.py': 'common = 2\n',
               'tests/test_alignment.py': ALIGNMENT.format(extra=", 'tests/test_new.py'"),
               'tests/test_shared.py': 'shared = 1\n', 'tests/test_new.py': 'new = 1\n',
               'tests/test_reference_only.py': 'changed\n'}
        self.commit_tag(new, 'sandbox-ref-3')
        result = self.run_tool(new='sandbox-ref-3')
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(l for l in result.stdout.splitlines() if l.startswith('Run in the target: '))
        self.assertEqual(line, 'Run in the target: bash tests/run-runtime.sh --shared; bash tests/run-runtime.sh --setup; '
                               'bash tests/run-runtime.sh --guard; bash tests/run-runtime.sh --network')

    def test_preconditions_refuse_without_writing(self):
        cases = []
        (self.target / 'README.md').write_text('local edit\n')
        cases.append(('uncommitted changes', {}))
        for message, kwargs in cases:
            before = self.snapshot()
            result = self.run_tool(**kwargs)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
            self.assertEqual(self.snapshot(), before)
        git(self.target, 'checkout', '--', 'README.md')
        for kwargs, message in (({'old': 'sandbox-ref-2', 'new': 'sandbox-ref-2'}, 'adopts sandbox-ref-1'),
                                ({'new': 'sandbox-ref-9'}, 'tag sandbox-ref-9 does not exist')):
            result = self.run_tool(**kwargs)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn(message, result.stderr)
        # A forked shared file is refused.
        (self.target / 'network/b.py').write_text('b = 99\n')
        git(self.target, 'commit', '-qam', 'fork')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('network/b.py differs from sandbox-ref-1', result.stderr)
        git(self.target, 'reset', '-q', '--hard', 'HEAD~1')
        # An existing adoption branch is refused.
        git(self.target, 'branch', 'adopt-sandbox-ref-2')
        result = self.run_tool('--apply')
        self.assertEqual(result.returncode, 1)
        self.assertIn('branch adopt-sandbox-ref-2 already exists', result.stderr)
        self.assertEqual(git(self.target, 'branch', '--show-current').strip(), 'main')
        git(self.target, 'branch', '-D', 'adopt-sandbox-ref-2')
        # A malformed manifest is refused.
        manifest = self.target / 'tests/test_reference_copy.py'
        manifest.write_text(manifest.read_text().replace("',\n}", "'\n}"))
        git(self.target, 'commit', '-qam', 'malformed')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('unreadable manifest line', result.stderr)

    def test_same_tag_reports_no_changes(self):
        result = self.run_tool(old='sandbox-ref-1', new='sandbox-ref-1')
        self.assertEqual(result.returncode, 0, result.stderr)
        for label in ('modified', 'added', 'removed', 'not adopted', 'documents'):
            self.assertIn(label + ': none\n', result.stdout)


if __name__ == '__main__':
    unittest.main()
