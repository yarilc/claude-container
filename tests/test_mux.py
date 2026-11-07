"""Bounded transport, state-machine and cross-stream isolation tests."""
import asyncio
from pathlib import Path
import random
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'network'))
import mux
import proxy
from unittest.mock import patch


class MuxTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Avoid traceback/source inspection on the Windows bind for every task.
        asyncio.get_running_loop().set_debug(False)
        self.peers = []
        self.errors = []
        self.block = asyncio.Event()
        self.audit = type('Audit', (), {'record': lambda _, *args: self.errors.append(args)})()
        self.server = await asyncio.start_server(self.accept, '127.0.0.1', 0)
        reader, writer = await asyncio.open_connection('127.0.0.1', self.server.sockets[0].getsockname()[1])
        self.client = await mux.Channel(reader, writer).start()

    async def accept(self, reader, writer):
        channel = mux.Channel(reader, writer, on_open=self.echo, audit=self.audit)
        self.peers.append(channel)
        try:
            await channel.start()
            await channel.receiver
        except (mux.ProtocolError, asyncio.IncompleteReadError, OSError):
            pass
        finally:
            await channel.close()

    async def echo(self, stream, authority):
        stream.opened = True
        await stream.channel.frame(mux.OPEN_OK, stream.ident)
        if authority == b'blocked.test:443':
            await self.block.wait()
        while True:
            data = await stream.read()
            if not data:
                await stream.eof()
                return
            await stream.send(data)

    async def asyncTearDown(self):
        await self.client.close()
        for channel in self.peers:
            await channel.close()
        self.server.close()
        await self.server.wait_closed()

    async def test_more_than_concurrency_limit_sequential_requests(self):
        for index in range(80):
            stream = await self.client.open(b'allowed.test:443')
            value = str(index).encode()
            await stream.send(value)
            self.assertEqual(await stream.read(), value)
            await stream.eof()
            self.assertEqual(await stream.read(), b'')
            await stream.close()
        self.assertFalse(self.client.closed)
        self.assertEqual(self.client.queued, 0)
        self.assertEqual(self.client.streams, {})

    async def test_concurrent_streams_do_not_mix_data(self):
        async def exchange(index):
            stream = await self.client.open(b'allowed.test:443')
            payload = bytes([index]) * 16384
            await stream.send(payload)
            self.assertEqual(await stream.read(), payload)
            await stream.close()
        await asyncio.wait_for(asyncio.gather(*(exchange(i) for i in range(64))), 30)
        self.assertFalse(self.client.closed)

    async def test_backpressure_is_bounded_and_other_streams_progress(self):
        blocked = await self.client.open(b'blocked.test:443')
        sender = asyncio.create_task(blocked.send(b'x' * (mux.WINDOW + mux.MAX_DATA)))
        await asyncio.sleep(0.05)
        self.assertFalse(sender.done())
        self.assertLessEqual(self.peers[0].queued, mux.WINDOW)
        normal = await self.client.open(b'allowed.test:443')
        await normal.send(b'other-stream')
        self.assertEqual(await normal.read(), b'other-stream')
        await normal.close()
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)
        await blocked.close()
        self.assertFalse(self.client.closed)

    async def test_channel_death_wakes_blocked_clients(self):
        stream = await self.client.open(b'blocked.test:443')
        pending = asyncio.create_task(stream.read())
        await self.peers[0].close()
        with self.assertRaises(mux.StreamClosed):
            await asyncio.wait_for(pending, 2)

    async def test_malformed_lengths_versions_and_ids_close_channel(self):
        rng = random.Random(9731)
        cases = [b'x' * len(mux.MAGIC),
                 mux.MAGIC + mux.HEADER.pack(mux.DATA, 1, mux.MAX_DATA + 1),
                 mux.MAGIC + mux.HEADER.pack(mux.OPEN, 0, 1) + b'x',
                 mux.MAGIC + mux.HEADER.pack(mux.OPEN, 1, mux.MAX_OPEN + 1),
                 mux.MAGIC + mux.HEADER.pack(mux.DATA, 1, 1) + b'x',
                 mux.MAGIC + mux.HEADER.pack(mux.OPEN, 3, 1) + b'x']
        cases += [mux.MAGIC + mux.HEADER.pack(rng.randint(8, 255), rng.randint(0, 100), rng.randint(0, 0xffffffff)) for _ in range(50)]
        for wire in cases:
            reader, writer = await asyncio.open_connection('127.0.0.1', self.server.sockets[0].getsockname()[1])
            writer.write(wire)
            await writer.drain()
            self.assertEqual(await reader.readexactly(len(mux.MAGIC)), mux.MAGIC)
            self.assertEqual(await asyncio.wait_for(reader.read(), 2), b'')
            writer.close()
            await writer.wait_closed()

    async def test_invalid_credit_duplicate_open_and_state(self):
        stream = await self.client.open(b'allowed.test:443')
        await self.client.frame(mux.WINDOW_UPDATE, stream.ident, struct.pack('!I', mux.WINDOW + 1))
        await asyncio.wait_for(self.client.receiver, 2)
        self.assertTrue(self.client.closed)
        self.assertEqual(self.peers[0].queued, 0)

    async def test_reused_ids_invalid_transitions_and_credit_are_rejected(self):
        authority = b'allowed.test:443'
        frame = lambda kind, ident=1, data=b'': mux.HEADER.pack(kind, ident, len(data)) + data
        cases = [frame(mux.OPEN, data=authority),
                 frame(mux.WINDOW_UPDATE, data=struct.pack('!I', 0)),
                 frame(mux.WINDOW_UPDATE, data=struct.pack('!I', 0xffffffff)),
                 frame(mux.HALF_CLOSE) * 2,
                 frame(mux.HALF_CLOSE) + frame(mux.DATA, data=b'x'),
                 frame(mux.DATA, ident=2, data=b'x'),
                 frame(mux.OPEN_OK),
                 frame(mux.CLOSE, data=b'secret')]
        for invalid in cases:
            reader, writer = await asyncio.open_connection('127.0.0.1', self.server.sockets[0].getsockname()[1])
            writer.write(mux.MAGIC)
            await writer.drain()
            await reader.readexactly(len(mux.MAGIC))
            writer.write(frame(mux.OPEN, data=authority))
            await writer.drain()
            self.assertEqual(await reader.readexactly(mux.HEADER.size), mux.HEADER.pack(mux.OPEN_OK, 1, 0))
            writer.write(invalid)
            await writer.drain()
            await asyncio.wait_for(reader.read(), 2)
            writer.close()
            await writer.wait_closed()
        self.assertNotIn('secret', repr(self.errors))

    async def test_active_stream_limit_and_cancel_preserve_channel(self):
        streams = [await self.client.open(b'blocked.test:443') for _ in range(mux.MAX_STREAMS)]
        with self.assertRaises(mux.StreamClosed):
            await self.client.open(b'allowed.test:443')
        await streams.pop().close()
        normal = await self.client.open(b'allowed.test:443')
        await normal.send(b'reused-capacity')
        self.assertEqual(await normal.read(), b'reused-capacity')
        await normal.close()
        await asyncio.gather(*(stream.close() for stream in streams))
        self.assertFalse(self.client.closed)

    async def test_proxy_reauthorizes_every_logical_open_and_redacts(self):
        instance = proxy.Proxy({'destinations': [{'host': 'allowed.test', 'port': 443}]}, self.audit)
        server = await asyncio.start_server(instance.handle, '127.0.0.1', 0)
        reader, writer = await asyncio.open_connection('127.0.0.1', server.sockets[0].getsockname()[1])
        client = await mux.Channel(reader, writer).start()
        try:
            with patch('proxy.resolve') as resolve:
                for authority in (b'allowed.test.evil.test:443', b'allowed.test:80', b'user:secret@allowed.test:443', b'allowed.test:443/path?secret'):
                    with self.assertRaises(mux.StreamClosed):
                        await client.open(authority)
                resolve.assert_not_called()
            self.assertNotIn('secret', repr(self.errors))
            self.assertFalse(client.closed)
        finally:
            await client.close()
            server.close()
            await server.wait_closed()
