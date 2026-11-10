import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
import asyncio
import json
import copy
import os
import re
import sys
from pathlib import Path
from queue import Empty, SimpleQueue
from tempfile import NamedTemporaryFile
from threading import Event, Thread
import xml.etree.ElementTree as ET
from workout_data import (
    normalize_segment, normalize_workout, normalize_block_values,
    calculate_totals as workout_totals,
)
from device_capabilities import ProfileCompatibilityError, assess_workout
from qz_connection_config import load_qz_endpoint, save_qz_endpoint
from qz_ws_client import QzConnectionError, QzSaveUncertainError, save_training_program, verify_qz
from qz_ws_payload import build_save_payload
from qz_xml_export import QzXmlExportError, export_workout


BRAND_ASSETS = Path(__file__).resolve().parent / "assets" / "brand"
UI_FONT = "Segoe UI"
DEFAULT_WORKOUT_NAME = "My Running Workout"


def write_qz_xml(path, xml, *, overwrite):
    """Publish a complete file, refusing races on a new destination."""
    path = Path(path)
    temporary = None
    try:
        with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(xml.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def format_qz_duration(total_seconds):
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02}m {seconds:02}s"
    return f"{minutes}m {seconds:02}s"


def qz_preview(result):
    distance_rows = [row for row in ET.fromstring(result.xml) if "distance" in row.attrib]
    estimates = [row.attrib["duration"] for row in distance_rows if "duration" in row.attrib]
    estimated_seconds = sum(
        sum(int(part) * scale for part, scale in zip(value.split(":"), (3600, 60, 1)))
        for value in estimates
    )
    summary = [
        f"XML rows: {result.row_count}",
        f"Timed segments: {result.row_count - len(distance_rows)}"
        f"  •  Scheduled duration: {format_qz_duration(result.timed_seconds)}",
        f"Distance segments: {len(distance_rows)}",
    ]
    details = {"Blocking errors": [], "Warnings": [], "Information": []}
    if estimates:
        summary.append(
            f"Estimated duration: {format_qz_duration(estimated_seconds)}"
            f" for {len(estimates)} of {len(distance_rows)} distance segments"
        )
    elif distance_rows:
        summary.append("Estimated duration: unavailable")
    if distance_rows:
        details["Information"].append(
            "Distance determines when these segments end. Times are estimates."
        )
    groups = {"error": "Blocking errors", "warning": "Warnings"}
    for item in result.diagnostics:
        message = f"{item.path}: {item.message}" if item.path else item.message
        details[groups.get(item.severity, "Information")].append(message)
    return summary, details


class TreadmillApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TreadCraft")
        self.root.minsize(900, 600)
        self.configure_styles()

        self.blocks = []
        self.editing_segment = None
        self.editing_block = None

        # Presets are expressed as (duration in minutes, speed km/h, incline %).
        self.segment_presets = {
            "Warm-up": (10, 6, 1),
            "Easy Run": (10, 8, 1),
            "Recovery": (3, 5, 0),
            "Steady Run": (10, 9, 1),
            "Tempo Run": (10, 11, 1),
            "Threshold": (5, 12, 1),
            "Interval": (3, 12, 1),
            "Hill Climb": (3, 8, 5),
            "Hill Recovery": (3, 5, 1),
            "Cool-down": (5, 5, 0),
            "Walking": (5, 5, 0),
            "Custom": (10, 6, 0),
        }

        self.create_interface()
        self.refresh_tree()
        self.update_summary()

    # --------------------------------------------------
    # DARK THEME AND COLOURED CONTROLS
    # --------------------------------------------------

    def configure_styles(self):
        self.colors = {
            "background": "#010B2B",
            "panel": "#04114D",
            "panel_alt": "#102053",
            "foreground": "#FEFEFE",
            "muted": "#aab7c7",
            "accent": "#00E8F8",
            "accent_hover": "#70F4FC",
            "border": "#354457",
            "input": "#020F37",
            "selected": "#0048F8",
            "red": "#A83448",
            "orange": "#d58a43",
            "blue": "#4d91c7",
            "purple": "#9271c7",
            "green": "#22694F",
            "yellow": "#b79a43",
            "teal": "#248f91",
        }

        self.root.configure(bg=self.colors["background"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = self.colors["background"]
        panel = self.colors["panel"]
        fg = self.colors["foreground"]
        muted = self.colors["muted"]
        accent = self.colors["accent"]

        style.configure(".", background=bg, foreground=fg, font=(UI_FONT, 10))
        style.configure("TFrame", background=bg)
        style.configure("TLabelframe", background=bg, foreground=fg,
                        bordercolor=self.colors["border"], relief="solid")
        style.configure("TLabelframe.Label", background=bg, foreground=accent,
                        font=(UI_FONT, 10, "bold"))
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TEntry", fieldbackground=self.colors["input"],
                        foreground=fg, insertcolor=fg, bordercolor=self.colors["border"],
                        lightcolor=self.colors["border"], darkcolor=self.colors["border"],
                        padding=5)
        style.map("TEntry", bordercolor=[("focus", accent)])
        style.configure("TCombobox", fieldbackground=self.colors["input"],
                        background=panel, foreground=fg, arrowcolor=accent,
                        bordercolor=self.colors["border"], padding=5)
        style.map("TCombobox",
                  bordercolor=[("focus", accent)],
                  fieldbackground=[("readonly", self.colors["input"])],
                  foreground=[("readonly", fg)],
                  selectbackground=[("readonly", self.colors["selected"])],
                  selectforeground=[("readonly", fg)])
        style.configure("TButton", background=accent, foreground="#010B2B",
                        bordercolor=accent, padding=(10, 6),
                        font=(UI_FONT, 9, "bold"))
        style.map("TButton",
                  bordercolor=[("focus", fg)],
                  background=[("disabled", "#3b4653"), ("pressed", "#23C0D1"),
                              ("active", self.colors["accent_hover"])],
                  foreground=[("disabled", "#8793a1"), ("active", "#010B2B")])
        style.configure("Primary.TButton", background=accent, foreground="#010B2B")
        style.map("Primary.TButton", background=[("active", self.colors["accent_hover"])])
        style.configure("Secondary.TButton", background="#425268", foreground=fg,
                        bordercolor="#425268")
        style.map("Secondary.TButton", background=[("active", "#53677f")])
        style.configure("Danger.TButton", background=self.colors["red"], foreground="#ffffff",
                        bordercolor=self.colors["red"])
        style.map("Danger.TButton", background=[("active", "#B94659")])
        style.configure("Success.TButton", background=self.colors["green"], foreground="#ffffff",
                        bordercolor=self.colors["green"])
        style.configure("Compact.Success.TButton", padding=(7, 4))
        style.map("Success.TButton", background=[("active", "#28785A")])
        style.configure("Treeview", background=self.colors["input"],
                        fieldbackground=self.colors["input"], foreground=fg,
                        rowheight=29, bordercolor=self.colors["border"],
                        lightcolor=self.colors["border"], darkcolor=self.colors["border"])
        style.configure("Treeview.Heading", background=self.colors["panel_alt"],
                        foreground=fg, padding=7, font=(UI_FONT, 9, "bold"))
        style.map("Treeview",
                  background=[("selected", self.colors["selected"])],
                  foreground=[("selected", "#ffffff")])
        style.map("Treeview.Heading", background=[("active", "#34465b")])
        style.configure("Vertical.TScrollbar", background=panel,
                        troughcolor=bg, bordercolor=bg, arrowcolor=fg)

    def make_button(self, parent, *, role="Primary", **kwargs):
        return ttk.Button(parent, style=f"{role}.TButton", **kwargs)

    def load_brand(self):
        try:
            self.root.iconbitmap(default=str(BRAND_ASSETS / "TreadCraft.ico"))
        except tk.TclError:
            pass  # Keep the platform icon if the ICO is unavailable.
        if sys.platform == "win32" and self.root.winfo_fpixels("1i") <= 97:
            self.root.after_idle(self.set_windows_title_icon)
        try:
            return tk.PhotoImage(
                master=self.root,
                file=str(BRAND_ASSETS / "treadcraft-logo-dark-header.png"),
            )
        except tk.TclError:
            return None

    def set_windows_title_icon(self):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32")
        load = user32.LoadImageW
        load.argtypes = (wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                         ctypes.c_int, ctypes.c_int, wintypes.UINT)
        load.restype = wintypes.HANDLE
        icon = load(None, str(BRAND_ASSETS / "TreadCraft-title-16.ico"),
                    1, 16, 16, 0x0010)  # IMAGE_ICON, LR_LOADFROMFILE
        if not icon:
            return

        # "wm frame" returns the native wrapper that owns the title bar.
        hwnd = int(self.root.frame(), 0)
        set_class = getattr(user32, "SetClassLongPtrW", None) or user32.SetClassLongW
        set_class.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_void_p)
        set_class.restype = ctypes.c_void_p
        previous = set_class(hwnd, -34, icon)  # GCLP_HICONSM
        destroy = user32.DestroyIcon
        destroy.argtypes = (wintypes.HANDLE,)
        destroy.restype = wintypes.BOOL
        def release(event):
            if event.widget is self.root:
                set_class(hwnd, -34, previous)
                destroy(icon)

        self.root.bind("<Destroy>", release, add="+")

    def segment_colour_tag(self, segment):
        name = segment.get("name", "").lower()
        if "warm" in name or "cool" in name or "recovery" in name or "walk" in name:
            return "recovery"
        if "tempo" in name or "threshold" in name:
            return "tempo"
        if "interval" in name or "sprint" in name:
            return "interval"
        if "hill" in name:
            return "hill"
        if "easy" in name or "steady" in name:
            return "aerobic"
        return "custom"

    # --------------------------------------------------
    # INTERFACE
    # --------------------------------------------------

    def create_interface(self):
        header = ttk.Frame(self.root, padding=(12, 6))
        header.pack(fill="x")
        self.brand_logo = self.load_brand()
        brand = ttk.Label(header, text="TreadCraft", font=(UI_FONT, 20, "bold"))
        if self.brand_logo is not None:
            brand.configure(image=self.brand_logo)
        brand.pack(side="left")

        name_frame = ttk.Frame(header)
        name_frame.pack(side="left", fill="x", expand=True, padx=(16, 0))

        ttk.Label(name_frame, text="Workout name:").pack(side="left")
        self.workout_name = tk.StringVar(value=DEFAULT_WORKOUT_NAME)
        ttk.Entry(
            name_frame, textvariable=self.workout_name, width=24
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        # FILE ACTIONS
        file_actions = ttk.Frame(self.root, padding=(12, 0, 12, 4))
        file_actions.pack(fill="x")

        self.make_button(
            file_actions, text="Open Workout", role="Secondary", command=self.open_workout
        ).pack(side="left", padx=(0, 5))

        self.make_button(
            file_actions, text="Save Workout", role="Success", command=self.save_workout
        ).pack(side="left", padx=5)
        self.make_button(
            file_actions, text="Check Commercial LE", command=self.check_commercial_le
        ).pack(side="left", padx=5)

        self.make_button(file_actions, text="Export to QZ XML",
                         command=self.export_qz_xml).pack(side="left", padx=5)

        self.create_qz_controls()
        summary_bar = ttk.Frame(self.root, padding=(12, 0, 12, 6))
        summary_bar.pack(fill="x")
        self.summary = tk.StringVar()
        ttk.Label(
            summary_bar,
            textvariable=self.summary,
            font=(UI_FONT, 11, "bold"),
        ).pack(anchor="w")

        workspace = ttk.Frame(self.root)
        workspace.pack(fill="both", expand=True)
        self.page_canvas = tk.Canvas(
            workspace, background=self.colors["background"],
            highlightthickness=0, borderwidth=0
        )
        page_scrollbar = ttk.Scrollbar(
            workspace, orient="vertical", command=self.page_canvas.yview
        )
        self.page_canvas.configure(yscrollcommand=page_scrollbar.set)
        page_scrollbar.pack(side="right", fill="y")
        self.page_canvas.pack(side="left", fill="both", expand=True)

        self.content_frame = ttk.Frame(self.page_canvas)
        self.content_window = self.page_canvas.create_window(
            (0, 0), window=self.content_frame, anchor="nw"
        )
        self.content_frame.bind("<Configure>", self._on_content_configure)
        self.page_canvas.bind("<Configure>", self._on_canvas_configure)
        self.root.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.root.bind("<FocusIn>", self._on_workspace_focus, add="+")

        # WORKOUT TREE
        self.structure_panel = ttk.LabelFrame(
            self.content_frame, text="Workout Structure", padding=10
        )

        # WORKOUT POOL AND SEGMENT ACTIONS
        pool_content = ttk.Frame(self.structure_panel)
        pool_content.pack(fill="both", expand=True)

        tree_frame = ttk.Frame(pool_content)
        tree_frame.pack(fill="both", expand=True)

        segment_actions = ttk.Frame(pool_content, padding=(0, 6))
        segment_actions.pack(fill="x", before=tree_frame)

        edit = self.make_button(
            segment_actions, text="Edit Segment", role="Secondary", command=self.edit_segment
        )

        duplicate = self.make_button(
            segment_actions, text="Duplicate Segment", role="Secondary", command=self.duplicate_segment
        )

        remove = self.make_button(
            segment_actions, text="Remove Segment", role="Danger", command=self.remove_segment
        )
        segment_actions.bind("<Configure>", lambda event: self._wrap_segment_actions(
            event.width, (edit, duplicate, remove)
        ))
        columns = ("duration", "speed", "incline", "distance")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            selectmode="browse",
            height=6,
        )

        self.tree.tag_configure(
            "recovery", background="#293b4b", foreground="#b9d5e8"
        )
        self.tree.tag_configure(
            "tempo", background="#49364f", foreground="#f0c9f4"
        )
        self.tree.tag_configure(
            "interval", background="#56343a", foreground="#ffd0d3"
        )
        self.tree.tag_configure(
            "hill", background="#51432f", foreground="#f3d8a5"
        )
        self.tree.tag_configure(
            "aerobic", background="#25463e", foreground="#c0eadb"
        )
        self.tree.tag_configure(
            "custom", background="#303b4b", foreground="#d7e0ed"
        )
        self.tree.tag_configure(
            "block", background="#102053", foreground="#ffffff"
        )

        self.tree.heading("#0", text="Block / Segment")
        headings = {
            "duration": "Time (min)", "speed": "Speed km/h",
            "incline": "Incline %", "distance": "Dist. (km)",
        }
        heading_font = tkfont.Font(root=self.root, family=UI_FONT, size=9, weight="bold")
        name_width = heading_font.measure("Block / Segment") + 18
        self.tree.column("#0", width=name_width, minwidth=name_width)
        self.tree_min_width = name_width
        for column, label in headings.items():
            width = heading_font.measure(label) + 18
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, minwidth=width, anchor="e", stretch=False)
            self.tree_min_width += width

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview
        )
        horizontal = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<ButtonPress-1>", self.start_tree_drag, add="+")
        self.tree.bind("<B1-Motion>", self.show_tree_drag_preview, add="+")
        self.tree.bind("<ButtonRelease-1>", self.finish_tree_drag, add="+")
        self.root.bind("<Escape>", self.clear_tree_selection, add="+")

        editor = self.editor_panel = ttk.Frame(self.content_frame)
        # BLOCK EDITOR
        block_frame = ttk.LabelFrame(
            editor, text="Workout Blocks", padding=10
        )
        block_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(block_frame, text="Block name:").grid(
            row=0, column=0, padx=5, sticky="w"
        )
        self.block_name = tk.StringVar(value="New Block")
        ttk.Entry(
            block_frame, textvariable=self.block_name, width=16
        ).grid(row=0, column=1, padx=5, pady=3, sticky="w")

        ttk.Label(block_frame, text="Repetitions:").grid(
            row=0, column=2, padx=(8, 4), sticky="w"
        )
        self.block_repetitions = tk.StringVar(value="1")
        ttk.Entry(
            block_frame, textvariable=self.block_repetitions, width=4
        ).grid(row=0, column=3, padx=(0, 5), pady=3, sticky="w")

        block_actions = ttk.Frame(block_frame)
        block_actions.grid(row=1, column=0, columnspan=4, sticky="w")

        self.make_button(
            block_actions, text="Add Block", role="Success", command=self.add_block
        ).grid(row=0, column=0, padx=4, pady=3, sticky="ew")

        self.update_block_button = self.make_button(
            block_actions,
            text="Update Block", role="Secondary",
            command=self.update_block,
            state="disabled",
        )
        self.update_block_button.grid(row=0, column=1, padx=4, pady=3, sticky="ew")

        self.make_button(
            block_actions, text="Duplicate Block", role="Secondary", command=self.duplicate_block
        ).grid(row=0, column=2, padx=4, pady=3, sticky="ew")
        self.make_button(
            block_actions, text="Remove Block", role="Danger", command=self.remove_block
        ).grid(row=1, column=0, padx=4, pady=3, sticky="ew")
        self.make_button(
            block_actions,
            text="Move Block Up",
            command=lambda: self.move_item(-1, "block"),
        ).grid(row=1, column=1, padx=4, pady=3, sticky="ew")
        self.make_button(
            block_actions,
            text="Move Block Down",
            command=lambda: self.move_item(1, "block"),
        ).grid(row=1, column=2, padx=4, pady=3, sticky="ew")

        # SEGMENT EDITOR
        input_frame = ttk.LabelFrame(
            editor, text="Add or Edit Segment", padding=10
        )
        input_frame.pack(fill="x", pady=(0, 8), before=block_frame)

        ttk.Label(input_frame, text="Segment type:").grid(
            row=0, column=0, padx=5, sticky="w"
        )
        self.preset_type = tk.StringVar(value="Warm-up")

        preset_menu = ttk.Combobox(
            input_frame,
            textvariable=self.preset_type,
            values=list(self.segment_presets.keys()),
            state="readonly",
            width=15,
        )
        preset_menu.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        preset_menu.bind("<<ComboboxSelected>>", self.apply_preset)

        ttk.Label(input_frame, text="Segment name:").grid(
            row=0, column=1, padx=5, sticky="w"
        )
        self.segment_name = tk.StringVar(value="Warm-up")
        ttk.Entry(
            input_frame, textvariable=self.segment_name, width=15
        ).grid(row=1, column=1, padx=5, pady=5)

        mode_fields = ttk.Frame(input_frame)
        mode_fields.grid(row=2, column=0, rowspan=2, padx=5, sticky="w")
        ttk.Label(mode_fields, text="Set by:").grid(row=0, column=0, sticky="w")
        self.measure_mode = tk.StringVar(value="Time")
        mode_menu = ttk.Combobox(
            mode_fields,
            textvariable=self.measure_mode,
            values=("Time", "Distance"),
            state="readonly",
            width=10,
        )
        mode_menu.grid(row=1, column=0, pady=5, sticky="w")
        mode_menu.bind("<<ComboboxSelected>>", self.update_measure_label)

        self.measure_label = ttk.Label(input_frame, text="Duration (min):")
        self.measure_label.grid(row=2, column=1, padx=5, sticky="w")
        self.measure_value = tk.StringVar(value="10")
        self.measure_entry = ttk.Entry(
            input_frame, textvariable=self.measure_value, width=10
        )
        self.measure_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.distance_unit = tk.StringVar(value="km")
        self.distance_unit_label = ttk.Label(mode_fields, text="Unit:")
        self.distance_unit_label.grid(row=0, column=1, padx=(4, 0), sticky="w")
        self.distance_unit_menu = ttk.Combobox(
            mode_fields,
            textvariable=self.distance_unit,
            values=("km", "m"),
            state="readonly",
            width=3,
        )
        self.distance_unit_menu.grid(row=1, column=1, padx=(4, 0), pady=5, sticky="w")
        mode_fields.columnconfigure(
            1, minsize=max(self.distance_unit_label.winfo_reqwidth(),
                           self.distance_unit_menu.winfo_reqwidth()) + 4,
        )
        self.distance_unit_label.grid_remove()
        self.distance_unit_menu.grid_remove()

        ttk.Label(input_frame, text="Speed (km/h):").grid(
            row=0, column=2, padx=5, sticky="w"
        )
        self.speed = tk.StringVar(value="6")
        ttk.Entry(input_frame, textvariable=self.speed, width=7).grid(
            row=1, column=2, padx=5, pady=5, sticky="w"
        )

        ttk.Label(input_frame, text="Incline (%):").grid(
            row=2, column=2, padx=5, sticky="w"
        )
        self.incline = tk.StringVar(value="1")
        ttk.Entry(input_frame, textvariable=self.incline, width=7).grid(
            row=3, column=2, padx=5, pady=5, sticky="w"
        )

        segment_commands = ttk.Frame(input_frame)
        segment_commands.grid(row=4, column=0, columnspan=3, sticky="w")
        self.add_segment_button = self.make_button(
            segment_commands, text="Add Segment", role="Compact.Success",
            command=self.add_segment
        )
        self.add_segment_button.pack(side="left", padx=4)

        self.update_segment_button = self.make_button(
            segment_commands,
            text="Update Segment", role="Compact.Success",
            command=self.update_segment,
            state="disabled",
        )
        self.update_segment_button.pack(side="left", padx=4)

        self.content_frame.columnconfigure(0, weight=1)
        self.structure_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=4)
        editor.grid(row=0, column=1, sticky="new", padx=(0, 12), pady=4)
        self.root.after_idle(self._set_initial_window_size)

    def _set_initial_window_size(self):
        self.root.update_idletasks()
        # Include the workspace scrollbar and the table's frame and scrollbar.
        width = max(900, self.editor_panel.winfo_reqwidth() + self.tree_min_width + 108)
        self.root.minsize(width, 600)
        header_height = sum(
            widget.winfo_reqheight() for widget in self.root.pack_slaves()
            if widget is not self.page_canvas.master
        )
        height = header_height + self.content_frame.winfo_reqheight()
        self.root.geometry(f"{width}x{max(600, min(height, self.root.maxsize()[1]))}")

    def _wrap_segment_actions(self, width, buttons):
        stacked = sum(button.winfo_reqwidth() + 6 for button in buttons) > width
        for index, button in enumerate(buttons):
            button.grid(row=index if stacked else 0, column=0 if stacked else index,
                        sticky="w", padx=(0, 6), pady=2)

    def _on_content_configure(self, event=None):
        height = max(self.page_canvas.winfo_height(), self.content_frame.winfo_reqheight())
        self.page_canvas.itemconfigure(self.content_window, height=height)
        self.page_canvas.configure(scrollregion=self.page_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.page_canvas.itemconfigure(
            self.content_window, width=event.width,
            height=max(event.height, self.content_frame.winfo_reqheight()),
        )

    def _on_mousewheel(self, event):
        if event.widget is not self.tree and (
            event.widget is self.page_canvas or self._in_workspace(event.widget)
        ):
            self.page_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _in_workspace(self, widget):
        while widget is not None:
            if widget is self.content_frame:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _on_workspace_focus(self, event):
        widget = event.widget
        if not self._in_workspace(widget):
            return
        canvas = self.page_canvas
        top = widget.winfo_rooty() - canvas.winfo_rooty()
        bottom = top + widget.winfo_height()
        height = self.content_frame.winfo_height()
        if top < 0:
            canvas.yview_moveto((canvas.canvasy(0) + top) / height)
        elif bottom > canvas.winfo_height():
            canvas.yview_moveto(
                (canvas.canvasy(0) + bottom - canvas.winfo_height()) / height
            )

    # --------------------------------------------------
    # PRESETS, MEASUREMENT MODE AND VALIDATION
    # --------------------------------------------------

    def update_measure_label(self, event=None):
        if self.measure_mode.get() == "Distance":
            self.measure_label.config(text="Distance:")
            self.distance_unit_label.grid()
            self.distance_unit_menu.grid()
        else:
            self.measure_label.config(text="Duration (min):")
            self.distance_unit_label.grid_remove()
            self.distance_unit_menu.grid_remove()

    def apply_preset(self, event=None):
        preset = self.preset_type.get()
        duration, speed, incline = self.segment_presets[preset]
        self.segment_name.set(preset)
        self.measure_mode.set("Time")
        self.measure_value.set(str(duration))
        self.distance_unit.set("km")
        self.speed.set(str(speed))
        self.incline.set(str(incline))
        self.update_measure_label()

    def get_segment_values(self):
        try:
            return normalize_segment({
                "name": self.segment_name.get(),
                "measure_mode": self.measure_mode.get(),
                "measure_value": self.measure_value.get(),
                "distance_unit": self.distance_unit.get(),
                "speed_kmh": self.speed.get(),
                "incline_percent": self.incline.get(),
            })
        except ValueError as error:
            messagebox.showerror("Invalid segment", str(error))
            return None

    def get_block_values(self):
        try:
            return normalize_block_values(
                self.block_name.get(), self.block_repetitions.get()
            )
        except ValueError as error:
            messagebox.showerror("Invalid block", str(error))
            return None

    def normalize_segment(self, segment):
        """Keep the existing method available for callers of the editor."""
        return normalize_segment(segment)

    # --------------------------------------------------
    # BLOCK MANAGEMENT
    # --------------------------------------------------

    def add_block(self):
        block = self.get_block_values()
        if block is None:
            return
        block["type"] = "block"
        block["segments"] = []
        self.blocks.append(block)
        self.reset_block_editor()
        self.refresh_tree()
        self.update_summary()

    def update_block(self):
        if self.editing_block is None:
            return
        block = self.get_block_values()
        if block is None:
            return
        index = self.editing_block
        if self.blocks[index].get("type") == "segment":
            return
        self.blocks[index]["name"] = block["name"]
        self.blocks[index]["repetitions"] = block["repetitions"]
        self.reset_block_editor()
        self.refresh_tree()
        self.update_summary()

    def duplicate_block(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Duplicate Block", "Select a block first.")
            return
        item = selection[0]
        if self.tree.parent(item):
            messagebox.showinfo(
                "Duplicate Block", "Select the block heading, not a segment."
            )
            return
        index = self.tree.index(item)
        if self.blocks[index].get("type") == "segment":
            messagebox.showinfo("Duplicate Block", "Select a block heading.")
            return
        new_block = copy.deepcopy(self.blocks[index])
        new_block["name"] += " (Copy)"
        new_block["type"] = "block"
        self.blocks.insert(index + 1, new_block)
        self.reset_block_editor()
        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()

    def remove_block(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Remove Block", "Select a block first.")
            return
        item = selection[0]
        if self.tree.parent(item):
            messagebox.showinfo(
                "Remove Block",
                "Select the block heading, not one of its segments.",
            )
            return
        index = self.tree.index(item)
        if self.blocks[index].get("type") == "segment":
            messagebox.showinfo("Remove Block", "Select a block heading.")
            return
        if not messagebox.askyesno(
            "Remove Block", "Remove this block and all its segments?"
        ):
            return
        self.blocks.pop(index)
        self.reset_block_editor()
        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()

    def reset_block_editor(self):
        self.editing_block = None
        self.block_name.set("New Block")
        self.block_repetitions.set("1")
        self.update_block_button.config(state="disabled")

    def edit_block(self, index):
        block = self.blocks[index]
        if block.get("type") == "segment":
            return
        self.editing_block = index
        self.block_name.set(block["name"])
        self.block_repetitions.set(str(block["repetitions"]))
        self.update_block_button.config(state="normal")

    # --------------------------------------------------
    # SEGMENT MANAGEMENT
    # --------------------------------------------------

    def get_selected_segment_location(self):
        selection = self.tree.selection()
        if not selection:
            return None
        item = selection[0]
        parent = self.tree.parent(item)
        if parent:
            return ("block", self.tree.index(parent), self.tree.index(item))
        index = self.tree.index(item)
        entry = self.blocks[index]
        if entry.get("type") == "segment":
            return ("standalone", index, None)
        return None

    def add_segment(self):
        """
        Add a segment to the selected block.
        If no block is selected, create a standalone segment instead.
        Selecting a segment inside a block also targets that block.
        """
        segment = self.get_segment_values()
        if segment is None:
            return

        selection = self.tree.selection()
        target_block_index = None
        insert_after_standalone = None

        if selection:
            item = selection[0]
            parent = self.tree.parent(item)

            if parent:
                # A segment inside a block is selected.
                target_block_index = self.tree.index(parent)
            else:
                selected_index = self.tree.index(item)
                selected_entry = self.blocks[selected_index]

                if selected_entry.get("type") == "block":
                    # The block heading is selected.
                    target_block_index = selected_index
                else:
                    # A standalone segment is selected: insert the new
                    # standalone segment immediately after it.
                    insert_after_standalone = selected_index

        if target_block_index is not None:
            self.blocks[target_block_index]["segments"].append(segment)
        elif insert_after_standalone is not None:
            self.blocks.insert(
                insert_after_standalone + 1,
                {"type": "segment", "segment": segment},
            )
        else:
            # Nothing selected: keep the new segment independent.
            self.blocks.append({"type": "segment", "segment": segment})

        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()

    def edit_segment(self):
        location = self.get_selected_segment_location()
        if location is None:
            messagebox.showinfo("Edit Segment", "Select a segment first.")
            return
        kind, first, second = location
        segment = (self.blocks[first]["segments"][second] if kind == "block"
                   else self.blocks[first]["segment"])
        self.editing_segment = location
        self.segment_name.set(segment["name"])
        self.measure_mode.set(segment.get("measure_mode", "Time"))
        self.measure_value.set(str(segment.get("measure_value", segment["duration_min"])))
        self.distance_unit.set(segment.get("distance_unit", "km"))
        self.speed.set(str(segment["speed_kmh"]))
        self.incline.set(str(segment["incline_percent"]))
        self.preset_type.set("Custom")
        self.update_measure_label()
        self.update_segment_button.config(state="normal")

    def update_segment(self):
        if self.editing_segment is None:
            return
        segment = self.get_segment_values()
        if segment is None:
            return
        kind, first, second = self.editing_segment
        if kind == "block":
            self.blocks[first]["segments"][second] = segment
        else:
            self.blocks[first]["segment"] = segment
        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()
        messagebox.showinfo("Segment Updated", "Segment updated successfully.")

    def duplicate_segment(self):
        location = self.get_selected_segment_location()
        if location is None:
            messagebox.showinfo("Duplicate Segment", "Select a segment first.")
            return
        kind, first, second = location
        if kind == "block":
            duplicate = copy.deepcopy(self.blocks[first]["segments"][second])
            duplicate["name"] += " (Copy)"
            self.blocks[first]["segments"].insert(second + 1, duplicate)
        else:
            duplicate = copy.deepcopy(self.blocks[first]["segment"])
            duplicate["name"] += " (Copy)"
            self.blocks.insert(first + 1, {"type": "segment", "segment": duplicate})
        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()

    def remove_segment(self):
        location = self.get_selected_segment_location()
        if location is None:
            messagebox.showinfo("Remove Segment", "Select a segment first.")
            return
        kind, first, second = location
        if kind == "block":
            self.blocks[first]["segments"].pop(second)
        else:
            self.blocks.pop(first)
        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()

    def reset_segment_editor(self):
        self.editing_segment = None
        self.preset_type.set("Custom")
        self.segment_name.set("")
        self.measure_mode.set("Time")
        self.measure_value.set("10")
        self.distance_unit.set("km")
        self.speed.set("6")
        self.incline.set("0")
        self.update_measure_label()
        self.update_segment_button.config(state="disabled")

    # --------------------------------------------------
    # REORDERING
    # --------------------------------------------------

    def move_item(self, direction, item_type):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Move Item", "Select an item first.")
            return
        item = selection[0]
        parent = self.tree.parent(item)
        if item_type == "block":
            if parent:
                messagebox.showinfo("Move Block", "Select a block heading.")
                return
            index = self.tree.index(item)
            if self.blocks[index].get("type") != "block":
                messagebox.showinfo("Move Block", "Select a block heading.")
                return
            new_index = index + direction
            if not 0 <= new_index < len(self.blocks):
                return
            self.blocks[index], self.blocks[new_index] = self.blocks[new_index], self.blocks[index]
        elif item_type == "segment":
            if parent:
                block_index = self.tree.index(parent)
                segment_index = self.tree.index(item)
                segments = self.blocks[block_index]["segments"]
                new_index = segment_index + direction
                if not 0 <= new_index < len(segments):
                    return
                segments[segment_index], segments[new_index] = segments[new_index], segments[segment_index]
            else:
                index = self.tree.index(item)
                if self.blocks[index].get("type") != "segment":
                    messagebox.showinfo("Move Segment", "Select a segment.")
                    return
                new_index = index + direction
                if not 0 <= new_index < len(self.blocks):
                    return
                self.blocks[index], self.blocks[new_index] = self.blocks[new_index], self.blocks[index]
        self.reset_block_editor()
        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()

    # --------------------------------------------------
    # TREE DISPLAY AND SUMMARY
    # --------------------------------------------------

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_data = {}

        for block_index, entry in enumerate(self.blocks):
            if entry.get("type") == "segment":
                segment = entry["segment"]
                iid = f"standalone_{block_index}"
                self.tree.insert("", "end", iid=iid, text=segment["name"], values=(
                    f"{segment['duration_min']:.2f}", f"{segment['speed_kmh']:g}",
                    f"{segment['incline_percent']:g}", f"{segment['estimated_distance_km']:.3f}"
                ), tags=(self.segment_colour_tag(segment),))
                self.tree_item_data[iid] = {"kind": "segment", "segment": segment,
                                            "parent_block": None, "wrapper": entry}
                continue

            repetitions = entry["repetitions"]
            block_duration = sum(seg["duration_min"] for seg in entry["segments"])
            block_distance = sum(seg["estimated_distance_km"] for seg in entry["segments"])
            block_id = f"block_{block_index}"
            self.tree.insert("", "end", iid=block_id,
                text=f"{repetitions}×{entry['name']}", values=(
                    f"{block_duration * repetitions:.2f}", "-", "-", f"{block_distance * repetitions:.2f}"
                ), open=True, tags=("block",))
            self.tree_item_data[block_id] = {"kind": "block", "block": entry}

            for segment_index, segment in enumerate(entry["segments"]):
                iid = f"segment_{block_index}_{segment_index}"
                self.tree.insert(block_id, "end", iid=iid, text=segment["name"], values=(
                    f"{segment['duration_min']:.2f}", f"{segment['speed_kmh']:g}",
                    f"{segment['incline_percent']:g}", f"{segment['estimated_distance_km']:.3f}"
                ), tags=(self.segment_colour_tag(segment),))
                self.tree_item_data[iid] = {"kind": "segment", "segment": segment,
                                            "parent_block": entry, "wrapper": None}

    def start_tree_drag(self, event):
        item = self.tree.identify_row(event.y)
        self.drag_source_item = item if item in self.tree_item_data else None
        self.drag_start = (event.x, event.y)
        self.drag_original_position = None
        if not item and self.tree.identify_region(event.x, event.y) == "nothing":
            return self.clear_tree_selection()

    def show_tree_drag_preview(self, event):
        iid = getattr(self, "drag_source_item", None)
        source = self.tree_item_data.get(iid)
        if not source or source["kind"] != "segment":
            return
        start_x, start_y = self.drag_start
        if self.drag_original_position is None:
            if max(abs(event.x - start_x), abs(event.y - start_y)) < 5:
                return
        target_iid = self.tree.identify_row(event.y)
        if target_iid == iid or self.tree.identify_region(event.x, event.y) in (
            "heading", "separator"
        ):
            return

        if self.drag_original_position is None:
            self.drag_original_position = (self.tree.parent(iid), self.tree.index(iid))

        target = self.tree_item_data.get(target_iid)
        box = self.tree.bbox(target_iid) if target else None
        above_block = self.is_drop_above_source_block(source, target, box, event.y)
        after = bool(box and event.y > box[1] + box[3] / 2)
        if target is None:
            parent, index = "", "end"
        elif above_block:
            parent, index = "", self.tree.index(target_iid)
            if self.tree.parent(iid) == parent and self.tree.index(iid) < index:
                index -= 1
        elif target["kind"] == "block":
            self.tree.item(target_iid, open=True)
            parent, index = target_iid, "end"
        else:
            parent = self.tree.parent(target_iid)
            index = self.tree.index(target_iid) + int(after)
            if self.tree.parent(iid) == parent and self.tree.index(iid) < index:
                index -= 1

        self.tree.move(iid, parent, index)
        self.drag_destination = (target_iid, after, above_block)

    def is_drop_above_source_block(self, source, target, box, y):
        return (
            target is not None
            and target["kind"] == "block"
            and target["block"] is source["parent_block"]
            and bool(box and y < box[1] + box[3] / 2)
        )

    def restore_tree_drag_position(self, iid):
        position = getattr(self, "drag_original_position", None)
        if position is not None:
            self.tree.move(iid, *position)
            self.drag_original_position = None

    def clear_tree_selection(self, event=None):
        self.restore_tree_drag_position(getattr(self, "drag_source_item", None))
        self.drag_source_item = None
        selection = self.tree.selection()
        if selection:
            self.tree.selection_remove(*selection)
        self.tree.focus("")
        self.on_tree_select()
        return "break"

    def finish_tree_drag(self, event):
        source_iid = getattr(self, "drag_source_item", None)
        destination = (self.drag_destination
                       if getattr(self, "drag_original_position", None) is not None else None)
        self.restore_tree_drag_position(source_iid)
        self.drag_source_item = None
        if not source_iid or source_iid not in self.tree_item_data:
            return

        source = self.tree_item_data[source_iid]
        if source["kind"] != "segment":
            return  # Blocks retain their dedicated Move Block controls.

        if destination is None:
            target_iid = self.tree.identify_row(event.y)
            box = self.tree.bbox(target_iid) if target_iid else None
            after = bool(box and event.y > box[1] + box[3] / 2)
            above_block = self.is_drop_above_source_block(
                source, self.tree_item_data.get(target_iid), box, event.y
            )
        else:
            target_iid, after, above_block = destination
        target = self.tree_item_data.get(target_iid)
        if target_iid == source_iid:
            return

        segment = source["segment"]
        source_block = source["parent_block"]
        source_wrapper = source["wrapper"]

        # Remove the dragged segment from its current location first.
        if source_block is None:
            self.blocks.remove(source_wrapper)
        else:
            source_block["segments"].remove(segment)

        if target is None:
            # Dropping in the empty area converts/moves it to a standalone item.
            self.blocks.append({"type": "segment", "segment": segment})
        elif above_block:
            index = next(i for i, entry in enumerate(self.blocks) if entry is target["block"])
            self.blocks.insert(index, {"type": "segment", "segment": segment})
        elif target["kind"] == "block":
            target["block"]["segments"].append(segment)
        else:
            target_segment = target["segment"]
            target_block = target["parent_block"]
            if target_block is not None:
                siblings = target_block["segments"]
                index = siblings.index(target_segment)
                if after:
                    index += 1
                siblings.insert(index, segment)
            else:
                target_wrapper = target["wrapper"]
                index = self.blocks.index(target_wrapper)
                if after:
                    index += 1
                self.blocks.insert(index, {"type": "segment", "segment": segment})

        self.reset_block_editor()
        self.reset_segment_editor()
        self.refresh_tree()
        self.update_summary()

    def on_tree_select(self, event=None):
        selection = self.tree.selection()
        if (self.editing_segment is not None
                and self.editing_segment != self.get_selected_segment_location()):
            self.editing_segment = None
            self.update_segment_button.config(state="disabled")
        if not selection:
            self.reset_block_editor()
            return
        item = selection[0]
        parent = self.tree.parent(item)
        if parent:
            self.reset_block_editor()
        else:
            index = self.tree.index(item)
            if self.blocks[index].get("type") == "block":
                self.edit_block(index)
            else:
                self.reset_block_editor()

    def calculate_totals(self):
        return workout_totals(self.blocks)

    def update_summary(self):
        total_duration, total_distance = self.calculate_totals()
        self.summary.set(
            f"Total duration: {total_duration:.2f} min"
            f" | Estimated distance: {total_distance:.2f} km"
        )

    # --------------------------------------------------
    # SAVE WORKOUT
    # --------------------------------------------------

    def check_commercial_le(self):
        """Check a snapshot without changing the workout or saving a file."""
        report = assess_workout({
            "format_version": 4,
            "workout_name": self.workout_name.get(),
            "blocks": self.blocks,
        })
        show = messagebox.showerror if report.has_blockers else messagebox.showwarning
        show("Commercial LE compatibility", report.text())
        return report

    def create_qz_controls(self):
        panel = ttk.Frame(self.root, padding=(12, 0, 12, 3))
        panel.pack(fill="x")
        self.last_qz_endpoint = load_qz_endpoint()
        self.qz_address = tk.StringVar(master=self.root, value=self.last_qz_endpoint or "")
        self.qz_status = tk.StringVar(master=self.root, value="Enter the address shown by QZ.")
        self.qz_result = None
        self.qz_cancel = None
        ttk.Label(panel, text="QZ address:").grid(row=0, column=0, sticky="w")
        address_entry = ttk.Entry(panel, textvariable=self.qz_address, width=16)
        address_entry.grid(row=0, column=1, sticky="ew", padx=6)
        test_button = self.make_button(panel, text="Test Connection", role="Secondary",
                                       command=self.test_qz_connection)
        test_button.grid(row=0, column=2, padx=(0, 6))
        send_button = self.make_button(panel, text="Send to QZ", command=self.send_to_qz)
        send_button.grid(row=0, column=5)
        self.qz_controls = (address_entry, test_button, send_button)
        self.qz_reconnect_button = self.make_button(
            panel, text="Reconnect to QZ", role="Secondary", command=self.reconnect_to_qz
        )
        self.qz_reconnect_button.grid(row=0, column=3, padx=(0, 6))
        self.qz_cancel_button = self.make_button(
            panel, text="Cancel", role="Secondary", command=self.cancel_qz_verification
        )
        self.qz_cancel_button.grid(row=0, column=4, padx=(0, 6))
        self.qz_cancel_button.state(["disabled"])
        if not self.last_qz_endpoint:
            self.qz_reconnect_button.state(["disabled"])
        panel.columnconfigure(1, weight=1)
        status = ttk.Label(panel, textvariable=self.qz_status, justify="left")
        status.grid(row=1, column=0, columnspan=6, sticky="w")
        panel.bind("<Configure>", lambda event: status.configure(
            wraplength=max(1, event.width - 24)
        ))
        self.qz_address.trace_add("write", lambda *_: self.qz_status.set(
            "Address changed. Test the connection or send a workout."
        ))

    def test_qz_connection(self):
        if self.qz_result is None:
            self.start_qz_operation(verify_qz, "Verifying QZ…", verification=True)

    def reconnect_to_qz(self):
        if self.qz_result is None and self.last_qz_endpoint:
            self.qz_address.set(self.last_qz_endpoint)
            self.start_qz_operation(verify_qz, "Reconnecting to QZ…", verification=True)

    def cancel_qz_verification(self):
        if self.qz_cancel is not None:
            self.qz_cancel.set()
            self.qz_cancel_button.state(["disabled"])
            self.qz_status.set("Cancelling QZ verification…")

    def send_to_qz(self):
        if self.qz_result is not None:
            return
        if not self.qz_address.get().strip():
            self.qz_status.set("Enter the address shown by QZ.")
            return
        name = self.workout_name.get().strip() or DEFAULT_WORKOUT_NAME
        try:
            payload = build_save_payload({"workout_name": name, "blocks": self.blocks}, name=name)
        except (ProfileCompatibilityError, QzXmlExportError) as error:
            self.qz_status.set(f"Workout not sent. {error}")
            return
        self.start_qz_operation(save_training_program, "Sending workout to QZ…", payload)

    def start_qz_operation(self, operation, status, *args, verification=False):
        address = self.qz_address.get().strip()
        if not address:
            self.qz_status.set("Enter the address shown by QZ.")
            return
        result = self.qz_result = SimpleQueue()
        cancel = self.qz_cancel = Event() if verification else None
        for widget in self.qz_controls:
            widget.state(["disabled"])
        self.qz_reconnect_button.state(["disabled"])
        if verification:
            self.qz_cancel_button.state(["!disabled"])
        self.qz_status.set(status)

        async def run_verification():
            task = asyncio.create_task(operation(address, *args))
            try:
                while not cancel.is_set():
                    done, _ = await asyncio.wait({task}, timeout=0.05)
                    if done:
                        return task.result()
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

        def work():
            try:
                if verification:
                    endpoint = asyncio.run(run_verification())
                    result.put(("QZ verified.", endpoint))
                else:
                    receipt = asyncio.run(operation(address, *args))
                    message = f"Saved in QZ: {receipt.name} ({receipt.row_count} rows)."
                    result.put((message, None))
            except (QzConnectionError, QzSaveUncertainError) as error:
                message = str(error)
                if verification:
                    message += " If QZ restarted, paste its current floating-window URL."
                result.put((message, None))
            except Exception:
                result.put(("QZ operation interrupted. Check QZ before trying again.", None))

        Thread(target=work, daemon=True).start()
        self.root.after(50, self.poll_qz_operation)

    def poll_qz_operation(self):
        try:
            message, endpoint = self.qz_result.get_nowait()
        except Empty:
            self.root.after(50, self.poll_qz_operation)
            return
        if self.qz_cancel is not None and self.qz_cancel.is_set():
            message = "QZ verification cancelled."
        elif endpoint is not None:
            self.last_qz_endpoint = endpoint
            try:
                save_qz_endpoint(endpoint)
            except OSError:
                message = "QZ verified. The address could not be saved for the next session."
        self.qz_cancel = self.qz_result = None
        self.qz_cancel_button.state(["disabled"])
        if self.last_qz_endpoint:
            self.qz_reconnect_button.state(["!disabled"])
        for widget in self.qz_controls:
            widget.state(["!disabled"])
        self.qz_status.set(message)

    def confirm_qz_preview(self, title, result):
        summary, details = qz_preview(result)
        previous_focus = self.root.focus_get()
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()
        dialog.title(title)
        dialog.transient(self.root)
        dialog.minsize(520, 360)
        panel = ttk.Frame(dialog, padding=16)
        panel.pack(fill="both", expand=True)
        blocked = bool(details["Blocking errors"])
        if blocked:
            status = "Export blocked"
        elif details["Warnings"]:
            status = "Ready to export with warnings"
        else:
            status = "Ready to export"
        ttk.Label(panel, text=status, font=(UI_FONT, 12, "bold")).pack(anchor="w")
        for line in summary:
            ttk.Label(panel, text=line).pack(anchor="w", pady=(3, 0))

        buttons = ttk.Frame(panel)
        buttons.pack(side="bottom", fill="x", pady=(10, 0))
        confirmed = False

        def confirm():
            nonlocal confirmed
            confirmed = True
            dialog.destroy()

        ttk.Button(buttons, text="Export", command=confirm,
                   state="disabled" if blocked else "normal").pack(side="right")
        cancel = ttk.Button(buttons, text="Cancel", command=dialog.destroy)
        cancel.pack(side="right", padx=(0, 8))

        diagnostics = ttk.Frame(panel)
        diagnostics.pack(fill="both", expand=True, pady=(12, 0))
        scrollbar = ttk.Scrollbar(diagnostics)
        scrollbar.pack(side="right", fill="y")
        messages = tk.Text(
            diagnostics, wrap="word", width=50, height=8, padx=8, pady=6,
            bg=self.colors["input"], fg=self.colors["foreground"],
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=messages.yview)
        messages.pack(fill="both", expand=True)
        messages.tag_configure("heading", font=(UI_FONT, 10, "bold"))
        for heading, items in details.items():
            if items:
                messages.insert("end", f"{heading}\n", "heading")
                messages.insert("end", "\n\n".join(items) + "\n\n")
        if not any(details.values()):
            messages.insert("end", "No diagnostics.")
        messages.config(state="disabled")
        dialog.bind("<Escape>", lambda event: (dialog.destroy(), "break")[1])
        dialog.update_idletasks()
        width = max(520, dialog.winfo_reqwidth())
        height = max(360, dialog.winfo_reqheight())
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - width) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}{x:+d}{y:+d}")
        dialog.deiconify()
        dialog.wait_visibility()
        dialog.grab_set()
        cancel.focus_set()
        dialog.wait_window()
        if previous_focus is not None and previous_focus.winfo_exists():
            previous_focus.focus_set()
        return confirmed

    def export_qz_xml(self):
        title = "Export to QZ XML"
        try:
            result = export_workout({
                "workout_name": self.workout_name.get(),
                "blocks": self.blocks,
            })
        except (ProfileCompatibilityError, QzXmlExportError) as error:
            messagebox.showerror(title, str(error), parent=self.root)
            return
        if not self.confirm_qz_preview(title, result):
            return
        destination = filedialog.asksaveasfilename(
            title=title, parent=self.root, defaultextension=".xml",
            filetypes=[("QZ XML files", "*.xml")], confirmoverwrite=False,
        )
        if not destination:
            return
        if Path(destination).suffix.lower() != ".xml":
            messagebox.showerror(title, "Choose a filename ending in .xml.", parent=self.root)
            return
        overwrite = os.path.lexists(destination)
        if overwrite and not messagebox.askyesno(
            title, f"Replace the existing file?\n{destination}", parent=self.root,
        ):
            return
        try:
            write_qz_xml(destination, result.xml, overwrite=overwrite)
        except OSError as error:
            messagebox.showerror(title, str(error), parent=self.root)
            return

    def save_workout(self):
        try:
            workout = normalize_workout({
                "format_version": 4,
                "workout_name": self.workout_name.get().strip(),
                "blocks": self.blocks,
            })
            if not any(entry["type"] == "segment" or entry["segments"]
                       for entry in workout["blocks"]):
                messagebox.showwarning(
                    "Empty Workout", "Add at least one segment before saving."
                )
                return
            # Validate and serialize before opening any destination file.
            contents = json.dumps(workout, indent=4, ensure_ascii=False, allow_nan=False)
            contents.encode("utf-8")
        except (TypeError, ValueError) as error:
            messagebox.showerror("Save Error", str(error))
            return

        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", workout["workout_name"])
        filename = filename[:120].strip(" .") or DEFAULT_WORKOUT_NAME
        if filename.lower().endswith(".json"):
            filename = filename[:-5].rstrip(" .") or DEFAULT_WORKOUT_NAME
        if re.fullmatch(r"CON|PRN|AUX|NUL|(?:COM|LPT)[1-9¹²³]",
                        filename.split(".", 1)[0], re.IGNORECASE):
            filename = "_" + filename
        path = filedialog.asksaveasfilename(
            title="Save Workout",
            initialfile=f"{filename}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(contents)
            messagebox.showinfo(
                "Workout Saved", f"Workout saved successfully:\n{path}"
            )
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Save Error", str(error))

    # --------------------------------------------------
    # LOAD WORKOUT
    # --------------------------------------------------

    def open_workout(self):
        path = filedialog.askopenfilename(
            title="Open Workout",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                workout = json.load(file)

            validated = normalize_workout(workout)
            self.blocks = validated["blocks"]
            name = validated["workout_name"].strip()
            self.workout_name.set(
                Path(path).stem if not name or name == DEFAULT_WORKOUT_NAME
                else validated["workout_name"]
            )
            self.reset_block_editor()
            self.reset_segment_editor()
            self.refresh_tree()
            self.update_summary()
            messagebox.showinfo("Workout Loaded", "Workout loaded successfully.")

        except (
            OSError,
            json.JSONDecodeError,
            UnicodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            messagebox.showerror(
                "Open Workout Error",
                f"Could not load the workout:\n{error}",
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = TreadmillApp(root)
    root.mainloop()
