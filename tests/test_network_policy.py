"""Credential-free negative tests for the trusted network boundary."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

NETWORK = Path(__file__).resolve().parents[1] / 'network'
sys.path.insert(0, str(NETWORK))
import policy
import proxy
import mux


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads((NETWORK / 'policies/default.json').read_text())

    def test_profiles_and_normalization(self):
        policy.validate(self.value)
        self.assertEqual(policy.hostname('API.Anthropic.COM.'), 'api.anthropic.com')
        self.assertEqual(len(policy.selected(self.value, 'anthropic-api')['destinations']), 1)
        self.assertEqual(len(policy.selected(self.value, 'anthropic-account')['destinations']), 4)
        with self.assertRaises(policy.PolicyError):
            policy.selected(self.value, 'missing')

    def test_reject_invalid_policy_fields_and_rules(self):
        for mutate in (
            lambda v: v.update(unknown=True),
            lambda v: v.update(schema_version=True),
            lambda v: v['profiles']['anthropic-api'].update(unknown=True),
            lambda v: v['profiles']['anthropic-api'].update(disable_optional_traffic=False),
            lambda v: v['profiles']['anthropic-api']['destinations'].clear(),
            lambda v: v['profiles']['anthropic-api']['destinations'].append({'host': 'API.ANTHROPIC.COM.', 'port': 443}),
            lambda v: v['profiles']['anthropic-api']['destinations'][0].update(port=80),
            lambda v: v['profiles']['anthropic-api']['destinations'][0].update(host='*.anthropic.com'),
            lambda v: v['profiles']['anthropic-api']['destinations'][0].update(host='api.anthropic.com.evil.test'),
            lambda v: v['profiles']['anthropic-api']['destinations'][0].update(port=True),
        ):
            value = copy.deepcopy(self.value)
            mutate(value)
            with self.subTest(value=value), self.assertRaises(policy.PolicyError):
                policy.validate(value)

    def test_authority_grammar_and_no_credentials(self):
        self.assertEqual(proxy.authority(b'CONNECT API.ANTHROPIC.COM.:443 HTTP/1.1\r\nHost: api.anthropic.com\r\n\r\n'),
                         ('api.anthropic.com', 443))
        for target in ('user:secret@api.anthropic.com:443', 'api.anthropic.com:0443',
                       'api.anthropic.com:0', 'api.anthropic.com:65536',
                       '127.0.0.1:443', '[::1]:443', 'api%2eanthropic.com:443',
                       'api.anthropic.com..:443', '*.anthropic.com:443',
                       'api.anthropic.com:443/path?token=secret', 'api.anthropic.com:443\x00'):
            with self.subTest(target=target), self.assertRaises(proxy.Rejected) as caught:
                proxy.authority(f'CONNECT {target} HTTP/1.1\r\n\r\n'.encode())
            self.assertEqual(caught.exception.host, '')
        for request in (b'GET https://api.anthropic.com HTTP/1.1\r\n\r\n',
                        b'CONNECT api.anthropic.com:443 HTTP/1.1\r\nContent-Length: 5\r\n\r\n',
                        b'CONNECT api.anthropic.com:443 HTTP/1.1\r\nProxy-Authorization: secret\r\n\r\n'):
            with self.assertRaises(proxy.Rejected):
                proxy.authority(request)

    def test_address_classification(self):
        for network in policy.SPECIAL_NETWORKS:
            self.assertFalse(policy.public_address(str(network.network_address)))
            self.assertFalse(policy.public_address(str(network.broadcast_address)))
        for address in ('127.0.0.1', '10.0.0.1', '172.16.0.1', '192.168.0.1',
                        '169.254.169.254', '100.64.0.1', '0.0.0.0', '192.0.2.1',
                        '224.0.0.1', '240.0.0.1', '::1', '::', 'fc00::1', 'fe80::1',
                        '2001:db8::1', 'ff02::1', '::ffff:8.8.8.8', '64:ff9b::808:808',
                        '2002:0808:0808::1'):
            with self.subTest(address=address):
                self.assertFalse(policy.public_address(address))
        self.assertTrue(policy.public_address('1.1.1.1'))
        self.assertTrue(policy.public_address('2606:4700:4700::1111'))

    def test_dns_mixed_rebinding_and_single_resolution(self):
        public = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('1.1.1.1', 443))
        private = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('127.0.0.1', 443))
        with patch('socket.getaddrinfo', return_value=[public]) as resolver:
            result = proxy.resolve('allowed.test', 443)
            self.assertEqual(result[0][-1], ('1.1.1.1', 443))
            self.assertEqual(resolver.call_count, 1)
        for answers in ([public, private], [private], []):
            with patch('socket.getaddrinfo', return_value=answers), self.assertRaises(proxy.Rejected):
                proxy.resolve('allowed.test', 443)
        with patch('socket.getaddrinfo', side_effect=socket.gaierror()), self.assertRaises(proxy.Rejected) as caught:
            proxy.resolve('allowed.test', 443)
        self.assertEqual(caught.exception.reason, 'dns-failure')

    def test_explicit_exception_cannot_broaden_address(self):
        profile = {'authentication': 'custom', 'disable_optional_traffic': True,
                   'destinations': [{'host': 'local.test', 'port': 8443, 'addresses': ['127.0.0.1']}]}
        self.value['profiles']['local-provider'] = profile
        policy.validate(self.value)
        local = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('127.0.0.1', 8443))
        with patch('socket.getaddrinfo', return_value=[local]):
            self.assertEqual(proxy.resolve('local.test', 8443, ['127.0.0.1'])[0][-1], local[-1])
            with self.assertRaises(proxy.Rejected):
                proxy.resolve('local.test', 8443, ['127.0.0.2'])

    def test_mount_overlap(self):
        parent = Path('/workspace')
        self.assertTrue(policy.overlaps(parent, parent / 'policy.json'))
        self.assertTrue(policy.overlaps(parent / 'policy.json', parent))
        self.assertFalse(policy.overlaps(parent, Path('/workspace-other/policy.json')))

    def test_trusted_paths_and_immutable_snapshot(self):
        native = os.environ.get('CLAUDE_TEST_STATE_ROOT', str(Path.home()))
        if any(p.stat().st_mode & 0o022 for p in (Path(native), *Path(native).parents)):
            self.skipTest('native protected ancestors required; run tests/run-runtime.sh --network-policy')
        with tempfile.TemporaryDirectory(prefix='policy-test-', dir=native) as directory:
            root = Path(directory)
            install = root / 'installed'
            (install / 'network').mkdir(parents=True)
            for name in ('control.py', 'policy.py', 'relay.py', 'mux.py', 'resolv.conf'):
                shutil.copyfile(NETWORK / name, install / 'network' / name)
            import hashlib, struct
            binary_dir = install / 'network/bin'
            binary_dir.mkdir()
            # Synthetic ELF metadata fixture; preflight never executes it.
            elf = bytearray(64)
            elf[:6] = b'\x7fELF\x02\x01'
            struct.pack_into('<H', elf, 18, 62)
            struct.pack_into('<Q', elf, 32, 64)
            struct.pack_into('<HH', elf, 54, 56, 0)
            guard = binary_dir / 'claude-egress-guard'
            guard.write_bytes(elf)
            guard.chmod(0o500)
            (binary_dir / 'claude-egress-guard.sha256').write_text(hashlib.sha256(elf).hexdigest() + '  claude-egress-guard\n')
            (install / 'claude-container.sh').write_text('protected fixture')
            policy_file = install / 'policy.json'
            policy_file.write_text(json.dumps(self.value))
            workspace = root / 'workspace'
            workspace.mkdir()
            runtime = root / 'runtime'
            runtime.mkdir(mode=0o700)
            session = runtime / 'session'
            session.mkdir(mode=0o700)
            command = [sys.executable, '-I', str(install / 'network/control.py'), 'snapshot',
                       '--installation', str(install), '--writable', str(workspace),
                       '--policy', str(policy_file), '--profile', 'anthropic-api',
                       '--proxy-image', 'sha256:' + 'a' * 64,
                       '--runtime', str(runtime), '--session', str(session)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((session / 'config/manifest.json').read_text())
            self.assertEqual(manifest['sha256'], hashlib.sha256(elf).hexdigest())
            self.assertEqual(manifest['protocol'], 1)
            self.assertEqual(manifest['session'], session.name)
            preflight = command.copy()
            preflight[3] = 'preflight'
            for target in ('/', '/tmp', '/tmp/child', '/run/nested', '/var/tmp/child'):
                rejected = subprocess.run([*preflight, '--mount-target', target], capture_output=True, text=True)
                self.assertNotEqual(rejected.returncode, 0, target)
                self.assertIn('reserved private IPC hierarchy', rejected.stderr)
            guard.chmod(0o700)
            guard.write_bytes(bytes(elf) + b'tampered')
            rejected = subprocess.run(preflight, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('bootstrap digest mismatch', rejected.stderr)
            guard.write_bytes(elf)
            original = (session / 'config/policy.json').read_bytes()
            policy_file.write_text('{}')
            self.assertEqual((session / 'config/policy.json').read_bytes(), original)
            self.assertEqual((session / 'config/policy.json').stat().st_mode & 0o777, 0o400)
            alias = workspace / 'alias.json'
            alias.symlink_to(policy_file)
            with self.assertRaises(policy.PolicyError):
                policy.trusted_path(alias, [workspace])
            for writable in (install, root, Path('/')):
                with self.assertRaises(policy.PolicyError):
                    policy.trusted_path(policy_file, [writable])
            policy_file.chmod(0o666)
            with self.assertRaises(policy.PolicyError):
                policy.trusted_path(policy_file)
            policy_file.chmod(0o600)
            install.chmod(0o777)
            with self.assertRaises(policy.PolicyError):
                policy.trusted_path(policy_file)

    def test_json_duplicate_keys_and_audit_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'policy.json'
            file.write_text('{"schema_version":1,"schema_version":2}')
            with self.assertRaises(policy.PolicyError):
                policy.load(file)
            audit = proxy.Audit(Path(directory) / 'audit.jsonl', 'synthetic-session')
            secret_request = b'CONNECT user:secret@allowed.test:443 HTTP/1.1\r\nAuthorization: secret\r\n\r\n'
            with self.assertRaises(proxy.Rejected) as caught:
                proxy.authority(secret_request)
            audit.record(caught.exception.reason, caught.exception.host, caught.exception.port)
            entry = audit.path.read_text()
            self.assertNotIn('secret', entry)
            self.assertNotIn('Authorization', entry)
            self.assertEqual(audit.path.stat().st_mode & 0o777, 0o600)
            audit.size_limit = 1
            audit.record('second-record')
            self.assertEqual(audit.path.read_text(), entry)


class AsyncProxyTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_transport_handshake_is_rejected_without_dns(self):
        import asyncio
        class Audit:
            def __init__(self):
                self.records = []
            def record(self, *args):
                self.records.append(args)
        audit = Audit()
        instance = proxy.Proxy({'destinations': [{'host': 'allowed.test', 'port': 443}]}, audit)
        server = await asyncio.start_server(instance.handle, '127.0.0.1', 0, limit=proxy.MAX_HEADER)
        reader, writer = await asyncio.open_connection('127.0.0.1', server.sockets[0].getsockname()[1])
        with patch('proxy.resolve') as resolver:
            writer.write(b'CONNECT allowed.test:443 HTTP/1.1\r\nX: ' + b'a' * 20000 + b'\r\n\r\n')
            await writer.drain()
            response = await asyncio.wait_for(reader.read(), 2)
            self.assertEqual(response, mux.MAGIC)
            resolver.assert_not_called()
        self.assertEqual(audit.records[0][0], 'transport-unavailable')
        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()

    async def test_unapproved_host_never_reaches_dns(self):
        instance = proxy.Proxy({'destinations': [{'host': 'allowed.test', 'port': 443}]}, None)
        for host, port in (('allowed.test.evil.test', 443), ('allowed.test', 80), ('127.0.0.1', 443)):
            with patch('proxy.resolve') as resolver, self.assertRaises(proxy.Rejected):
                await instance.connect(host, port)
            resolver.assert_not_called()

    async def test_connection_uses_validated_numeric_address(self):
        # Exercise actual socket path without contacting an external endpoint.
        import asyncio
        server = await asyncio.start_server(lambda r, w: w.close(), '127.0.0.1', 0)
        port = server.sockets[0].getsockname()[1]
        instance = proxy.Proxy({'destinations': [{'host': 'local.test', 'port': port, 'addresses': ['127.0.0.1']}]}, None)
        answers = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, ('127.0.0.1', port))]
        with patch('proxy.resolve', return_value=answers) as resolver, patch('socket.getaddrinfo', side_effect=AssertionError('second DNS lookup')):
            _, writer = await instance.connect('local.test', port)
            writer.close()
            await writer.wait_closed()
        self.assertEqual(resolver.call_count, 1)
        server.close()
        await server.wait_closed()
