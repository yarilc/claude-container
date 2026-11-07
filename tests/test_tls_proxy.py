"""Production proxy/relay inspection with controlled upstream byte counters."""
import asyncio
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'network'))
import mux
import proxy
import relay
import tls_client_hello as tls
from test_tls_client_hello import message, records, sni, extension


class TLSProxyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().set_debug(False)
        self.received = []
        self.connections = []
        self.audit = []
        self.instance = proxy.Proxy({'destinations': [{'host': 'allowed.test', 'port': 443}]},
                                    type('Audit', (), {'record': lambda _, *args: self.audit.append(args)})())
        self.upstream = await asyncio.start_server(self.endpoint, '127.0.0.1', 0)
        self.server = await asyncio.start_server(self.instance.handle, '127.0.0.1', 0)
        self.original_connect = self.instance.connect
        self.instance.connect = self.connect
        reader, writer = await asyncio.open_connection('127.0.0.1', self.server.sockets[0].getsockname()[1])
        self.channel = await mux.Channel(reader, writer).start()
        self.relay = await asyncio.start_server(relay.Relay(self.channel).handle, '127.0.0.1', 0)

    async def endpoint(self, reader, writer):
        self.connections.append(writer)
        data = bytearray()
        self.received.append(data)
        try:
            while part := await reader.read(16384):
                data.extend(part)
                writer.write(part)
                await writer.drain()
        finally:
            writer.close()

    async def connect(self, host, port):
        if (host, port) not in self.instance.rules:
            raise proxy.Rejected('policy-denied', host, port)
        return await asyncio.open_connection('127.0.0.1', self.upstream.sockets[0].getsockname()[1])

    async def asyncTearDown(self):
        await self.channel.close()
        for writer in self.connections:
            writer.close()
            await writer.wait_closed()
        for server in (self.relay, self.server, self.upstream):
            server.close()
            await server.wait_closed()
        await asyncio.sleep(.01)
        self.assertEqual(self.instance.inspection_storage, 0)

    async def rejected(self, payload):
        stream = await self.channel.open(b'allowed.test:443')
        await stream.send(payload)
        await stream.eof()
        try:
            data = await asyncio.wait_for(stream.read(), 2)
        except mux.StreamClosed:
            data = b''
        self.assertEqual(data, b'')
        await stream.close()
        self.assertEqual(bytes(self.received[-1]), b'')
        self.assertFalse(self.channel.closed)

    async def accepted(self, payload):
        stream = await self.channel.open(b'allowed.test:443')
        for index in range(0, len(payload), 7):
            await stream.send(payload[index:index + 7])
        result = bytearray()
        while len(result) < len(payload):
            result.extend(await asyncio.wait_for(stream.read(), 2))
        self.assertEqual(result, payload)
        await stream.close()

    async def test_direct_mux_rejection_zero_upstream_bytes_and_reuse(self):
        for payload in (records(message(sni(b'other.test'))), b'not-tls', records(message(b'')),
                        records(message(sni() + extension(0xfe0d, b'grease'))), records(message(sni() * 2)),
                        records(message(sni(b'secret-token.test'))), records(message(sni(b'secret\n.test')))):
            await self.rejected(payload)
        await self.accepted(records(message()) + b'ordered-trailing-bytes')
        self.assertNotIn('other.test', repr(self.audit))
        self.assertNotIn('grease', repr(self.audit))
        self.assertNotIn('secret', repr(self.audit))
        self.assertIn('tls-identity', repr(self.audit))
        self.assertIn('tls-ech', repr(self.audit))

    async def test_actual_connect_relay_progress_and_exact_forwarding(self):
        reader, writer = await asyncio.open_connection('127.0.0.1', self.relay.sockets[0].getsockname()[1])
        writer.write(b'CONNECT allowed.test:443 HTTP/1.1\r\n\r\n')
        await writer.drain()
        response = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 2)
        self.assertIn(b'200', response)
        self.assertEqual(bytes(self.received[-1]), b'')
        wire = records(message(), 1)
        writer.write(wire)
        await writer.drain()
        self.assertEqual(await asyncio.wait_for(reader.readexactly(len(wire)), 2), wire)
        writer.close()
        await writer.wait_closed()

    async def test_absolute_timeout_overflow_and_concurrent_progress(self):
        with patch('proxy.INSPECTION_TIMEOUT', .08):
            stream = await self.channel.open(b'allowed.test:443')
            async def trickle():
                try:
                    for byte in records(message()):
                        await stream.send(bytes([byte]))
                        await asyncio.sleep(.02)
                except mux.StreamClosed:
                    pass
            sending = asyncio.create_task(trickle())
            await self.accepted(records(message()))
            try:
                await asyncio.wait_for(stream.read(), 1)
            except mux.StreamClosed:
                pass
            await sending
            await stream.close()
        self.assertIn('tls-timeout', repr(self.audit))
        await self.rejected(b'\x16\x03\x03\0\x04\x01\x01\0\0')
        self.assertIn('tls-overflow', repr(self.audit))

    async def test_channel_death_releases_inspection(self):
        streams = await asyncio.gather(*(self.channel.open(b'allowed.test:443') for _ in range(64)))
        await asyncio.sleep(.01)
        self.assertEqual(self.instance.inspection_storage, 64 * tls.STORAGE)
        await self.channel.close()
        for _ in range(100):
            if self.instance.inspection_storage == 0:
                break
            await asyncio.sleep(.01)
        self.assertEqual(self.instance.inspection_storage, 0)

    async def test_inspection_storage_limit_fails_closed(self):
        # Reserve the complete bounded session budget, then exercise overflow.
        self.instance.inspection_storage = tls.STORAGE * proxy.MAX_CONNECTIONS
        try:
            try:
                stream = await self.channel.open(b'allowed.test:443')
            except mux.StreamClosed:
                pass
            else:
                try:
                    await asyncio.wait_for(stream.read(), 2)
                except mux.StreamClosed:
                    pass
                await stream.close()
            self.assertEqual(bytes(self.received[-1]), b'')
            self.assertIn('tls-overflow', repr(self.audit))
        finally:
            self.instance.inspection_storage = 0


if __name__ == '__main__':
    unittest.main()
