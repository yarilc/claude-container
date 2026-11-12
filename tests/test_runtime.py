"""Opt-in checks against a real rootless engine; synthetic state only."""
import os
from pathlib import Path
import shlex
import shutil
import selectors
import signal
import subprocess
import tempfile
import time
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'claude-container.sh'
IMAGE = os.environ.get('CLAUDE_CONTAINER_IMAGE', 'localhost/claude-code:latest')
ENABLED = os.environ.get('SANDBOX_RUNTIME_TESTS') == '1'


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

    def test_delegation_clears_image_environment_defaults(self):
        context = self.base / 'environment-context'
        context.mkdir()
        image = self.build_fixture(context, 'ENV CONTAINER_HOST=unix:///synthetic/default.sock\n')
        for isolated in ('', str(self.state)):
            for service in ('0', '1'):
                with self.subTest(isolated=isolated, service=service):
                    script = ('test "${CONTAINER_HOST+x}" != x\n'
                              'test ! -S /run/podman/podman.sock\n') if service == '0' else (
                              'test "$CONTAINER_HOST" = unix:///run/podman/podman.sock\n'
                              'test -S /run/podman/podman.sock\n'
                              "test \"$(podman info --format '{{.Host.Security.Rootless}}')\" = true\n")
                    self.assert_success(self.shell(script, CLAUDE_CONTAINER_IMAGE=image,
                                                   CLAUDE_CONTAINER_STATE_DIR=isolated,
                                                   CLAUDE_CONTAINER_PODMAN=service))

    def test_effective_hardening_and_budgets_in_every_unrestricted_variant(self):
        script = '''python3 - "$@" <<'CHECK'
import pathlib, sys
memory, nano, pids = map(int, sys.argv[1:4])
status = dict(line.split(':', 1) for line in pathlib.Path('/proc/self/status').read_text().splitlines())
assert all(int(status[k], 16) == 0 for k in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')), status
assert int(status['NoNewPrivs']) == 1
root = pathlib.Path('/sys/fs/cgroup')
assert pathlib.Path('/proc/self/cgroup').read_text() == '0::/\\n'
assert int((root / 'memory.max').read_text()) == memory
assert int((root / 'pids.max').read_text()) == pids
quota, period = (root / 'cpu.max').read_text().split()
assert int(quota) * 10**9 == nano * int(period)
print('EFFECTIVE_HARDENING_OK')
CHECK
git --version >/dev/null && openspec --version >/dev/null && claude --version >/dev/null
'''
        cases = ((dict(), (4 << 30, 2 * 10**9, 512)),
                 (dict(CLAUDE_CONTAINER_MEMORY_LIMIT='1536m', CLAUDE_CONTAINER_CPU_LIMIT='1.5',
                       CLAUDE_CONTAINER_PIDS_LIMIT='256'), (1536 << 20, 1500000000, 256)))
        for env, expected in cases:
            for isolated in ('', str(self.state)):
                for service in ('0', '1'):
                    with self.subTest(env=env, isolated=isolated, service=service):
                        arguments = 'set -- ' + ' '.join(map(str, expected)) + '\n'
                        result = self.shell(arguments + script, CLAUDE_CONTAINER_STATE_DIR=isolated,
                                            CLAUDE_CONTAINER_PODMAN=service, **env)
                        self.assert_success(result)
                        self.assertIn('EFFECTIVE_HARDENING_OK', result.stdout)
        # Delegated children still work without capabilities in the agent.
        result = self.shell(f'podman run --rm --pull=never --entrypoint true {shlex.quote(IMAGE)}\n'
                            'echo DELEGATED_CHILD_OK\n', CLAUDE_CONTAINER_PODMAN='1')
        self.assert_success(result)
        self.assertIn('DELEGATED_CHILD_OK', result.stdout)
        # A process budget is enforced, not just reported.
        result = self.shell('python3 - <<\'CHECK\'\nimport subprocess\nchildren = []\ntry:\n'
                            '    for _ in range(80):\n        children.append(subprocess.Popen(["sleep", "30"]))\n'
                            'except (BlockingIOError, OSError):\n    print("PIDS_BUDGET_ENFORCED")\n'
                            'finally:\n    [child.kill() for child in children]\nCHECK\n',
                            CLAUDE_CONTAINER_PIDS_LIMIT='32')
        self.assert_success(result)
        self.assertIn('PIDS_BUDGET_ENFORCED', result.stdout)

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
for path, size in (('/tmp', 256 << 20), ('/run', 16 << 20), ('/var/tmp', 256 << 20)):
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
            for service in ('0', '1'):
                with self.subTest(isolated=isolated, service=service):
                    env = {'CLAUDE_CONTAINER_STATE_DIR': isolated,
                           'CLAUDE_CONTAINER_PODMAN': service}
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

    def test_child_container_absolute_bind(self):
        script = '''test -S /run/podman/podman.sock
        podman run --rm --read-only --userns=keep-id --user "$(id -u):$(id -g)" \\
          --volume "$PWD:$PWD:rw" --workdir "$PWD" --entrypoint /bin/sh \\
          ''' + shlex.quote(IMAGE) + ''' -ec 'printf child > child-file'
        test "$(cat child-file)" = child
        '''
        for isolated in ('', str(self.state)):
            self.assert_success(self.shell(script, CLAUDE_CONTAINER_PODMAN='1',
                                           CLAUDE_CONTAINER_STATE_DIR=isolated))
            self.assertEqual((self.project / 'child-file').stat().st_uid, os.getuid())

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
                for service in ('0', '1'):
                    for option in ('--help', '--version'):
                        result = subprocess.run([str(WRAPPER), option], cwd=self.project,
                                                env=self.env | {'CLAUDE_CONTAINER_STATE_DIR': isolated,
                                                                'CLAUDE_YOLO': yolo,
                                                                'CLAUDE_CONTAINER_PODMAN': service},
                                                stdin=subprocess.DEVNULL, text=True,
                                                capture_output=True, timeout=60)
                        self.assert_success(result)


if __name__ == '__main__':
    unittest.main()
