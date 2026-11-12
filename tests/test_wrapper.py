"""Behavior checks for the wrapper without an engine or Claude credentials."""
import json
import itertools
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import signal
import shutil
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'claude-container.sh'
OWNED_ID = 'a' * 64
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
state = pathlib.Path(str(log) + '.container')
command = args[0]
if command in os.environ.get('FAKE_STALL', '').split(',') and (command != 'ps' or '--filter' in args):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    pathlib.Path(str(log) + '.stalled-' + command).write_text(str(os.getpid()))
    while True:
        time.sleep(0.05)
if command in os.environ.get('FAKE_FAIL', '').split(','):
    print('synthetic control failure: ' + command, file=sys.stderr)
    sys.exit(17)
if args[:2] == ['--remote', '--url']:
    sys.stdout.write(os.environ.get('FAKE_SOCKET_RAW',
                     os.environ.get('FAKE_SOCKET_ROOTLESS', 'true') + ' ' +
                     os.environ.get('FAKE_HOST_SOCKET', '/host/podman.sock') + '\n'))
    sys.exit(int(os.environ.get('FAKE_SOCKET_STATUS', '0')))
elif args[0] == 'info':
    if args[-1] == '{{json .Host}}':
        print(os.environ.get('FAKE_PLATFORM',json.dumps({'kernel':'6.6.87.2-microsoft-standard-WSL2','arch':'amd64',
            'security':{'seccompEnabled':True,'selinuxEnabled':False,'apparmorEnabled':False}})))
        sys.exit(0)
    if args[-1] == '{{.Host.NetworkBackend}}':
        print(os.environ.get('FAKE_BACKEND', 'netavark'))
        sys.exit(0)
    if args[-1] == '{{.Host.CgroupControllers}}':
        print(os.environ.get('FAKE_CONTROLLERS', '[cpu memory pids]'))
        sys.exit(int(os.environ.get('FAKE_CONTROLLERS_STATUS', '0')))
    sys.stdout.write(os.environ.get('FAKE_INFO_RAW', os.environ.get('FAKE_INFO', 'true linux false') + '\n'))
    sys.exit(int(os.environ.get('FAKE_INFO_STATUS', '0')))
elif args[0] == 'version':
    print(os.environ.get('FAKE_SERVER_VERSION', '4.9.3'))
elif args[:2] == ['image', 'exists']:
    sys.exit(int(os.environ.get('FAKE_IMAGE_STATUS', '0')))
elif args[:2] == ['image', 'inspect']:
    print('d' * 64)
elif args[0] == 'build':
    time.sleep(float(os.environ.get('FAKE_BUILD_DELAY', '0')))
    sys.exit(int(os.environ.get('FAKE_BUILD_STATUS', '0')))
elif args[0] == 'ps':
    if '--filter' in args:
        print(os.environ.get('FAKE_RECOVERY_ID', 'a' * 64) if state.exists() else '')
    else:
        print(os.environ.get('FAKE_NAMES', ''))
elif args[0] == 'create':
    if os.environ.get('FAKE_NETWORK') and any(a.startswith('io.claude-container.egress=') for a in args):
        pathlib.Path(args[args.index('--cidfile') + 1]).write_text('b' * 64 + '\n')
        print('b' * 64)
        sys.exit(0)
    collision = pathlib.Path(str(log) + '.collision')
    if os.environ.get('FAKE_COLLISION') and (not collision.exists() or os.environ.get('FAKE_ALWAYS_COLLIDE')):
        collision.touch()
        sys.exit(125)
    if os.environ.get('FAKE_CREATE_FAILURE'):
        print('create failed', file=sys.stderr)
        sys.exit(125)
    token = args[args.index('--label') + 1].split('=', 1)[1]
    state.write_text(token)
    from decimal import Decimal
    flag = lambda name: next((a.split('=', 1)[1] for a in args if a.startswith(name + '=')), '0')
    pathlib.Path(str(log) + '.budgets').write_text(' '.join((flag('--memory'),
        str(int(Decimal(flag('--cpus')) * 10**9)), flag('--pids-limit'))))
    pause = os.environ.get('FAKE_CREATE_PAUSE')
    if pause != 'before':
        pathlib.Path(args[args.index('--cidfile') + 1]).write_text('a' * 64 + '\n')
    if pause:
        pathlib.Path(str(log) + '.create-pid').write_text(str(os.getpid()))
        pathlib.Path(str(log) + '.creating').touch()
        while True:
            time.sleep(0.05)
    print('a' * 64)
    sys.exit(int(os.environ.get('FAKE_CREATED_STATUS', '0')))
elif args[0] == 'inspect':
    if '{{.HostConfig.Memory}}' in args[-2]:
        # Report the created configuration unless a test overrides it.
        budgets = pathlib.Path(str(log) + '.budgets')
        if 'FAKE_AGENT_BUDGETS' in os.environ:
            print(os.environ['FAKE_AGENT_BUDGETS'])
        elif budgets.exists():
            print(budgets.read_text())
        sys.exit(0)
    if os.environ.get('FAKE_NETWORK') and args[-1] == 'b' * 64 and args[-2] == '{{json .HostConfig}}':
        print(os.environ.get('FAKE_PROXY_CONFIG', '{"PidsLimit":128,"Memory":268435456}'))
        sys.exit(0)
    print(state.read_text() if state.exists() and args[-1] == 'a' * 64 else 'foreign-session')
elif args[0] == 'exec' and os.environ.get('FAKE_NETWORK'):
    print(os.environ.get('FAKE_PROXY_EFFECTIVE', '{"pids":128,"memory":268435456,"capabilities":[0,0,0,0,0],"no_new_privs":1,"seccomp":2}'))
elif args[:2] == ['container', 'exists']:
    sys.exit(0 if os.environ.get('FAKE_COLLISION') else 1)
elif args[0] == 'kill':
    pid = pathlib.Path(str(log) + '.pid')
    if pid.exists():
        os.kill(int(pid.read_text()), signal.SIGTERM)
elif args[0] == 'rm':
    if os.environ.get('FAKE_NETWORK') and args[-1] == 'b' * 64:
        sys.exit(0)
    assert args[-1] == 'a' * 64, 'refusing to remove unrelated identity'
    state.unlink(missing_ok=True)
    pid = pathlib.Path(str(log) + '.pid')
    if pid.exists():
        try:
            os.kill(int(pid.read_text()), signal.SIGKILL)
        except ProcessLookupError:
            pass
elif args[0] == 'start':
    if os.environ.get('FAKE_NETWORK') and args[-1] == 'b' * 64:
        sys.exit(0)
    if os.environ.get('FAKE_START_STDERR'):
        sys.stderr.write(os.environ['FAKE_START_STDERR'])
        sys.stderr.flush()
    time.sleep(float(os.environ.get('FAKE_START_DELAY', '0')))
    if os.environ.get('FAKE_WAIT'):
        for name in ('TERM', 'INT', 'HUP'):
            signal.signal(getattr(signal, 'SIG' + name),
                          signal.SIG_IGN if os.environ.get('FAKE_IGNORE_SIGNALS') else signal.SIG_DFL)
        pathlib.Path(str(log) + '.pid').write_text(str(os.getpid()))
        pathlib.Path(str(log) + '.started').touch()
        time.sleep(20)
    if not os.environ.get('FAKE_NO_STDIN'):
        print('stdin:' + sys.stdin.read())
    sys.exit(int(os.environ.get('FAKE_EXIT', '0')))
