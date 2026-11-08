"""Bounded installation qualification. Never runs a supplied application command."""
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_GATE = None
sys.path.insert(0, str(ROOT / 'network'))
from policy import PolicyError, canonical, load, trusted_path
import qualification_records as records

module = importlib.util.spec_from_file_location('claude_platform', ROOT / 'network/platform_check.py')
platform = importlib.util.module_from_spec(module)
module.loader.exec_module(platform)


class GateError(ValueError):
    pass


def stop(process, grace=1):
    # Keep ownership of the group even if the leader has exited while its
    # descendants still hold pipes. Never kill a group selected by user input.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=grace)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.communicate(timeout=2)


class Gate:
    def __init__(self, env):
        self.env = env.copy()
        self.deadline = time.monotonic() + 300
        self.token = uuid.uuid4().hex
        self.process = None
        self.cancelled = False

    def run(self, command, *, env=None, timeout=30, input=None, cwd=None):
        remaining = min(timeout, self.deadline - time.monotonic())
        if remaining <= 0:
            raise GateError('qualification deadline expired')
        process = subprocess.Popen([str(value) for value in command], env=env or self.env, cwd=cwd,
            stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        self.process = process
        try:
            output, error = process.communicate(input=input, timeout=remaining)
            if process.returncode:
                # These are fixed credential-free probes, never ordinary app
                # commands. Retain bounded diagnostics without terminal escapes.
                detail = ''.join(char for char in error[-1600:] if char.isprintable() or char in '\n\t')
                raise GateError('required operation failed: ' + Path(str(command[0])).name + ': ' + detail.replace('\n', ' | '))
            if len(output) > 1024 * 1024:
                raise GateError('oversized qualification output')
            return output.removesuffix('\n')
        finally:
            stop(process, grace=0 if self.cancelled else
                 22 if str(ROOT / 'claude-container.sh') in [str(value) for value in command] else 1)
            self.process = None

    def engine(self, *args, **kwargs):
        return self.run(['podman', *args], **kwargs)

    def cleanup(self):
        # All resources carry the unique gate identity, including wrapper roles.
        # Use a separate bounded budget even after the primary gate deadline.
        original_deadline = self.deadline
        self.deadline = time.monotonic() + (10 if self.cancelled else 20)
        try:
            self.cleanup_resources()
        finally:
            self.deadline = original_deadline

    def cleanup_resources(self):
        ids = self.engine('ps', '--all', '--no-trunc', '--filter',
                          'label=io.claude-container.qualification=' + self.token, '--format', '{{.ID}}')
        for ident in ids.splitlines():
            owner = self.engine('inspect', '--format',
                '{{index .Config.Labels "io.claude-container.qualification"}}', ident)
            if owner != self.token:
                raise GateError('qualification resource ownership mismatch')
            self.engine('rm', '--force', '--time', '0', '--ignore', ident, timeout=4)
        names = self.engine('network', 'ls', '--filter',
            'label=io.claude-container.qualification=' + self.token, '--format', '{{.Name}}')
        for name in names.splitlines():
            self.engine('network', 'rm', name, timeout=4)

    def common(self, image, network='none'):
        return ['--pull=never', '--network=' + network, '--read-only', '--cap-drop=all',
                '--security-opt=no-new-privileges', '--userns=keep-id', '--user', f'{os.getuid()}:{os.getgid()}',
                '--label', 'io.claude-container.qualification=' + self.token]

    @contextmanager
    def endpoints(self, project):
        sockets, workers, seen = [], [], set()
        finished = threading.Event()
        directory = os.open(project, os.O_RDONLY | os.O_DIRECTORY)

        def serve(name, server, kind):
            while not finished.is_set():
                try:
                    if kind == socket.SOCK_DGRAM:
                        value = server.recv(64)
                    else:
                        peer, _ = server.accept()
                        with peer:
                            peer.settimeout(1); value = peer.recv(64)
                    if value == b'qualification-positive':
                        seen.add(name)
                except socket.timeout:
                    pass
                except OSError:
                    if not finished.is_set():
                        raise

        def create(name, kind):
            server = socket.socket(socket.AF_UNIX, kind)
            sockets.append(server)
            server.bind(f'/proc/self/fd/{directory}/{name}')
            server.settimeout(.1)
            if kind != socket.SOCK_DGRAM:
                server.listen(8)
            worker = threading.Thread(target=serve, args=(name, server, kind), daemon=True)
            workers.append(worker); worker.start()

        def late():
            deadline = time.monotonic() + 60
            while not finished.is_set() and time.monotonic() < deadline:
                if (project / 'guard-ready').exists():
                    create('late.sock', socket.SOCK_STREAM)
                    return
                finished.wait(.02)

        try:
            for name, kind in (('external.sock', socket.SOCK_STREAM), ('seq.sock', socket.SOCK_SEQPACKET),
                               ('dgram.sock', socket.SOCK_DGRAM)):
                create(name, kind)
            (project / 'alias.sock').symlink_to('external.sock')
            os.link(project / 'external.sock', project / 'hardlink.sock')
            worker = threading.Thread(target=late, daemon=True)
            workers.append(worker); worker.start()
            yield seen
        finally:
            finished.set()
            for worker in workers:
                worker.join(1)
            for server in sockets:
                server.close()
            os.close(directory)

    def case(self, work, identity, network, addresses, *, isolated, tls=False):
        phase = work / ('tls' if tls else 'isolated' if isolated else 'shared')
        phase.mkdir(mode=0o700)
        project, home, runtime = (phase / name for name in ('project', 'home', 'egress'))
        for path in (project, home, runtime):
            path.mkdir(mode=0o700)
        config = dict(schema=1, token=self.token, addresses=addresses, workspace=str(project),
                      provider=identity['mode'] == 'provider', tls=tls)
        input_path = phase / 'input.json'
        input_path.write_bytes(canonical(config)); input_path.chmod(0o600)
        env = {key: value for key, value in self.env.items() if key in ('PATH', 'CONTAINER_HOST')}
        env.update(HOME=str(home), CLAUDE_CONTAINER_NETWORK=identity['mode'],
            CLAUDE_CONTAINER_IMAGE=identity['runtime'], CLAUDE_CONTAINER_PODMAN='0',
            CLAUDE_CONTAINER_QUALIFICATION_INPUT=str(input_path),
            CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR=str(runtime))
        if isolated:
            env['CLAUDE_CONTAINER_STATE_DIR'] = str(phase / 'state')
        if identity['mode'] == 'provider':
            env.update(CLAUDE_CONTAINER_NETWORK_PROFILE=self.env['CLAUDE_CONTAINER_NETWORK_PROFILE'],
                       CLAUDE_CONTAINER_NETWORK_POLICY=self.env['CLAUDE_CONTAINER_NETWORK_POLICY'],
                       CLAUDE_CONTAINER_EGRESS_IMAGE=identity['proxy'])
        if tls:
            self.engine('run', '--rm', *self.common(identity['runtime']), '--volume', f'{phase}:/qualification:rw',
                '--entrypoint', 'openssl', identity['runtime'], 'req', '-x509', '-newkey', 'rsa:2048',
                '-nodes', '-days', '1', '-subj', '/CN=qualification.invalid', '-addext',
                'subjectAltName=DNS:qualification.invalid,DNS:alternate.invalid',
                '-keyout', '/qualification/key.pem', '-out', '/qualification/cert.pem')
            policy = load(self.env['CLAUDE_CONTAINER_NETWORK_POLICY'])
            policy['profiles']['qualification-fixture'] = dict(authentication='custom', disable_optional_traffic=True,
                destinations=[dict(host='qualification.invalid', port=8443, addresses=['127.0.0.1'])])
            policy_path = phase / 'policy.json'; policy_path.write_bytes(canonical(policy)); policy_path.chmod(0o600)
            env.update(CLAUDE_CONTAINER_NETWORK_PROFILE='qualification-fixture',
                       CLAUDE_CONTAINER_NETWORK_POLICY=str(policy_path))
        control = ['podman', 'run', '--rm', *self.common(identity['runtime'], network),
            '--volume', f'{project}:/workspace:rw',
            '--volume', f'{input_path}:/opt/claude-egress/qualification.json:ro',
            '--volume', f'{ROOT / "network/qualification_probe.py"}:/probe.py:ro',
            '--entrypoint', 'python3', identity['runtime'], '-I', '/probe.py', 'control']
        with self.endpoints(project) as seen:
            self.run(control)
            if not {'external.sock', 'seq.sock', 'dgram.sock'} <= seen:
                # Server threads can record the received bytes after CLI exit.
                deadline = time.monotonic() + 2
                while not {'external.sock', 'seq.sock', 'dgram.sock'} <= seen and time.monotonic() < deadline:
                    time.sleep(.01)
            if not {'external.sock', 'seq.sock', 'dgram.sock'} <= seen:
                raise GateError('Unix positive controls failed')
            command = ['bash', str(ROOT / 'claude-container.sh'), '--container-qualify-probe']
            if not tls:
                output = self.run(command, env=env, timeout=70, cwd=project)
            else:
                process = subprocess.Popen(command, env=env, cwd=project, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                self.process = process
                try:
                    output = b''
                    deadline = min(time.monotonic() + 65, self.deadline)
                    while b'qualification-proxy-loss-ready\n' not in output:
                        if time.monotonic() >= deadline or process.poll() is not None:
                            raise GateError('controlled TLS probe failed')
                        ready, _, _ = select.select([process.stdout], [], [], .1)
                        if ready:
                            part = os.read(process.stdout.fileno(), 65536)
                            if not part:
                                raise GateError('controlled TLS probe ended early')
                            output += part
                    sessions = list(runtime.glob('session.*'))
                    if len(sessions) != 1:
                        raise GateError('ambiguous fixture proxy ownership')
                    counts = sessions[0] / 'logs/qualification-counts.json'
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        values = json.loads(counts.read_text()) if counts.exists() else []
                        if len(values) == 2:
                            break
                        time.sleep(.02)
                    if len(values) != 2 or values[0] <= 0 or values[1] != 0:
                        raise GateError('TLS mismatch zero-byte evidence missing')
                    proxy = self.engine('ps', '--no-trunc', '--filter',
                        'label=io.claude-container.egress=' + sessions[0].name, '--format', '{{.ID}}')
                    owner = self.engine('inspect', '--format',
                        '{{index .Config.Labels "io.claude-container.qualification"}}', proxy)
                    if owner != self.token:
                        raise GateError('fixture proxy ownership mismatch')
                    self.engine('rm', '--force', '--time', '0', proxy)
                    tail, error = process.communicate(b'proxy-removed\n', timeout=25)
                    output = (output + tail).decode()
                    if process.returncode:
                        raise GateError('proxy-loss probe failed')
                finally:
                    stop(process, grace=0 if self.cancelled else 22); self.process = None
            if 'qualification-probe-ok' not in output:
                raise GateError('qualification probe did not confirm all checks')
            # Verify the late service is a live positive control as well.
            if not (project / 'late.sock').is_socket():
                raise GateError('late socket fixture missing')
            with socket.socket(socket.AF_UNIX) as peer:
                descriptor = os.open(project, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    peer.connect(f'/proc/self/fd/{descriptor}/late.sock')
                    peer.sendall(b'qualification-positive')
                finally:
                    os.close(descriptor)

    def qualify(self, identity):
        trusted_path(ROOT.parent, [], directory=True)
        with tempfile.TemporaryDirectory(prefix='.claude-qualification-', dir=ROOT.parent) as temporary:
            work = Path(temporary)
            network = 'claude-qualification-' + self.token
            self.engine('network', 'create', '--internal', '--ipv6', '--label',
                        'io.claude-container.qualification=' + self.token, network)
            peer = self.engine('create', *self.common(identity['runtime'], network),
                '--volume', f'{ROOT / "network/qualification_peer.py"}:/peer.py:ro',
                '--entrypoint', 'python3', identity['runtime'], '-I', '/peer.py')
            self.engine('start', peer)
            deadline = time.monotonic() + 10
            while 'qualification-peer-ready' not in self.engine('logs', peer):
                if time.monotonic() >= deadline:
                    raise GateError('dual-stack positive-control fixture unavailable')
                time.sleep(.05)
            networks = json.loads(self.engine('inspect', '--format', '{{json .NetworkSettings.Networks}}', peer))
            value = networks[network]
            addresses = [value['IPAddress'], value['GlobalIPv6Address']]
            if not all(addresses):
                raise GateError('dual-stack fixture identity unavailable')
            for isolated in (False, True):
                self.case(work, identity, network, addresses, isolated=isolated)
            if identity['mode'] == 'provider':
                self.case(work, identity, network, addresses, isolated=True, tls=True)


def writable(env):
    paths = [Path.cwd().resolve()]
    if env.get('CLAUDE_CONTAINER_STATE_DIR'):
        paths.append(Path(env['CLAUDE_CONTAINER_STATE_DIR']).resolve())
    else:
        paths.extend((Path(env.get('CLAUDE_CONFIG_DIR') or str(Path.home() / '.claude')).resolve(),
                      (Path.home() / '.config/openspec').resolve()))
    return [str(path) for path in paths]


def main():
    global ACTIVE_GATE
    if sys.argv[1:] not in (['qualify'], ['check']):
        raise GateError('use --container-qualify alone')
    env = os.environ.copy()
    endpoint = env.get('CONTAINER_HOST', '')
    if (env.get('CONTAINER_CONNECTION') or not endpoint.startswith('unix:///') or
            not endpoint[7:].strip('/')):
        raise platform.PlatformError('qualification requires an explicit same-host Unix endpoint, without named connections')
    if (env.get('CLAUDE_CONTAINER_NETWORK') or 'offline') not in ('offline', 'provider'):
        raise GateError('qualification requires offline or provider mode')
    if env.get('CLAUDE_CONTAINER_PODMAN') == '1':
        raise GateError('qualification rejects Podman delegation')
    paths = writable(env)
    trusted_path(ROOT, paths, directory=True)
    for name in records.CODE:
        trusted_path(ROOT / name, paths)
    gate = Gate(env)
    ACTIVE_GATE = gate
    preflight = ['python3', '-I', str(ROOT / 'network/control.py'), 'preflight', '--installation', str(ROOT)]
    for path in paths:
        preflight.extend(('--writable', path))
    if (env.get('CLAUDE_CONTAINER_NETWORK') or 'offline') == 'provider':
        preflight.extend(('--policy', env.get('CLAUDE_CONTAINER_NETWORK_POLICY', ''),
            '--profile', env.get('CLAUDE_CONTAINER_NETWORK_PROFILE', ''),
            '--proxy-image', env.get('CLAUDE_CONTAINER_EGRESS_IMAGE', ''),
            '--runtime', env.get('CLAUDE_CONTAINER_NETWORK_RUNTIME_DIR', '')))
    try:
        gate.run(preflight)
        identity, reusable = records.fingerprint(ROOT, env, gate.run, platform, gate.token)
        if sys.argv[1] == 'check':
            report = records.read(ROOT, identity, paths)
            if reusable and report['reusable']:
                report_status = records.status(ROOT, identity, paths)
                print('claude-container: status=' + report_status
                      + ('; this installation is not release-measured' if report_status == 'locally-qualified' else ''), file=sys.stderr)
                return
        gate.qualify(identity)
        gate.cleanup()
        after, after_reusable = records.fingerprint(ROOT, env, gate.run, platform, gate.token)
        if identity != after or reusable != after_reusable:
            raise GateError('enforcement inputs changed during qualification')
    finally:
        gate.cleanup()
    records.publish(ROOT, identity, reusable, paths)
    report_status = records.status(ROOT, identity, paths)
    print('claude-container: status=' + report_status
          + ('; this installation is not release-measured' if report_status == 'locally-qualified' else ''), file=sys.stderr)
    if sys.argv[1] == 'qualify':
        print('CLAUDE_QUALIFICATION_STATUS=' + report_status)
        print('CLAUDE_QUALIFICATION_OK')


def interrupted(signum, frame):
    if ACTIVE_GATE is not None:
        ACTIVE_GATE.cancelled = True
        ACTIVE_GATE.deadline = time.monotonic()
    raise GateError('qualification interrupted')


if __name__ == '__main__':
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, interrupted)
    try:
        main()
    except platform.PlatformError as error:
        print('claude-container: status=ineligible: ' + str(error)
              + '; no unrestricted fallback or automatic policy change.', file=sys.stderr)
        sys.exit(1)
    except (GateError, PolicyError, OSError, ValueError, KeyError,
            subprocess.SubprocessError) as error:
        print('claude-container: status=qualification-required: ' + str(error)
              + '; run --container-qualify or rerun --container-setup. No unrestricted fallback.', file=sys.stderr)
        sys.exit(1)
