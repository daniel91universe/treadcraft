import asyncio
import json
import unittest

from websockets.asyncio.server import serve

from qz_ws_client import (QzConnectionError, QzSaveUncertainError,
                          check_connection, save_training_program)
from qz_ws_payload import build_save_payload


class QzClientTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.payload = build_save_payload({"segments": [{
            "name": "Run", "duration_min": 5, "speed_kmh": 8, "incline_percent": 1,
        }]}, name="Test workout")

    async def server(self, handler):
        server = await self.enterAsyncContext(serve(handler, "127.0.0.1", 0))
        return f"127.0.0.1:{server.sockets[0].getsockname()[1]}"

    async def test_connection_check_sends_no_command(self):
        received = []

        async def handler(ws):
            async for message in ws:
                received.append(message)

        address = await self.server(handler)
        await check_connection(f"http://{address}/floating/floating.htm")
        self.assertEqual(received, [])

    async def test_save_ignores_telemetry_and_confirms_matching_receipt(self):
        requests = []

        async def handler(ws):
            message = json.loads(await ws.recv())
            requests.append(message)
            await ws.send('{"msg":"workout","content":{}}')
            await ws.send(json.dumps({"msg": "R_savetrainingprogram", "content": {
                "name": message["content"]["name"], "list": 1,
            }}))

        address = await self.server(handler)
        first = await save_training_program(f"ws://{address}/", self.payload)
        second = await save_training_program(address, self.payload)
        self.assertNotEqual(first.name, second.name)
        self.assertEqual(first.row_count, 1)
        self.assertEqual(requests[0], {"msg": "savetrainingprogram", "content": {
            "name": first.name, "list": self.payload["content"]["list"],
        }})
        self.assertEqual(self.payload["content"]["name"], "Test workout")

    async def test_malformed_reply_is_uncertain(self):
        async def handler(ws):
            await ws.recv()
            await ws.send("not JSON")

        with self.assertRaisesRegex(QzSaveUncertainError, "invalid response"):
            await save_training_program(await self.server(handler), self.payload)

    async def test_wrong_name_or_count_does_not_confirm(self):
        for mismatch in ("name", "count", "boolean count"):
            async def handler(ws):
                sent = json.loads(await ws.recv())["content"]
                await ws.send(json.dumps({"msg": "R_savetrainingprogram", "content": {
                    "name": "other" if mismatch == "name" else sent["name"],
                    "list": True if mismatch == "boolean count" else 0 if mismatch == "count" else 1,
                }}))

            with self.subTest(mismatch=mismatch):
                address = await self.server(handler)
                with self.assertRaisesRegex(QzSaveUncertainError, "did not match"):
                    await save_training_program(address, self.payload)

    async def test_timeout_does_not_retry_save(self):
        received = []

        async def handler(ws):
            async for message in ws:
                received.append(message)
                await ws.send('{"msg":"workout"}')

        address = await self.server(handler)
        with self.assertRaisesRegex(QzSaveUncertainError, "timed out"):
            await save_training_program(address, self.payload, timeout=0.3)
        self.assertEqual(len(received), 1)

    async def test_disconnect_after_send_is_uncertain(self):
        async def handler(ws):
            await ws.recv()
            await ws.close()

        with self.assertRaises(QzSaveUncertainError):
            await save_training_program(await self.server(handler), self.payload)

    async def test_connection_refused_is_not_a_save_attempt(self):
        async with serve(lambda ws: ws.wait_closed(), "127.0.0.1", 0) as server:
            address = f"127.0.0.1:{server.sockets[0].getsockname()[1]}"
        with self.assertRaises(QzConnectionError):
            await save_training_program(address, self.payload)

    async def test_non_websocket_response_is_connection_error(self):
        async def http(reader, writer):
            try:
                await reader.readuntil(b"\r\n\r\n")
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()

        server = await self.enterAsyncContext(await asyncio.start_server(http, "127.0.0.1", 0))
        with self.assertRaises(QzConnectionError):
            await check_connection(f"127.0.0.1:{server.sockets[0].getsockname()[1]}")

    async def test_public_address_and_unverified_paths_are_rejected(self):
        for address in ("8.8.8.8:6666", "ws://127.0.0.1:6666/fetcher", "127.0.0.1",
                        "http://127.0.0.1:6666/"):
            with self.subTest(address=address), self.assertRaises(QzConnectionError):
                await check_connection(address)