'''


# Shared accept/reject table for the Bash wrapper and network/agent_budgets.py.
BUDGET_REJECTIONS = {
    'MEMORY_LIMIT': ('', ' ', '0', '0g', '-1', '-1g', 'max', '4', '4t', '4gb', '1.5g', '04g', 'abc', '2000000g'),
    'CPU_LIMIT': ('', '0', '0.0', '0.0000', '-1', 'max', '1.5555', '1.', '.5', '1025', 'two', ' 2'),
    'PIDS_LIMIT': ('', '0', '-1', 'max', '4194305', '01', '1.5', 'x'),
    'RUN_TIMEOUT': ('-1', '1.5', 'x', '01', '2147483648', ' 5'),
}
BUDGET_ACCEPTED = {
    'MEMORY_LIMIT': ('1k', '4g', '4G', '512m', '1048576k', '1048576g'),
    'CPU_LIMIT': ('0.001', '2', '1.5', '1024', '02', '3.25'),
    'PIDS_LIMIT': ('1', '512', '4194304'),
    'RUN_TIMEOUT': ('0', '1', '2147483647'),
}


class AccountInventoryTests(unittest.TestCase):
    """Claude-specific exact provider inventories (N21)."""
    def setUp(self):
        import sys
        sys.path.insert(0, str(ROOT / 'network'))
        import agent_profile
        import policy
        self.policy = policy
        self.rules = agent_profile.load().policy_rules()
        self.value = json.loads((ROOT / agent_profile.POLICY).read_text())

    def hosts(self, name):
        return {(d['host'], d['port']) for d in self.value['profiles'][name]['destinations']}

    def test_shipped_inventories_are_exact(self):
        self.policy.validate(json.loads(json.dumps(self.value)), self.rules)
        self.assertEqual(self.hosts('anthropic-api'), {('api.anthropic.com', 443)})
        self.assertEqual(self.hosts('anthropic-account'), {('api.anthropic.com', 443), ('platform.claude.com', 443)})
        self.assertEqual(self.value['revision'], 'anthropic-2026-11-08-v2')

    def test_removed_account_hosts_require_a_separate_profile(self):
        for host in ('claude.ai', 'claude.com'):
            with self.subTest(host=host):
                value = json.loads(json.dumps(self.value))
                value['profiles']['anthropic-account']['destinations'].append({'host': host, 'port': 443})
                with self.assertRaisesRegex(self.policy.PolicyError, 'exact base profile'):
                    self.policy.validate(value, self.rules)
        value = json.loads(json.dumps(self.value))
        value['profiles']['account-with-web'] = {
            'authentication': 'account', 'disable_optional_traffic': True,
            'destinations': [*value['profiles']['anthropic-account']['destinations'],
                             {'host': 'claude.ai', 'port': 443}, {'host': 'claude.com', 'port': 443}]}
        self.policy.validate(value, self.rules)


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='claude-wrapper-', dir=os.environ.get('SANDBOX_TEST_TMPDIR'))
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
        self.env = {'PATH': os.environ['PATH'], 'CLAUDE_CONTAINER_NETWORK': 'unrestricted',
                    'CLAUDE_CONTAINER_MAINTENANCE': '1'}
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
        return subprocess.run([str(getattr(self, 'wrapper', WRAPPER)), *args], cwd=cwd or self.project,
                              env=self.env | env, input='input payload',
                              text=True, capture_output=True, timeout=25, umask=caller_umask)

    def calls(self):
        return [json.loads(s) for s in self.log.read_text().splitlines()] if self.log.exists() else []

    def create(self):
        return next(c for c in self.calls() if c[0] == 'create')

    def wait_marker(self, proc, suffix):
        marker = Path(str(self.log) + suffix)
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            if proc.poll() is not None:
                self.fail(str(proc.communicate()))
            time.sleep(0.02)
        self.assertTrue(marker.exists(), suffix)

    def start_waiting_wrapper(self, marker='.started', **env):
        diagnostics = self.base / 'diagnostics'
        diagnostics.mkdir(exist_ok=True)
        proc = subprocess.Popen([str(WRAPPER)], cwd=self.project,
                                env=self.env | {'TMPDIR': str(diagnostics)} | env,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        def finish():
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=25)
            pid_files = [Path(str(self.log) + suffix) for suffix in ('.pid', '.create-pid')]
            pid_files.extend(self.base.glob('calls.jsonl.stalled-*'))
            for pid in pid_files:
                if pid.exists():
                    try:
                        child = int(pid.read_text())
                        if str(self.bin / 'podman').encode() in Path(f'/proc/{child}/cmdline').read_bytes():
                            os.kill(child, signal.SIGKILL)
                    except (ProcessLookupError, FileNotFoundError):
                        pass
        self.addCleanup(finish)
        self.wait_marker(proc, marker)
        return proc, diagnostics

    def assert_no_fake_client(self):
        for suffix in ('.pid', '.create-pid'):
            path = Path(str(self.log) + suffix)
            if path.exists():
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(path.read_text()), 0)

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

    def test_missing_network_mode_requires_setup_without_side_effects(self):
        for mode in (None, ''):
            with self.subTest(mode=mode):
                env = self.env.copy()
                env.pop('CLAUDE_CONTAINER_NETWORK')
                if mode is not None:
                    env['CLAUDE_CONTAINER_NETWORK'] = mode
                result = subprocess.run(['/bin/bash', str(WRAPPER)], cwd=self.project,
                                        env=env, input='input payload', text=True,
                                        capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('setup required: run bash ', result.stderr)
                self.assertIn('--container-setup', result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertFalse(self.calls())
                self.assertFalse(self.state.exists())
                self.assertFalse(Path(env['HOME']).exists())

    def test_missing_mode_precedes_options_prerequisites_and_other_configuration(self):
        (self.project / 'setup.json').write_text('{"network":"unrestricted"}')
        (self.project / 'qualification').mkdir()
        (self.project / 'qualification/report.json').write_text('{"checks":"passed"}')
        options = ('--container-shell', '--container-build', '--container-git-worktree')
        for enabled in itertools.product((False, True), repeat=3):
            for missing_tools in (False, True):
                for mode in (None, ''):
                    with self.subTest(enabled=enabled, missing_tools=missing_tools, mode=mode):
                        env = self.env | {'CLAUDE_YOLO': 'invalid',
                            'CLAUDE_CONTAINER_TRUST_HOST_CA': 'invalid',
                            'CLAUDE_CONTAINER_PODMAN': '1', 'CONTAINER_HOST': 'invalid',
                            'CLAUDE_CONTAINER_NETWORK_POLICY': '/invalid/policy',
                            'CLAUDE_CONFIG_DIR': '/conflicting/config'}
                        env.pop('CLAUDE_CONTAINER_NETWORK')
                        if mode is not None:
                            env['CLAUDE_CONTAINER_NETWORK'] = mode
                        if missing_tools:
                            env['PATH'] = ''
                        args = [option for option, use in zip(options, enabled) if use]
                        result = subprocess.run(['/bin/bash', str(WRAPPER), *args, '-p', ''],
                                                cwd=self.project, env=env, input='payload',
                                                text=True, capture_output=True, timeout=5)
                        self.assertEqual(result.returncode, 1, result.stderr)
                        self.assertIn('setup required:', result.stderr)
                        self.assertEqual(result.stdout, '')
                        self.assertFalse(self.calls())
                        self.assertFalse(self.state.exists())
                        self.assertFalse(Path(env['HOME']).exists())
        for mode in ('invalid', ' ', '\t'):
            with self.subTest(invalid_mode=repr(mode)):
                result = self.run_wrapper(CLAUDE_CONTAINER_NETWORK=mode)
                self.assertEqual(result.returncode, 1)
                self.assertIn('must be offline, provider, or unrestricted', result.stderr)
                self.assertNotIn('setup required:', result.stderr)
                self.assertFalse(self.calls())

    def test_setup_diagnostic_quotes_invoked_symlink_and_runs_from_other_workspace(self):
        link = self.base / 'wrapper with spaces $(touch injected) `touch injected-too`.sh'
        link.symlink_to(WRAPPER)
        env = self.env.copy()
        env.pop('CLAUDE_CONTAINER_NETWORK')
        for wrapper in (str(link), os.path.relpath(link, self.project), str(WRAPPER)):
            with self.subTest(wrapper=wrapper):
                result = subprocess.run(['/bin/bash', wrapper], cwd=self.project,
                                        env=env, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 1)
                command = result.stderr.split('setup required: run ', 1)[1].split(
                    '; use the managed launcher afterward', 1)[0]
                # Execute the suggested command with help taking precedence over
                # setup: this verifies shell quoting without starting a setup.
                help_result = subprocess.run(['/bin/bash', '-c', command + ' --container-help'],
                                             cwd=self.project, env=env, capture_output=True,
                                             text=True, timeout=5)
                self.assertEqual(help_result.returncode, 0, help_result.stderr)
                self.assertIn('Container options:', help_result.stdout)
                if wrapper != str(WRAPPER):
                    self.assertIn('wrapper', command)
                    self.assertNotIn(str(WRAPPER), command)
                self.assertFalse((self.project / 'injected').exists())
                self.assertFalse((self.project / 'injected-too').exists())
                self.assertFalse(self.calls())
                self.assertFalse(self.state.exists())

    def test_network_preflight_rejections_precede_image_operations(self):
        for values in (
            {'CLAUDE_CONTAINER_NETWORK': 'invalid'},
            {'CLAUDE_CONTAINER_NETWORK': 'provider'},
            {'CLAUDE_CONTAINER_NETWORK': 'offline', 'CLAUDE_CONTAINER_PODMAN': '1'},
            {'CLAUDE_CONTAINER_NETWORK': 'provider', 'CLAUDE_CONTAINER_PODMAN': '1'},
        ):
            for flags in ((), ('--container-shell', '--container-build', '--container-git-worktree')):
                with self.subTest(values=values, flags=flags):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper(*flags, **values)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(self.calls())
        fixture = self.restricted_fixture()
        for values in ({'FAKE_BACKEND': 'cni'}, {'FAKE_SERVER_VERSION': '4.8.0'}):
            self.log.unlink(missing_ok=True)
            result = self.run_wrapper(**(fixture | values | {'CLAUDE_CONTAINER_NETWORK':'offline'}))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ineligible restricted platform', result.stderr)
            self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_maintenance_is_separate_from_runtime_mode(self):
        for maintenance in ('', '0', 'true', 'yes', '01'):
            for explicit in (False, True):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(*(['--container-build'] if explicit else []),
                    CLAUDE_CONTAINER_MAINTENANCE=maintenance, FAKE_IMAGE_STATUS='1')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('MAINTENANCE=1', result.stderr)
                self.assertFalse(any(c[0] in ('build', 'pull', 'create') for c in self.calls()))

    def test_restricted_unprotected_installation_fails_before_image_operations(self):
        result = self.run_wrapper('--container-shell', '--container-build',
                                  CLAUDE_CONTAINER_NETWORK='offline',
                                  CONTAINER_HOST='unix:///run/service.sock',
                                  FAKE_INFO='true linux true')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('network policy preflight failed', result.stderr)
        self.assertFalse(any(c[0] in ('image', 'build', 'pull', 'create') for c in self.calls()))

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

    def restricted_fixture(self):
        # Argument/lifecycle instrumentation only. Real guard and protected-path
        # acceptance lives in test_network_runtime; no production check is changed.
        install = self.base / 'synthetic-install'
        (install / 'network/bin').mkdir(parents=True)
        self.wrapper = install / 'claude-container.sh'
        shutil.copyfile(WRAPPER, self.wrapper)
        self.wrapper.chmod(0o700)
        guard = install / 'network/bin/sandbox-egress-guard'
        guard.write_text('#!/bin/sh\nexit 0\n')
        guard.chmod(0o700)
        (guard.parent / 'sandbox-egress-guard.sha256').write_text('c' * 64 + '  sandbox-egress-guard\n')
        shutil.copyfile(ROOT / 'network/proxy_hardening.py', install / 'network/proxy_hardening.py')
        shutil.copyfile(ROOT / 'network/platform_check.py', install / 'network/platform_check.py')
        for name in ('network/session.py', 'network/agent_profile.py', 'network/agent_budgets.py', 'network/policy.py',
                     'network/revisions.py', 'agent/profile.json'):
            (install / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, install / name)
        (install / 'network/qualify.py').write_text('# Synthetic argument fixture only.\n')
        (install / 'network/control.py').write_text('''import pathlib,socket,sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from revisions import TLS_ENFORCEMENT
