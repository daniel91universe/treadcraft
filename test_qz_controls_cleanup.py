import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import TreadmillApp
from qz_ws_client import verify_qz


class QzControlsTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.root.withdraw()
        self.addCleanup(self.close_root)
        self.enterContext(patch('app.DiscoveryControls'))
        self.enterContext(patch('app.load_qz_endpoint', return_value=None))
        self.saved = self.enterContext(patch('app.save_qz_endpoint'))
        self.app = TreadmillApp(self.root)

    def close_root(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()

    def buttons(self, widget):
        found = []
        for child in widget.winfo_children():
            if child.winfo_class() in ('TButton', 'Button'):
                found.append(child.cget('text'))
            found.extend(self.buttons(child))
        return found

    def test_removed_buttons_and_preserved_actions(self):
        texts = self.buttons(self.root)
        self.assertNotIn('Test Connection', texts)
        self.assertNotIn('Reconnect to QZ', texts)
        for text in ('Send to QZ', 'Export XML', 'QZ Devices'):
            self.assertIn(text, texts)

    def test_manual_ui_removed_but_endpoint_configuration_retained(self):
        self.assertFalse(hasattr(self.app, 'qz_manual_panel'))
        texts = self.buttons(self.root)
        self.assertNotIn('Manual address…', texts)
        self.assertNotIn('Verify manual address', texts)
        self.app.qz_address.set('ws://192.168.1.12:12345/')
        self.assertEqual(self.app.qz_address.get(), 'ws://192.168.1.12:12345/')

    def test_internal_manual_verifier_and_reconnect_remain(self):
        self.app.start_qz_operation = Mock()
        self.app.test_qz_connection()
        self.assertIs(self.app.start_qz_operation.call_args.args[0], verify_qz)
        self.app.last_qz_endpoint = 'ws://192.168.1.12:12345/'
        self.app.reconnect_to_qz()
        self.assertEqual(self.app.qz_address.get(), self.app.last_qz_endpoint)
        self.assertTrue(self.app.start_qz_operation.call_args.kwargs['verification'])

    def run_operation(self, verification):
        self.app.qz_address.set('ws://192.168.1.12:12345/')
        async def operation(address):
            return address if verification else SimpleNamespace(name='test', row_count=8)
        def thread(**kwargs):
            return SimpleNamespace(start=kwargs['target'])
        with patch('app.Thread', side_effect=thread):
            self.app.start_qz_operation(operation, 'Testing', verification=verification)

    def test_cancel_is_visible_only_during_verification(self):
        self.assertFalse(self.app.qz_cancel_button.winfo_manager())
        self.run_operation(True)
        self.assertEqual(self.app.qz_cancel_button.winfo_manager(), 'grid')
        self.app.poll_qz_operation()
        self.assertFalse(self.app.qz_cancel_button.winfo_manager())
        self.saved.assert_called_once()

    def test_cancelled_verification_does_not_persist(self):
        self.run_operation(True)
        self.app.cancel_qz_verification()
        self.app.poll_qz_operation()
        self.saved.assert_not_called()
        self.assertIn('cancelled', self.app.qz_status.get())

    def test_send_does_not_offer_unsafe_cancel(self):
        self.run_operation(False)
        self.assertFalse(self.app.qz_cancel_button.winfo_manager())
        self.app.poll_qz_operation()
        self.assertIn('8 rows', self.app.qz_status.get())

    def test_no_endpoint_gives_actionable_message(self):
        self.app.send_to_qz()
        self.assertIn('QZ Devices', self.app.qz_status.get())


if __name__ == '__main__':
    unittest.main()
