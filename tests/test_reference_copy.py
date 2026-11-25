"""Per-agent check that the shared components equal the sandbox-container reference copy.

Complements the shared ``tests/test_alignment.py`` (identifier scan and
wrapper consistency) with a byte-identity check: ``network/``, ``setup/`` and
the shared tests must stay byte-identical to ``sandbox-container`` at the reference
tag; a defect is fixed there first and copied afterwards.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_TAG = 'sandbox-ref-35'
REFERENCE_COMMIT = '2f407bf5bcb881a1e05912e98e5e5832460146ae'
SIBLING = ROOT.parent / 'sandbox-container'
# Shared directories whose complete file set is fixed by the manifest.
CLOSED_DIRECTORIES = ('launcher', 'network', 'setup')
SKIPPED_PARTS = ('__pycache__', 'bin')
MANIFEST = {
    'launcher/core.sh': '59807fed661114b9bf9f30b1cd9791e712c31cb5c697a71a356a37cc9bb27c66',
    'launcher/engine/.containerignore': '43b4090ba70a3c821b6eb27778ba357c3f99e10f4c55cf9f9c38f1c97d66dc7f',
    'launcher/engine/Containerfile': '133ebb116d600f813b8a38fbdb8c8b3327bf0c62e08a40f7b1e221cc305ff87f',
    'launcher/engine/containers.conf': '5e265f551762c9c327866c7374b5afa3ed84e296e6366b402eaed1e2247c5a79',
    'launcher/engine/entrypoint.sh': 'bcda48a005f9df6c7dccf554cf0dfab958868e8f01c6a1c39f0ea39009cd6f2b',
    'launcher/engine/resolv.conf': '8e40d95c29f83fe652b8a5d0dfda2ecfd94f9b51e0f406a517de1a3aa3fc6ad5',
    'launcher/engine/storage.conf': '79b646bc37a283ced2525bb278deebb0afe664f8fa92ed408c1d66034b2db9d3',
    'launcher/windows/bootstrap.sh': '2074ccfc72ddf9923375ec2d812d0e77d98283b4bbdef82952afcb8d479aa5a2',
    'launcher/windows/core.ps1': 'af5bf1783f22a5469e29cc3d1d1d1a7321782f481da4c86a273532fbb90b3f0f',
    'launcher/windows/enter.sh': '12c7844fddf9cf724b1f7fe3290e2e2b01de8459c1d9ceeb43901a5d53cada3f',
    'launcher/windows/install.ps1': 'fdb938da5a08059e1eb9760f3c7fc20fab68daddddd588d1566bb02a568e18b5',
    'launcher/windows/user-path.ps1': 'f72b1181925d8a1844d2e587ee0018f44b15ebc2b70c45df6f4e7bc912ef6458',
    'network/.containerignore': '938d84510789e940b804c8062c45c257d4a119ad55d21f60db57d6290590187c',
    'network/Containerfile': 'b909198e5027bc58ceca4e6076ea4b1a54faa592083e4c0190b2c671cc5b2f36',
    'network/README.md': '2b89e0d582fe45cf5b5e73258bbc2711f12e72288110426852a1f9236cd3de77',
    'network/agent_budgets.py': '96164f336b5a1b90098f00444612f9d45ae8a08c526f46abbfc75d7ac815d435',
    'network/agent_profile.py': 'f50069524f890d5c404644f2c3f0d1c87eb283a7408c5dea1069c59a7802ff17',
    'network/build-guard.sh': 'e0cc2fce71feb01c447dcb4daf5194f65f098b8a4c9837f756de7e12345cc611',
    'network/control.py': 'f5845bf6a7e7aeda21040749c799a4c2057428e5e31942aedf80842b4e1dc325',
    'network/guard-build.Containerfile': '7c882fff4fe515aa07219392388a084fd972188d549e47be416730f9153f60ad',
    'network/guard.c': '56bea4256f96592d385011819d2acafd878edd0d769449b47493b58d8acc452e',
    'network/guard_landlock.h': '8d490d342fa3b037f494cb32578c204302bbb8208c20ee74f5486388110744d0',
    'network/guard_seccomp.h': 'c158d67589d1ba5e3b0e5188974865d881e31bd2eee19ec9a08f1993f4ca4e16',
    'network/mux.py': '1f30d2016f2d9463a1c23d9e3007a2cc14b66de931dd86229df73961d65bc72c',
    'network/platform_check.py': 'c8372fdf47e7036f3d34190074678a17d33dc68e21384a0571db5fc00185f4cd',
    'network/policy.py': '9b300a3052254993c9f4149a540d4565193c0dba09a34ac2350dada7b4cf097a',
    'network/proxy.py': '73b4ea218a50512a23eaf9d7e3eec606fcadb7e14b91097a0593af5cc19494e2',
    'network/proxy_hardening.py': 'f528ba746a459586f490e266920c7def794139bda53a42db75894b2943b7a579',
    'network/qualification_peer.py': 'eaea202213ca9466dd8c904732b8a635bcfd20dcbcfcd5fe0a031cb9dd4dca0c',
    'network/qualification_probe.py': '1d55732db8f2beb639243f9a9c81bb8373b24b3fa588629c3130566ee3ff5b3a',
    'network/qualification_proxy.py': 'fea115190b81f5c7bd4ddaa6be825e3a50d3c7cc44c0ae30b1e70d66f36d48ab',
    'network/qualification_records.py': '0aaaed54fa3d58e8a571380980b46468389e3a1b6f1f60fc04d7a6a29a54ede3',
    'network/qualification_runtime.py': 'a9395438a6ee7c3dcdcc74d366ca3f00b92c5c55c248687e25c96ac735b37ada',
    'network/qualify.py': '9ef95460bf41155b96106ecbf6a3ad5bafea220c9c9a8746f6fc72a67f134935',
    'network/relay.py': '67f64f5a83994770f3bbac249d541f193dae3f494e20aa15a21cf2a44c0ce0ef',
    'network/release_acceptance.json': '50c7caa261f64c534af10d02d6420d5b08ffd20d1a8cc25a6321350bf186cefe',
    'network/resolv.conf': '8e40d95c29f83fe652b8a5d0dfda2ecfd94f9b51e0f406a517de1a3aa3fc6ad5',
    'network/revisions.py': 'fa35bcac26f5590c0d0b9477fea2773faa1f1eb285215e735e5cb8aa6b2b9cb1',
    'network/session.py': '4dfa508342c4197749bedc2046b395f29a11f0ed576adfc8747e1689126773ff',
    'network/tls_client_hello.py': 'a4ce71c1710cb1dba7c9ad5889b16549b5d7ebb4a7ae7c2edbf96eab32771e80',
    'setup/common.py': 'a6f8c97f292fab1f3436d75053fd7ee5ade45cbe06462b07123cd997cd072557',
    'setup/diagnostics.py': 'd6f2a81010f115f5631c829ccc70c39ba329b1baf44b393e34a33a884a3bdc3d',
    'setup/engine.py': 'f65bcdc2f4908317a2236613f46c2d2dda9752dba9e9a5480d2caf167f8a454c',
    'setup/launch.py': '6f7142f115842efec5ba4e1a5c7b776688998256367b8b852359c4c9201071b6',
    'setup/setup.py': '1d01438fbce67e9c7d930fc9b31f56427b082885c180ae27413381484a281a7d',
    'setup/smoke.py': 'c78fcaeeb0b7b435e235a0934d93f866bc16a3da3b6a58d5fa792c4743905720',
    'setup/toolchain-catalog/go.json': '020ec845d14171d59f1fea6adad5ad14ba53522a6f6ea227ae552852cbf91d1f',
    'setup/toolchain-catalog/java21.json': 'b8635f7ced74ea5027254b3602a0fa00dd0e78964bc755d6dc353e447c63c4a8',
    'setup/toolchain-catalog/maven3.9.json': 'd76f4b83786f1df674ab9bc2f85b2e4b621535a9fe1563490962b653dba2715c',
    'setup/toolchain-catalog/node24.json': '629613d5adca72397e865ee70d21afc73bd086ff9d003513013b744bc4e4cc80',
    'setup/toolchain-catalog/python3.13.json': 'ecefb40ae867a413cb9825dfb18fc49a9cd820591c46c2fa5d93bd9223fe29fd',
    'setup/toolchain-catalog/rust.json': 'eec2ab3d4c1e349cae9f0f59dcde01785b03801dec2033c9d93028f1c00dfefc',
    'setup/toolchains.py': '1a0771302d13173687a3b87b3fdfd846eaa745804ed07b4c170e58fa858dd7dd',
    'tests/fake_podman.py': '25c6ca6254af9d4204276d1d81310b61cdaff0296ca51fc57396a5280d6ead20',
    'tests/fixtures/agent/launcher.sh': 'd1093748a8d2b54150c3abf72461921798f00b56fe6349caf4b64fbe881ce3f4',
    'tests/fixtures/agent/policies/default.json': '4a990d9c90c90401c019faf5c7a96c083ae510b7a3507af584fec1f5bef8bb6f',
    'tests/fixtures/agent/profile.json': '25ea638dc7104e955b56b1c6663366c1a2d7280f92a04cb0997aece4b7d66d04',
    'tests/fixtures/shell-agent/launcher.sh': '0374bdeb8fec096a0b2b8eac9686eb85c8a2bb8b8e222744f877a89af1f4073b',
    'tests/fixtures/shell-agent/policies/default.json': 'a4a765ecaa63acb1f3aed3838b3f409a3c19dca57346ab284ce5ceda96b5f1fc',
    'tests/fixtures/shell-agent/profile.json': 'd254b6c0fdc5531c7fef98de074b206a753f4313394c4bfb2f0217134072376b',
    'tests/guard_bind_fixture.py': 'd6e4eb85cedb249ec9c6b4f2a026d14acbd5e1309a63ac036647be06781287cc',
    'tests/guard_mux_fixture.py': 'c641e419f5f2939c0c0af34d8a19dfcbcdf42302e0686e2d446bfad1bfc85f3d',
    'tests/guard_runtime_fixture.py': '6b41803115d149891213e6aa9940549ee91c10daf1ec066094cf3f9ab290905c',
    'tests/guard_syscall_mock.c': '56ba41dcf49c0f07b40dff43b5527b697f5682beb3f6ed14827230f8d7c86670',
    'tests/guard_terminal_probe.py': 'a4e5a6486c73c8cd3a43867e349e9cbe7b3721514e763152e2045c9cb6155f03',
    'tests/idle_mux_fixture.py': 'a85aff09892732f71f1c8436465a9d531dd027eab7cdc158c9073005d6508d58',
    'tests/mux_failure_fixture.py': 'a53da415f54bf98cceca6e546d705969c69a4d5619f5b3584cb35214353669b6',
    'tests/mux_fault_boundary.py': 'faf7aaa356dabd64306df8f5c0cb4054f9d267263db653bc0359c3d2cf2672fd',
    'tests/network_fixture.py': '1ca72af54ca825c4c081d04a26fd2a7deeeee9b785bd8da6aa945c2e87050786',
    'tests/proxy_budget_fixture.py': 'cde9c888d3842045752a93ec1963110749a3d9cd4d48ef76d199e0b4847fea67',
    'tests/sandbox_profile.py': 'ca73c66b3dc2e814197ca714b4dbe8ce7c3c4063b8dfd48b864a6869a563b87f',
    'tests/test_agent_profile.py': '51072b5c037496f5ad057610247d508c03ebe07e6b855ab440f8b9179c0b3ea6',
    'tests/test_alignment.py': '09451b6d5fbbc5ba5faa31d89d146c8ada57e1c562e4afb2c2efbd7840b4cbf9',
    'tests/test_engine.py': 'd2665ad9f812b1b3e0b19e319ba32a27e223be9f937cd5713c521ce2325c73f4',
    'tests/test_guard.py': 'aba9caeeb7084bd609e6c299e85cd048162b4f924e988ae4fcc569277ce97546',
    'tests/test_launcher.py': '549645b943d27d583b36360ee3c457b1cc5d1aaa5ef1464ae52cc1130a1767f6',
    'tests/test_mux.py': 'fb3a7cf8675d247c6609a337d56682d484cde6296e14ea939bfde70537cc8446',
    'tests/test_network_feasibility.py': '9d17c308598e4c51739f9a9b4f171b59d521acf19acd109fa2fdcab64fe0b1c7',
    'tests/test_network_policy.py': 'f57b3fe72deca821510855b6a474efb2e606471c4d231c210a699627e056f032',
    'tests/test_platform.py': 'e5e30cbb9edb3561e0a6cac67641ab27986ce9e6bd425e5be96976c39fb5fecf',
    'tests/test_qualification.py': 'b0df2ad151193f66ea665836132ffac464883a5e2ae7e47d29511f07d9997dfa',
    'tests/test_session.py': '30e01a4f1835fcc2bbadebe21f71ce74a3e380141806b75af8674f052582fe5f',
    'tests/test_setup.py': '954853d82c4b4a03957549fcb26718d8907edd3cb985b8aa2485d59f7b6b4212',
    'tests/test_tls_client_hello.py': '7d8f889af0c4a8f6d40038bdbda915f3afa3adc08c47b5506a02180b595b7ccc',
    'tests/test_tls_proxy.py': '77f9dda900a8ee28ef76d018d862bd0475193f5b90840fd29005a04fe4403e83',
    'tests/test_toolchains.py': '1bef34e1b9b8b3a36d4771235fb3876bc45e07922c775fdbdf76067aaf7fd863',
    'tests/test_windows_bootstrap.py': '2904d6057b83208f552f213226aad8ed8dbe0aaaeedab046bed7e4e2541a0ad8',
    'tests/test_windows_enter.py': 'c696a32b11e1b59ef695c71f8f8c9980a6caf8ffdec66c242a718f9b5a3ecb42',
    'tests/tls_binding_fixture.py': '062fe63ec1fc8ad399199a5f5823515070d5d1fa4ac62607f8722a61347f3331',
    'tests/windows/shim_tests.ps1': 'b2c258e00586517467c6c8b12735d5f0498acf7ce20df76927a6b4092bef85c0',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(root):
    """Changed, missing and extra shared files below ``root``."""
    found = []
    for name, expected in sorted(MANIFEST.items()):
        path = root / name
        if not path.is_file():
            found.append('missing ' + name)
        elif digest(path) != expected:
            found.append('changed ' + name)
    for directory in CLOSED_DIRECTORIES:
        for path in sorted((root / directory).rglob('*')):
            relative = path.relative_to(root)
            if path.is_file() and not any(part in SKIPPED_PARTS for part in relative.parts) \
                    and str(relative) not in MANIFEST:
                found.append('extra ' + str(relative))
    return found


def identifiers(root):
    return json.loads((root / 'agent/profile.json').read_text())['identifiers']


def literals(root, names):
    pattern = re.compile('|'.join(map(re.escape, names)), re.IGNORECASE)
    found = []
    for name in sorted(MANIFEST):
        for number, line in enumerate((root / name).read_text(errors='replace').splitlines(), 1):
            if pattern.search(line):
                found.append(f'{name}:{number}: {line.strip()[:120]}')
    return found


def scratch_copy(directory):
    copy = Path(directory)
    for name in (*CLOSED_DIRECTORIES, 'tests', 'agent'):
        if (ROOT / name).is_dir():
            shutil.copytree(ROOT / name, copy / name, ignore=shutil.ignore_patterns(*SKIPPED_PARTS))
    return copy


class ReferenceCopy(unittest.TestCase):
    def test_shared_files_match_the_reference_manifest(self):
        self.assertEqual(differences(ROOT), [])

    def test_manifest_detects_changed_missing_and_extra_files(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = scratch_copy(directory)
            target = copy / 'network/control.py'
            target.write_bytes(target.read_bytes() + b' ')
            setup = copy / 'setup/common.py'
            setup.write_bytes(setup.read_bytes() + b' ')
            (copy / 'network/mux.py').unlink()
            (copy / 'network/local.py').write_text('')
            self.assertEqual(differences(copy), [
                'changed network/control.py', 'missing network/mux.py', 'changed setup/common.py',
                'extra network/local.py'])

    @unittest.skipUnless((ROOT / 'agent/profile.json').is_file(), 'agent profile not written yet')
    def test_shared_files_contain_no_agent_identifiers(self):
        self.assertEqual(literals(ROOT, identifiers(ROOT)), [])

    @unittest.skipUnless((ROOT / 'agent/profile.json').is_file(), 'agent profile not written yet')
    def test_scan_detects_an_injected_identifier(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = scratch_copy(directory)
            target = copy / 'network/control.py'
            target.write_text(target.read_text() + '\n# ' + identifiers(ROOT)[0].title() + ' literal\n')
            found = literals(copy, identifiers(ROOT))
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0].startswith('network/control.py:'))

    def test_sibling_checkout_at_the_reference_tag_matches(self):
        if not (SIBLING / '.git').exists():
            self.skipTest('no sibling sandbox-container checkout')
        commit = subprocess.run(['git', '-C', str(SIBLING), 'rev-parse', '--verify', '-q',
                                 REFERENCE_TAG + '^{commit}'], capture_output=True, text=True)
        if commit.returncode:
            self.skipTest('sibling checkout has no ' + REFERENCE_TAG)
        self.assertEqual(commit.stdout.strip(), REFERENCE_COMMIT)
        with tempfile.TemporaryDirectory() as directory:
            archive = subprocess.run(['git', '-C', str(SIBLING), 'archive', REFERENCE_TAG, *sorted(MANIFEST)],
                                     capture_output=True, check=True).stdout
            subprocess.run(['tar', '-x', '-C', directory], input=archive, check=True)
            self.assertEqual(differences(Path(directory)), [])
            result = subprocess.run(['diff', '-r', '-x', '__pycache__', '-x', 'bin', directory + '/network',
                                     str(ROOT / 'network')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
