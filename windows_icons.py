"""Assign DPI-sized, privately owned Windows icons to a Tk toplevel."""

import ctypes
from ctypes import wintypes


class _WindowsAPI:
    def __init__(self):
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.shcore = ctypes.WinDLL("shcore", use_last_error=True)
        signatures = {
            "LoadImageW": (wintypes.HANDLE, (wintypes.HINSTANCE, wintypes.LPCWSTR,
                           wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT)),
            "SendMessageW": (wintypes.LPARAM, (wintypes.HWND, wintypes.UINT,
                                              wintypes.WPARAM, wintypes.LPARAM)),
            "GetDpiForWindow": (wintypes.UINT, (wintypes.HWND,)),
            "GetWindowDpiAwarenessContext": (wintypes.HANDLE, (wintypes.HWND,)),
            "GetAwarenessFromDpiAwarenessContext": (ctypes.c_int, (wintypes.HANDLE,)),
            "MonitorFromWindow": (wintypes.HANDLE, (wintypes.HWND, wintypes.DWORD)),
            "GetSystemMetricsForDpi": (ctypes.c_int, (ctypes.c_int, wintypes.UINT)),
            "DestroyIcon": (wintypes.BOOL, (wintypes.HICON,)),
            "IsWindow": (wintypes.BOOL, (wintypes.HWND,)),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(self.user32, name)
            function.restype = result
            function.argtypes = arguments
        self.shcore.GetScaleFactorForMonitor.argtypes = (
            wintypes.HANDLE, ctypes.POINTER(ctypes.c_int),
        )
        self.shcore.GetScaleFactorForMonitor.restype = wintypes.LONG

    def sizes(self, hwnd):
        dpi = self.user32.GetDpiForWindow(hwnd) or 96
        context = self.user32.GetWindowDpiAwarenessContext(hwnd)
        if self.user32.GetAwarenessFromDpiAwarenessContext(context) == 0:
            # GetDpiForWindow returns 96 for an unaware window, even on a
            # scaled monitor. Read the monitor scale without changing awareness.
            monitor = self.user32.MonitorFromWindow(hwnd, 2)
            scale = ctypes.c_int()
            if self.shcore.GetScaleFactorForMonitor(monitor, ctypes.byref(scale)) == 0:
                dpi = round(96 * scale.value / 100)
        return tuple(
            (self.user32.GetSystemMetricsForDpi(x, dpi),
             self.user32.GetSystemMetricsForDpi(y, dpi))
            for x, y in ((49, 50), (11, 12))
        )

    def load(self, path, size):
        return self.user32.LoadImageW(None, str(path), 1, *size, 0x0010)

    def current(self, hwnd, kind):
        return self.user32.SendMessageW(hwnd, 0x007F, kind, 0)

    def assign(self, hwnd, kind, handle):
        return self.user32.SendMessageW(hwnd, 0x0080, kind, handle)

    def exists(self, hwnd):
        return self.user32.IsWindow(hwnd)

    def destroy(self, handle):
        self.user32.DestroyIcon(handle)

    def show_message(self, owner, handles, show):
        # Tk installs its own creation hook using cached icons. Apply the
        # parent's runtime icons when this owned message box is activated.
        hook_type = ctypes.WINFUNCTYPE(
            wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
        )
        user = self.user32
        signatures = {
            "SetWindowsHookExW": (wintypes.HANDLE, (
                ctypes.c_int, hook_type, wintypes.HINSTANCE, wintypes.DWORD,
            )),
            "UnhookWindowsHookEx": (wintypes.BOOL, (wintypes.HANDLE,)),
            "CallNextHookEx": (wintypes.LPARAM, (
                wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM,
            )),
            "GetWindow": (wintypes.HWND, (wintypes.HWND, wintypes.UINT)),
            "GetClassNameW": (ctypes.c_int, (
                wintypes.HWND, wintypes.LPWSTR, ctypes.c_int,
            )),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(user, name)
            function.restype = result
            function.argtypes = arguments
        kernel = ctypes.WinDLL("kernel32")
        kernel.GetCurrentThreadId.argtypes = ()
        kernel.GetCurrentThreadId.restype = wintypes.DWORD

        @hook_type
        def on_activate(code, hwnd, data):
            if code == 5 and user.GetWindow(hwnd, 4) == owner:
                class_name = ctypes.create_unicode_buffer(256)
                user.GetClassNameW(hwnd, class_name, len(class_name))
                if class_name.value == "#32770":
                    for kind, handle in enumerate(handles):
                        self.assign(hwnd, kind, handle)
            return user.CallNextHookEx(None, code, hwnd, data)

        hook = user.SetWindowsHookExW(5, on_activate, None, kernel.GetCurrentThreadId())
        try:
            return show()
        finally:
            if hook:
                user.UnhookWindowsHookEx(hook)


class WindowsIcons:
    def __init__(self, window, path, *, api=None):
        self.window = window
        self.path = path
        self.api = api if api is not None else _WindowsAPI()
        self.key = None
        self.handles = ()
        self.previous = ()
        self.job = None
        self.closed = False
        window.bind("<Configure>", self._schedule, add="+")
        window.bind("<Map>", self._schedule, add="+")
        window.bind("<Destroy>", self._close, add="+")
        self._schedule()

    def show_message(self, function, *args, **kwargs):
        self.window.update_idletasks()
        if self.closed or not self.handles:
            return function(*args, **kwargs)
        return self.api.show_message(
            int(self.window.frame(), 0), self.handles,
            lambda: function(*args, **kwargs),
        )

    def _schedule(self, event=None):
        if event is not None and event.widget is not self.window:
            return
        if not self.closed and self.job is None:
            self.job = self.window.after_idle(self._refresh)

    def _refresh(self):
        self.job = None
        if self.closed:
            return
        hwnd = int(self.window.frame(), 0)
        sizes = self.api.sizes(hwnd)
        key = (hwnd, sizes)
        if key == self.key:
            return
        handles = []
        for size in sizes:
            handle = self.api.load(self.path, size)
            if not handle:
                for loaded in handles:
                    self.api.destroy(loaded)
                return
            handles.append(handle)
        self._release()
        self.previous = tuple(
            self.api.assign(hwnd, kind, handle)
            for kind, handle in enumerate(handles)
        )
        self.handles = tuple(handles)
        self.key = key

    def _release(self):
        if self.key is None:
            return
        hwnd, _ = self.key
        for kind, handle in enumerate(self.handles):
            if self.api.exists(hwnd) and self.api.current(hwnd, kind) == handle:
                self.api.assign(hwnd, kind, self.previous[kind])
            self.api.destroy(handle)
        self.handles = self.previous = ()
        self.key = None

    def _close(self, event):
        if event.widget is not self.window:
            return
        self.closed = True
        if self.job is not None:
            self.window.after_cancel(self.job)
            self.job = None
        self._release()
