"""Behavior checks for the wrapper without an engine or Claude credentials."""
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'claude-container.sh'
FAKE = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time, signal
args = sys.argv[1:]
log = pathlib.Path(os.environ['FAKE_LOG'])
if os.environ.get('FAKE_UMASK_LOG'):
    mask = os.umask(0)
    os.umask(mask)
    with pathlib.Path(os.environ['FAKE_UMASK_LOG']).open('a') as f:
        f.write(json.dumps([args[0], mask]) + '\n')
with log.open('a') as f:
    f.write(json.dumps(args) + '\n')
if args[:2] == ['--remote', '--url']:
    sys.exit(int(os.environ.get('FAKE_SOCKET_STATUS', '0'))) if os.environ.get('FAKE_SOCKET_STATUS') else None
    print(os.environ.get('FAKE_SOCKET_ROOTLESS', 'true') + ' ' + os.environ.get('FAKE_HOST_SOCKET', '/host/podman.sock'))
elif args[0] == 'info':
    sys.exit(int(os.environ.get('FAKE_INFO_STATUS', '0'))) if os.environ.get('FAKE_INFO_STATUS') else None
    print(os.environ.get('FAKE_INFO', 'true linux false'))
elif args[:2] == ['image', 'exists']:
    sys.exit(int(os.environ.get('FAKE_IMAGE_STATUS', '0')))
elif args[0] == 'build':
    sys.exit(int(os.environ.get('FAKE_BUILD_STATUS', '0')))
elif args[0] == 'ps':
    print(os.environ.get('FAKE_NAMES', ''))
elif args[0] == 'create':
    collision = pathlib.Path(str(log) + '.collision')
    if os.environ.get('FAKE_COLLISION') and (not collision.exists() or os.environ.get('FAKE_ALWAYS_COLLIDE')):
        collision.touch()
        sys.exit(125)
    if os.environ.get('FAKE_CREATE_FAILURE'):
        print('create failed', file=sys.stderr)
        sys.exit(125)
    print('owned-test-container-id')
elif args[:2] == ['container', 'exists']:
    sys.exit(0 if os.environ.get('FAKE_COLLISION') else 1)
elif args[0] == 'kill':
    pid = pathlib.Path(str(log) + '.pid')
    if pid.exists():
        os.kill(int(pid.read_text()), signal.SIGTERM)
elif args[0] == 'start':
    if os.environ.get('FAKE_WAIT'):
        pathlib.Path(str(log) + '.pid').write_text(str(os.getpid()))
        pathlib.Path(str(log) + '.started').touch()
        time.sleep(20)
    if not os.environ.get('FAKE_NO_STDIN'):
        print('stdin:' + sys.stdin.read())
    sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
