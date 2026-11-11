import unittest
from types import SimpleNamespace

from windows_icons import WindowsIcons


class FakeWindow:
    def __init__(self):
        self.pending = {}
        self.next_job = 0

    def bind(self, *args, **kwargs):
        pass

    def frame(self):
        return "0x123"

    def update_idletasks(self):
        self.flush()

    def after_idle(self, callback):
        self.next_job += 1
        self.pending[self.next_job] = callback
        return self.next_job

    def after_cancel(self, job):
        del self.pending[job]

    def flush(self):
        jobs, self.pending = self.pending, {}
        for callback in jobs.values():
            callback()


class FakeAPI:
    def __init__(self):
        self.dimensions = ((24, 24), (48, 48))
        self.icons = [101, 102]
        self.loaded = []
        self.destroyed = []
        self.fail_size = None

    def sizes(self, hwnd):
        return self.dimensions

    def load(self, path, size):
        if size == self.fail_size:
            return None
        handle = 200 + len(self.loaded)
        self.loaded.append((handle, size))
        return handle

    def current(self, hwnd, kind):
        return self.icons[kind]

    def assign(self, hwnd, kind, handle):
        previous = self.icons[kind]
        self.icons[kind] = handle
        return previous

    def exists(self, hwnd):
        return True

    def destroy(self, handle):
        self.destroyed.append(handle)

    def show_message(self, owner, handles, show):
        self.message_icons = (owner, handles)
        return show()


class WindowsIconTests(unittest.TestCase):
    def setUp(self):
        self.window = FakeWindow()
        self.api = FakeAPI()
        self.manager = WindowsIcons(self.window, "test.ico", api=self.api)
        self.window.flush()

    def test_uses_metric_sizes_and_skips_unchanged_configuration(self):
        self.assertEqual(self.api.loaded, [(200, (24, 24)), (201, (48, 48))])
        self.manager._schedule()
        self.window.flush()
        self.assertEqual(len(self.api.loaded), 2)

    def test_dpi_change_replaces_and_releases_only_owned_handles(self):
        self.api.dimensions = ((28, 28), (56, 56))
        self.manager._schedule()
        self.window.flush()
        self.assertEqual(self.api.icons, [202, 203])
        self.assertEqual(self.api.destroyed, [200, 201])
        self.manager._close(SimpleNamespace(widget=self.window))
        self.assertEqual(self.api.icons, [101, 102])
        self.assertEqual(self.api.destroyed, [200, 201, 202, 203])

    def test_partial_load_failure_preserves_current_icons(self):
        self.api.dimensions = ((28, 28), (56, 56))
        self.api.fail_size = (56, 56)
        self.manager._schedule()
        self.window.flush()
        self.assertEqual(self.api.icons, [200, 201])
        self.assertEqual(self.api.destroyed, [202])

    def test_close_cancels_pending_work_and_preserves_external_replacement(self):
        self.api.icons[0] = 999
        self.manager._schedule()
        self.manager._close(SimpleNamespace(widget=self.window))
        self.assertFalse(self.window.pending)
        self.assertEqual(self.api.icons, [999, 102])
        self.assertEqual(self.api.destroyed, [200, 201])

    def test_child_events_do_not_release_or_reload_toplevel_icons(self):
        child = SimpleNamespace(widget=object())
        self.manager._schedule(child)
        self.manager._close(child)
        self.assertFalse(self.manager.closed)
        self.assertFalse(self.window.pending)
        self.assertEqual(self.api.destroyed, [])

    def test_message_uses_owned_icons_and_preserves_result(self):
        calls = []
        def show(title, *, parent):
            calls.append((title, parent))
            return "ok"
        self.assertEqual(
            self.manager.show_message(show, "Workout Loaded", parent=self.window), "ok",
        )
        self.assertEqual(self.api.message_icons, (0x123, (200, 201)))
        self.assertEqual(calls, [("Workout Loaded", self.window)])
        self.assertEqual(self.api.destroyed, [])
