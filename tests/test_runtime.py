"""Opt-in checks against a real rootless engine; synthetic state only."""
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import selectors
import signal
import subprocess
import tarfile
import tempfile
import time
import unittest
import uuid
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'network'))
import agent_budgets  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'claude-container.sh'
IMAGE = os.environ.get('CLAUDE_CONTAINER_IMAGE', 'localhost/claude-code:latest')
ENGINE_IMAGE = os.environ.get('CLAUDE_CONTAINER_ENGINE_IMAGE', 'localhost/claude-code-engine:latest')
# A small local image the library copies into its store (pinned, already in the engine).
SAMPLE = os.environ.get('SANDBOX_TEST_ENGINE_SAMPLE', 'docker.io/library/alpine@sha256:'
                        'c64c687cbea9300178b30c95835354e34c4e4febc4badfe27102879de0483b5e')
ENABLED = os.environ.get('SANDBOX_RUNTIME_TESTS') == '1'


def engine_budgets(env):
    """Delegated controllers and process mechanism of the engine, by the launcher's rule."""
    def info(template):
        return subprocess.run(['podman', 'info', '--format', template], env=env, check=True,
                              capture_output=True, text=True, timeout=60).stdout.strip()
    delegated = agent_budgets.delegated(info('{{.Host.CgroupControllers}}'), info('{{.Host.CgroupManager}}'))
    return delegated, agent_budgets.process_mechanism(delegated, info('{{.Host.Kernel}}'))


def start_crowd(test, env, count):
    """A container of the caller holding count sleeping processes, removed at cleanup."""
    name = 'claude-test-crowd-' + uuid.uuid4().hex[:12]
    test.addCleanup(subprocess.run, ['podman', 'rm', '--force', '--time', '0', '--ignore', name],
                    env=env, capture_output=True, timeout=60)
    subprocess.run(['podman', 'run', '--detach', '--rm', '--name', name, '--userns=keep-id',
                    '--user', f'{os.getuid()}:{os.getgid()}', '--network=none', '--entrypoint', '/bin/sh', IMAGE,
                    '-c', f'i=0; while [ $i -lt {count} ]; do sleep 600 & i=$((i + 1)); done; wait'],
                   env=env, check=True, capture_output=True, text=True, timeout=60)
    deadline = time.monotonic() + 60
    while True:
        top = subprocess.run(['podman', 'top', name, 'pid'], env=env, capture_output=True, text=True, timeout=30)
        # The header line, the shell and its sleeping children.
        if len(top.stdout.splitlines()) >= count + 2 or time.monotonic() > deadline:
            break
        time.sleep(0.5)
    test.assertGreaterEqual(len(top.stdout.splitlines()), count + 2, top.stdout + top.stderr)
    return name


