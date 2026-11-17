import asyncio
from queue import SimpleQueue
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app import TreadmillApp
from qz_discovery import SERVICE_TYPE, QzService, discover, parse_service, verify_service
from qz_discovery_ui import DiscoveryControls
from qz_ws_client import QzConnectionError


NAME = 'QZ Fitness WebSocket.' + SERVICE_TYPE


def info(port=38729, properties=None):
    return SimpleNamespace(port=port, server='qz-websocket.local.', properties=(
        {b'path': b'/', b'protocol': b'ws', b'version': b'1'} if properties is None else properties))


class ParserTests(unittest.TestCase):
    def test_endpoint_uses_dynamic_ip_and_port(self):
        for address, port in [('192.168.1.12', 38729), ('10.4.3.2', 46047)]:
            self.assertEqual(parse_service(NAME, info(port), [address]).endpoints,
                             (f'ws://{address}:{port}/',))

    def test_missing_txt_allowed_but_marked_unverified(self):
        self.assertTrue(parse_service(NAME, info(properties={}), ['192.168.1.12']).warning)

    def test_multiple_addresses_filter_mobile_and_sort_lan_first(self):
        found = parse_service(NAME, info(), ['100.121.43.182', '127.0.0.1', '::1', 'bad',
                                            '169.254.2.3', '192.168.1.12', '192.168.1.12'])
        self.assertEqual(found.endpoints, ('ws://192.168.1.12:38729/', 'ws://169.254.2.3:38729/'))

    def test_bad_ports(self):
        for port in (0, -1, 65536, True, '38729'):
            with self.subTest(port=port), self.assertRaises(ValueError):
                parse_service(NAME, info(port), ['192.168.1.12'])

    def test_untrusted_txt_is_rejected(self):
        for txt in ({b'path': b'//evil/'}, {b'protocol': b'wss'}, {b'version': b'2'},
                    {b'path': b'\xff'}, {'path': b'/'}, {b'path': b'/' * 4097}):
            with self.subTest(txt=str(txt)[:40]), self.assertRaises(ValueError):
                parse_service(NAME, info(properties=txt), ['192.168.1.12'])

    def test_no_local_address(self):
        with self.assertRaises(ValueError):
            parse_service(NAME, info(), ['8.8.8.8', '0.0.0.0', '224.0.0.251'])


