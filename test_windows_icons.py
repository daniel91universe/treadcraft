import ctypes
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import windows_icons
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


class NativeFunction:
    def __init__(self, function):
        self.function = function

    def __call__(self, *args):
        return self.function(*args)


class NativeHookTests(unittest.TestCase):
    def setUp(self):
        self.assertFalse(windows_icons._pending_hooks)
        self.callbacks = []
        self.removals = []
        self.unhook_results = []
        self.assignments = []
        self.next_hook = 100
        self.user = SimpleNamespace(
            SetWindowsHookExW=NativeFunction(self.install),
            UnhookWindowsHookEx=NativeFunction(self.unhook),
            CallNextHookEx=NativeFunction(lambda *args: 17),
            GetWindow=NativeFunction(lambda *args: 0x123),
            GetClassNameW=NativeFunction(self.class_name),
            SendMessageW=NativeFunction(self.assign),
        )
        kernel = SimpleNamespace(GetCurrentThreadId=NativeFunction(lambda: 7))
        self.api = windows_icons._WindowsAPI.__new__(windows_icons._WindowsAPI)
        self.api.user32 = self.user
        for context in (
            patch.object(ctypes, "WinDLL", return_value=kernel, create=True),
            patch.object(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE, create=True),
            patch.object(ctypes, "get_last_error", return_value=5, create=True),
        ):
            context.start()
            self.addCleanup(context.stop)

    def tearDown(self):
        # All native functions in these tests are simulated.
        windows_icons._pending_hooks.clear()

    def install(self, kind, callback, instance, thread):
        self.callbacks.append(callback)
        self.next_hook += 1
        return self.next_hook

    def unhook(self, hook):
        self.removals.append(hook)
        return self.unhook_results.pop(0) if self.unhook_results else True

    def class_name(self, hwnd, buffer, length):
        buffer.value = "#32770"
        return len(buffer.value)

    def assign(self, hwnd, message, kind, handle):
        self.assignments.append((kind, handle))
        return 0

    def show(self, function=lambda: "ok"):
        return self.api.show_message(0x123, (200, 201), function)

    def test_success_removes_hook_and_preserves_result(self):
        def message():
            self.assertEqual(self.callbacks[-1](5, 0x456, 0), 17)
            return "ok"
        self.assertEqual(self.show(message), "ok")
        self.assertEqual(self.assignments, [(0, 200), (1, 201)])
        self.assertEqual(self.removals, [101])
        self.assertFalse(windows_icons._pending_hooks)

    def test_exception_still_removes_hook(self):
        failure = RuntimeError("message failed")
        def message():
            raise failure
        with self.assertRaises(RuntimeError) as caught:
            self.show(message)
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.removals, [101])
        self.assertFalse(windows_icons._pending_hooks)

    def test_unhook_failure_retains_disabled_callback(self):
        self.unhook_results = [False]
        with self.assertLogs("windows_icons", level="WARNING") as logs:
            self.assertEqual(self.show(), "ok")
        self.assertIn("Windows error 5", logs.output[0])
        callback = windows_icons._pending_hooks[(7, 101)]
        self.callbacks.clear()
        self.assertEqual(callback(5, 0x456, 0), 17)
        self.assertFalse(self.assignments)

    def test_unhook_failure_preserves_original_exception(self):
        self.unhook_results = [False]
        failure = RuntimeError("message failed")
        def message():
            raise failure
        with self.assertLogs("windows_icons"), self.assertRaises(RuntimeError) as caught:
            self.show(message)
        self.assertIs(caught.exception, failure)
        self.assertIn((7, 101), windows_icons._pending_hooks)

    def test_next_message_retries_removal(self):
        self.unhook_results = [False, True, True]
        with self.assertLogs("windows_icons"):
            self.show()
        self.assertEqual(self.show(), "ok")
        self.assertEqual(self.removals, [101, 101, 102])
        self.assertFalse(windows_icons._pending_hooks)

    def test_persistent_failure_does_not_accumulate_hooks(self):
        self.unhook_results = [False, False]
        with self.assertLogs("windows_icons"):
            self.show()
            self.assertEqual(self.show(), "ok")
        self.assertEqual(len(self.callbacks), 1)
        self.assertEqual(list(windows_icons._pending_hooks), [(7, 101)])

    def test_retry_does_not_remove_another_threads_hook(self):
        foreign_callback = object()
        windows_icons._pending_hooks[(8, 999)] = foreign_callback
        self.assertEqual(self.show(), "ok")
        self.assertEqual(self.removals, [101])
        self.assertIs(windows_icons._pending_hooks[(8, 999)], foreign_callback)