'''


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='claude-wrapper-', dir=os.environ.get('CLAUDE_TEST_TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        podman = self.bin / 'podman'
        podman.write_text(FAKE)
        podman.chmod(0o755)
        self.project = self.base / 'parent with spaces' / 'my project'
        self.project.mkdir(parents=True)
        self.log = self.base / 'calls.jsonl'
        self.state = self.base / 'state'
        self.env = {'PATH': os.environ['PATH']}
        self.env['HOME'] = str(self.base / 'host-home')
        self.env.pop('CLAUDE_CONFIG_DIR', None)
        self.env.update(PATH=str(self.bin) + ':' + self.env['PATH'],
                        FAKE_LOG=str(self.log),
                        CLAUDE_CONTAINER_STATE_DIR=str(self.state))
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket_path = self.base / 'podman.sock'
        self.socket.bind(str(self.socket_path))
        self.addCleanup(self.socket.close)
        self.env['CLAUDE_CONTAINER_PODMAN_SOCKET'] = str(self.socket_path)

    def run_wrapper(self, *args, cwd=None, caller_umask=-1, **env):
        return subprocess.run([str(WRAPPER), *args], cwd=cwd or self.project,
                              env=self.env | env, input='input payload',
                              text=True, capture_output=True, timeout=10, umask=caller_umask)

    def calls(self):
        return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []

    def create(self):
        return next(c for c in self.calls() if c[0] == 'create')

    def test_help_without_podman_or_side_effects(self):
        help_bin = self.base / 'help-bin'
        help_bin.mkdir()
        (help_bin / 'cat').symlink_to('/bin/cat')
        result = subprocess.run(
            ['/bin/bash', str(WRAPPER), '--container-help'],
            env=self.env | {'PATH': str(help_bin), 'CLAUDE_YOLO': 'invalid'},
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('beyond the workspace', result.stdout)
        self.assertFalse(self.calls())
        self.assertFalse(self.state.exists())

    def test_argument_forwarding_and_defaults(self):
        result = self.run_wrapper('-p', 'hello world', '', '--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.create()[-5:], ['localhost/claude-code:latest', '-p', 'hello world', '', '--help'])
        self.assertNotIn('--tty', self.create())
        self.assertNotIn('--dangerously-skip-permissions', self.create())
        self.assertIn('--unsetenv', self.create())
        self.assertEqual(self.create()[self.create().index('--unsetenv') + 1], 'CONTAINER_HOST')
        self.assertIn('stdin:input payload', result.stdout)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_four_independent_permission_combinations(self):
        for yolo in ('0', '1'):
            for service in ('0', '1'):
                with self.subTest(yolo=yolo, service=service):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper('-p', 'test', CLAUDE_YOLO=yolo,
                                              CLAUDE_CONTAINER_PODMAN=service)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual('--dangerously-skip-permissions' in self.create(), yolo == '1')
                    self.assertEqual('CONTAINER_HOST=unix:///run/podman/podman.sock' in self.create(), service == '1')
                    self.assertNotIn('--privileged', self.create())
                    self.assertFalse(any('label=disable' in a for a in self.create()))

    def test_boolean_forms_and_invalid_values(self):
        for value in ('1', 'true', 'TrUe', 'yes', 'YES', '', '0', 'false', 'FALSE', 'no', 'NO'):
            self.assertEqual(self.run_wrapper(CLAUDE_YOLO=value).returncode, 0)
        for variable in ('CLAUDE_YOLO', 'CLAUDE_CONTAINER_TRUST_HOST_CA'):
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(**{variable: 'maybe'})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(variable, result.stderr)
            self.assertFalse(self.calls())

    def test_shell_does_not_receive_yolo_or_cli_arguments(self):
        result = self.run_wrapper('--container-shell', '-p', 'ignored', CLAUDE_YOLO='1')
        self.assertEqual(result.returncode, 0)
        create = self.create()
        self.assertEqual(create[-3:], ['--entrypoint', '/bin/bash', 'localhost/claude-code:latest'])
        self.assertNotIn('--dangerously-skip-permissions', create)

    def test_workspace_worktree_and_symlink(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.project, target_is_directory=True)
        self.assertEqual(self.run_wrapper(cwd=alias).returncode, 0)
        self.assertIn(f'{self.project}:{self.project}:rw', self.create())
        self.assertIn(str(self.project), self.create())
        self.log.unlink()
        self.assertEqual(self.run_wrapper('--container-git-worktree', cwd=alias).returncode, 0)
        self.assertIn(f'{self.project.parent}:{self.project.parent}:rw', self.create())
        self.assertIn(str(self.project), self.create())
        self.assertNotIn(f'{self.project}:{self.project}:rw', self.create())

    def test_read_only_identity_and_no_extra_host_mounts(self):
        self.assertEqual(self.run_wrapper().returncode, 0)
        create = self.create()
        for option in ('--read-only', '--userns=keep-id', f'{os.getuid()}:{os.getgid()}'):
            self.assertIn(option, create)
        volumes = [create[i+1] for i, a in enumerate(create) if a == '--volume']
        self.assertEqual(len(volumes), 2)
        self.assertIn(f'{self.state}:/claude-home:rw', volumes)

    def test_insecure_existing_state_rejected(self):
        self.state.mkdir(mode=0o777)
        self.state.chmod(0o777)
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must be private', result.stderr)
        self.assertFalse(any(c[0] == 'create' for c in self.calls()))

    def test_tty_allocated_for_terminal(self):
        import pty
        master, slave = pty.openpty()
        proc = subprocess.Popen([str(WRAPPER), '--version'], cwd=self.project,
                                env=self.env | {'FAKE_NO_STDIN': '1'},
                                stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        try:
            self.assertEqual(proc.wait(timeout=10), 0)
            self.assertIn('--tty', self.create())
        finally:
            os.close(master)
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)

    def test_socket_only_required_when_enabled(self):
        missing = str(self.base / 'missing.sock')
        self.assertEqual(self.run_wrapper(CLAUDE_CONTAINER_PODMAN_SOCKET=missing).returncode, 0)
        self.log.unlink()
        result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1', CLAUDE_CONTAINER_PODMAN_SOCKET=missing)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('socket', result.stderr)
        self.assertFalse(any(c[0] in ('build', 'create') for c in self.calls()))

    def test_socket_engine_must_be_rootless(self):
        result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1', FAKE_SOCKET_ROOTLESS='false')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rootless', result.stderr)

    def test_rootful_and_remote_rejected_local_unix_accepted(self):
        cases = ({'FAKE_INFO': 'false linux false'},
                 {'CONTAINER_HOST': 'ssh://other-host'},
                 {'CONTAINER_HOST': 'tcp://127.0.0.1:1234'},
                 {'CONTAINER_CONNECTION': 'machine'},
                 {'FAKE_INFO': 'true linux true'})
        for env in cases:
            self.assertNotEqual(self.run_wrapper(**env).returncode, 0)
        self.assertEqual(self.run_wrapper(FAKE_INFO='true linux true', CONTAINER_HOST='unix:///run/podman/podman.sock').returncode, 0)

    def test_build_location_refresh_and_missing_image(self):
        self.assertEqual(self.run_wrapper('--container-build').returncode, 0)
        build = next(c for c in self.calls() if c[0] == 'build')
        self.assertEqual(build[-3:], ['--file', str(ROOT / 'Containerfile'), str(ROOT)])
        self.log.unlink()
        self.assertEqual(self.run_wrapper(FAKE_IMAGE_STATUS='1').returncode, 0)
        self.assertTrue(any(c[0] == 'build' for c in self.calls()))

    def test_build_and_image_inspection_errors(self):
        self.assertEqual(self.run_wrapper('--container-build', FAKE_BUILD_STATUS='17').returncode, 17)
        self.assertNotEqual(self.run_wrapper(FAKE_IMAGE_STATUS='125').returncode, 0)
        self.assertFalse(any(c[0] == 'create' for c in self.calls()))

    def test_exit_status_and_owned_cleanup(self):
        for status in ('7', '125'):
            result = self.run_wrapper(FAKE_EXIT=status)
            self.assertEqual(result.returncode, int(status))
            self.assertIn(['rm', '--force', '--ignore', 'owned-test-container-id'], self.calls())

    def test_existing_names_and_collision_retry(self):
        result = self.run_wrapper(FAKE_NAMES='my-project-2\nmy-project-09\nother-50', FAKE_COLLISION='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        creates = [c for c in self.calls() if c[0] == 'create']
        self.assertEqual(creates[0][2], 'my-project-10')
        self.assertEqual(creates[1][2], 'my-project-11')

    def test_create_failure_preserved_without_cleanup_of_other_containers(self):
        result = self.run_wrapper(FAKE_CREATE_FAILURE='1')
        self.assertEqual(result.returncode, 125)
        self.assertIn('create failed', result.stderr)
        self.assertFalse(any(c[0] in ('rm', 'start') for c in self.calls()))

    def test_term_forwarding(self):
        proc = subprocess.Popen([str(WRAPPER)], cwd=self.project, env=self.env | {'FAKE_WAIT': '1'},
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        import time
        for _ in range(100):
            if Path(str(self.log) + '.started').exists():
                break
            time.sleep(0.02)
        proc.terminate()
        proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 143)
        self.assertTrue(any(c[:3] == ['kill', '--signal', 'TERM'] for c in self.calls()))

    def test_launch_verification_fails_before_image_operations(self):
        for result in ('', 'false linux false', 'true darwin false', 'true linux',
                       'true linux maybe', 'true linux false extra', 'true linux false\nextra'):
            with self.subTest(result=result):
                self.log.unlink(missing_ok=True)
                run = self.run_wrapper('--container-build', FAKE_INFO=result)
                self.assertNotEqual(run.returncode, 0)
                self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))
        self.assertNotEqual(self.run_wrapper(FAKE_INFO_STATUS='125').returncode, 0)

    def test_pathless_or_relative_unix_launch_endpoint_rejected_before_query(self):
        for endpoint in ('unix://', 'unix:///', 'unix://////', 'unix://relative/socket'):
            for delegation in ('0', '1'):
                for override in ('', str(self.socket_path)):
                    with self.subTest(endpoint=endpoint, delegation=delegation, override=override):
                        self.log.unlink(missing_ok=True)
                        result = self.run_wrapper('--container-build', CONTAINER_HOST=endpoint,
                                                  CLAUDE_CONTAINER_PODMAN=delegation,
                                                  CLAUDE_CONTAINER_PODMAN_SOCKET=override)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('absolute Unix socket path', result.stderr)
                        self.assertEqual(self.calls(), [])

    def test_help_with_pathless_launch_endpoint(self):
        result = self.run_wrapper('--container-help', CONTAINER_HOST='unix:///')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('absolute socket pathname', result.stdout)
        self.assertEqual(self.calls(), [])
        self.assertFalse(self.state.exists())

    def test_shared_state_default_and_override(self):
        for custom in ('', str(self.base / 'custom Claude')):
            with self.subTest(custom=custom):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(CLAUDE_CONTAINER_STATE_DIR='', CLAUDE_CONFIG_DIR=custom)
                self.assertEqual(result.returncode, 0, result.stderr)
                home = Path(self.env['HOME'])
                source = Path(custom) if custom else home / '.claude'
                self.assertIn(f'{source}:/claude-home/.claude:rw', self.create())
                self.assertIn(f'{home}/.config/openspec:/claude-home/.config/openspec:rw', self.create())
                self.assertNotIn(f'{self.state}:/claude-home:rw', self.create())
                self.assertFalse((home / '.cache').exists())
                self.assertFalse((home / '.local/share').exists())

    def test_state_conflict_fails_without_engine(self):
        result = self.run_wrapper(CLAUDE_CONFIG_DIR=str(self.base / 'custom'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('conflicts', result.stderr)
        self.assertFalse(self.calls())

    def test_private_creation_does_not_change_host_command_umask(self):
        for mask in (0o022, 0o002):
            for isolated in (False, True):
                with self.subTest(mask=oct(mask), isolated=isolated):
                    home = self.base / f'home-{mask}-{isolated}'
                    state = self.base / f'state-{mask}-{isolated}'
                    umask_log = self.base / f'umask-{mask}-{isolated}.jsonl'
                    result = self.run_wrapper('--container-build', caller_umask=mask,
                                              HOME=str(home), FAKE_UMASK_LOG=str(umask_log),
                                              CLAUDE_CONTAINER_STATE_DIR=str(state) if isolated else '')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    observations = [json.loads(line) for line in umask_log.read_text().splitlines()]
                    self.assertTrue({'build', 'create', 'start', 'rm'} <= {c for c, _ in observations})
                    self.assertTrue(all(actual == mask for _, actual in observations), observations)
                    root = state if isolated else home
                    for relative in ('.', '.claude', '.config', '.config/openspec'):
                        self.assertEqual((root / relative).stat().st_mode & 0o777, 0o700)

    def test_state_alias_and_configuration_escape(self):
        self.state.mkdir(mode=0o700)
        alias = self.base / 'state-alias'
        alias.symlink_to(self.state)
        self.assertEqual(self.run_wrapper(CLAUDE_CONTAINER_STATE_DIR=str(alias)).returncode, 0)
        self.assertIn(f'{self.state}:/claude-home:rw', self.create())
        outside = self.base / 'outside'
        outside.mkdir()
        for relative in ('.claude', '.config/openspec'):
            with self.subTest(relative=relative):
                target = self.state / relative
                target.rmdir()
                target.symlink_to(outside)
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('escapes', result.stderr)
                self.assertFalse(any(c[0] == 'create' for c in self.calls()))
                target.unlink()
                target.mkdir(mode=0o700)

    def test_private_existing_claude_and_wrong_owner(self):
        self.state.mkdir(mode=0o700)
        config = self.state / '.claude'
        config.mkdir(mode=0o755)
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(config), result.stderr)
        self.assertEqual(config.stat().st_mode & 0o777, 0o755)
        config.chmod(0o700)
        stat = self.bin / 'stat'
        stat.write_text('#!/bin/bash\nif [[ "$2" == %u ]]; then echo 999999; else exec /usr/bin/stat "$@"; fi\n')
        stat.chmod(0o755)
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('belong', result.stderr)

    def test_inaccessible_state_and_ignored_permissions(self):
        self.state.mkdir(mode=0o700)
        self.state.chmod(0o000)
        try:
            result = self.run_wrapper()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(str(self.state), result.stderr)
        finally:
            self.state.chmod(0o700)
        stat = self.bin / 'stat'
        stat.write_text('#!/bin/bash\nif [[ "$2" == %a ]]; then echo 777; else exec /usr/bin/stat "$@"; fi\n')
        stat.chmod(0o755)
        self.assertIn('native Linux storage', self.run_wrapper().stderr)

    def test_socket_disabled_values_skip_delegation_checks(self):
        for value in ('', '0', 'true', 'yes', '01', 'maybe'):
            with self.subTest(value=value):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN=value,
                                          CLAUDE_CONTAINER_PODMAN_SOCKET='relative-missing')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
                self.assertNotIn('CONTAINER_HOST=unix:///run/podman/podman.sock', self.create())
                self.assertEqual(self.create()[self.create().index('--unsetenv') + 1], 'CONTAINER_HOST')

    def test_socket_precedence_and_remapping(self):
        alias = self.base / 'socket-alias'
        alias.symlink_to(self.socket_path)
        cases = (
            {'CLAUDE_CONTAINER_PODMAN_SOCKET': str(alias), 'CONTAINER_HOST': 'unix:///other/engine'},
            {'CLAUDE_CONTAINER_PODMAN_SOCKET': '', 'CONTAINER_HOST': f'unix://{self.socket_path}'},
        )
        for env in cases:
            with self.subTest(env=env):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1', **env)
                self.assertEqual(result.returncode, 0, result.stderr)
                query = next(c for c in self.calls() if c[0] == '--remote')
                self.assertEqual(query[2], f'unix://{self.socket_path}')
                self.assertIn('/host/podman.sock:/run/podman/podman.sock:rw', self.create())
        runtime = self.base / 'runtime'
        (runtime / 'podman').mkdir(parents=True)
        (runtime / 'podman/podman.sock').symlink_to(self.socket_path)
        self.log.unlink()
        result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1', CLAUDE_CONTAINER_PODMAN_SOCKET='',
                                  XDG_RUNTIME_DIR=str(runtime))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(next(c for c in self.calls() if c[0] == '--remote')[2], f'unix://{self.socket_path}')

    def test_socket_fallback_and_invalid_sources(self):
        result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1', CLAUDE_CONTAINER_PODMAN_SOCKET='')
        self.assertIn(f'/run/user/{os.getuid()}/podman/podman.sock', result.stderr)
        for source in ('relative', str(self.base / 'missing'), str(WRAPPER)):
            with self.subTest(source=source):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper('--container-build', CLAUDE_CONTAINER_PODMAN='1',
                                          CLAUDE_CONTAINER_PODMAN_SOCKET=source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(source, result.stderr)
                self.assertFalse(any(c[0] in ('build', 'image', 'create') for c in self.calls()))
        self.socket_path.chmod(0o000)
        try:
            self.assertIn('not accessible', self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1').stderr)
        finally:
            self.socket_path.chmod(0o700)

    def test_invalid_delegation_results_gate_explicit_build(self):
        for env in ({'FAKE_SOCKET_STATUS': '125'}, {'FAKE_SOCKET_ROOTLESS': ''},
                    {'FAKE_SOCKET_ROOTLESS': 'unexpected'}, {'FAKE_SOCKET_ROOTLESS': 'false'},
                    {'FAKE_HOST_SOCKET': ''}, {'FAKE_HOST_SOCKET': 'relative'},
                    {'FAKE_HOST_SOCKET': '/path\nextra'}):
            with self.subTest(env=env):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper('--container-build', CLAUDE_CONTAINER_PODMAN='1', **env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(self.socket_path), result.stderr)
                self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_composition_and_independence_in_both_state_modes(self):
        for isolated in ('', str(self.state)):
            for shell in (False, True):
                for yolo in ('0', '1'):
                    for service in ('0', '1'):
                        with self.subTest(isolated=isolated, shell=shell, yolo=yolo, service=service):
                            self.log.unlink(missing_ok=True)
                            options = ['--container-build', '--container-git-worktree']
                            if shell:
                                options.append('--container-shell')
                            result = self.run_wrapper(*options, CLAUDE_CONTAINER_STATE_DIR=isolated,
                                                      CLAUDE_YOLO=yolo, CLAUDE_CONTAINER_PODMAN=service)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            create = self.create()
                            self.assertEqual('--dangerously-skip-permissions' in create, yolo == '1' and not shell)
                            self.assertEqual('CONTAINER_HOST=unix:///run/podman/podman.sock' in create, service == '1')
                            self.assertEqual('--unsetenv' in create, service != '1')
                            self.assertIn('--read-only-tmpfs=false', create)
                            mounts = [create[i+1] for i, arg in enumerate(create) if arg == '--tmpfs']
                            self.assertEqual(mounts, [
                                '/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777',
                                '/run:rw,nosuid,nodev,noexec,size=16m',
                                '/var/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777'])
                            self.assertIn(f'{self.project.parent}:{self.project.parent}:rw', create)

    def test_disabled_delegation_preserves_host_launch_endpoint(self):
        probe = self.bin / 'podman'
        probe.write_text(FAKE.replace("args = sys.argv[1:]",
                         "assert os.environ['CONTAINER_HOST'] == 'unix:///launch/socket'\nargs = sys.argv[1:]"))
        result = self.run_wrapper('--container-build', CONTAINER_HOST='unix:///launch/socket')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--unsetenv', self.create())

    def test_ca_mount_and_security_policy(self):
        ca = self.base / 'bundle.pem'
        ca.write_text('synthetic certificate bundle')
        for isolated in ('', str(self.state)):
            for trust in ('0', '1', 'TrUe'):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(CLAUDE_CONTAINER_STATE_DIR=isolated,
                                          CLAUDE_CONTAINER_TRUST_HOST_CA=trust,
                                          CLAUDE_CONTAINER_CA_BUNDLE=str(ca))
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.create()
                for variable in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'NODE_EXTRA_CA_CERTS'):
                    self.assertEqual(f'{variable}=/claude-home/ca/bundle.pem' in create, trust != '0')
                self.assertEqual(f'{ca}:/claude-home/ca/bundle.pem:ro' in create, trust != '0')
                self.assertIn('/tmp:rw,nosuid,nodev,noexec,size=256m,mode=1777', create)
                self.assertIn('/run:rw,nosuid,nodev,noexec,size=16m', create)
                self.assertFalse(any(x.startswith(('--privileged', '--cap-add', '--security-opt')) for x in create))
                self.assertFalse(any(x.endswith((':z', ':Z')) for x in create))
        self.log.unlink()
        self.assertNotEqual(self.run_wrapper(CLAUDE_CONTAINER_TRUST_HOST_CA='1',
                                            CLAUDE_CONTAINER_CA_BUNDLE='/missing').returncode, 0)
        self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_symlink_invocation_and_native_permissions(self):
        alias = self.base / 'claude'
        alias.symlink_to(WRAPPER)
        result = subprocess.run([str(alias), '--container-build', '--dangerously-skip-permissions'],
                                cwd=self.project, env=self.env, input='', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        build = next(c for c in self.calls() if c[0] == 'build')
        self.assertEqual(build[-3:], ['--file', str(ROOT / 'Containerfile'), str(ROOT)])
        self.assertEqual(self.create()[-1], '--dangerously-skip-permissions')

    def test_collision_exhaustion_and_diagnostic_cleanup(self):
        diagnostics = self.base / 'diagnostics'
        diagnostics.mkdir()
        result = self.run_wrapper(FAKE_COLLISION='1', FAKE_ALWAYS_COLLIDE='1', TMPDIR=str(diagnostics))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('20 attempts', result.stderr)
        self.assertEqual(len([c for c in self.calls() if c[0] == 'create']), 20)
        self.assertFalse(list(diagnostics.iterdir()))
        self.assertFalse(any(c[0] == 'rm' for c in self.calls()))

    def test_int_and_hup_forwarding(self):
        import signal
        import time
        for name, status in (('INT', 130), ('HUP', 129)):
            self.log.unlink(missing_ok=True)
            Path(str(self.log) + '.started').unlink(missing_ok=True)
            proc = subprocess.Popen([str(WRAPPER)], cwd=self.project, env=self.env | {'FAKE_WAIT': '1'},
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for _ in range(100):
                    if Path(str(self.log) + '.started').exists():
                        break
                    time.sleep(0.02)
                proc.send_signal(getattr(signal, 'SIG' + name))
                proc.communicate(timeout=5)
                self.assertEqual(proc.returncode, status)
                self.assertTrue(any(c[:3] == ['kill', '--signal', name] for c in self.calls()))
                self.assertIn(['rm', '--force', '--ignore', 'owned-test-container-id'], self.calls())
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate()


if __name__ == '__main__':
    unittest.main()