class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    def backend(self, events, specs=None, broken_browser=False):
        state = SimpleNamespace(closed=False, cancelled=False, requests=0)
        specs = specs or {}
        class Zc:
            def __init__(self, **kwargs): self.zeroconf = self
            async def async_close(self): state.closed = True
        class Browser:
            def __init__(self, zc, type_, handlers):
                if broken_browser: raise OSError('No network interface')
                self.handles = [asyncio.get_running_loop().call_later(
                    delay, lambda n=name, s=change: handlers[0](
                        zeroconf=zc, service_type=type_, name=n, state_change=s))
                    for delay, name, change in events]
            async def async_cancel(self):
                state.cancelled = True
                for handle in self.handles: handle.cancel()
        class Info:
            def __init__(self, type_, name):
                self.name = name
                self.port = specs.get(name, {}).get('port', 38729)
                ports = specs.get(name, {}).get('ports')
                if ports:
                    self.port = ports[min(state.requests, len(ports) - 1)]
                self.properties = {}
                self.server = 'qz-websocket.local.'
            async def async_request(self, zc, timeout):
                state.requests += 1
                if specs.get(self.name, {}).get('error'):
                    raise OSError('Resolution failed')
                await asyncio.sleep(specs.get(self.name, {}).get('delay', 0))
                return specs.get(self.name, {}).get('resolved', True)
            def parsed_addresses(self, ipv4):
                return specs.get(self.name, {}).get('ips', ['192.168.1.12'])
        return (Zc, Browser, Info, 'ipv4', 'removed'), state

    async def scan(self, events=(), specs=None, **kwargs):
        backend, state = self.backend(events, specs)
        snapshots = []
        result = await discover(duration=.12, backend=backend, emit=snapshots.append, **kwargs)
        self.assertTrue(state.closed and state.cancelled)
        return result, snapshots

    async def test_zero_devices(self): self.assertEqual((await self.scan())[0], ())

    async def test_one_device(self):
        self.assertEqual(len((await self.scan([(0, NAME, 'added')]))[0]), 1)

    async def test_two_devices(self):
        second = 'Second.' + SERVICE_TYPE
        result, _ = await self.scan([(0, NAME, 'added'), (0, second, 'added')],
                                   {second: {'ips': ['192.168.1.13']}})
        self.assertEqual(len(result), 2)

    async def test_removed_device_is_not_offered(self):
        result, snapshots = await self.scan([(0, NAME, 'added'), (.04, NAME, 'removed')])
        self.assertEqual(result, ())
        self.assertEqual(snapshots[-1], ())

    async def test_removal_cancels_pending_resolution(self):
        result, _ = await self.scan([(0, NAME, 'added'), (.02, NAME, 'removed')],
                                   {NAME: {'delay': 10}})
        self.assertEqual(result, ())

    async def test_unresolved_service(self):
        self.assertEqual((await self.scan([(0, NAME, 'added')], {NAME: {'resolved': False}}))[0], ())

    async def test_duplicate_endpoints_presented_once(self):
        _, snapshots = await self.scan([(0, NAME, 'added'), (0, 'Copy.' + SERVICE_TYPE, 'added')])
        self.assertEqual(len(snapshots[-1]), 1)

    async def test_updated_port_replaces_old_endpoint(self):
        result, snapshots = await self.scan([(0, NAME, 'added'), (.03, NAME, 'updated')],
                                           {NAME: {'ports': [38729, 12345]}})
        self.assertEqual(snapshots[0][0].endpoints, ('ws://192.168.1.12:38729/',))
        self.assertEqual(result[0].endpoints, ('ws://192.168.1.12:12345/',))

    async def test_resolution_failure_does_not_escape_worker(self):
        self.assertEqual((await self.scan([(0, NAME, 'added')], {NAME: {'error': True}}))[0], ())

    async def test_cancellation_closes_browser_and_sockets(self):
        cancel = Event(); cancel.set()
        backend, state = self.backend([])
        await discover(duration=10, backend=backend, cancel=cancel)
        self.assertTrue(state.cancelled and state.closed)

    async def test_browser_failure_still_closes_zeroconf(self):
        backend, state = self.backend([], broken_browser=True)
        with self.assertRaises(OSError): await discover(backend=backend)
        self.assertTrue(state.closed)

    async def test_invalid_duration(self):
        for duration in (0, float('inf'), 31):
            with self.assertRaises(ValueError): await discover(duration=duration)

    async def test_candidate_failure_tries_next_via_existing_verifier(self):
        service = QzService(NAME, ('ws://192.168.1.12:1/', 'ws://192.168.1.12:2/'))
        with patch('qz_discovery.verify_qz', new_callable=AsyncMock) as verify:
            verify.side_effect = [QzConnectionError('refused'), service.endpoints[1]]
            self.assertEqual(await verify_service(service), service.endpoints[1])
            self.assertEqual(verify.await_count, 2)

    async def test_failed_identity_does_not_persist_or_send_workout(self):
        with patch('qz_discovery.verify_qz', new_callable=AsyncMock) as verify:
            verify.side_effect = QzConnectionError('unrecognized')
            with self.assertRaises(QzConnectionError):
                await verify_service(QzService(NAME, ('ws://192.168.1.12:1/',)))


class GuiTests(unittest.TestCase):
    def test_selection_reuses_existing_operation_and_manual_field(self):
        app = TreadmillApp.__new__(TreadmillApp)
        app.qz_result = None; app.qz_address = Mock(); app.start_qz_operation = Mock()
        app.connect_discovered_qz(QzService(NAME, ('ws://192.168.1.12:12345/',)))
        app.qz_address.set.assert_called_once_with('ws://192.168.1.12:12345/')
        self.assertTrue(app.start_qz_operation.call_args.kwargs['verification'])

    def test_busy_operation_does_not_change_manual_address(self):
        app = TreadmillApp.__new__(TreadmillApp); app.qz_result = object(); app.qz_address = Mock()
        app.connect_discovered_qz(QzService(NAME, ('ws://192.168.1.12:12345/',)))
        app.qz_address.set.assert_not_called()

    def test_close_cancels_without_tk_calls_from_worker(self):
        controls = DiscoveryControls.__new__(DiscoveryControls)
        controls.cancel = Event(); controls.dialog = Mock()
        controls.close()
        self.assertTrue(controls.cancel.is_set())
        self.assertIsNone(controls.dialog)

    def test_old_search_snapshot_is_ignored(self):
        controls = DiscoveryControls.__new__(DiscoveryControls)
        controls.closed=False; controls.generation=2; controls.queue=SimpleQueue(); controls.app=Mock()
        controls.queue.put((1, 'devices', (object(),)))
        controls.render=Mock(); controls.poll()
        controls.render.assert_not_called()


if __name__ == '__main__': unittest.main()