args=sys.argv[1:]
if args[0]=='snapshot':
 p=pathlib.Path(args[args.index('--session')+1]); (p/'transport').mkdir()
 (p/'config').mkdir(); (p/'logs').mkdir()
 s=socket.socket(socket.AF_UNIX); s.bind(str(p/'transport/proxy.sock')); s.close()
 (p/'transport/ready').write_text('fixture-policy guard='+ 'c'*64 +' mux=1 tls=' + TLS_ENFORCEMENT + '\\n')
 print('fixture-policy')
''')
        runtime = self.base / 'network-runtime'
        runtime.mkdir()
        return dict(FAKE_NETWORK='1', FAKE_INFO='true linux true',
                    CONTAINER_HOST='unix:///run/service.sock',
                    CLAUDE_CONTAINER_NETWORK_POLICY=str(install / 'policy.json'),
                    CLAUDE_CONTAINER_NETWORK_PROFILE='fixture',
                    CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR=str(runtime),
                    CLAUDE_CONTAINER_EGRESS_IMAGE='d' * 64)

    def test_hardening_and_budgets_in_every_mode(self):
        values = self.restricted_fixture()
        cases = [(mode, state, flags, {}) for mode in ('offline', 'provider', 'unrestricted')
                 for state in ('', str(self.state)) for flags in ((), ('--container-shell',))]
        cases += [('unrestricted', str(self.state), flags, {'CLAUDE_CONTAINER_PODMAN': '1'})
                  for flags in ((), ('--container-shell',))]
        for mode, state, flags, extra in cases:
            with self.subTest(mode=mode, state=state, flags=flags, extra=extra):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(*flags, **(values | extra | {
                    'CLAUDE_CONTAINER_NETWORK': mode, 'CLAUDE_CONTAINER_STATE_DIR': state}))
                self.assertEqual(result.returncode, 0, result.stderr)
                creates = [c for c in self.calls() if c[0] == 'create']
                self.assertEqual(len(creates), 2 if mode == 'provider' else 1)
                for create in creates:
                    for option in ('--cap-drop=all', '--security-opt=no-new-privileges', '--userns=keep-id'):
                        self.assertIn(option, create)
                    self.assertIn(f'{os.getuid()}:{os.getgid()}', create)
                    proxy = any(a.startswith('io.claude-container.egress=') for a in create)
                    self.assertEqual('--pids-limit=128' in create, proxy)
                    self.assertEqual('--memory=256m' in create, proxy)
                    agent = ('--memory=4294967296', '--cpus=2', '--pids-limit=512')
                    for option in agent:
                        self.assertEqual(option in create, not proxy)
                    self.assertFalse(any(a == '--timeout' for a in create))
                agent_inspect = [c for c in self.calls() if c[0] == 'inspect' and '{{.HostConfig.Memory}}' in c[-2]]
                self.assertEqual(len(agent_inspect), 1)
                self.assertEqual(agent_inspect[0][-1], OWNED_ID)
                if '--container-shell' not in flags:
                    self.assertNotIn('lifetime limit', result.stderr)

    def test_budget_overrides_and_rejections_precede_engine(self):
        result = self.run_wrapper(CLAUDE_CONTAINER_MEMORY_LIMIT='8G', CLAUDE_CONTAINER_CPU_LIMIT='1.5',
                                  CLAUDE_CONTAINER_PIDS_LIMIT='1024', CLAUDE_CONTAINER_RUN_TIMEOUT='60')
        self.assertEqual(result.returncode, 0, result.stderr)
        create = self.create()
        for option in ('--memory=8589934592', '--cpus=1.5', '--pids-limit=1024'):
            self.assertIn(option, create)
        self.assertEqual(create[create.index('--timeout') + 1], '60')
        for value in ('', '0', None):
            with self.subTest(timeout=value):
                self.log.unlink(missing_ok=True)
                env = {} if value is None else {'CLAUDE_CONTAINER_RUN_TIMEOUT': value}
                self.assertEqual(self.run_wrapper(**env).returncode, 0)
                self.assertNotIn('--timeout', self.create())
        for name, cases in BUDGET_REJECTIONS.items():
            for value in cases:
                with self.subTest(name=name, value=value):
                    self.log.unlink(missing_ok=True)
                    fresh = self.base / 'rejected-state'
                    result = self.run_wrapper(**{'CLAUDE_CONTAINER_' + name: value,
                                                 'CLAUDE_CONTAINER_STATE_DIR': str(fresh)})
                    self.assertEqual(result.returncode, 1)
                    self.assertIn('CLAUDE_CONTAINER_' + name + ' must be', result.stderr)
                    self.assertFalse(self.calls())
                    self.assertFalse(fresh.exists())

    def test_budget_rules_match_shared_python_module(self):
        import sys
        sys.path.insert(0, str(ROOT / 'network'))
        import agent_budgets
        keys = {'MEMORY_LIMIT': 'memory', 'CPU_LIMIT': 'nano_cpus', 'PIDS_LIMIT': 'pids', 'RUN_TIMEOUT': 'timeout'}
        for name, values in BUDGET_REJECTIONS.items():
            for value in values:
                with self.subTest(rejected=name, value=value), self.assertRaises(agent_budgets.BudgetError):
                    agent_budgets.normalize({name: value})
        for name, values in BUDGET_ACCEPTED.items():
            for value in values:
                with self.subTest(accepted=name, value=value):
                    self.log.unlink(missing_ok=True)
                    expected = agent_budgets.normalize({name: value})
                    result = self.run_wrapper(**{'CLAUDE_CONTAINER_' + name: value})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    create = self.create()
                    timeout = int(create[create.index('--timeout') + 1]) if '--timeout' in create else 0
                    configured = Path(str(self.log) + '.budgets').read_text().split()
                    actual = dict(memory=int(configured[0]), nano_cpus=int(configured[1]),
                                  pids=int(configured[2]), timeout=timeout)
                    self.assertEqual(actual, expected)
                    self.assertEqual(actual[keys[name]], expected[keys[name]])

    def test_budgets_follow_delegated_controllers(self):
        notices = {'memory': 'agent memory budget not enforced: cgroup controller memory',
                   'cpu': 'agent CPU budget not enforced: cgroup controller cpu',
                   'pids': 'agent process budget not enforced: cgroup controller pids'}
        flags = {'memory': '--memory=4294967296', 'cpu': '--cpus=2', 'pids': '--pids-limit=512'}
        for controllers in ('[cpu memory pids]', '[cpuset cpu io memory pids]', '[memory pids]',
                            '[cpu pids]', '[cpu memory]', '[]'):
            with self.subTest(controllers=controllers):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(FAKE_CONTROLLERS=controllers)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.create()
                present = controllers[1:-1].split()
                for name in ('memory', 'cpu', 'pids'):
                    self.assertEqual(flags[name] in create, name in present)
                    self.assertEqual(notices[name] in result.stderr, name not in present)
                self.assertEqual('--pids-limit=-1' in create, 'pids' not in present)
                self.assertFalse(any(a.startswith('--cpus=') for a in create) and 'cpu' not in present)
                self.assertTrue(any(c[0] == 'start' for c in self.calls()))
        # A delegated controller whose limit the engine drops still stops the launch;
        # an unenforced limit that unexpectedly appears is rejected too.
        for controllers, reported in (('[memory pids]', '0 0 512'), ('[memory pids]', '4294967296 2000000000 512'),
                                      ('[cpu memory]', '4294967296 2000000000 512'),
                                      ('[cpu memory]', '4294967296 2000000000 2048')):
            with self.subTest(controllers=controllers, reported=reported):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(FAKE_CONTROLLERS=controllers, FAKE_AGENT_BUDGETS=reported)
                self.assertEqual(result.returncode, 1)
                self.assertIn('agent resource budgets were not applied', result.stderr)
                self.assertFalse(any(c[0] == 'start' for c in self.calls()))
        for controllers in ('cpu memory pids', '[cpu,memory]', '[CPU]', '[ cpu]', ''):
            with self.subTest(malformed=controllers):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(FAKE_CONTROLLERS=controllers)
                self.assertEqual(result.returncode, 1)
                self.assertIn('unverifiable cgroup controller list', result.stderr)
                self.assertFalse(any(c[0] == 'create' for c in self.calls()))
        self.log.unlink(missing_ok=True)
        result = self.run_wrapper(FAKE_CONTROLLERS_STATUS='125')
        self.assertEqual(result.returncode, 1)
        self.assertIn('cannot query the rootless cgroup controllers', result.stderr)

    def test_engine_default_secrets_are_masked_in_every_mode(self):
        mask = 'type=tmpfs,destination=/run/secrets,ro=true'
        for args, env in (((), {}), (('--container-shell',), {}), (('--container-git-worktree',), {}),
                          ((), {'CLAUDE_CONTAINER_PODMAN': '1'})):
            with self.subTest(args=args, env=env):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(*args, **env)
                self.assertEqual(result.returncode, 0, result.stderr)
                create = self.create()
                index = create.index(mask)
                self.assertEqual(create[index - 1], '--mount')
                self.assertEqual(create.count(mask), 1)
                self.assertFalse(any(':/run/secrets' in arg for arg in create))

    def assert_agent_dev_layout(self, create):
        self.assertIn('--read-only', create)
        self.assertNotIn('--read-only-tmpfs=false', create)
        # The engine provides /dev and a devpts that allows pseudo-terminals; an
        # explicit devpts would get ptmxmode=000.
        tmpfs = [create[i + 1] for i, arg in enumerate(create) if arg == '--tmpfs']
        self.assertFalse(any(t == '/dev' or t.startswith('/dev:') or t.startswith('/dev/') for t in tmpfs), tmpfs)
        mounts = [create[i + 1] for i, arg in enumerate(create) if arg == '--mount']
        self.assertFalse(any('type=devpts' in m or m.endswith('destination=/dev') or 'destination=/dev,' in m
                             for m in mounts), mounts)
        self.assertIn('type=tmpfs,destination=/dev/shm,ro=true', mounts)
        self.assertIn('type=tmpfs,destination=/run/secrets,ro=true', mounts)

    def test_agent_dev_layout_attaches_terminals_in_every_mode(self):
        values = self.restricted_fixture()
        cases = [(mode, flags, {}) for mode in ('offline', 'provider', 'unrestricted')
                 for flags in ((), ('--container-shell',), ('--container-git-worktree',))]
        cases.append(('unrestricted', (), {'CLAUDE_CONTAINER_PODMAN': '1'}))
        for mode, flags, extra in cases:
            with self.subTest(mode=mode, flags=flags, extra=extra):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(*flags, **(values | extra | {'CLAUDE_CONTAINER_NETWORK': mode}))
                self.assertEqual(result.returncode, 0, result.stderr)
                for create in (c for c in self.calls() if c[0] == 'create'):
                    if any(a.startswith('io.claude-container.egress=') for a in create):
                        # The proxy never attaches a terminal and keeps /dev read-only.
                        self.assertIn('--read-only-tmpfs=false', create)
                        self.assertFalse(any(a.startswith('/dev') or 'destination=/dev' in a for a in create))
                    else:
                        self.assert_agent_dev_layout(create)

    def test_ignored_budgets_stop_before_start_and_remove_owned_container(self):
        for reported in ('0 0 0', '4294967296 2000000000 0', '4294967296 0 512', '0 2000000000 512',
                         '4294967296 2000000000 513', ''):
            with self.subTest(reported=reported):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(FAKE_AGENT_BUDGETS=reported)
                self.assertEqual(result.returncode, 1)
                self.assertIn('agent resource budgets were not applied', result.stderr)
                self.assertIn('controller delegation', result.stderr)
                self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                self.assertTrue(any(c[0] == 'rm' and c[-1] == OWNED_ID for c in self.calls()))
        self.log.unlink(missing_ok=True)
        result = self.run_wrapper(FAKE_FAIL='inspect')
        self.assertEqual(result.returncode, 1)
        self.assertIn('cannot inspect agent resource budgets', result.stderr)
        self.assertFalse(any(c[0] == 'start' for c in self.calls()))

    def test_lifetime_notice_preserves_status(self):
        result = self.run_wrapper(CLAUDE_CONTAINER_RUN_TIMEOUT='1', FAKE_START_DELAY='1.2', FAKE_EXIT='137')
        self.assertEqual(result.returncode, 137)
        self.assertIn('session lifetime limit reached (1 s); exit status 137', result.stderr)
        for env in ({'FAKE_EXIT': '3'}, {'FAKE_START_DELAY': '1.2', 'FAKE_EXIT': '0'}):
            with self.subTest(env=env):
                result = self.run_wrapper(CLAUDE_CONTAINER_RUN_TIMEOUT='1', **env)
                self.assertEqual(result.returncode, int(env['FAKE_EXIT']))
                self.assertNotIn('lifetime limit', result.stderr)

    def test_sensitive_workspaces_refused_before_engine(self):
        home = Path(self.env['HOME'])
        home.mkdir()
        (home / 'project').mkdir()
        etc_link = self.base / 'etc-link'
        etc_link.symlink_to('/etc', target_is_directory=True)
        refused = [(home, ()), (home / 'project', ('--container-git-worktree',)), (etc_link, ()),
                   (Path('/'), ()), (Path('/tmp'), ())]
        if Path('/mnt').is_dir():
            refused.append((Path('/mnt'), ()))
        for cwd, flags in refused:
            for override in (None, 'true', 'yes', '0', ' 1'):
                with self.subTest(cwd=str(cwd), flags=flags, override=override):
                    self.log.unlink(missing_ok=True)
                    env = {} if override is None else {'CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE': override}
                    result = self.run_wrapper(*flags, cwd=cwd, **env)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('refusing sensitive workspace', result.stderr)
                    self.assertIn('project subdirectory', result.stderr)
                    self.assertFalse(self.calls())
                    self.assertFalse(self.state.exists())
        self.log.unlink(missing_ok=True)
        result = self.run_wrapper(cwd=home, CLAUDE_CONTAINER_ALLOW_UNSAFE_WORKSPACE='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'WARNING: sensitive workspace explicitly exposed read/write: {home}', result.stderr)
        self.assertIn(f'{home}:{home}:rw', self.create())
        self.log.unlink(missing_ok=True)
        self.assertEqual(self.run_wrapper(cwd=home / 'project').returncode, 0)
        self.assertNotIn('WARNING', self.run_wrapper(cwd=home / 'project').stderr)

    def test_wsl_drive_roots_refused_but_subdirectories_accepted(self):
        drives = [p for p in Path('/mnt').glob('?') if p.is_dir()] if Path('/mnt').is_dir() else []
        if not drives:
            self.skipTest('no single-letter drive root under /mnt')
        result = self.run_wrapper(cwd=drives[0])
        self.assertEqual(result.returncode, 1)
        self.assertIn('refusing sensitive workspace ' + str(drives[0]), result.stderr)
        self.assertFalse(self.calls())

    def test_proxy_hardening_failure_never_starts_agent(self):
        values = self.restricted_fixture() | {'CLAUDE_CONTAINER_NETWORK': 'provider'}
        good = dict(pids=128, memory=268435456, capabilities=[0]*5, no_new_privs=1, seccomp=2)
        cases = [{'FAKE_PROXY_CONFIG': raw} for raw in ('{}', 'null', 'not-json',
            '{"PidsLimit":0,"Memory":268435456}', '{"PidsLimit":128,"Memory":0}')]
        cases += [{'FAKE_PROXY_EFFECTIVE': json.dumps(good | change)} for change in (
            {'pids':129}, {'memory':536870912}, {'capabilities':[0,0,1,0,0]},
            {'no_new_privs':0}, {'seccomp':0}, {'memory':True})]
        cases += [{'FAKE_PROXY_EFFECTIVE': raw} for raw in ('{}', 'null', 'not-json')]
        cases += [{'FAKE_FAIL': name} for name in ('exec', 'inspect')]
        for case in cases:
            with self.subTest(case=case):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(**(values | case))
                self.assertNotEqual(result.returncode, 0)
                creates = [c for c in self.calls() if c[0] == 'create']
                self.assertEqual(len(creates), 1)
                self.assertIn('--pids-limit=128', creates[0])
                self.assertIn('--memory=256m', creates[0])
                self.assertTrue(any(c[0] == 'rm' and c[-1] == 'b' * 64 for c in self.calls()))

    def test_proxy_probe_timeout_and_interruption_clean_only_proxy(self):
        values = self.restricted_fixture() | {'CLAUDE_CONTAINER_NETWORK': 'provider', 'FAKE_STALL': 'exec'}
        for interrupt in (False, True):
            with self.subTest(interrupt=interrupt):
                self.log.unlink(missing_ok=True)
                marker = Path(str(self.log) + '.stalled-exec')
                marker.unlink(missing_ok=True)
                proc = subprocess.Popen([str(self.wrapper)], cwd=self.project, env=self.env | values,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                try:
                    self.wait_marker(proc, '.stalled-exec')
                    started = time.monotonic()
                    if interrupt:
                        proc.terminate()
                    stdout, stderr = proc.communicate(timeout=22)
                    self.assertEqual(proc.returncode, 143 if interrupt else 1, stdout + stderr)
                    self.assertLess(time.monotonic() - started, 21)
                    creates = [c for c in self.calls() if c[0] == 'create']
                    self.assertEqual(len(creates), 1)
                    self.assertTrue(any(c[0] == 'rm' and c[-1] == 'b' * 64 for c in self.calls()))
                    # The timeout owns its exec child even when shutdown signals it.
                    deadline = time.monotonic() + 2
                    while Path('/proc/' + marker.read_text()).exists() and time.monotonic() < deadline:
                        time.sleep(.02)
                    if Path('/proc/' + marker.read_text() + '/stat').exists():
                        self.assertEqual(Path('/proc/' + marker.read_text() + '/stat').read_text().split()[2], 'Z')
                finally:
                    if proc.poll() is None:
                        proc.kill(); proc.communicate()
                    if marker.exists():
                        pid = int(marker.read_text())
                        command = Path(f'/proc/{pid}/cmdline')
                        if command.exists() and str(self.bin / 'podman').encode() in command.read_bytes():
                            os.kill(pid, signal.SIGKILL)
                    proc.stdout.close(); proc.stderr.close()

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
            self.assert_agent_dev_layout(self.create())
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

    def test_runtime_build_receives_host_ca_only_when_trusted(self):
        ca = self.base / 'bundle.pem'
        ca.write_text('synthetic certificate bundle')
        for trust in ('0', '1'):
            for build in (('--container-build',), ()):
                with self.subTest(trust=trust, build=build):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper(*build, CLAUDE_CONTAINER_TRUST_HOST_CA=trust,
                                              CLAUDE_CONTAINER_CA_BUNDLE=str(ca),
                                              **({} if build else {'FAKE_IMAGE_STATUS': '1'}))
                    self.assertEqual(result.returncode, 0, result.stderr)
                    args = next(c for c in self.calls() if c[0] == 'build')
                    secrets = [args[i + 1] for i, arg in enumerate(args) if arg == '--secret']
                    # The wrapper passes the resolved bundle path (readlink -f).
                    self.assertEqual(secrets, [f'id=build-ca,src={ca.resolve()}'] if trust == '1' else [])
                    self.assertEqual(args[-3:], ['--file', str(ROOT / 'Containerfile'), str(ROOT)])

    def test_build_and_image_inspection_errors(self):
        self.assertEqual(self.run_wrapper('--container-build', FAKE_BUILD_STATUS='17').returncode, 17)
        self.assertNotEqual(self.run_wrapper(FAKE_IMAGE_STATUS='125').returncode, 0)
        self.assertFalse(any(c[0] == 'create' for c in self.calls()))

    def test_exit_status_and_owned_cleanup(self):
        for status in ('7', '125'):
            result = self.run_wrapper(FAKE_EXIT=status)
            self.assertEqual(result.returncode, int(status))
            self.assertIn(['rm', '--force', '--time', '0', '--ignore', OWNED_ID], self.calls())

    def test_successful_restart_check_is_informational_and_real_errors_remain(self):
        diagnostics = ('ERRO[0074] Should restart: false\n'
                       'ERRO[0074] Failed to check if container should restart: unavailable\n'
                       'ERRO[0074] Should restart: true\n')
        result = self.run_wrapper('--version', FAKE_START_STDERR=diagnostics, FAKE_EXIT='17')
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertIn('INFO[0074] Should restart: false\n', result.stderr)
        self.assertNotIn('ERRO[0074] Should restart: false\n', result.stderr)
        self.assertIn('ERRO[0074] Failed to check if container should restart: unavailable\n', result.stderr)
        self.assertIn('ERRO[0074] Should restart: true\n', result.stderr)
        self.assertNotIn('Should restart', result.stdout)

    def test_cleanup_failure_or_stall_preserves_application_status(self):
        for mode in ('FAKE_FAIL', 'FAKE_STALL'):
            for status in (0, 7, 125):
                with self.subTest(mode=mode, status=status):
                    self.log.unlink(missing_ok=True)
                    started = time.monotonic()
                    result = self.run_wrapper(FAKE_EXIT=str(status), **{mode: 'rm'})
                    self.assertEqual(result.returncode, status, result.stderr)
                    self.assertLess(time.monotonic() - started, 22)
                    self.assertIn('cleanup rm failed or timed out', result.stderr)
                    self.assertIn(OWNED_ID, result.stderr)
                    self.assertTrue(all(c[-1] == OWNED_ID for c in self.calls() if c[0] == 'rm'))

    def test_ignored_signals_force_owned_removal(self):
        for name, status in (('TERM', 143), ('INT', 130), ('HUP', 129)):
            with self.subTest(signal=name):
                self.log.unlink(missing_ok=True)
                Path(str(self.log) + '.started').unlink(missing_ok=True)
                proc, diagnostics = self.start_waiting_wrapper(FAKE_WAIT='1', FAKE_IGNORE_SIGNALS='1')
                started = time.monotonic()
                proc.send_signal(getattr(signal, 'SIG' + name))
                _, stderr = proc.communicate(timeout=25)
                self.assertEqual(proc.returncode, status, stderr)
                self.assertGreater(time.monotonic() - started, 3.5)
                self.assertLess(time.monotonic() - started, 22)
                self.assertIn(['kill', '--signal', name, OWNED_ID], self.calls())
                self.assertIn(['rm', '--force', '--time', '0', '--ignore', OWNED_ID], self.calls())
                self.assertEqual(list(diagnostics.iterdir()), [])
                self.assert_no_fake_client()

    def test_stalled_controls_and_repeated_signal_are_bounded(self):
        proc, diagnostics = self.start_waiting_wrapper(FAKE_WAIT='1', FAKE_IGNORE_SIGNALS='1',
                                                       FAKE_STALL='kill,rm')
        started = time.monotonic()
        proc.terminate()
        self.wait_marker(proc, '.stalled-kill')
        proc.send_signal(signal.SIGHUP)
        _, stderr = proc.communicate(timeout=25)
        self.assertEqual(proc.returncode, 143, stderr)
        self.assertLess(time.monotonic() - started, 22)
        self.assertIn('cleanup kill failed or timed out', stderr)
        self.assertIn('cleanup rm failed or timed out', stderr)
        self.assertEqual(len([c for c in self.calls() if c[0] == 'rm']), 1)
        self.assertEqual(list(diagnostics.iterdir()), [])
        self.assert_no_fake_client()

    def test_interrupted_creation_recovers_only_owned_identity(self):
        for phase in ('before', 'after'):
            with self.subTest(phase=phase):
                self.log.unlink(missing_ok=True)
                Path(str(self.log) + '.creating').unlink(missing_ok=True)
                proc, diagnostics = self.start_waiting_wrapper('.creating', FAKE_CREATE_PAUSE=phase)
                create = self.create()
                cid_file = Path(create[create.index('--cidfile') + 1])
                self.assertEqual(cid_file.parent.stat().st_mode & 0o777, 0o700)
                self.assertEqual(cid_file.exists(), phase == 'after')
                proc.terminate()
                _, stderr = proc.communicate(timeout=25)
                self.assertEqual(proc.returncode, 143, stderr)
                self.assertIn(['rm', '--force', '--time', '0', '--ignore', OWNED_ID], self.calls())
                self.assertFalse(any(c[0] == 'start' for c in self.calls()))
                self.assertEqual(list(diagnostics.iterdir()), [])
                self.assert_no_fake_client()

    def test_interrupted_creation_rejects_foreign_recovery_result(self):
        proc, diagnostics = self.start_waiting_wrapper('.creating', FAKE_CREATE_PAUSE='before',
                                                       FAKE_RECOVERY_ID='b' * 64)
        proc.terminate()
        _, stderr = proc.communicate(timeout=25)
        self.assertEqual(proc.returncode, 143, stderr)
        self.assertIn('could not confirm recovered container ownership', stderr)
        self.assertFalse(any(c[0] in ('rm', 'start') for c in self.calls()))
        self.assertEqual(list(diagnostics.iterdir()), [])
        self.assert_no_fake_client()

    def test_interrupted_creation_recovery_calls_are_bounded(self):
        for phase, stalled in (('before', 'ps'), ('after', 'inspect')):
            with self.subTest(phase=phase, stalled=stalled):
                self.log.unlink(missing_ok=True)
                Path(str(self.log) + '.creating').unlink(missing_ok=True)
                proc, diagnostics = self.start_waiting_wrapper('.creating', FAKE_CREATE_PAUSE=phase,
                                                               FAKE_STALL=stalled)
                started = time.monotonic()
                proc.terminate()
                _, stderr = proc.communicate(timeout=25)
                self.assertEqual(proc.returncode, 143, stderr)
                self.assertLess(time.monotonic() - started, 22)
                self.assertIn('failed or timed out', stderr)
                self.assertIn('interrupted creation could not be reconciled', stderr)
                self.assertFalse(any(c[0] in ('rm', 'start') for c in self.calls()))
                self.assertEqual(list(diagnostics.iterdir()), [])
                self.assert_no_fake_client()

    def test_collision_reconciliation_can_be_interrupted(self):
        proc, diagnostics = self.start_waiting_wrapper('.stalled-inspect', FAKE_COLLISION='1',
                                                       FAKE_STALL='inspect')
        proc.terminate()
        _, stderr = proc.communicate(timeout=25)
        self.assertEqual(proc.returncode, 143, stderr)
        self.assertFalse(any(c[0] in ('rm', 'start') for c in self.calls()))
        self.assertEqual(list(diagnostics.iterdir()), [])
        with self.assertRaises(ProcessLookupError):
            os.kill(int(Path(str(self.log) + '.stalled-inspect').read_text()), 0)

    def test_failed_create_after_id_publication_is_cleaned(self):
        result = self.run_wrapper(FAKE_CREATED_STATUS='19')
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertIn(['rm', '--force', '--time', '0', '--ignore', OWNED_ID], self.calls())
        self.assertFalse(any(c[0] == 'start' for c in self.calls()))

    def test_failed_signal_delivery_still_removes_owned_container(self):
        proc, diagnostics = self.start_waiting_wrapper(FAKE_WAIT='1', FAKE_IGNORE_SIGNALS='1',
                                                       FAKE_FAIL='kill')
        proc.terminate()
        _, stderr = proc.communicate(timeout=25)
        self.assertEqual(proc.returncode, 143, stderr)
        self.assertIn('cleanup kill failed or timed out', stderr)
        self.assertIn(['rm', '--force', '--time', '0', '--ignore', OWNED_ID], self.calls())
        self.assertEqual(list(diagnostics.iterdir()), [])
        self.assert_no_fake_client()

    def test_timeout_prerequisite_and_independent_help(self):
        restricted = self.base / 'prerequisite-bin'
        restricted.mkdir()
        for name, target in (('bash', '/bin/bash'), ('cat', '/bin/cat'),
                             ('podman', str(self.bin / 'podman'))):
            (restricted / name).symlink_to(target)
        for unsupported in (False, True):
            with self.subTest(unsupported=unsupported):
                if unsupported:
                    timeout = restricted / 'timeout'
                    timeout.write_text('#!/bin/sh\nprintf "unsupported timeout\\n"\n')
                    timeout.chmod(0o755)
                result = self.run_wrapper(PATH=str(restricted))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('GNU timeout is required', result.stderr)
                self.assertFalse(self.calls())
                self.assertFalse(self.state.exists())
                help_result = self.run_wrapper('--container-help', PATH=str(restricted))
                self.assertEqual(help_result.returncode, 0, help_result.stderr)

    def test_healthy_build_and_session_outlive_shutdown_budget(self):
        started = time.monotonic()
        result = subprocess.run([str(WRAPPER), '--container-build'], cwd=self.project,
                                env=self.env | {'FAKE_BUILD_DELAY': '21', 'FAKE_START_DELAY': '21'},
                                input='healthy input', text=True, capture_output=True, timeout=55)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(time.monotonic() - started, 40)
        self.assertIn('stdin:healthy input', result.stdout)

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

    def test_verification_preserves_exact_record_boundaries_and_status(self):
        for query, valid in (('INFO', 'true linux false'), ('SOCKET', 'true /host/socket with spaces')):
            for raw, accepted in ((valid, True), (valid + '\n', True), ('', False),
                                  (valid + '\n\n', False), (valid + '\n\n\n', False),
                                  ('\n' + valid, False), (valid + '\n\nextra\n', False),
                                  (valid + '\nextra\n', False)):
                with self.subTest(query=query, raw=repr(raw)):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper('--container-build', CLAUDE_CONTAINER_PODMAN='1',
                                              **{f'FAKE_{query}_RAW': raw})
                    self.assertEqual(result.returncode == 0, accepted, result.stderr)
                    operations = [c for c in self.calls() if c[0] in ('image', 'build', 'create')]
                    self.assertEqual(bool(operations), accepted)
                    if query == 'SOCKET' and not accepted:
                        self.assertIn(str(self.socket_path), result.stderr)
                    if query == 'SOCKET' and accepted:
                        self.assertIn('/host/socket with spaces:/run/podman/podman.sock:rw', self.create())
            for raw in (valid, valid + '\n', valid + '\n\n'):
                with self.subTest(query=query, failed_after_output=repr(raw)):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper('--container-build', CLAUDE_CONTAINER_PODMAN='1',
                                              **{f'FAKE_{query}_RAW': raw, f'FAKE_{query}_STATUS': '19'})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('cannot query Podman', result.stderr)
                    self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_delegated_response_rejects_carriage_returns_before_image_operations(self):
        responses = ('true /host/socket with spaces\r\n',
                     'true /host/podman.sock\r', '\rtrue /host/podman.sock\n',
                     'tr\rue /host/podman.sock\n', 'true\r /host/podman.sock\n',
                     'true \r/host/podman.sock\n', 'true /host/pod\rman.sock\n')
        for options in ((), ('--container-build',)):
            for raw in responses:
                with self.subTest(options=options, raw=repr(raw)):
                    self.log.unlink(missing_ok=True)
                    result = self.run_wrapper(*options, CLAUDE_CONTAINER_PODMAN='1',
                                              FAKE_SOCKET_RAW=raw)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f'invalid Podman socket response: {self.socket_path}', result.stderr)
                    self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))

    def test_response_validation_composes_with_launch_modes(self):
        for isolated in ('', str(self.state)):
            for shell in (False, True):
                for service in ('0', '1'):
                    for bad_query in ('', 'INFO', 'SOCKET'):
                        with self.subTest(isolated=isolated, shell=shell, service=service, query=bad_query):
                            self.log.unlink(missing_ok=True)
                            options = ['--container-build', '--container-git-worktree']
                            if shell:
                                options.append('--container-shell')
                            values = {'FAKE_INFO_RAW': 'true linux false\n',
                                      'FAKE_SOCKET_RAW': 'true /host/socket with spaces\n'}
                            if bad_query:
                                values[f'FAKE_{bad_query}_RAW'] += '\n'
                            accepted = not bad_query or (bad_query == 'SOCKET' and service == '0')
                            result = self.run_wrapper(*options, CLAUDE_CONTAINER_STATE_DIR=isolated,
                                                      CLAUDE_CONTAINER_PODMAN=service, **values)
                            self.assertEqual(result.returncode == 0, accepted, result.stderr)
                            self.assertEqual(any(c[0] in ('build', 'image', 'create') for c in self.calls()), accepted)
                            if service == '0':
                                self.assertFalse(any(c[0] == '--remote' for c in self.calls()))

    def test_delegated_cr_response_preserves_query_failure_and_disabled_access(self):
        for raw in ('true /host/podman.sock\r\n', 'true /host/pod\rman.sock'):
            with self.subTest(raw=repr(raw), query_failure=True):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper('--container-build', CLAUDE_CONTAINER_PODMAN='1',
                                          FAKE_SOCKET_RAW=raw, FAKE_SOCKET_STATUS='19')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'cannot query Podman socket: {self.socket_path}', result.stderr)
                self.assertNotIn('invalid Podman socket response', result.stderr)
                self.assertFalse(any(c[0] in ('image', 'build', 'create') for c in self.calls()))
            with self.subTest(raw=repr(raw), delegation_disabled=True):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='0', FAKE_SOCKET_RAW=raw)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(any(c[0] == '--remote' for c in self.calls()))
                self.assertNotIn('CONTAINER_HOST=unix:///run/podman/podman.sock', self.create())

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

    def test_podman5_unix_url_host_socket_is_bound_as_path(self):
        # Podman 5 reports Host.RemoteSocket.Path as a unix:// URL.
        for reported, accepted in (('unix:///host/podman.sock', True), ('unix://relative.sock', False)):
            with self.subTest(reported=reported):
                self.log.unlink(missing_ok=True)
                result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1', FAKE_HOST_SOCKET=reported)
                self.assertEqual(result.returncode == 0, accepted, result.stderr)
                if accepted:
                    self.assertIn('/host/podman.sock:/run/podman/podman.sock:rw', self.create())
                    self.assertNotIn('unix:///host/podman.sock:', self.create())
                else:
                    self.assertIn('absolute host socket path', result.stderr)

    def test_socket_fallback_and_invalid_sources(self):
        default = f'/run/user/{os.getuid()}/podman/podman.sock'
        result = self.run_wrapper(CLAUDE_CONTAINER_PODMAN='1', CLAUDE_CONTAINER_PODMAN_SOCKET='')
        if Path(default).exists():
            # A real user service exists on this host; the fake engine answers for it,
            # so verify the selected fallback endpoint instead of a missing-socket error.
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(next(c for c in self.calls() if c[0] == '--remote')[2], 'unix://' + default)
        else:
            self.assertIn(default, result.stderr)
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
                            self.assertNotIn('--read-only-tmpfs=false', create)
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
                self.assertFalse(any(x.startswith(('--privileged', '--cap-add')) for x in create))
                self.assertEqual([x for x in create if x.startswith('--security-opt')],
                                 ['--security-opt=no-new-privileges'])
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
                self.assertIn(['rm', '--force', '--time', '0', '--ignore', OWNED_ID], self.calls())
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.communicate()


if __name__ == '__main__':
    unittest.main()
