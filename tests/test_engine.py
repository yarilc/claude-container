"""Session container engine: shared build inputs (session-container-engine, design D3)."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sandbox_profile import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / 'setup'))
import common  # noqa: E402
import engine  # noqa: E402

ENGINE = ROOT / 'launcher/engine'
# An -immutable tag: quay.io deletes the manifests of the other podman/stable tags when it rebuilds them.
PINNED_BASE = re.compile(r'quay\.io/podman/stable:v[0-9]+(\.[0-9]+)*-immutable@sha256:[a-f0-9]{64}')
# Defaults of the base image that the engine must not keep (design D3).
REMOVED = ('/usr/share/containers/containers.conf.d/00-vendor.conf',
           '/etc/containers/containers.rootless.conf.d/20-image_build.conf')
EMPTIED = ('/etc/containers/mounts.conf', '/usr/share/containers/mounts.conf')


def recipe_violations(recipe):
    """What makes an engine recipe unacceptable: unpinned, networked or keeping base defaults."""
    found = []
    bases = re.findall(r'(?im)^\s*FROM\s+(\S+)', recipe)
    if len(bases) != 1 or not PINNED_BASE.fullmatch(bases[0]):
        found.append('the base must be one quay.io/podman/stable -immutable tag pinned by digest')
    if re.search(r'(?i)\b(dnf|yum|microdnf|curl|wget|pip)\b', recipe):
        found.append('the recipe must build without fetching anything')
    for path in REMOVED:
        if path not in recipe:
            found.append('keeps ' + path)
    for path in EMPTIED:
        if ': > ' + path not in recipe:
            found.append('does not empty ' + path)
    if not re.search(r'(?m)^USER podman$', recipe):
        found.append('the engine must run as the unprivileged podman user')
    if 'COPY containers.conf /etc/containers/containers.conf' not in recipe:
        found.append('does not replace containers.conf')
    return found


def configuration_violations(text):
    found = []
    settings = dict(re.findall(r'(?m)^\s*([a-z_]+)\s*=\s*(.+?)\s*$', text))
    for key in ('netns', 'pidns', 'ipcns', 'utsns', 'userns', 'cgroupns', 'cgroups', 'volumes', 'mounts'):
        if key in settings:
            found.append(key + ' must keep the rootless default')
    if settings.get('log_driver') != '"k8s-file"':
        found.append('log_driver must be k8s-file')
    if settings.get('runtime') != '"crun"':
        found.append('runtime must be crun')
    return found


class EngineRecipeTests(unittest.TestCase):
    def setUp(self):
        self.recipe = (ENGINE / 'Containerfile').read_text()
        self.configuration = (ENGINE / 'containers.conf').read_text()

    def test_recipe_is_pinned_offline_and_replaces_base_defaults(self):
        self.assertEqual(recipe_violations(self.recipe), [])
        cases = {
            'tag only': self.recipe.replace(re.search(r'@sha256:[a-f0-9]{64}', self.recipe).group(0), ''),
            'rebuilt tag': self.recipe.replace('-immutable@sha256:', '@sha256:'),
            'second base': self.recipe + '\nFROM docker.io/library/alpine@sha256:' + 'a' * 64 + '\n',
            'package install': self.recipe.replace('RUN rm -f', 'RUN dnf -y install strace && rm -f'),
            'journald kept': self.recipe.replace(REMOVED[0], '/nonexistent'),
            'host /proc kept': self.recipe.replace(REMOVED[1], '/nonexistent'),
            'secrets passthrough kept': self.recipe.replace(': > ' + EMPTIED[0], 'true'),
            'root engine': self.recipe.replace('USER podman', 'USER root'),
        }
        for name, mutated in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(mutated, self.recipe)
                self.assertTrue(recipe_violations(mutated))

    def test_configuration_keeps_private_namespaces(self):
        self.assertEqual(configuration_violations(self.configuration), [])
        for setting in ('utsns = "host"', 'cgroups = "disabled"', 'volumes = ["/proc:/proc"]', 'netns = "host"'):
            with self.subTest(setting=setting):
                mutated = self.configuration.replace('[containers]\n', '[containers]\n' + setting + '\n')
                self.assertTrue(configuration_violations(mutated))
        self.assertTrue(configuration_violations(self.configuration.replace('k8s-file', 'journald')))

    def test_build_context_admits_only_engine_inputs(self):
        ignore = (ENGINE / '.containerignore').read_text().splitlines()
        admitted = sorted(line[1:] for line in ignore if line.startswith('!'))
        self.assertEqual(ignore[ignore.index('**')], '**')
        self.assertEqual(admitted, ['.containerignore', 'Containerfile', 'containers.conf', 'entrypoint.sh',
                                    'podman-build-secret*', 'resolv.conf', 'storage.conf'])
        # The engine's resolver is the restricted sessions' one.
        self.assertEqual((ENGINE / 'resolv.conf').read_text(), (ROOT / 'network/resolv.conf').read_text())

    def test_storage_lives_on_a_neutral_path(self):
        # A workspace mounted at the same path never shadows the engine's storage.
        storage = (ENGINE / 'storage.conf').read_text()
        self.assertIn('rootless_storage_path = "' + engine.STORAGE + '/storage"', storage)
        self.assertIn('COPY storage.conf /etc/containers/storage.rootless.conf.d/', self.recipe)
        self.assertIn(engine.STORAGE, self.recipe)
        self.assertFalse(engine.STORAGE.startswith('/home/'))

    def test_entrypoint_serves_loopback_and_unix_socket(self):
        entrypoint = (ENGINE / 'entrypoint.sh').read_text()
        self.assertIn('tcp://127.0.0.1:$port', entrypoint)
        self.assertIn('unix://$socket', entrypoint)
        self.assertNotIn('0.0.0.0', entrypoint)
        self.assertIn('ENV XDG_RUNTIME_DIR=/run/user/1000', self.recipe)

    def test_entrypoint_sets_the_process_limit_after_the_port(self):
        # set-process-limits-inside-containers, design D2: the limit after the port is
        # set before the services start; invalid arguments start nothing.
        import resource
        hard = resource.getrlimit(resource.RLIMIT_NPROC)[1]
        if hard != resource.RLIM_INFINITY and hard < 64:
            self.skipTest('the process rlimit of this test is below 64')
        chosen = '999' if hard == resource.RLIM_INFINITY else str(hard - 1)
        # The stub must be executable: SANDBOX_TEST_TMPDIR when /tmp is noexec.
        with tempfile.TemporaryDirectory(dir=os.environ.get('SANDBOX_TEST_TMPDIR')) as temporary:
            base = Path(temporary)
            (base / 'bin').mkdir()
            podman = base / 'bin/podman'
            podman.write_text('#!/usr/bin/env python3\nimport os, sys\n'
                              'row = next(line for line in open("/proc/self/limits") if line.startswith("Max processes"))\n'
                              'with open(os.environ["LOG"], "a") as log:\n'
                              '    log.write(" ".join([*row.split()[2:4], *sys.argv[1:]]) + "\\n")\n')
            podman.chmod(0o700)
            for shell in ('sh', 'bash'):
                for arguments, status, limit, port in (
                        ([], 0, None, '2375'), (['2400'], 0, None, '2400'), (['2375', chosen], 0, chosen, '2375'),
                        (['2375', '0'], 2, None, None), (['2375', '012'], 2, None, None),
                        (['2375', '-1'], 2, None, None), (['2375', 'x'], 2, None, None), (['2375', ''], 2, None, None),
                        (['x'], 2, None, None), (['2375', chosen, 'x'], 2, None, None),
                        *([] if hard == resource.RLIM_INFINITY else [(['2375', str(hard + 1)], 'failed', None, None)])):
                    with self.subTest(shell=shell, arguments=arguments):
                        log = base / 'calls.log'
                        log.unlink(missing_ok=True)
                        result = subprocess.run([shell, str(ENGINE / 'entrypoint.sh'), *arguments],
                                                env={'PATH': f'{base / "bin"}:/usr/bin:/bin', 'LOG': str(log),
                                                     'XDG_RUNTIME_DIR': str(base / 'run')},
                                                capture_output=True, text=True, timeout=30)
                        if status == 'failed':
                            self.assertNotEqual(result.returncode, 0)
                        else:
                            self.assertEqual(result.returncode, status, result.stderr)
                        if port is None:
                            self.assertFalse(log.exists())
                            continue
                        for _ in range(100):
                            calls = log.read_text().splitlines() if log.exists() else []
                            if len(calls) == 2:
                                break
                            time.sleep(0.05)
                        self.assertEqual(sorted(call.split(' ', 2)[2] for call in calls),
                                         [f'system service --time=0 tcp://127.0.0.1:{port}',
                                          f'system service --time=0 unix://{base}/run/podman/podman.sock'])
                        for call in calls:
                            soft, hard_value = call.split(' ', 2)[:2]
                            if limit:
                                self.assertEqual((soft, hard_value), (limit, limit))
                            else:
                                self.assertNotEqual((soft, hard_value), (chosen, chosen))

    def test_engine_inputs_are_installed(self):
        for path in sorted(ENGINE.iterdir()):
            with self.subTest(path=path.name):
                self.assertIn('launcher/engine/' + path.name, common.MANIFEST)


# The default profile's shape for the hostname calls: allowed with CAP_SYS_ADMIN, EPERM otherwise.
DEFAULT_PROFILE = {
    'defaultAction': 'SCMP_ACT_ERRNO', 'defaultErrnoRet': 38,
    'syscalls': [
        {'names': ['read', 'write'], 'action': 'SCMP_ACT_ALLOW'},
        {'names': ['setdomainname', 'sethostname'], 'action': 'SCMP_ACT_ALLOW',
         'includes': {'caps': ['CAP_SYS_ADMIN']}},
        {'names': ['mount', 'setdomainname', 'sethostname'], 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 1,
         'excludes': {'caps': ['CAP_SYS_ADMIN']}},
    ],
}


class EngineSeccompTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, True)

    def test_profile_allows_only_the_hostname_calls_unconditionally(self):
        profile = engine.seccomp_profile(DEFAULT_PROFILE)
        self.assertEqual(profile['defaultAction'], 'SCMP_ACT_ERRNO')
        self.assertEqual(profile['defaultErrnoRet'], 38)
        rules = profile['syscalls']
        self.assertEqual(rules[0], DEFAULT_PROFILE['syscalls'][0])
        # The conditional allow lost both names and is gone; the denial keeps mount only.
        self.assertEqual(rules[1], {'names': ['mount'], 'action': 'SCMP_ACT_ERRNO', 'errnoRet': 1,
                                    'excludes': {'caps': ['CAP_SYS_ADMIN']}})
        self.assertEqual(rules[2], {'names': ['sethostname', 'setdomainname'], 'action': 'SCMP_ACT_ALLOW'})
        self.assertEqual(len(rules), 3)
        mentioned = [rule for rule in rules if set(engine.HOSTNAME_CALLS) & set(rule['names'])]
        self.assertEqual(len(mentioned), 1)
        self.assertNotIn('includes', mentioned[0])

    def test_written_profile_is_private_and_identified(self):
        source = self.base / 'default.json'
        source.write_text(json.dumps(DEFAULT_PROFILE))
        destination = self.base / 'seccomp.json'
        digest = engine.write_seccomp(source, destination)
        self.assertEqual(digest, hashlib.sha256(destination.read_bytes()).hexdigest())
        self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
        self.assertEqual(json.loads(destination.read_text()), engine.seccomp_profile(DEFAULT_PROFILE))
        self.assertEqual(engine.write_seccomp(source, destination), digest)
        for invalid in ('not json', json.dumps({'syscalls': 'none'}), json.dumps({'syscalls': [{'action': 'x'}]})):
            with self.subTest(invalid=invalid):
                source.write_text(invalid)
                with self.assertRaises(engine.EngineError):
                    engine.write_seccomp(source, destination)
        with self.assertRaises(engine.EngineError):
            engine.write_seccomp(self.base / 'missing.json', destination)

    def test_inputs_identity_covers_every_build_input(self):
        copy = self.base / 'release'
        for name in engine.INPUTS:
            (copy / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, copy / name)
        self.assertEqual(engine.inputs_identity(copy), engine.inputs_identity(ROOT))
        self.assertEqual(sorted(engine.INPUTS), sorted('launcher/engine/' + path.name for path in ENGINE.iterdir()))
        for name in engine.INPUTS:
            with self.subTest(name=name):
                original = (copy / name).read_bytes()
                (copy / name).write_bytes(original + b'\n')
                self.assertNotEqual(engine.inputs_identity(copy), engine.inputs_identity(ROOT))
                (copy / name).write_bytes(original)


class EngineOptionsTests(unittest.TestCase):
    def options(self, **extra):
        values = dict(name='project-0-engine', seccomp='/release/launcher/engine/seccomp.json',
                      store='/home/user/.local/share/sandbox-toolchains/.images')
        return engine.container_options(**(values | extra))

    def test_options_hold_exactly_the_documented_exceptions(self):
        # session-container-engine: Fixed engine hardening exceptions / Engine carries no secrets.
        options = self.options()
        for expected in ('--rm', '--init', '--cap-drop=all', '--cap-add=SETUID,SETGID,SYS_CHROOT', '--security-opt=no-new-privileges',
                         '--security-opt=unmask=ALL', '--security-opt=label=disable', '--device=/dev/fuse',
                         '--device=/dev/net/tun', '--http-proxy=false', engine.USERNS,
                         '--security-opt=seccomp=/release/launcher/engine/seccomp.json'):
            self.assertIn(expected, options)
        self.assertEqual(options[options.index('--user') + 1], 'podman')
        self.assertIn('type=tmpfs,destination=/run/secrets,ro=true', options)
        for forbidden in ('--privileged', '--env', '--env-host', '--pid=host', '--network=host', '--userns=host'):
            self.assertFalse([value for value in options if value.startswith(forbidden)], forbidden)
        self.assertFalse([value for value in options if 'podman.sock' in value])

    def test_mounts_are_storage_store_workspace_and_ca_only(self):
        # session-container-engine: Engine mounts only the workspace and the image store.
        options = self.options(mounts=['/home/user/project', '/home/user'], ca_bundle='/etc/ssl/ca.pem',
                               labels=['io.example.session=token'])
        volumes = [options[i + 1] for i, value in enumerate(options) if value == '--volume']
        self.assertEqual(volumes, [
            engine.STORAGE,
            '/home/user/.local/share/sandbox-toolchains/.images/storage:/var/lib/shared:ro',
            '/home/user/project:/home/user/project:rw', '/home/user:/home/user:rw',
            '/etc/ssl/ca.pem:' + engine.CA + ':ro'])
        labels = [options[i + 1] for i, value in enumerate(options) if value == '--label']
        self.assertEqual(labels, [engine.STORE_LABEL + '=/home/user/.local/share/sandbox-toolchains/.images',
                                  'io.example.session=token'])
        with self.assertRaises(engine.EngineError):
            self.options(mounts=['/work\nspace'])

    def test_command_line_prints_nul_separated_options(self):
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'setup/engine.py'), 'options',
                                 '--name', 'n', '--seccomp', '/s.json', '--store', '/lib/.images',
                                 '--mount', '/w', '--label', 'a=b'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split('\0')[:-1],
                         engine.container_options(name='n', seccomp='/s.json', store='/lib/.images',
                                                  mounts=['/w'], labels=['a=b']))
        for argv in (['options', '--name', 'n'], ['options', '--bogus', 'x'], ['other']):
            with self.subTest(argv=argv):
                result = subprocess.run([sys.executable, '-I', str(ROOT / 'setup/engine.py'), *argv],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
