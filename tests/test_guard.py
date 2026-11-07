"""Native guard component tests. Mocked passes are never enforcement evidence."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENABLED = os.environ.get('CLAUDE_GUARD_TESTS') == '1'


@unittest.skipUnless(ENABLED, 'run tests/run-runtime.sh --guard with a prepared toolchain')
class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(prefix='guard-component-', dir=os.environ.get('CLAUDE_TEST_STATE_ROOT'))
        cls.addClassCleanup(cls.storage.cleanup)
        cls.base = Path(cls.storage.name)
        cls.binary = cls.base / 'claude-egress-guard'
        cls.mock = cls.base / 'guard-component-mock'
        cls.toolchain = os.environ['CLAUDE_GUARD_TOOLCHAIN']
        if not re.fullmatch(r'(sha256:)?[a-f0-9]{64}', cls.toolchain):
            raise RuntimeError('test toolchain must be an immutable prepared image ID')
        cls.compile(cls.binary)
        cls.compile(cls.mock, mock=True)

    @classmethod
    def compile(cls, destination, mock=False):
        arguments = ['podman', 'run', '--rm', '--network=none', '--read-only',
                     '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
                     '--volume', f'{ROOT}:{ROOT}:ro', '--volume', f'{cls.base}:{cls.base}:rw',
                     '--workdir', str(ROOT), '--env', 'LC_ALL=C', '--env', 'SOURCE_DATE_EPOCH=0',
                     cls.toolchain, '-std=c11', '-O2', '-static', '-Wall', '-Wextra', '-Werror',
                     '-D_FORTIFY_SOURCE=2', '-fstack-protector-strong', '-fno-ident',
                     '-Wl,--build-id=none', '-I', str(ROOT / 'network'), str(ROOT / 'network/guard.c')]
        if mock:
            arguments.extend([str(ROOT / 'tests/guard_syscall_mock.c'),
                              '-Wl,--wrap=syscall,--wrap=prctl,--wrap=open,--wrap=mkdir,--wrap=fstatfs,--wrap=fstatvfs'])
        result = subprocess.run([*arguments, '-o', str(destination)], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    def setUp(self):
        self.fixture = Path(tempfile.mkdtemp(prefix='case-', dir=self.base))
        self.addCleanup(shutil.rmtree, self.fixture)
        for name in ('tmp', 'run', 'var/tmp', 'run/claude-egress'):
            (self.fixture / name).mkdir(parents=True, exist_ok=True)
        (self.fixture / 'mountinfo').write_text('1 0 0:1 / /tmp rw - tmpfs tmpfs rw\n2 0 0:2 / /run rw - tmpfs tmpfs rw\n3 0 0:3 / /var/tmp rw - tmpfs tmpfs rw\n')
        self.marker = self.fixture / 'agent-started'
        self.env = os.environ | {'CLAUDE_GUARD_TEST_ROOT': str(self.fixture),
                                'CLAUDE_GUARD_TEST_MODE': 'offline',
                                'CLAUDE_GUARD_TEST_ABI': '3', 'CLAUDE_GUARD_TEST_FAULT': ''}

    def run_guard(self, *command, production=False, mode='offline', **environment):
        binary = self.binary if production else self.mock
        return subprocess.run([str(binary), '--' + mode, '--', *command],
                              env=self.env | {'CLAUDE_GUARD_TEST_MODE': mode} | environment,
                              input='synthetic stdin', capture_output=True, text=True, timeout=10)

    def sentinel(self):
        return [sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).touch()', str(self.marker)]

    def test_static_identity_and_repeatable_build(self):
        data = self.binary.read_bytes()
        self.assertEqual(data[:6], b'\x7fELF\x02\x01')
        phoff = struct.unpack_from('<Q', data, 32)[0]
        phentsize, phnum = struct.unpack_from('<HH', data, 54)
        types = {struct.unpack_from('<I', data, phoff + i * phentsize)[0] for i in range(phnum)}
        self.assertTrue(types.isdisjoint({2, 3}), 'dynamic or interpreter program header')
        self.assertNotIn(b'CLAUDE_GUARD_TEST_', data)
        repeated = self.base / 'guard-repeat'
        self.compile(repeated)
        self.assertEqual(hashlib.sha256(data).digest(), hashlib.sha256(repeated.read_bytes()).digest())
        result = subprocess.run([str(self.binary), '--version'], capture_output=True, text=True, check=True)
        self.assertIn('abi3-seccomp-mux-v1 required-abi=3', result.stdout)
        print('production guard sha256=' + hashlib.sha256(data).hexdigest(), flush=True)

    def test_actual_kernel_query_refuses_unsupported_abi(self):
        result = subprocess.run([str(self.binary), '--probe'], capture_output=True, text=True)
        if result.returncode == 0:
            self.assertIn('query-only, enforcement unverified', result.stdout)
        else:
            self.assertEqual(result.returncode, 78)
            self.assertIn('Landlock ABI', result.stderr)
            result = self.run_guard(*self.sentinel(), production=True)
            self.assertEqual(result.returncode, 78)
            self.assertFalse(self.marker.exists())
            print('actual kernel rejection: ' + result.stderr.strip(), flush=True)

    def test_old_abi_and_setup_errors_never_execute_program(self):
        for values, stage in (
            ({'CLAUDE_GUARD_TEST_ABI': '1'}, 'ABI 1 is unsupported'),
            ({'CLAUDE_GUARD_TEST_ABI': '2'}, 'ABI 2 is unsupported'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'query'}, 'ABI query'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'descriptors'}, 'descriptor cleanup'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'filesystem'}, 'private runtime directory validation'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'oci-profile'}, 'existing OCI seccomp validation'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'privileges'}, 'no_new_privs'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'create'}, 'ruleset creation'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'rule'}, 'path rule installation'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'restrict'}, 'Landlock enforcement'),
            ({'CLAUDE_GUARD_TEST_FAULT': 'filter'}, 'seccomp filter installation'),
        ):
            with self.subTest(values=values):
                result = self.run_guard(*self.sentinel(), **values)
                self.assertEqual(result.returncode, 78, result.stderr)
                self.assertIn(stage, result.stderr)
                self.assertFalse(self.marker.exists())

    def test_rule_sequence_arguments_stdin_and_exit_status_component_only(self):
        command = [sys.executable, '-c', 'import os,sys,json; print(json.dumps([sys.argv[1:],sys.stdin.read(),os.environ["XDG_RUNTIME_DIR"]])); sys.exit(37)', 'space value', '']
        result = self.run_guard(*command, XDG_RUNTIME_DIR='/unsafe/state')
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(json.loads(result.stdout), [['space value', ''], 'synthetic stdin', '/tmp/claude-runtime'])
        self.assertIn('COMPONENT MOCK', result.stderr)

    def test_provider_requires_exact_private_socket_on_readonly_mount(self):
        endpoint = self.fixture / 'run/claude-egress/proxy.sock'
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        directory_fd = os.open(endpoint.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            # The host-visible native volume path can exceed sun_path's limit.
            # Bind through this process-local alias; the inode is the same.
            listener.bind(f'/proc/self/fd/{directory_fd}/proxy.sock')
        finally:
            os.close(directory_fd)
        endpoint.chmod(0o700)
        endpoint.parent.chmod(0o700)
        listener.listen(8)
        result = self.run_guard(*self.sentinel(), mode='provider')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.marker.unlink()
        for permission, fault, stage in ((0o777, '', 'proxy identity/read-only mount validation'),
                                         (0o700, 'writable-proxy', 'proxy identity/read-only mount validation')):
            endpoint.chmod(permission)
            result = self.run_guard(*self.sentinel(), mode='provider', CLAUDE_GUARD_TEST_FAULT=fault)
            self.assertEqual(result.returncode, 78, result.stderr)
            self.assertIn(stage, result.stderr)
            self.assertFalse(self.marker.exists())

    def test_extra_descriptors_are_closed_and_socket_stdio_rejected(self):
        with self.marker.open('wb') as handle:
            inode = os.fstat(handle.fileno()).st_ino
            command = [str(self.mock), '--offline', '--', sys.executable, '-c',
                       'import os,sys; fd=int(sys.argv[1]); inode=int(sys.argv[2]);\ntry: found=os.fstat(fd).st_ino==inode\nexcept OSError: found=False\nassert not found', str(handle.fileno()), str(inode)]
            result = subprocess.run(command, env=self.env, pass_fds=(handle.fileno(),),
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)
        result = subprocess.run([str(self.mock), '--offline', '--', '/bin/true'], env=self.env,
                                stdin=left, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 78)
        self.assertIn('standard I/O validation', result.stderr)

    def test_namespace_stdio_is_not_an_ordinary_redirected_file(self):
        with open('/proc/self/ns/net', 'rb') as namespace:
            result = subprocess.run([str(self.binary), '--offline', '--', '/bin/true'],
                stdin=namespace, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 78, result.stderr)
        self.assertIn('standard I/O validation', result.stderr)

    def test_runtime_symlink_and_unsafe_mode_are_rejected(self):
        runtime = self.fixture / 'tmp/claude-runtime'
        runtime.symlink_to(self.fixture / 'run', target_is_directory=True)
        result = self.run_guard('/bin/true')
        self.assertEqual(result.returncode, 78)
        runtime.unlink()
        runtime.mkdir(mode=0o777)
        runtime.chmod(0o777)
        result = self.run_guard('/bin/true')
        self.assertEqual(result.returncode, 78)
        self.assertIn('runtime directory validation', result.stderr)

    def production_container(self, script, mode='offline', extra=(), program=None):
        image = os.environ.get('CLAUDE_CONTAINER_IMAGE', 'localhost/claude-code:latest')
        command = ['podman', 'run', '--rm', '--interactive', '--network=none',
                   '--pid=private', '--ipc=private', '--read-only',
                   '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
                   '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777',
                   '--tmpfs', '/run:rw,nosuid,nodev,noexec,size=16m',
                   '--tmpfs', '/var/tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777',
                   '--volume', f'{self.binary}:/usr/local/bin/guard:ro',
                   '--volume', f'{self.fixture}:/workspace:rw',
                   '--volume', f'{ROOT / "network/resolv.conf"}:/etc/resolv.conf:ro',
                   *extra, '--entrypoint', '/usr/local/bin/guard', image,
                   '--' + mode, '--', *(program or ['/usr/bin/python3', '-I', '-c', script])]
        return subprocess.run(command, input='', capture_output=True, text=True, timeout=60)

    def test_production_filter_and_landlock_on_real_rootless_kernel(self):
        endpoint = self.fixture / 'external.sock'
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        directory = os.open(self.fixture, os.O_RDONLY | os.O_DIRECTORY)
        try:
            listener.bind(f'/proc/self/fd/{directory}/external.sock')
        finally:
            os.close(directory)
        listener.listen(4)
        (self.fixture / 'alias.sock').symlink_to('external.sock')
        result = self.production_container((ROOT / 'tests/guard_runtime_fixture.py').read_text())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['native_guard'], 'passed')
        print('real guarded runtime: ' + result.stdout.strip(), flush=True)

    def test_existing_late_sockets_and_aliases_across_bind_roots(self):
        import threading
        import time
        sockets = []
        directory = os.open(self.fixture, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for name, kind in [('stream.sock', socket.SOCK_STREAM),
                               ('seq.sock', socket.SOCK_SEQPACKET),
                               ('dgram.sock', socket.SOCK_DGRAM)]:
                server = socket.socket(socket.AF_UNIX, kind)
                self.addCleanup(server.close)
                server.bind(f'/proc/self/fd/{directory}/{name}')
                server.settimeout(10)
                if kind != socket.SOCK_DGRAM:
                    server.listen(4)
                sockets.append((name, kind, server))
        finally:
            os.close(directory)
        (self.fixture / 'alias.sock').symlink_to('stream.sock')
        os.link(self.fixture / 'stream.sock', self.fixture / 'hardlink.sock')
        image = os.environ.get('CLAUDE_CONTAINER_IMAGE', 'localhost/claude-code:latest')
        # Unguarded network=none positive control reaches every synthetic type.
        control = "import socket;\nfor path,kind in [('stream.sock',1),('dgram.sock',2),('seq.sock',5)]:\n s=socket.socket(socket.AF_UNIX,kind); s.connect('/workspace/'+path); s.send(b'unguarded-control'); s.close()\nsocket.socket(40,socket.SOCK_STREAM).close()"
        result = subprocess.run(['podman', 'run', '--rm', '--network=none',
            '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
            '--volume', f'{self.fixture}:/workspace:rw', '--entrypoint', 'python3', image,
            '-I', '-c', control], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        for _, kind, server in sockets:
            if kind == socket.SOCK_DGRAM:
                data = server.recv(64)
            else:
                peer, _ = server.accept()
                with peer:
                    data = peer.recv(64)
            self.assertEqual(data, b'unguarded-control')
        late = socket.socket(socket.AF_UNIX)
        self.addCleanup(late.close)
        errors = []
        def create_late():
            try:
                deadline = time.monotonic() + 10
                while not (self.fixture / 'guard-ready').exists():
                    if time.monotonic() >= deadline:
                        raise RuntimeError('guard readiness timed out')
                    time.sleep(0.02)
                fd = os.open(self.fixture, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    late.bind(f'/proc/self/fd/{fd}/late.sock')
                finally:
                    os.close(fd)
                late.listen(4)
            except BaseException as error:
                errors.append(error)
        worker = threading.Thread(target=create_late)
        worker.start()
        script = (ROOT / 'tests/guard_bind_fixture.py').read_text()
        result = self.production_container(script, extra=[
            '--volume', f'{self.fixture}:/worktree-parent:rw',
            '--volume', f'{self.fixture}:/shared-state:rw',
            '--volume', f'{self.fixture}:/isolated-home:rw'])
        worker.join(12)
        self.assertFalse(errors, errors)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('all-bind-roots-denied', result.stdout)
        for _, kind, server in sockets:
            server.settimeout(.1)
            with self.assertRaises(socket.timeout):
                server.recv(1) if kind == socket.SOCK_DGRAM else server.accept()

    def test_real_nested_runtime_mount_is_rejected_before_exec(self):
        result = self.production_container("open('/workspace/agent-started','w').close()", extra=[
            '--volume', f'{self.fixture}:/tmp/untrusted-nested:rw'])
        self.assertEqual(result.returncode, 78, result.stderr)
        self.assertIn('nested private IPC mount validation', result.stderr)
        self.assertFalse(self.marker.exists())

    def test_real_provider_preconnect_and_descriptor_contract(self):
        import threading
        endpoint = self.fixture / 'run/claude-egress/proxy.sock'
        endpoint.parent.chmod(0o700)
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        directory = os.open(endpoint.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            listener.bind(f'/proc/self/fd/{directory}/proxy.sock')
        finally:
            os.close(directory)
        endpoint.chmod(0o700)
        listener.listen(4)
        listener.settimeout(10)
        received = []
        def peer():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(10)
                received.append(connection.recv(32))
                connection.sendall(b'policy-channel-only')
        worker = threading.Thread(target=peer)
        worker.start()
        script = "import os,socket; s=socket.socket(fileno=3); s.setblocking(True); s.sendall(b'approved-channel'); assert s.recv(32)==b'policy-channel-only'; print('provider-channel-ok')"
        result = self.production_container(script, mode='provider', extra=(
            '--volume', f'{endpoint.parent}:/run/claude-egress:ro'))
        worker.join(12)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(received, [b'approved-channel'])

    def test_guarded_multiplex_proxy_tls_streaming_and_websocket(self):
        import time
        from test_network_runtime import NetworkRuntime
        harness = NetworkRuntime('test_provider_uses_real_proxy_and_cleans_resources')
        harness.guard_output = type('Output', (), {'name': str(self.base)})()
        # setUp expects packaged assets; provide the component's real digest.
        (self.base / 'claude-egress-guard.sha256').write_text(hashlib.sha256(self.binary.read_bytes()).hexdigest() + '  claude-egress-guard\n')
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        context, environment = harness.provider_fixture()
        transport = self.fixture / 'transport'
        transport.mkdir(mode=0o700)
        config = self.fixture / 'config'
        config.mkdir(mode=0o700)
        shutil.copyfile(harness.policy_file, config / 'policy.json')
        sys.path.insert(0, str(ROOT / "network"))
        from policy import revision
        manifest = {'sha256': hashlib.sha256(self.binary.read_bytes()).hexdigest(),
                    'revision': 'abi3-seccomp-mux-v1', 'required_abi': 3,
                    'filter': 'native-x86_64-v1', 'protocol': 1,
                    'tls_enforcement': 'tls-clienthello-sni-v1',
                    'policy': revision(json.loads((config / 'policy.json').read_text())),
                    'profile': 'controlled-test', 'session': 'guarded-synthetic'}
        (config / 'manifest.json').write_text(json.dumps(manifest))
        logs = self.fixture / 'logs'
        logs.mkdir(mode=0o700)
        name = harness.podman('create', '--read-only', '--userns=keep-id', '--user',
                              f'{os.getuid()}:{os.getgid()}',
                              '--volume', f'{transport}:/transport:rw',
                              '--volume', f'{config}:/config:ro',
                              '--volume', f'{logs}:/logs:rw',
                              '--env', 'EGRESS_PROFILE=controlled-test',
                              '--env', 'EGRESS_SESSION=guarded-synthetic',
                              environment['CLAUDE_CONTAINER_EGRESS_IMAGE'])
        self.addCleanup(harness.podman, 'rm', '--force', '--time', '0', '--ignore', name)
        harness.podman('start', name)
        deadline = time.monotonic() + 10
        while not (transport / 'ready').exists():
            self.assertLess(time.monotonic(), deadline, harness.podman('logs', name))
            time.sleep(0.05)
        shutil.copyfile(context / 'cert.pem', self.fixture / 'cert.pem')
        script = (ROOT / 'tests/guard_mux_fixture.py').read_text() + '\n' + (ROOT / 'tests/tls_binding_fixture.py').read_text()
        (self.fixture / 'client.py').write_text(script)
        extra = ['--volume', f'{transport}:/run/claude-egress:ro',
                 '--volume', f'{ROOT / "network/relay.py"}:/opt/claude-egress/relay.py:ro',
                 '--volume', f'{ROOT / "network/mux.py"}:/opt/claude-egress/mux.py:ro',
                 '--env', 'HTTPS_PROXY=http://127.0.0.1:18080',
                 '--env', 'https_proxy=http://127.0.0.1:18080']
        result = self.production_container('', mode='provider', extra=extra, program=[
            '/usr/bin/python3', '-I', '/opt/claude-egress/relay.py',
            '/usr/bin/python3', '-I', '/workspace/client.py'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + harness.podman('logs', name))
        self.assertIn('guarded-mux-tls-ok', result.stdout)

    def test_operator_packaging_uses_same_static_immutable_artifact(self):
        destination = self.fixture / 'packaged'
        destination.mkdir(mode=0o700)
        result = subprocess.run(['bash', str(ROOT / 'network/build-guard.sh'), str(destination)],
            env=os.environ | {'CLAUDE_CONTAINER_MAINTENANCE': '1', 'CLAUDE_GUARD_TOOLCHAIN': self.toolchain},
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((destination / 'claude-egress-guard').read_bytes(), self.binary.read_bytes())
        self.assertEqual((destination / 'claude-egress-guard.sha256').read_text(),
                         hashlib.sha256(self.binary.read_bytes()).hexdigest() + '  claude-egress-guard\n')

    def test_no_runtime_bypass_and_loader_environment_cannot_preempt_guard(self):
        # This launch has no private runtime tmpfs and must reject setup before
        # executing any injected hook or application sentinel.
        payload = self.fixture / 'initialization.sh'
        payload.write_text('touch ' + str(self.marker) + '\n')
        result = self.run_guard(*self.sentinel(), production=True, LD_PRELOAD=str(payload),
                                LD_AUDIT=str(payload), BASH_ENV=str(payload), ENV=str(payload),
                                PYTHONSTARTUP=str(payload), NODE_OPTIONS='--require=' + str(payload),
                                CLAUDE_GUARD_TEST_ABI='999')
        self.assertEqual(result.returncode, 78)
        self.assertFalse(self.marker.exists())
        result = subprocess.run([str(self.binary), '--probe', '--', '/bin/true'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 64)