@unittest.skipUnless(ENABLED, 'set SANDBOX_RUNTIME_TESTS=1 to use a real rootless engine')
class RuntimeTests(unittest.TestCase):
    def setUp(self):
        workspace_root = ROOT / '.test-state'
        workspace_root.mkdir(exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix='runtime-', dir=workspace_root))
        self.addCleanup(shutil.rmtree, self.base)
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        # With a Unix launch service this directory must exist at the identical
        # host path. The disposable runner supplies a native Linux volume.
        self.native = Path(tempfile.mkdtemp(prefix='claude-runtime-',
                           dir=os.environ.get('SANDBOX_TEST_STATE_ROOT')))
        self.addCleanup(shutil.rmtree, self.native)
        self.state = self.native / 'state'
        self.host_home = self.native / 'synthetic-host-home'
        self.host_home.mkdir(mode=0o700)
        self.env = {'PATH': os.environ['PATH'], 'HOME': str(self.host_home),
                    'CLAUDE_CONTAINER_NETWORK': 'unrestricted',
                    'CLAUDE_CONTAINER_MAINTENANCE': '1',
                    'CLAUDE_CONTAINER_IMAGE': IMAGE,
                    'CLAUDE_CONTAINER_STATE_DIR': str(self.state)}
        if os.environ.get('CONTAINER_HOST'):
            self.env['CONTAINER_HOST'] = os.environ['CONTAINER_HOST']

    def shell(self, script, *options, caller_umask=-1, **env):
        return subprocess.run([str(WRAPPER), '--container-shell', *options], cwd=self.project,
                              env=self.env | env, input='set -Eeuo pipefail\n' + script,
                              text=True, capture_output=True, timeout=90, umask=caller_umask)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def build_fixture(self, context, recipe):
        image = 'localhost/claude-test-' + uuid.uuid4().hex + ':latest'
        (context / 'Containerfile').write_text(f'FROM {IMAGE}\n' + recipe)
        # Register before building so partially successful builds are cleaned up.
        self.addCleanup(subprocess.run, ['podman', 'image', 'rm', '--force', '--ignore', image],
                        env=self.env, check=True, capture_output=True, text=True, timeout=60)
        result = subprocess.run(['podman', 'build', '--pull=never', '--tag', image,
                                 '--file', str(context / 'Containerfile'), str(context)],
                                env=self.env, text=True, capture_output=True, timeout=120)
        self.assert_success(result)
        return image

    def test_image_environment_defaults_are_cleared_and_delegation_is_refused(self):
        context = self.base / 'environment-context'
        context.mkdir()
        image = self.build_fixture(context, 'ENV CONTAINER_HOST=unix:///synthetic/default.sock\n')
        for isolated in ('', str(self.state)):
            with self.subTest(isolated=isolated):
                self.assert_success(self.shell('test "${CONTAINER_HOST+x}" != x\ntest ! -S /run/podman/podman.sock\n',
                                               CLAUDE_CONTAINER_IMAGE=image, CLAUDE_CONTAINER_STATE_DIR=isolated))
                # Host Podman delegation was removed; the old opt-in stops the launch.
                result = self.shell('true\n', CLAUDE_CONTAINER_IMAGE=image, CLAUDE_CONTAINER_STATE_DIR=isolated,
                                    CLAUDE_CONTAINER_PODMAN='1')
                self.assertEqual(result.returncode, 1)
                self.assertIn('CLAUDE_CONTAINER_PODMAN=1: host Podman delegation was removed', result.stderr)

    def engine_budgets(self):
        return engine_budgets(self.env)

    def test_effective_hardening_and_budgets_in_every_unrestricted_variant(self):
        # Budgets apply as the engine allows: cgroup limits only for delegated
        # controllers, the process rlimit as fallback, and a notice otherwise.
        delegated, mechanism = self.engine_budgets()
        script = '''python3 - "$@" <<'CHECK'
import pathlib, sys
memory, nano, pids = map(int, sys.argv[1:4])
delegated, mechanism = sys.argv[4].split(','), sys.argv[5]
status = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines())
assert all(int(status[k], 16) == 0 for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')), status
assert int(status['NoNewPrivs']) == 1
root = pathlib.Path('/sys/fs/cgroup')
assert pathlib.Path('/proc/self/cgroup').read_text() == '0::/\\n'
def limit(name):
    path = root / name
    return path.read_text().split() if path.exists() else ['max']
if 'memory' in delegated:
    assert int(limit('memory.max')[0]) == memory
else:
    assert limit('memory.max') == ['max'], limit('memory.max')
quota, *period = limit('cpu.max')
if 'cpu' in delegated:
    assert int(quota) * 10**9 == nano * int(period[0])
else:
    assert quota == 'max', quota
if mechanism == 'cgroup':
    assert int(limit('pids.max')[0]) == pids
else:
    assert limit('pids.max') == ['max'], limit('pids.max')
if mechanism == 'rlimit':
    line = next(l for l in pathlib.Path('/proc/self/limits').read_text().splitlines() if l.startswith('Max processes'))
    assert line.split()[2:4] == [str(pids), str(pids)], line
print('EFFECTIVE_HARDENING_OK')
CHECK
git --version >/dev/null && openspec --version >/dev/null && claude --version >/dev/null
'''
        cases = ((dict(), (4 << 30, 2 * 10**9, 512)),
                 (dict(CLAUDE_CONTAINER_MEMORY_LIMIT='1536m', CLAUDE_CONTAINER_CPU_LIMIT='1.5',
                       CLAUDE_CONTAINER_PIDS_LIMIT='256'), (1536 << 20, 1500000000, 256)))
        for env, expected in cases:
            for isolated in ('', str(self.state)):
                with self.subTest(env=env, isolated=isolated):
                    arguments = 'set -- ' + ' '.join(map(shlex.quote, [*map(str, expected),
                                                     ','.join(delegated) or 'none', mechanism])) + '\n'
                    result = self.shell(arguments + script, CLAUDE_CONTAINER_STATE_DIR=isolated, **env)
                    self.assert_success(result)
                    self.assertIn('EFFECTIVE_HARDENING_OK', result.stdout)
                    for budget, controller in (('memory', 'memory'), ('CPU', 'cpu')):
                        notice = f'agent {budget} budget not enforced'
                        if controller in delegated:
                            self.assertNotIn(notice, result.stderr)
                        else:
                            self.assertIn(notice, result.stderr)
                    rlimit = f'agent process budget enforced through the process rlimit ({expected[2]} tasks'
                    self.assertEqual(rlimit in result.stderr, mechanism == 'rlimit', result.stderr)
                    self.assertEqual('agent process budget not enforced' in result.stderr,
                                     mechanism == 'none', result.stderr)
        if mechanism == 'none':
            return
        # A process budget is enforced, not just reported.
        result = self.shell('python3 - <<\'CHECK\'\nimport subprocess\nchildren = []\ntry:\n'
                            '    for _ in range(200):\n        children.append(subprocess.Popen(["sleep", "30"]))\n'
                            'except (BlockingIOError, OSError):\n    print("PIDS_BUDGET_ENFORCED")\n'
                            'finally:\n    [child.kill() for child in children]\nCHECK\n',
                            CLAUDE_CONTAINER_PIDS_LIMIT='128')
        self.assert_success(result)
        self.assertIn('PIDS_BUDGET_ENFORCED', result.stdout)

    def test_process_rlimit_counts_per_container(self):
        # set-process-limits-inside-containers, design D4: on the rlimit fallback, other
        # containers of the user do not consume the session's budget. A limit applied at
        # creation would count them, and the session could not even start.
        _, mechanism = self.engine_budgets()
        if mechanism != 'rlimit':
            self.skipTest('the engine does not use the process rlimit fallback')
        start_crowd(self, self.env, 150)
        result = self.shell('python3 - <<\'CHECK\'\nimport subprocess\nchildren = []\n'
                            'def spawn(total):\n    try:\n        while len(children) < total:\n'
                            '            children.append(subprocess.Popen(["sleep", "60"]))\n'
                            '    except (BlockingIOError, OSError):\n        pass\n    return len(children)\n'
                            'first, second = spawn(100), spawn(200)\n[child.kill() for child in children]\n'
                            'print("PROCESSES", first, second)\nCHECK\n', CLAUDE_CONTAINER_PIDS_LIMIT='128')
        self.assert_success(result)
        counts = next(line.split()[1:] for line in result.stdout.splitlines() if line.startswith('PROCESSES'))
        first, second = map(int, counts)
        self.assertEqual(first, 100, result.stdout)
        # The session's own processes count as well: the shell, Python and the init process.
        self.assertTrue(115 <= second < 128, result.stdout)

    def test_session_lifetime_limit_and_early_exit(self):
        started = time.monotonic()
        result = self.shell('sleep 60\n', CLAUDE_CONTAINER_RUN_TIMEOUT='3')
        self.assertLess(time.monotonic() - started, 45)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'session lifetime limit reached (3 s); exit status {result.returncode}', result.stderr)
        self.assertNotIn(self.project.name, subprocess.run(['podman', 'ps', '--all', '--format', '{{.Names}}'],
                         env=self.env, capture_output=True, text=True).stdout.replace(' ', '-'))
        result = self.shell('exit 7\n', CLAUDE_CONTAINER_RUN_TIMEOUT='30')
        self.assertEqual(result.returncode, 7)
        self.assertNotIn('lifetime limit', result.stderr)

    def test_sensitive_workspace_refused_before_engine(self):
        result = subprocess.run([str(WRAPPER), '--container-shell'], cwd=self.host_home, env=self.env,
                                input='true\n', text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertIn('refusing sensitive workspace ' + str(self.host_home), result.stderr)
        self.assertFalse(self.state.exists())

    def test_explicit_temporary_mounts_and_lifecycle(self):
        script = '''python3 - <<'CHECK'
import errno, json, os, pathlib, shutil, stat, subprocess
for path, size in (('/tmp', 512 << 20), ('/run', 32 << 20), ('/var/tmp', 512 << 20)):
    mount = json.loads(subprocess.check_output([
        'findmnt', '--json', '--bytes', '--output', 'TARGET,FSTYPE,OPTIONS,SIZE',
        '--target', path]))['filesystems'][0]
    assert mount['target'] == path and mount['fstype'] == 'tmpfs', mount
    assert {'rw', 'nosuid', 'nodev', 'noexec'} <= set(mount['options'].split(',')), mount
    assert int(mount['size']) == size, mount
    if path == '/run':
        continue
    directory = pathlib.Path(path)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o1777
    (directory / 'ephemeral-sentinel').write_text('temporary')
    executable = directory / 'claude-test-executable'
    shutil.copy('/bin/true', executable)
    executable.chmod(0o755)
    try:
        subprocess.run([str(executable)], check=True)
    except PermissionError as error:
        assert error.errno == errno.EACCES
    else:
        raise AssertionError('execution allowed from ' + path)
print('Explicit temporary mount checks passed.')
CHECK
! touch /var/log/claude-test-write 2>/dev/null
'''
        for isolated in ('', str(self.state)):
            with self.subTest(isolated=isolated):
                env = {'CLAUDE_CONTAINER_STATE_DIR': isolated}
                self.assert_success(self.shell(script, **env))
                self.assert_success(self.shell(
                    'test ! -e /tmp/ephemeral-sentinel\n'
                    'test ! -e /var/tmp/ephemeral-sentinel\n', **env))

    def test_pseudo_terminals_and_device_masks(self):
        # Interactive tools open their own PTY: the session must allocate one,
        # while /dev/shm and /run/secrets stay empty read-only masks.
        probe = r'''import os
import pathlib
import pty
master, slave = pty.openpty()
assert os.ttyname(slave).startswith('/dev/pts/'), os.ttyname(slave)
os.close(master); os.close(slave)
for path in ('/dev/shm', '/run/secrets'):
    assert list(pathlib.Path(path).iterdir()) == [], path
    try:
        (pathlib.Path(path) / 'probe').write_text('x')
    except OSError:
        pass
    else:
        raise AssertionError(path + ' is writable')
print('pty-and-masks-ok')
'''
        result = self.shell('python3 -c ' + shlex.quote(probe) + '\n')
        self.assert_success(result)
        self.assertIn('pty-and-masks-ok', result.stdout)

    # Toolchain library

    def toolchain(self, *args, **env):
        return subprocess.run([str(WRAPPER), '--container-toolchain', *args], cwd=self.project,
                              env=self.env | env, text=True, capture_output=True, timeout=300)

    def archive_recipe(self, name, commands, **values):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for directory in (name + '-1', name + '-1/bin'):
                info = tarfile.TarInfo(directory)
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                archive.addfile(info)
            for command, output in commands.items():
                data = ('#!/bin/sh\necho ' + output + '-"$*"\n').encode()
                info = tarfile.TarInfo(name + '-1/bin/' + command)
                info.size, info.mode = len(data), 0o755
                archive.addfile(info, io.BytesIO(data))
        path = self.native / (name + '.tar.gz')
        path.write_bytes(buffer.getvalue())
        recipe = {'schema': 1, 'name': name, 'version': '1', 'default': True, 'path': ['bin'],
                  'env': {name.upper() + '_HOME': {'toolchain': ''}}, 'check': [next(iter(commands)), 'check'],
                  'source': {'archive': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'strip_components': 1}}
        recipe.update(values)
        recipe_path = self.native / (name + '.json')
        recipe_path.write_text(json.dumps(recipe))
        return recipe_path

    def test_toolchain_library_sources_environment_and_read_only_mount(self):
        library = self.host_home / '.local/share/sandbox-toolchains'
        self.assert_success(self.toolchain('add', str(self.archive_recipe('hello', {'hello': 'hello'}))))
        # A default toolchain providing node and python3 never replaces the runtime's own.
        self.assert_success(self.toolchain('add', str(self.archive_recipe(
            'shadow', {'node': 'fake-node', 'python3': 'fake-python'}, env={}))))
        failing = self.archive_recipe('broken', {'broken': 'broken'}, check=['false'], env={})
        result = self.toolchain('add', str(failing))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('toolchain check failed for broken', result.stderr)
        self.assertFalse((library / 'broken').exists())
        context = self.native / 'image-context'
        (context / 'opt/imgtool/bin').mkdir(parents=True)
        (context / 'opt/imgtool/bin/imgtool').write_text('#!/bin/sh\necho image-tool\n')
        (context / 'opt/imgtool/bin/imgtool').chmod(0o755)
        (context / 'Containerfile').write_text('FROM scratch\nCOPY opt /opt\n')
        image = 'localhost/claude-toolchain-test-' + uuid.uuid4().hex
        self.addCleanup(subprocess.run, ['podman', 'image', 'rm', '--force', '--ignore', image + ':latest'],
                        env=self.env, capture_output=True, timeout=60)
        self.assert_success(subprocess.run(['podman', 'build', '--tag', image + ':latest', str(context)],
                                           env=self.env, text=True, capture_output=True, timeout=120))
        digest = subprocess.run(['podman', 'image', 'inspect', '--format', '{{.Digest}}', image + ':latest'],
                                env=self.env, text=True, capture_output=True, timeout=60).stdout.strip()
        recipe = self.native / 'imgtool.json'
        recipe.write_text(json.dumps({'schema': 1, 'name': 'imgtool', 'version': '1', 'default': False,
                                      'source': {'image': image + '@' + digest, 'path': '/opt/imgtool'},
                                      'check': ['imgtool']}))
        self.assert_success(self.toolchain('add', str(recipe)))
        listing = self.toolchain('list')
        self.assert_success(listing)
        for name in ('hello', 'shadow', 'imgtool'):
            self.assertIn(name + '\t', listing.stdout)
        result = self.shell('''test "$(hello a)" = hello-a
test "$HELLO_HOME" = /toolchains/hello
test "$(command -v node)" = /usr/local/bin/node
test "$(command -v python3)" = /usr/bin/python3
test "$(. /toolchains/shadow/env.sh && node b)" = fake-node-b
test "$(. /toolchains/imgtool/env.sh && imgtool)" = image-tool
if command -v imgtool; then exit 9; fi
grep -q 'hello 1' /toolchains/toolchains.md
python3 -c 'import json; assert [t["name"] for t in json.load(open("/toolchains/index.json"))["toolchains"]] == ["hello", "imgtool", "shadow"]'
if touch /toolchains/new 2>/dev/null; then exit 10; fi
if rm /toolchains/hello/bin/hello 2>/dev/null; then exit 11; fi
test -x /toolchains/hello/bin/hello
echo toolchains-ok
''')
        self.assert_success(result)
        self.assertIn('toolchains-ok', result.stdout)
        self.assert_success(self.toolchain('remove', 'imgtool'))
        self.assertFalse((library / 'imgtool').exists())

    def test_toolchain_library_can_be_omitted(self):
        result = self.shell('test ! -e /toolchains\necho omitted\n', CLAUDE_CONTAINER_TOOLCHAINS='0')
        self.assert_success(result)
        self.assertIn('omitted', result.stdout)

    def test_runtime_permissions_are_measured_separately(self):
        script = '''python3 - <<'CHECK'
import json, os, pathlib, stat, tempfile
mask = os.umask(0)
os.umask(mask)
config = pathlib.Path(os.environ['CLAUDE_CONFIG_DIR'])
assert stat.S_IMODE(config.stat().st_mode) == 0o700
with tempfile.TemporaryDirectory(dir=config) as directory:
    root = pathlib.Path(directory)
    file = root / 'file'
    file.write_text('synthetic')
    child = root / 'directory'
    child.mkdir()
    file_mode = stat.S_IMODE(file.stat().st_mode)
    directory_mode = stat.S_IMODE(child.stat().st_mode)
    assert file_mode == 0o666 & ~mask
    assert directory_mode == 0o777 & ~mask
    assert file.stat().st_uid == os.getuid()
    print(json.dumps({'umask': oct(mask), 'file': oct(file_mode),
                      'directory': oct(directory_mode)}))
CHECK
'''
        for isolated in ('', str(self.state)):
            for mask in (0o022, 0o002):
                with self.subTest(isolated=isolated, host_umask=oct(mask)):
                    result = self.shell(script, caller_umask=mask,
                                        CLAUDE_CONTAINER_STATE_DIR=isolated)
                    self.assert_success(result)
                    source = self.state if isolated else self.host_home / '.claude'
                    self.assertEqual(source.stat().st_mode & 0o777, 0o700)
                    print(f'Runtime permissions (isolated={bool(isolated)}, '
                          f'host umask={oct(mask)}): {result.stdout.strip()}', flush=True)

    def test_build_context_excludes_sensitive_and_unrelated_files(self):
        context = self.base / 'synthetic-build-context'
        context.mkdir()
        shutil.copyfile(ROOT / '.containerignore', context / '.containerignore')
        for relative in ('.git/config', '.claude/settings.json', '.test-state/token',
                         'custom-private-home/.claude/token', '.env',
                         '__pycache__/module.pyc', '.agents/skills/private.md',
                         'nested/unrelated.txt', 'README.md', 'network/policies/secret.json',
                         'network/proxy.py'):
            path = context / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic excluded sentinel')
        (context / 'network/relay.py').write_text('explicit runtime input')
        (context / 'network/mux.py').write_text('explicit transport input')
        self.build_fixture(context, '''COPY . /claude-build-context/
RUN test -f /claude-build-context/Containerfile \\
    && test -f /claude-build-context/.containerignore \\
    && test -f /claude-build-context/network/relay.py \\
    && test -z "$(find /claude-build-context -mindepth 1 ! -path /claude-build-context/Containerfile ! -path /claude-build-context/.containerignore ! -path /claude-build-context/network ! -path /claude-build-context/network/relay.py ! -path /claude-build-context/network/mux.py -print -quit)"
''')

    def test_image_smoke_both_state_modes(self):
        script = (ROOT / 'tests/image-smoke.sh').read_text()
        for isolated in ('', str(self.state)):
            result = self.shell(script, CLAUDE_CONTAINER_STATE_DIR=isolated)
            self.assert_success(result)
            self.assertIn('Image smoke checks passed.', result.stdout)

    def test_mount_boundary_identity_and_persistence(self):
        sentinel = self.base / 'outside-sentinel'
        sentinel.write_text('outside')
        for isolated in ('', str(self.state)):
            with self.subTest(isolated=isolated):
                script = f'''test "$PWD" = {shlex.quote(str(self.project))}
                test ! -e {shlex.quote(str(sentinel))}
                ! touch /usr/claude-test-write 2>/dev/null
                printf owned > owned-file
                printf persistent > "$CLAUDE_CONFIG_DIR/persistent"
                printf temporary > /tmp/ephemeral-sentinel
                test ! -S /run/podman/podman.sock
                test -z "${{CONTAINER_HOST:-}}"
                '''
                self.assert_success(self.shell(script, CLAUDE_CONTAINER_STATE_DIR=isolated))
                self.assertEqual((self.project / 'owned-file').stat().st_uid, os.getuid())
                source = self.state / '.claude' if isolated else self.host_home / '.claude'
                self.assertEqual((source / 'persistent').read_text(), 'persistent')
                self.assert_success(self.shell('test "$(cat "$CLAUDE_CONFIG_DIR/persistent")" = persistent\n'
                                               'test ! -e /tmp/ephemeral-sentinel\n',
                                               CLAUDE_CONTAINER_STATE_DIR=isolated))
                self.assertEqual(source.stat().st_mode & 0o777, 0o700)

    def test_isolated_profiles_do_not_import_or_merge(self):
        shared = self.host_home / '.claude'
        shared.mkdir(mode=0o700)
        (shared / 'host-sentinel').write_text('synthetic')
        self.assert_success(self.shell('test ! -e "$CLAUDE_CONFIG_DIR/host-sentinel"\n'
                                       'printf isolated > "$HOME/isolated-marker"\n'))
        self.assert_success(self.shell('test -e "$CLAUDE_CONFIG_DIR/host-sentinel"\n'
                                       'test ! -e "$HOME/isolated-marker"\n', CLAUDE_CONTAINER_STATE_DIR=''))
        self.assertEqual((self.state / 'isolated-marker').read_text(), 'isolated')
        self.assertEqual((shared / 'host-sentinel').read_text(), 'synthetic')

    def test_real_worktree_and_outside_metadata(self):
        repo = self.base / 'main'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True, env=self.env)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                        'commit', '--allow-empty', '-qm', 'initial'], check=True, env=self.env)
        worktree = self.base / 'worktree'
        subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-qb', 'test', str(worktree)],
                       check=True, env=self.env)
        self.project = worktree
        self.assert_success(self.shell('git status --porcelain\ngit worktree list\n'
                                       'printf sibling > ../sibling-file\n', '--container-git-worktree'))
        self.assertEqual((self.base / 'sibling-file').read_text(), 'sibling')
        self.assertNotEqual(self.shell('git status --porcelain\n').returncode, 0)

    def test_ca_mount_and_environment(self):
        bundle = self.native / 'synthetic-ca.pem'
        bundle.write_text('synthetic bundle, no TLS request')
        for isolated in ('', str(self.state)):
            self.assert_success(self.shell('test ! -e /claude-home/ca/bundle.pem\n'
                                           'test -z "${SSL_CERT_FILE:-}${REQUESTS_CA_BUNDLE:-}${CURL_CA_BUNDLE:-}${NODE_EXTRA_CA_CERTS:-}"\n',
                                           CLAUDE_CONTAINER_STATE_DIR=isolated))
            if isolated:
                # Keep the synthetic mount parent caller-owned for cleanup;
                # an engine-created parent can belong to a mapped root UID.
                (self.state / 'ca').mkdir(mode=0o700, exist_ok=True)
            script = '''for variable in SSL_CERT_FILE REQUESTS_CA_BUNDLE CURL_CA_BUNDLE NODE_EXTRA_CA_CERTS; do
                test "${!variable}" = /claude-home/ca/bundle.pem
            done
            test "$(cat /claude-home/ca/bundle.pem)" = 'synthetic bundle, no TLS request'
            ! printf denied >> /claude-home/ca/bundle.pem
            '''
            self.assert_success(self.shell(script, CLAUDE_CONTAINER_STATE_DIR=isolated,
                                           CLAUDE_CONTAINER_TRUST_HOST_CA='1',
                                           CLAUDE_CONTAINER_CA_BUNDLE=str(bundle)))
        self.assertEqual(bundle.read_text(), 'synthetic bundle, no TLS request')

    def test_exit_code_and_concurrent_sessions(self):
        for status in (23, 125):
            self.assertEqual(self.shell(f'exit {status}\n').returncode, status)
        first = subprocess.Popen([str(WRAPPER), '--container-shell'], cwd=self.project,
                                 env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        try:
            first.stdin.write('echo ready\nread -r finish\n')
            first.stdin.flush()
            self.assertEqual(first.stdout.readline().strip(), 'ready')
            self.assert_success(self.shell('printf second\n'))
            self.assertIsNone(first.poll())
            first.stdin.write('finish\n')
            first.stdin.close()
            self.assertEqual(first.wait(timeout=30), 0)
        finally:
            if first.poll() is None:
                first.terminate()
                first.wait(timeout=15)
            first.stdout.close()
            first.stderr.close()
            if not first.stdin.closed:
                first.stdin.close()

    def start_ready_shell(self, script, isolated):
        proc = subprocess.Popen([str(WRAPPER), '--container-shell'], cwd=self.project,
                                env=self.env | {'CLAUDE_CONTAINER_STATE_DIR': isolated},
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        identity = []
        def finish():
            if proc.poll() is None:
                proc.terminate()
            if proc.stdin is not None and proc.stdin.closed:
                proc.stdin = None
            try:
                proc.communicate(timeout=25)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=5)
            if identity:
                result = subprocess.run(['podman', 'rm', '--force', '--time', '0', '--ignore', identity[0]],
                                        env=self.env, text=True, capture_output=True, timeout=10)
                self.assert_success(result)
        self.addCleanup(finish)
        proc.stdin.write(script)
        proc.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            self.assertTrue(selector.select(timeout=15), 'shell did not announce readiness')
        ready = proc.stdout.readline().strip().split()
        self.assertEqual(ready[:1], ['ready'])
        result = subprocess.run(['podman', 'inspect', '--format', '{{.Id}}', ready[1]],
                                env=self.env, text=True, capture_output=True, timeout=10)
        self.assert_success(result)
        identity.append(result.stdout.strip())
        return proc, identity[0]

    def test_bounded_signal_shutdown_preserves_other_session(self):
        for isolated in ('', str(self.state)):
            other, other_id = self.start_ready_shell(
                'printf "ready %s\\n" "$HOSTNAME"\nread -r finish\n', isolated)
            for ignore in (False, True):
                for name, status in (('TERM', 143), ('INT', 130), ('HUP', 129)):
                    with self.subTest(isolated=isolated, ignore=ignore, signal=name):
                        handler = "trap '' TERM INT HUP\n" if ignore else "trap 'exit 0' TERM INT HUP\n"
                        proc, container = self.start_ready_shell(handler +
                            'printf "ready %s\\n" "$HOSTNAME"\n'
                            'while :; do read -r -t 0.2 ignored || true; done\n', isolated)
                        started = time.monotonic()
                        proc.send_signal(getattr(signal, 'SIG' + name))
                        stdout, stderr = proc.communicate(timeout=25)
                        self.assertEqual(proc.returncode, status, stdout + stderr)
                        self.assertLess(time.monotonic() - started, 22)
                        exists = subprocess.run(['podman', 'container', 'exists', container],
                                                env=self.env, capture_output=True, timeout=10)
                        self.assertEqual(exists.returncode, 1, stdout + stderr)
                        self.assertIsNone(other.poll())
                        running = subprocess.run(['podman', 'inspect', '--format', '{{.State.Running}}', other_id],
                                                 env=self.env, text=True, capture_output=True, timeout=10)
                        self.assert_success(running)
                        self.assertEqual(running.stdout.strip(), 'true')
            other.stdin.write('finish\n')
            other.stdin.close()
            self.assertEqual(other.wait(timeout=25), 0)

    def test_native_help_and_version_without_tty(self):
        for isolated in ('', str(self.state)):
            for yolo in ('0', '1'):
                for option in ('--help', '--version'):
                    result = subprocess.run([str(WRAPPER), option], cwd=self.project,
                                            env=self.env | {'CLAUDE_CONTAINER_STATE_DIR': isolated,
                                                            'CLAUDE_YOLO': yolo},
                                            stdin=subprocess.DEVNULL, text=True,
                                            capture_output=True, timeout=60)
                    self.assert_success(result)


@unittest.skipUnless(ENABLED, 'set SANDBOX_RUNTIME_TESTS=1 to use a real rootless engine')
class SessionEngineTests(unittest.TestCase):
    """The session container engine on a real rootless engine (session-container-engine)."""

    @classmethod
    def setUpClass(cls):
        for image in (ENGINE_IMAGE, SAMPLE):
            if subprocess.run(['podman', 'image', 'exists', image], capture_output=True).returncode:
                raise unittest.SkipTest('prepare ' + image + ' in the engine first')
        cls.sample_id = subprocess.run(['podman', 'image', 'inspect', '--format', '{{.Id}}', SAMPLE],
                                       capture_output=True, text=True, check=True).stdout.strip()

    def setUp(self):
        workspace_root = ROOT / '.test-state'
        workspace_root.mkdir(exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix='engine-', dir=workspace_root))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.project = self.base / 'project'
        self.project.mkdir()
        # Bind sources (the session's hosts file, the store) must exist at the same
        # path for the engine service: the disposable runner supplies a native volume.
        self.native = Path(tempfile.mkdtemp(prefix='sandbox-engine-', dir=os.environ.get('SANDBOX_TEST_STATE_ROOT')))
        self.addCleanup(shutil.rmtree, self.native, True)
        self.host_home = self.native / 'home'
        self.host_home.mkdir(mode=0o700)
        self.env = {'PATH': os.environ['PATH'], 'HOME': str(self.host_home), 'TMPDIR': str(self.native),
                    'CLAUDE_CONTAINER_NETWORK': 'unrestricted', 'CLAUDE_CONTAINER_MAINTENANCE': '1',
                    'CLAUDE_CONTAINER_IMAGE': IMAGE, 'CLAUDE_CONTAINER_ENGINE_IMAGE': ENGINE_IMAGE,
                    'CLAUDE_CONTAINER_STATE_DIR': str(self.native / 'state')}
        if os.environ.get('CONTAINER_HOST'):
            self.env['CONTAINER_HOST'] = os.environ['CONTAINER_HOST']
        self.add_image('sample', 'localhost/sandbox-test-sample:1')

    def toolchain(self, *args):
        # Operator recipes stay outside the directory the command runs from.
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'setup/toolchains.py'), *args], env=self.env,
                                cwd=self.project, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def add_image(self, name, reference):
        recipe = self.native / (name + '.json')
        recipe.write_text(json.dumps({
            'schema': 2, 'name': name, 'version': '1', 'default': False,
            'images': [{'local': 'sha256:' + self.sample_id.removeprefix('sha256:'), 'name': reference}],
            'check': ['podman', 'run', '--rm', '--network=none', reference, 'true']}))
        self.toolchain('add', str(recipe))
        self.addCleanup(subprocess.run, [sys.executable, '-I', str(ROOT / 'setup/toolchains.py'), 'remove', name],
                        env=self.env, cwd=self.project, capture_output=True, timeout=300)

    def shell(self, script, timeout=180):
        return subprocess.run([str(WRAPPER), '--container-shell'], cwd=self.project, env=self.env,
                              input='set -Eeuo pipefail\n' + script, text=True, capture_output=True, timeout=timeout)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def engines(self):
        listing = subprocess.run(['podman', 'ps', '--all', '--filter', 'label=sandbox-engine.owner',
                                  '--format', '{{.Names}}'], capture_output=True, text=True, check=True).stdout
        return [name for name in listing.split() if name.startswith('project-engine-')]

    def test_session_engine_runs_library_images_inside_the_session_boundaries(self):
        # session-container-engine: Loopback endpoint / Library images run offline from a read-only store /
        # Nested containers have private process and host-name views / Engine mounts only the workspace /
        # Engine carries no secrets / Session-owned engine storage.
        result = self.shell(r"""
test "$CONTAINER_HOST" = tcp://127.0.0.1:2375
test "$DOCKER_HOST" = tcp://127.0.0.1:2375
test "$(podman info --format '{{.Host.Security.Rootless}}')" = true
view=$(podman run --rm --network=none localhost/sandbox-test-sample:1 sh -c \
  'echo "$(cat /proc/1/comm) $(ls /proc | grep -c "^[0-9]") $(cat /proc/sys/kernel/hostname) $(ls -A /run/secrets 2>/dev/null | wc -l)"')
set -- $view
test "$1" = sh && test "$2" -le 4 && test "$3" != "$(cat /proc/sys/kernel/hostname)" && test "$4" = 0
echo "NESTED_VIEW $view"
podman run --rm --network=none -v "$PWD:$PWD" -w "$PWD" localhost/sandbox-test-sample:1 sh -c 'echo nested > nested-file'
test "$(stat -c %u nested-file)" = "$(id -u)"
podman run --rm --network=none -v /etc:/outside:ro localhost/sandbox-test-sample:1 grep -q k8s-file /outside/containers/containers.conf
! podman rmi localhost/sandbox-test-sample:1
podman image exists localhost/sandbox-test-sample:1
# Builds and the extraction of new layers (pull, load) chroot (design D4).
mkdir .build-context && printf 'FROM localhost/sandbox-test-sample:1\nRUN echo built > /built\n' > .build-context/Containerfile
podman build --quiet --pull=never --tag localhost/sandbox-test-built:1 .build-context >/dev/null
test "$(podman run --rm --network=none localhost/sandbox-test-built:1 cat /built)" = built
podman save --quiet --output .built.tar localhost/sandbox-test-built:1
podman rmi localhost/sandbox-test-built:1 >/dev/null
podman load --quiet --input .built.tar >/dev/null
podman image exists localhost/sandbox-test-built:1
rm -rf .build-context .built.tar
echo ENGINE_SESSION_OK
""")
        self.assert_success(result)
        self.assertIn('ENGINE_SESSION_OK', result.stdout)
        self.assertEqual((self.project / 'nested-file').stat().st_uid, os.getuid())
        self.assertEqual(self.engines(), [])

    def test_engine_process_rlimit_counts_per_container(self):
        # set-process-limits-inside-containers, design D4: on the rlimit fallback, an engine
        # session starts and runs a nested container beside a container holding more
        # processes than its budget. A limit applied at creation would count that container.
        if engine_budgets(self.env)[1] != 'rlimit':
            self.skipTest('the engine does not use the process rlimit fallback')
        start_crowd(self, self.env, 520)
        result = self.shell('test "$(grep "^Max processes" /proc/self/limits | tr -s " " | cut -d" " -f3,4)" = "512 512"\n'
                            'podman run --rm --network=none localhost/sandbox-test-sample:1 true\n'
                            'echo NESTED_BESIDE_CROWD_OK\n')
        self.assert_success(result)
        self.assertIn('NESTED_BESIDE_CROWD_OK', result.stdout)
        self.assertEqual(self.engines(), [])

    def test_no_engine_without_library_images(self):
        # session-container-engine: Library without images.
        self.toolchain('remove', 'sample')
        result = self.shell('test -z "${CONTAINER_HOST+x}${DOCKER_HOST+x}"\necho NO_ENGINE_OK\n')
        self.assert_success(result)
        self.assertNotIn('container engine', result.stderr)

    def test_live_image_and_isolated_concurrent_sessions(self):
        # session-container-engine: Image added during a session / Two sessions.
        marker = self.project / '.image-added'
        first = subprocess.Popen([str(WRAPPER), '--container-shell'], cwd=self.project, env=self.env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: first.poll() is None and first.kill())
        first.stdin.write(r"""set -Eeuo pipefail
podman run -d --name first-session-marker --network=none localhost/sandbox-test-sample:1 sleep 120 >/dev/null
echo FIRST_READY
while [ ! -e .image-added ]; do sleep 0.2; done
podman run --rm --network=none localhost/sandbox-test-live:1 true
echo LIVE_IMAGE_OK
podman rm -f -t 0 first-session-marker >/dev/null
""")
        first.stdin.close()
        first.stdin = None
        self.assertEqual(first.stdout.readline().strip(), 'FIRST_READY', first.stderr.read() if first.poll() else '')
        second = self.shell('! podman container exists first-session-marker\n'
                            'test -z "$(podman ps --all --quiet)"\necho SECOND_ISOLATED\n')
        self.assert_success(second)
        self.add_image('live', 'localhost/sandbox-test-live:1')
        marker.touch()
        stdout, stderr = first.communicate(timeout=180)
        self.assertEqual(first.returncode, 0, stdout + stderr)
        self.assertIn('LIVE_IMAGE_OK', stdout)
        self.assertEqual(self.engines(), [])


if __name__ == '__main__':
    unittest.main()
