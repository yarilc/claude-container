"""ClientHello identity, framing and adversarial length regressions."""
from pathlib import Path
import random
import ssl
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'network'))
import tls_client_hello as tls


def vector(data, size=2):
    return len(data).to_bytes(size, 'big') + data


def extension(kind, value):
    return kind.to_bytes(2, 'big') + vector(value)


def sni(name=b'allowed.test'):
    return extension(0, vector(b'\0' + vector(name)))


def message(extensions=None, compression=b'\0', ciphers=b'\x13\x01', session=b'', version=b'\x03\x03'):
    if extensions is None:
        extensions = sni()
    body = version + b'r' * 32 + vector(session, 1) + vector(ciphers) + vector(compression, 1) + vector(extensions)
    return b'\x01' + len(body).to_bytes(3, 'big') + body


def records(hello, size=16384):
    return b''.join(b'\x16\x03\x01' + vector(hello[i:i + size]) for i in range(0, len(hello), size))


def generated(version):
    context = ssl.create_default_context()
    context.minimum_version = context.maximum_version = version
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    client = context.wrap_bio(incoming, outgoing, server_side=False, server_hostname='allowed.test')
    try:
        client.do_handshake()
    except ssl.SSLWantReadError:
        pass
    return outgoing.read()


class ClientHelloTests(unittest.TestCase):
    def accept(self, wire, expected='allowed.test', split=None):
        parser = tls.ClientHello(expected)
        if split is None:
            self.assertTrue(parser.feed(wire))
        else:
            self.assertFalse(parser.feed(wire[:split]))
            self.assertTrue(parser.feed(wire[split:]))
        parser.finish()
        self.assertEqual(bytes(parser.original()), wire)
        return parser

    def reject(self, wire, reason=None):
        parser = tls.ClientHello('allowed.test')
        with self.assertRaises(tls.TLSRejected) as caught:
            if not parser.feed(wire):
                parser.finish()
        if reason:
            self.assertEqual(str(caught.exception), reason)
        self.assertLessEqual(parser.used, tls.MAX_WIRE)
        return parser

    def test_generated_versions_every_split(self):
        for version in (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
            wire = generated(version)
            self.accept(wire)
            for split in range(len(wire)):
                self.accept(wire, split=split)

    def test_record_fragmentation_and_coalesced_surplus(self):
        hello = message()
        for size in (1, 2, 3, 4, 5, 17):
            wire = records(hello, size) + b'\x17\x03\x03\0\x04tail'
            self.accept(wire)
        wire = records(hello, 1)
        parser = tls.ClientHello('allowed.test')
        for index, byte in enumerate(wire):
            self.assertEqual(parser.feed(bytes([byte])), index == len(wire) - 1)
        self.assertEqual(bytes(parser.original()), wire)

    def test_normalization(self):
        self.accept(records(message(sni(b'ALLOWED.TEST.'))))

    def test_names(self):
        for name in (b'', b'other.test', b'allowed.test.evil.test', b'127.0.0.1', b'::1', b'bad\0.test', b'bad\xff.test', b'a' * 255):
            self.reject(records(message(sni(name))), 'tls-identity')
        for extensions in (b'', sni() + sni(), sni() + sni(b'other.test'),
                           extension(0, vector(b'\0' + vector(b'allowed.test') + b'\0' + vector(b'other.test'))),
                           extension(0, vector(b'\x01' + vector(b'allowed.test'))),
                           extension(0, b'\0\0'), extension(0, vector(b'\0\0\x20short'))):
            self.reject(records(message(extensions)))

    def test_versions_ech_unknown_extensions(self):
        for version in (0x0303, 0x0304):
            self.accept(records(message(sni() + extension(43, vector(b'\x0a\x0a' + version.to_bytes(2, 'big'), 1)))))
        self.accept(records(message(sni() + extension(0xaaaa, b'opaque'))))
        self.reject(records(message(sni() + extension(43, vector(b'\x03\x02', 1)))), 'tls-unsupported')
        self.reject(records(message(version=b'\x03\x02')), 'tls-unsupported')
        for kind in tls.HIDDEN_NAME_EXTENSIONS:
            for ech in (b'', b'\0' * 128):
                self.reject(records(message(sni() + extension(kind, ech))), 'tls-ech')
        self.reject(records(message(sni() + extension(123, b'') * 2)), 'tls-malformed')
        self.reject(records(message(sni() + extension(43, b'\x01\x03'))), 'tls-malformed')

    def test_structural_errors_and_truncations(self):
        wire = records(message())
        for end in range(len(wire)):
            self.reject(wire[:end])
        for data in (b'GET / HTTP/1.1\r\n', b'\x80\x20\x01\x03\x03', b'\x16\x03\x03\0\0',
                     b'\x16\x03\x03\x40\x01', records(b'\x02\0\0\x01x'),
                     records(message(session=b'x' * 33)), records(message(ciphers=b'x')),
                     records(message(compression=b'\x01')), records(message() + b'x')[:10]):
            self.reject(data)

    def test_limits_and_random_mutations(self):
        # Exact handshake bound, with ordinary padding carried in an extension.
        base = len(message(sni() + extension(21, b'')))
        hello = message(sni() + extension(21, b'\0' * (tls.MAX_HELLO - base)))
        self.assertEqual(len(hello), tls.MAX_HELLO)
        self.accept(records(hello))
        self.accept(records(hello, 512))  # Exactly 128 records.
        exact_wire = records(hello)
        self.accept(exact_wire + b'x' * (tls.MAX_WIRE - len(exact_wire)))
        self.reject(records(b'\x01' + tls.MAX_HELLO.to_bytes(3, 'big') + b'xxxx'), 'tls-overflow')
        self.reject(b'x' * (tls.MAX_WIRE + 1), 'tls-overflow')
        # Record 129 is rejected even when each fragment is otherwise legal.
        self.reject(records(hello, 1), 'tls-overflow')
        wire = generated(ssl.TLSVersion.TLSv1_3)
        rng = random.Random(20261107)
        for _ in range(500):
            mutated = bytearray(wire)
            for _ in range(rng.randrange(1, 5)):
                mutated[rng.randrange(len(mutated))] = rng.randrange(256)
            parser = tls.ClientHello('allowed.test')
            try:
                if not parser.feed(mutated):
                    parser.finish()
            except tls.TLSRejected as error:
                self.assertIn(str(error), ('tls-malformed', 'tls-identity', 'tls-ech', 'tls-overflow', 'tls-unsupported'))
            self.assertEqual(len(parser.wire) + len(parser.hello), tls.STORAGE)


if __name__ == '__main__':
    unittest.main()
