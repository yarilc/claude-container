"""Opt-in production-wrapper network acceptance with synthetic state."""
import json
import os
from pathlib import Path
import shutil
import select
import signal
import subprocess
import tempfile
import unittest
import uuid
import time


ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get('CLAUDE_CONTAINER_IMAGE', 'localhost/claude-code:latest')


@unittest.skipUnless(os.environ.get('CLAUDE_RUNTIME_TESTS') == '1', 'requires real rootless engine')
class NetworkRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard_output = tempfile.TemporaryDirectory(prefix='network-guard-', dir=os.environ.get('CLAUDE_TEST_STATE_ROOT'))
        cls.addClassCleanup(cls.guard_output.cleanup)
        result = subprocess.run(['bash', str(ROOT / 'network/build-guard.sh'), cls.guard_output.name],
            env=os.environ | {'CLAUDE_CONTAINER_MAINTENANCE': '1'}, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

    def podman(self, *args):
        result = subprocess.run(['podman', *args], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='network-runtime-', dir=os.environ.get('CLAUDE_TEST_STATE_ROOT')))
        self.addCleanup(shutil.rmtree, self.base)
        self.install = self.base / 'installed'
        self.install.mkdir(mode=0o700)
        (self.install / 'network').mkdir(mode=0o700)
        self.wrapper = self.install / 'claude-container.sh'
        shutil.copyfile(ROOT / 'claude-container.sh', self.wrapper)
        self.wrapper.chmod(0o700)
        for name in ('control.py', 'policy.py', 'relay.py', 'mux.py', 'resolv.conf'):
            shutil.copyfile(ROOT / 'network' / name, self.install / 'network' / name)
        binary_dir = self.install / 'network/bin'
        binary_dir.mkdir(mode=0o700)
        for name in ('claude-egress-guard', 'claude-egress-guard.sha256'):
            shutil.copyfile(Path(self.guard_output.name) / name, binary_dir / name)
        (binary_dir / 'claude-egress-guard').chmod(0o500)
        self.project = self.base / 'project'
        self.project.mkdir()
        self.runtime = self.base / 'runtime'
        self.runtime.mkdir(mode=0o700)
        (self.base / 'home').mkdir(mode=0o700)
        self.env = {'PATH': os.environ['PATH'], 'HOME': str(self.base / 'home'),
                    'CONTAINER_HOST': os.environ['CONTAINER_HOST'],
                    'CLAUDE_CONTAINER_STATE_DIR': str(self.base / 'state'),
                    'CLAUDE_CONTAINER_IMAGE': IMAGE,
                    'CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR': str(self.runtime)}

    def shell(self, script, **environment):
        return subprocess.run([str(self.wrapper), '--container-shell'], cwd=self.project,
                              env=self.env | environment, input='set -Eeuo pipefail\n' + script,
                              text=True, capture_output=True, timeout=45)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_restricted_delegation_grid_and_disabled_override(self):
        for mode in ('offline', 'provider'):
            for state in ('', self.env['CLAUDE_CONTAINER_STATE_DIR']):
                for shell in (False, True):
                    for yolo in ('0', '1'):
                        result = subprocess.run([str(self.wrapper), *(['--container-shell'] if shell else ['--version'])],
                            cwd=self.project, env=self.env | {'CLAUDE_CONTAINER_NETWORK':mode,
                                'CLAUDE_CONTAINER_STATE_DIR':state, 'CLAUDE_YOLO':yolo,
                                'CLAUDE_CONTAINER_PODMAN':'1'}, input='', capture_output=True, text=True, timeout=10)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn('rejects CLAUDE_CONTAINER_PODMAN=1', result.stderr)
        _, provider = self.provider_fixture()
        for mode in ('offline', 'provider'):
            for state in ('', self.env['CLAUDE_CONTAINER_STATE_DIR']):
                environment = provider | {'CLAUDE_CONTAINER_NETWORK':mode}
                result = self.shell('test ! -S /run/podman/podman.sock; test -z "${CONTAINER_HOST+x}"\n',
                    **environment, CLAUDE_CONTAINER_STATE_DIR=state,
                    CLAUDE_CONTAINER_PODMAN='true', CLAUDE_CONTAINER_PODMAN_SOCKET='/absent/disabled.sock')
                self.assert_success(result)

    def test_offline_defaults_and_delegation_rejection(self):
        result = self.shell("python3 - <<'PY'\nimport os,socket\nassert os.listdir('/sys/class/net') == ['lo']\nassert 'HTTP_PROXY' not in os.environ\ntry: socket.create_connection(('1.1.1.1',443),1)\nexcept OSError: pass\nelse: raise AssertionError('direct route')\nPY\n")
        self.assert_success(result)
        self.assertIn('mode=offline', result.stderr)
        self.assertFalse(list(self.runtime.iterdir()))
        result = self.shell('true\n', CLAUDE_CONTAINER_PODMAN='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rejects CLAUDE_CONTAINER_PODMAN=1', result.stderr)

    def provider_fixture(self):
        context = self.base / 'fixture'
        context.mkdir(mode=0o700)
        # Build production proxy from the checked-out source and pin the result
        # by immutable image ID for this disposable operator policy invocation.
        proxy_tag = 'localhost/claude-egress-test-' + uuid.uuid4().hex
        self.addCleanup(self.podman, 'rmi', '--force', proxy_tag)
        self.podman('build', '--pull=never', '--tag', proxy_tag, '--file',
                    str(ROOT / 'network/Containerfile'), str(ROOT / 'network'))
        proxy_id = self.podman('image', 'inspect', '--format', '{{.Id}}', proxy_tag)
        self.podman('run', '--rm', '--network=none', '--userns=keep-id',
                    '--user', f'{os.getuid()}:{os.getgid()}', '--volume', f'{context}:/fixture:rw',
                    '--entrypoint', 'openssl', IMAGE, 'req', '-x509', '-newkey', 'rsa:2048',
                    '-nodes', '-days', '1', '-subj', '/CN=localhost.localdomain', '-addext',
                    'subjectAltName=DNS:localhost.localdomain', '-keyout', '/fixture/key.pem',
                    '-out', '/fixture/cert.pem')
        shutil.copyfile(ROOT / 'tests/network_tls_fixture.py', context / 'upstream.py')
        (context / 'Containerfile').write_text(f'FROM {proxy_id}\nCOPY cert.pem key.pem upstream.py /test/\nENTRYPOINT ["python3", "/test/upstream.py"]\n')
        # Synthetic key is world-readable inside only this disposable test image.
        (context / 'key.pem').chmod(0o644)
        fixture_tag = 'localhost/claude-tls-test-' + uuid.uuid4().hex
        self.addCleanup(self.podman, 'rmi', '--force', fixture_tag)
        self.podman('build', '--pull=never', '--tag', fixture_tag, str(context))
        fixture_id = self.podman('image', 'inspect', '--format', '{{.Id}}', fixture_tag)
        value = json.loads((ROOT / 'network/policies/default.json').read_text())
        value['profiles']['controlled-test'] = {'authentication': 'custom', 'disable_optional_traffic': True,
            'destinations': [{'host': 'localhost.localdomain', 'port': 8443, 'addresses': ['127.0.0.1', '::1']}]}
        policy_file = self.install / 'test-policy.json'
        policy_file.write_text(json.dumps(value))
        shutil.copyfile(context / 'cert.pem', self.project / 'cert.pem')
        environment = {'CLAUDE_CONTAINER_NETWORK': 'provider',
                       'CLAUDE_CONTAINER_NETWORK_POLICY': str(policy_file),
                       'CLAUDE_CONTAINER_NETWORK_PROFILE': 'controlled-test',
                       'CLAUDE_CONTAINER_EGRESS_IMAGE': fixture_id}
        self.policy_file = policy_file
        return context, environment

    def test_provider_uses_real_proxy_and_cleans_resources(self):
        context, environment = self.provider_fixture()
        result = self.shell("""test "$HTTP_PROXY" = http://127.0.0.1:18080
test "$http_proxy" = "$HTTP_PROXY"
test "$NO_PROXY" = localhost,127.0.0.1,::1
test -z "${ALL_PROXY+x}"
test -z "${SSL_CERT_FILE+x}${REQUESTS_CA_BUNDLE+x}${CURL_CA_BUNDLE+x}${NODE_EXTRA_CA_CERTS+x}"
test ! -e /config/policy.json
test ! -e /logs/denials.jsonl
test "$(curl --fail --silent --show-error --max-time 10 --cacert cert.pem https://localhost.localdomain:8443/)" = controlled-production-proxy-ok
test "$(curl --fail --silent --show-error --max-time 10 --cacert cert.pem https://localhost.localdomain:8443/stream)" = abc
if curl --silent --show-error --max-time 3 https://localhost.localdomain:8443/; then exit 43; fi
if curl --silent --show-error --max-time 3 https://unapproved.test/; then exit 41; fi
if curl --location --fail --silent --show-error --max-time 3 --cacert cert.pem https://localhost.localdomain:8443/redirect; then exit 44; fi
if curl --fail --silent --show-error --max-time 3 https://localhost.localdomain.evil.test:8443/; then exit 45; fi
if curl --fail --silent --show-error --max-time 3 https://localhost.localdomain:8444/; then exit 46; fi
if curl --noproxy '' --fail --silent --show-error --max-time 3 https://127.0.0.1:8443/; then exit 47; fi
if curl --fail --silent --show-error --max-time 3 http://127.0.0.1:18080/admin; then exit 48; fi
if env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy curl --max-time 3 https://1.1.1.1/; then exit 42; fi
python3 - <<'PY'
import socket,ssl
connection=socket.create_connection(('127.0.0.1',18080),3)
connection.sendall(b'CONNECT localhost.localdomain:8443 HTTP/1.1\\r\\n\\r\\n')
response=b''
while not response.endswith(b'\\r\\n\\r\\n'): response+=connection.recv(1)
assert b'200' in response
context=ssl.create_default_context(cafile='cert.pem')
with context.wrap_socket(connection,server_hostname='localhost.localdomain') as secure:
    secure.sendall(b'GET /websocket HTTP/1.1\\r\\nHost: localhost.localdomain\\r\\nUpgrade: websocket\\r\\nConnection: Upgrade\\r\\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\\r\\nSec-WebSocket-Version: 13\\r\\n\\r\\n')
    response=b''
    while not response.endswith(b'\\r\\n\\r\\n'): response+=secure.recv(1)
    assert b'101' in response
    assert secure.recv(4)==b'\\x81\\x02ok'
PY
""", **environment)
        self.assert_success(result)
        self.assertIn('profile=controlled-test', result.stderr)
        self.assertFalse(list(self.runtime.iterdir()), 'session transport/configuration leaked')
        self.assertIn('policy-denied', result.stderr)
        self.assertNotIn('fixture-secret-token', result.stderr)
        ca_result = self.shell("""test "$SSL_CERT_FILE" = /claude-home/ca/bundle.pem
test "$REQUESTS_CA_BUNDLE" = "$SSL_CERT_FILE"
test "$CURL_CA_BUNDLE" = "$SSL_CERT_FILE"
test "$NODE_EXTRA_CA_CERTS" = "$SSL_CERT_FILE"
test ! -w "$SSL_CERT_FILE"
test "$(curl --fail --silent --show-error --max-time 10 https://localhost.localdomain:8443/)" = controlled-production-proxy-ok
""", **environment, CLAUDE_CONTAINER_TRUST_HOST_CA='1',
            CLAUDE_CONTAINER_CA_BUNDLE=str(context / 'cert.pem'))
        self.assert_success(ca_result)
        self.assertEqual((self.base / 'state/ca').stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.base / 'state/ca').stat().st_uid, os.getuid())
        self.assertFalse(list(self.runtime.iterdir()))
        remaining = self.podman('ps', '--all', '--filter', 'label=io.claude-container.egress', '--format', '{{.ID}}')
        self.assertEqual(remaining, '')

    def start_session(self, command, environment):
        proc = subprocess.Popen([str(self.wrapper), '--container-shell'], cwd=self.project,
                                env=self.env | environment, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def finish():
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.communicate(timeout=25)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
        self.addCleanup(finish)
        proc.stdin.write(command + '\n')
        proc.stdin.flush()
        ready, _, _ = select.select([proc.stdout], [], [], 20)
        self.assertTrue(ready, 'session readiness timed out')
        self.assertEqual(proc.stdout.readline().strip(), 'network-ready')
        return proc

    def test_proxy_death_fails_closed_and_preserves_status(self):
        _, environment = self.provider_fixture()
        command = 'printf "network-ready\\n"; read -r marker; if curl --fail --silent --max-time 3 --cacert cert.pem https://localhost.localdomain:8443/; then exit 42; fi; exit 37'
        proc = self.start_session(command, environment)
        session = next(self.runtime.iterdir()).name
        proxy_id = self.podman('ps', '--no-trunc', '--filter', f'label=io.claude-container.egress={session}', '--format', '{{.ID}}')
        self.assertEqual(len(proxy_id), 64)
        self.podman('rm', '--force', '--time', '0', proxy_id)
        stdout, stderr = proc.communicate('proceed\n', timeout=25)
        self.assertEqual(proc.returncode, 37, stdout + stderr)
        self.assertFalse(list(self.runtime.iterdir()))

    def test_concurrent_policies_and_signal_cleanup_are_owned(self):
        _, environment = self.provider_fixture()
        value = json.loads(self.policy_file.read_text())
        value['profiles']['controlled-denied'] = {'authentication': 'custom', 'disable_optional_traffic': True,
            'destinations': [{'host': 'other.test', 'port': 443}]}
        self.policy_file.write_text(json.dumps(value))
        first = self.start_session('printf "network-ready\\n"; trap "" TERM; read -r marker; sleep 300', environment)
        second = self.start_session('printf "network-ready\\n"; read -r marker; if curl --fail --silent --max-time 3 https://localhost.localdomain:8443/; then exit 42; fi; exit 0',
                                    environment | {'CLAUDE_CONTAINER_NETWORK_PROFILE': 'controlled-denied',
                                                   'CLAUDE_CONTAINER_STATE_DIR': ''})
        self.assertEqual(len(list(self.runtime.iterdir())), 2)
        started = time.monotonic()
        first.send_signal(signal.SIGTERM)
        stdout, stderr = first.communicate(timeout=23)
        self.assertEqual(first.returncode, 143, stdout + stderr)
        self.assertLess(time.monotonic() - started, 22)
        self.assertIsNone(second.poll(), 'another session was removed')
        self.assertEqual(len(list(self.runtime.iterdir())), 1)
        stdout, stderr = second.communicate('proceed\n', timeout=25)
        self.assertEqual(second.returncode, 0, stdout + stderr)
        self.assertIn('policy-denied', stderr)
        self.assertFalse(list(self.runtime.iterdir()))

    def test_interrupted_and_failed_creation_recovers_both_roles(self):
        _, environment = self.provider_fixture()
        shim_dir = self.base / 'bin'
        shim_dir.mkdir()
        shim = shim_dir / 'podman'
        shim.write_text('''#!/usr/bin/env python3
import os,pathlib,subprocess,sys,time
args=sys.argv[1:]
real=os.environ['NETWORK_REAL_PODMAN']
selected=args and args[0]=='create' and any(a.startswith(os.environ['NETWORK_ROLE']+'=') for a in args)
if not selected: os.execv(real,[real,*args])
if os.environ['NETWORK_PHASE']=='before': sys.exit(17)
result=subprocess.run([real,*args],capture_output=True,text=True)
sys.stdout.write(result.stdout); sys.stdout.flush()
sys.stderr.write(result.stderr); sys.stderr.flush()
if result.returncode: sys.exit(result.returncode)
pathlib.Path(os.environ['NETWORK_MARKER']).write_text('created')
if os.environ['NETWORK_PHASE']=='after': sys.exit(17)
time.sleep(300)
''')
        shim.chmod(0o700)
        marker = self.base / 'creation-marker'
        for role in ('io.claude-container.egress', 'io.claude-container.session'):
            for phase in ('before', 'after', 'interrupt'):
                with self.subTest(role=role, phase=phase):
                    marker.unlink(missing_ok=True)
                    values = self.env | environment | {
                        'PATH': str(shim_dir) + ':' + os.environ['PATH'],
                        'NETWORK_REAL_PODMAN': shutil.which('podman'), 'NETWORK_ROLE': role,
                        'NETWORK_PHASE': phase, 'NETWORK_MARKER': str(marker)}
                    proc = subprocess.Popen([str(self.wrapper), '--container-shell'], cwd=self.project,
                                            env=values, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if phase == 'interrupt':
                        deadline = time.monotonic() + 15
                        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
                            time.sleep(0.02)
                        self.assertTrue(marker.exists(), 'create interception not reached')
                        proc.terminate()
                    stdout, stderr = proc.communicate(timeout=25)
                    self.assertEqual(proc.returncode, 143 if phase == 'interrupt' else 17, stdout + stderr)
                    self.assertFalse(list(self.runtime.iterdir()))
        self.assertEqual(self.podman('ps', '--all', '--filter', 'label=io.claude-container.egress', '--format', '{{.ID}}'), '')

    def test_readiness_binds_policy_guard_and_protocol(self):
        _, environment = self.provider_fixture()
        shim_dir = self.base / 'bin'
        shim_dir.mkdir()
        shim = shim_dir / 'podman'
        shim.write_text('''#!/usr/bin/env python3
import os,pathlib,subprocess,sys,time
args=sys.argv[1:]; real=os.environ['NETWORK_REAL_PODMAN']
if args and args[0]=='start':
 result=subprocess.run([real,*args],capture_output=True,text=True)
 if result.returncode==0:
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   paths=list(pathlib.Path(os.environ['NETWORK_RUNTIME']).glob('session.*/transport/ready'))
   if paths:
    paths[0].write_text('wrong-bootstrap-identity'); break
   time.sleep(.02)
 sys.stdout.write(result.stdout); sys.stderr.write(result.stderr); sys.exit(result.returncode)
os.execv(real,[real,*args])
''')
        shim.chmod(0o700)
        result = self.shell('touch agent-started\n', **environment,
            PATH=str(shim_dir)+':'+os.environ['PATH'], NETWORK_REAL_PODMAN=shutil.which('podman'),
            NETWORK_RUNTIME=str(self.runtime))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('identity mismatch', result.stderr)
        self.assertFalse((self.project / 'agent-started').exists())
        self.assertFalse(list(self.runtime.iterdir()))

    def test_guarded_arguments_stdin_status_and_tty_both_state_modes(self):
        import pty
        context = self.base / 'invocation-fixture'
        context.mkdir()
        source = '''#!/usr/bin/python3
import errno,json,socket,sys
try: socket.socket(socket.AF_UNIX)
except OSError as error: assert error.errno==errno.EPERM
else: raise AssertionError('guard missing')
is_terminal=sys.stdin.isatty()
print(json.dumps({'argv':sys.argv[1:],'stdin':'' if is_terminal else sys.stdin.read(),'tty':is_terminal}),flush=True)
sys.exit(37)
'''
        (context / 'claude-fixture').write_text(source)
        (context / 'Containerfile').write_text(f'FROM {IMAGE}\nRUN rm -f /usr/local/bin/claude\nCOPY claude-fixture /usr/local/bin/claude\nRUN chmod 555 /usr/local/bin/claude\n')
        tag = 'localhost/claude-invocation-test-' + uuid.uuid4().hex
        self.addCleanup(self.podman, 'rmi', '--force', tag)
        self.podman('build', '--pull=never', '--tag', tag, str(context))
        for state in ('', self.env['CLAUDE_CONTAINER_STATE_DIR']):
            environment = self.env | {'CLAUDE_CONTAINER_STATE_DIR': state, 'CLAUDE_CONTAINER_IMAGE': tag}
            arguments = ['-p', 'space value', '', '--help']
            try:
                result = subprocess.run([str(self.wrapper), *arguments], cwd=self.project, env=environment,
                    input='synthetic stdin\n', capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired as error:
                self.fail(f'guarded pipe timed out; isolated={bool(state)} stdout={error.stdout!r} stderr={error.stderr!r}')
            self.assertEqual(result.returncode, 37, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout), {'argv':arguments, 'stdin':'synthetic stdin\n', 'tty':False})
            master, slave = pty.openpty()
            try:
                proc = subprocess.Popen([str(self.wrapper), '--tty-probe'], cwd=self.project, env=environment,
                    stdin=slave, stdout=slave, stderr=subprocess.PIPE)
                os.close(slave); slave = -1
                _, error = proc.communicate(timeout=30)
                self.assertEqual(proc.returncode, 37, error.decode())
                output = b''
                while True:
                    try:
                        data = os.read(master, 65536)
                    except OSError:
                        break
                    if not data: break
                    output += data
                records = [json.loads(line) for line in output.decode().splitlines() if line.startswith('{"argv"')]
                self.assertEqual(records, [{'argv':['--tty-probe'], 'stdin':'', 'tty':True}])
            finally:
                if slave >= 0: os.close(slave)
                os.close(master)

    def test_bootstrap_failure_after_proxy_setup_cleans_owned_resources(self):
        _, environment = self.provider_fixture()
        shim_dir = self.base / 'bin'
        shim_dir.mkdir()
        shim = shim_dir / 'podman'
        shim.write_text("#!/usr/bin/env python3\nimport os,sys\nargs=sys.argv[1:]\nif args and args[0]=='create' and any(a.startswith('io.claude-container.session=') for a in args):\n args[1:1]=['--volume',os.environ['NETWORK_INJECTED_BIND']+':/tmp/untrusted-nested:rw']\nos.execv(os.environ['NETWORK_REAL_PODMAN'],[os.environ['NETWORK_REAL_PODMAN'],*args])\n")
        shim.chmod(0o700)
        result = self.shell('touch agent-started\n', **environment,
            PATH=str(shim_dir) + ':' + os.environ['PATH'],
            NETWORK_REAL_PODMAN=shutil.which('podman'), NETWORK_INJECTED_BIND=str(self.project))
        self.assertEqual(result.returncode, 78, result.stdout + result.stderr)
        self.assertIn('nested private IPC mount validation', result.stderr)
        self.assertFalse((self.project / 'agent-started').exists())
        self.assertFalse(list(self.runtime.iterdir()))

    def test_windows_workspace_ordinary_files_and_restricted_modes(self):
        parent = ROOT / '.test-state'
        parent.mkdir(exist_ok=True)
        project = Path(tempfile.mkdtemp(prefix='guarded-workspace-', dir=parent))
        self.addCleanup(shutil.rmtree, project)
        self.project = project
        for state in ('', self.env['CLAUDE_CONTAINER_STATE_DIR']):
            script = "mkdir -p first second; printf persisted >first/file; mv first/file second/file; test \"$(cat second/file)\" = persisted\n"
            script += "python3 - <<'CHECK'\nimport socket,errno\ntry: socket.socket(socket.AF_UNIX)\nexcept OSError as error: assert error.errno == errno.EPERM\nelse: raise AssertionError('Unix socket allowed')\nCHECK\n"
            result = self.shell(script, CLAUDE_CONTAINER_STATE_DIR=state)
            self.assert_success(result)
            self.assertEqual((project / 'second/file').read_text(), 'persisted')

    def test_stalled_proxy_cleanup_keeps_exit_status_and_deadline(self):
        _, environment = self.provider_fixture()
        shim_dir = self.base / 'bin'
        shim_dir.mkdir()
        shim = shim_dir / 'podman'
        shim.write_text('''#!/usr/bin/env python3
import os,signal,subprocess,sys,time
args=sys.argv[1:]
real=os.environ['NETWORK_REAL_PODMAN']
if args and args[0]=='rm':
    owner=subprocess.run([real,'inspect','--format','{{index .Config.Labels "io.claude-container.egress"}}',args[-1]],capture_output=True,text=True)
    if owner.returncode==0 and owner.stdout.strip():
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        time.sleep(300)
os.execv(real,[real,*args])
''')
        shim.chmod(0o700)
        values = environment | {'PATH': str(shim_dir) + ':' + os.environ['PATH'],
                                'NETWORK_REAL_PODMAN': shutil.which('podman')}
        proc = self.start_session('printf "network-ready\\n"; read -r marker; exit 37', values)
        session = next(self.runtime.iterdir()).name
        proxy_id = self.podman('ps', '--no-trunc', '--filter', f'label=io.claude-container.egress={session}', '--format', '{{.ID}}')
        self.addCleanup(self.podman, 'rm', '--force', '--time', '0', '--ignore', proxy_id)
        started = time.monotonic()
        stdout, stderr = proc.communicate('proceed\n', timeout=23)
        self.assertEqual(proc.returncode, 37, stdout + stderr)
        self.assertLess(time.monotonic() - started, 22)
        self.assertIn('failed or timed out', stderr)
        self.assertIn(proxy_id, stderr)

    def test_cli_permission_modes_and_optional_controls_both_state_modes(self):
        _, environment = self.provider_fixture()
        for state in ('', self.env['CLAUDE_CONTAINER_STATE_DIR']):
            values = self.env | environment | {'CLAUDE_CONTAINER_STATE_DIR': state,
                                               'ANTHROPIC_API_KEY': 'synthetic-not-a-real-key'}
            controls = self.shell("""test "$CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" = 1
test "$DISABLE_AUTOUPDATER" = 1
test "$DISABLE_TELEMETRY" = 1
test "$DISABLE_ERROR_REPORTING" = 1
test "$ENABLE_CLAUDEAI_MCP_SERVERS" = false
test "$CLAUDE_CODE_DISABLE_ARTIFACT" = 1
test "$ANTHROPIC_API_KEY" = synthetic-not-a-real-key
""", **environment, CLAUDE_CONTAINER_STATE_DIR=state, ANTHROPIC_API_KEY='synthetic-not-a-real-key')
            self.assert_success(controls)
            for flags, yolo in ((['--version'], '0'), (['--dangerously-skip-permissions', '--version'], '0'),
                                (['--version'], '1')):
                with self.subTest(state=state, flags=flags, yolo=yolo):
                    result = subprocess.run([str(self.wrapper), *flags], cwd=self.project,
                                            env=values | {'CLAUDE_YOLO': yolo}, input='',
                                            text=True, capture_output=True, timeout=30)
                    self.assert_success(result)
                    self.assertIn('2.1.316', result.stdout)
            self.assertFalse(list(self.runtime.iterdir()))

    def test_actual_claude_bash_tool_with_synthetic_messages_api(self):
        context, environment = self.provider_fixture()
        # The controlled custom profile and fixture CA authorize only this local
        # synthetic API. No account state, real key or external model is involved.
        for state in ('', self.env['CLAUDE_CONTAINER_STATE_DIR']):
            sentinel = self.project / 'claude-tool-sentinel'
            sentinel.unlink(missing_ok=True)
            script = "export ANTHROPIC_BASE_URL=https://localhost.localdomain:8443\n"
            script += "claude --dangerously-skip-permissions --model claude-sonnet-4-6 --max-turns 3 -p fixture-tool-operation </dev/null\n"
            script += "test \"$(cat claude-tool-sentinel)\" = actual-claude-tool-ok\n"
            result = self.shell(script, **environment, CLAUDE_CONTAINER_STATE_DIR=state,
                ANTHROPIC_API_KEY='synthetic-not-a-real-key',
                CLAUDE_CONTAINER_TRUST_HOST_CA='1', CLAUDE_CONTAINER_CA_BUNDLE=str(context / 'cert.pem'))
            self.assert_success(result)
            self.assertIn('fixture-tool-complete', result.stdout)
            self.assertEqual(sentinel.read_text(), 'actual-claude-tool-ok')

    def test_unsafe_policy_and_missing_proxy_image_fail_before_agent(self):
        _, environment = self.provider_fixture()
        self.policy_file.chmod(0o666)
        result = self.shell('touch agent-started\n', **environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('policy preflight failed', result.stderr)
        self.assertFalse((self.project / 'agent-started').exists())
        self.policy_file.chmod(0o600)
        result = self.shell('touch agent-started\n', **(environment | {
            'CLAUDE_CONTAINER_EGRESS_IMAGE': 'sha256:' + '0' * 64}))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('proxy image is absent', result.stderr)
        self.assertFalse((self.project / 'agent-started').exists())
        self.assertFalse(list(self.runtime.iterdir()))

    def test_tampered_bootstrap_fails_before_application(self):
        guard = self.install / 'network/bin/claude-egress-guard'
        guard.chmod(0o700)
        with guard.open('ab') as output:
            output.write(b'tampered')
        result = self.shell('touch agent-started\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('bootstrap digest mismatch', result.stderr)
        self.assertFalse((self.project / 'agent-started').exists())
        self.assertFalse(list(self.runtime.iterdir()))
