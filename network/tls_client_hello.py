"""Bounded inspection of the initial plaintext TLS ClientHello; never terminates TLS."""
from policy import PolicyError, hostname

MAX_HELLO = 64 * 1024
MAX_WIRE = 96 * 1024
MAX_RECORDS = 128
MAX_RECORD = 16 * 1024
STORAGE = MAX_HELLO + MAX_WIRE
INSPECTION_TIMEOUT = 10
ENFORCEMENT = 'tls-clienthello-sni-v1'
# RFC 9849 plus the retired ESNI/ECH draft name-hiding extensions.
HIDDEN_NAME_EXTENSIONS = (0xfe0d, 0xffce, 0xff02, 0xff03, 0xff04)


class TLSRejected(Exception):
    """Contains only a fixed reason code, never wire input."""


class Cursor:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, count):
        end = self.pos + count
        if end > len(self.data):
            raise TLSRejected('tls-malformed')
        result = self.data[self.pos:end]
        self.pos = end
        return result

    def number(self, size):
        return int.from_bytes(self.take(size), 'big')

    def vector(self, size):
        return self.take(self.number(size))

    def end(self):
        if self.pos != len(self.data):
            raise TLSRejected('tls-malformed')


def validate(data, expected):
    cursor = Cursor(data)
    if cursor.number(2) != 0x0303:
        raise TLSRejected('tls-unsupported')
    cursor.take(32)
    if len(cursor.vector(1)) > 32:
        raise TLSRejected('tls-malformed')
    ciphers = cursor.vector(2)
    if not ciphers or len(ciphers) % 2:
        raise TLSRejected('tls-malformed')
    compression = cursor.vector(1)
    if not compression or 0 not in compression:
        raise TLSRejected('tls-malformed')
    extensions = Cursor(cursor.vector(2))
    cursor.end()
    # Fixed 8 KiB metadata rather than an attacker-sized Python set.
    seen = bytearray(8192)
    name = None
    versions = None
    while extensions.pos < len(extensions.data):
        kind = extensions.number(2)
        value = extensions.vector(2)
        slot, bit = divmod(kind, 8)
        if seen[slot] & (1 << bit):
            raise TLSRejected('tls-malformed')
        seen[slot] |= 1 << bit
        if kind in HIDDEN_NAME_EXTENSIONS:
            raise TLSRejected('tls-ech')
        if kind == 0:
            names = Cursor(value)
            entry = Cursor(names.vector(2))
            names.end()
            if entry.number(1) != 0:
                raise TLSRejected('tls-identity')
            encoded = entry.vector(2)
            entry.end()
            if not 0 < len(encoded) <= 254:
                raise TLSRejected('tls-identity')
            try:
                name = hostname(bytes(encoded).decode('ascii'))
            except (UnicodeError, PolicyError):
                raise TLSRejected('tls-identity') from None
        elif kind == 43:
            offered = Cursor(value)
            encoded = offered.vector(1)
            offered.end()
            if not encoded or len(encoded) % 2:
                raise TLSRejected('tls-malformed')
            versions = any(int.from_bytes(encoded[i:i + 2], 'big') in (0x0303, 0x0304)
                           for i in range(0, len(encoded), 2))
    if versions is False:
        raise TLSRejected('tls-unsupported')
    if name is None or name != expected:
        raise TLSRejected('tls-identity')


class ClientHello:
    """Retains at most MAX_WIRE original bytes and MAX_HELLO handshake bytes.

    Fixed buffers avoid allocation from declared lengths and resizing/copy peaks.
    The caller reserves STORAGE before construction and owns the input chunk.
    """
    def __init__(self, expected):
        self.expected = expected
        self.wire = bytearray(MAX_WIRE)
        self.hello = bytearray(MAX_HELLO)
        self.used = self.offset = self.filled = self.records = 0
        self.length = None
        self.done = False

    def feed(self, data):
        if self.done:
            raise TLSRejected('tls-malformed')
        if len(data) > MAX_WIRE - self.used:
            raise TLSRejected('tls-overflow')
        wire, hello = memoryview(self.wire), memoryview(self.hello)
        wire[self.used:self.used + len(data)] = data
        self.used += len(data)
        while self.used - self.offset >= 5:
            header = wire[self.offset:self.offset + 5]
            if header[0] != 22 or int.from_bytes(header[1:3], 'big') not in (0x0301, 0x0302, 0x0303):
                raise TLSRejected('tls-malformed')
            size = int.from_bytes(header[3:5], 'big')
            if not 0 < size <= MAX_RECORD:
                raise TLSRejected('tls-malformed')
            if self.records >= MAX_RECORDS:
                raise TLSRejected('tls-overflow')
            end = self.offset + 5 + size
            if end > self.used:
                return False
            part = wire[self.offset + 5:end]
            self.records += 1
            self.offset = end
            while part:
                target = 4 if self.length is None else self.length
                count = min(len(part), target - self.filled)
                hello[self.filled:self.filled + count] = part[:count]
                self.filled += count
                part = part[count:]
                if self.filled < target:
                    break
                if self.length is None:
                    if hello[0] != 1:
                        raise TLSRejected('tls-malformed')
                    self.length = 4 + int.from_bytes(hello[1:4], 'big')
                    if self.length > MAX_HELLO:
                        raise TLSRejected('tls-overflow')
                    if self.length <= 4:
                        raise TLSRejected('tls-malformed')
                else:
                    validate(hello[4:self.length], self.expected)
                    self.done = True
                    return True
        return False

    def finish(self):
        if not self.done:
            raise TLSRejected('tls-malformed')

    def original(self):
        if not self.done:
            raise TLSRejected('tls-malformed')
        return memoryview(self.wire)[:self.used]
