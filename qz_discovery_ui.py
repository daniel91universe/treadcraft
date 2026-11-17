"""Tk adapter: bounded discovery worker communicates only through a queue."""
import asyncio
from queue import Empty, SimpleQueue
from threading import Event, Thread
import tkinter as tk
from tkinter import ttk

from qz_discovery import discover


class DiscoveryControls:
    def __init__(self, app, panel):
        self.app = app
        self.services = ()
        self.dialog = None
        self.closed = False
        self.cancel = None
        self.queue = SimpleQueue()
        self.generation = 0
        self.status = tk.StringVar(master=app.root, value="Searching for QZ…")
        self.button = app.make_button(panel, text="Finding QZ…", role="Secondary", command=self.open)
        self.button.grid(row=1, column=5, sticky="e")
        app.root.bind("<Destroy>", self.on_destroy, add="+")
        app.root.after(250, self.search)

    def on_destroy(self, event):
        if event.widget is self.app.root:
            self.closed = True
            if self.cancel:
                self.cancel.set()

    def search(self):
        if self.closed or self.cancel is not None:
            return
        self.generation += 1
        generation = self.generation
        self.services = ()
        self.render()
        self.status.set("Searching for QZ on this LAN…")
        self.button.configure(text="Finding QZ…")
        self.cancel = cancel = Event()

        def work():
            try:
                asyncio.run(discover(cancel=cancel, emit=lambda found: self.queue.put((generation, "devices", found))))
                self.queue.put((generation, "done", None))
            except Exception as error:
                self.queue.put((generation, "error", str(error)))
        Thread(target=work, daemon=True).start()
        self.app.root.after(50, self.poll)

    def poll(self):
        if self.closed:
            return
        finished = False
        while True:
            try:
                generation, kind, value = self.queue.get_nowait()
            except Empty:
                break
            if generation != self.generation:
                continue
            if kind == "devices":
                self.services = value
                self.render()
                self.status.set(f"{len(value)} QZ service(s) discovered. Select one to verify its identity.")
            else:
                finished = True
                self.cancel = None
                self.button.configure(text=f"QZ devices ({len(self.services)})…")
                if kind == "error":
                    self.status.set(f"Discovery unavailable: {value} Manual connection is available.")
                elif not self.services:
                    self.status.set("No QZ found or resolved. Keep QZ open, check the LAN, or use the manual address.")
                else:
                    self.status.set("Search finished. Discovery alone does not verify a QZ connection.")
        if not finished:
            self.app.root.after(50, self.poll)

    def render(self):
        if self.dialog is None:
            return
        for item in self.listbox.get_children():
            self.listbox.delete(item)
        for index, service in enumerate(self.services):
            name = service.name.removesuffix("._qzws._tcp.local.")
            name = "".join(c if c.isprintable() else " " for c in name)[:128]
            warning = " [TXT incomplete]" if service.warning else ""
            self.listbox.insert("", "end", iid=str(index),
                                values=(name + warning, ', '.join(service.endpoints)))

    def connect(self):
        if self.app.qz_result is not None:
            self.status.set("Wait for the current QZ operation to finish.")
            return
        selected = self.listbox.selection()
        if selected and int(selected[0]) < len(self.services):
            self.app.connect_discovered_qz(self.services[int(selected[0])])
            self.close()

    def close(self):
        if self.cancel:
            self.cancel.set()
        if self.dialog is not None:
            self.dialog.destroy()
            self.dialog = None

    def open(self):
        if self.dialog is not None:
            self.dialog.lift()
            return
        dialog = self.dialog = tk.Toplevel(self.app.root)
        dialog.title("QZ devices on your LAN")
        dialog.transient(self.app.root)
        self.app.set_windows_icons(dialog)
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, textvariable=self.status, wraplength=500).pack(fill="x")
        self.listbox = ttk.Treeview(frame, columns=("service", "endpoint"),
                                    show="headings", height=5, selectmode="browse")
        self.listbox.heading("service", text="QZ service (unverified)")
        self.listbox.heading("endpoint", text="IPv4 WebSocket endpoint(s)")
        self.listbox.column("service", width=210, minwidth=120)
        self.listbox.column("endpoint", width=330, minwidth=180)
        self.listbox.pack(fill="both", expand=True, pady=8)
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        self.app.make_button(actions, text="Search again", role="Secondary", command=self.search).pack(side="left")
        self.app.make_button(actions, text="Connect to selected QZ", command=self.connect).pack(side="left", padx=8)
        self.app.make_button(actions, text="Close", role="Secondary", command=self.close).pack(side="right")
        ttk.Label(frame, text="Discovered services are unverified. Connect checks QZ identity; it does not send a workout.",
                  wraplength=500).pack(fill="x", pady=(8, 0))
        self.render()
        dialog.protocol("WM_DELETE_WINDOW", self.close)
        dialog.bind("<Escape>", lambda event: self.close())
        self.search()
