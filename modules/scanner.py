import os
import ctypes
import hashlib
import datetime
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from config import (
    THEME,
    BG_MAIN,
    BG_CARD,
    BG_INPUT,
    FG_PRIMARY,
    FG_SECONDARY,
    FG_MUTED,
    BORDER_COLOR,
    FONT_BODY,
    FONT_BOLD,
    FONT_SMALL,
    FONT_MONO,
    create_header,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000

PROTECTED_SYSTEM_FILES = {
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
    "dumpstack.log.tmp",
}


def format_size(size_bytes: int | float) -> str:
    """Formats raw byte counts into human-readable strings (B, KB, MB, GB, TB)."""
    try:
        size = float(max(0, int(size_bytes)))
    except (TypeError, ValueError):
        return "0 B"

    if size == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while size >= 1024.0 and idx < len(units) - 1:
        size /= 1024.0
        idx += 1
    return f"{size:.2f} {units[idx]}" if idx > 0 else f"{int(size)} B"


def format_mtime(timestamp: float) -> str:
    """Formats a file modification timestamp into YYYY-MM-DD HH:MM."""
    try:
        return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def fast_file_signature(filepath: str, file_size: int) -> str | None:
    """Computes a fast partial BLAKE2b signature (first 64KB + middle 64KB + last 64KB)."""
    chunk_size = 65536
    hasher = hashlib.blake2b(digest_size=16)
    try:
        with open(filepath, "rb") as f:
            if file_size <= chunk_size * 3:
                hasher.update(f.read())
            else:
                hasher.update(f.read(chunk_size))
                f.seek(file_size // 2)
                hasher.update(f.read(chunk_size))
                f.seek(max(0, file_size - chunk_size))
                hasher.update(f.read(chunk_size))
        return hasher.hexdigest()
    except OSError:
        return None


def reveal_in_explorer(filepath: str) -> bool:
    """Opens Windows Explorer and highlights the exact file across any drive (C:, D:, etc.).
    Uses native Win32 SHOpenFolderAndSelectItems to avoid explorer.exe CLI quoting bugs
    that otherwise cause Explorer to open the default 'Documents' folder.
    """
    if not filepath or filepath == "-":
        return False

    abs_path = os.path.abspath(os.path.normpath(filepath))
    if not os.path.exists(abs_path):
        return False

    if os.name == "nt":
        try:
            shell32 = ctypes.windll.shell32
            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)

            shell32.ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
            shell32.ILCreateFromPathW.restype = ctypes.c_void_p

            shell32.SHOpenFolderAndSelectItems.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint,
                ctypes.c_void_p,
                ctypes.c_ulong,
            ]
            shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long

            shell32.ILFree.argtypes = [ctypes.c_void_p]
            shell32.ILFree.restype = None

            pidl = shell32.ILCreateFromPathW(abs_path)
            if pidl:
                try:
                    hr = shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
                    if hr == 0:
                        return True
                finally:
                    shell32.ILFree(pidl)
        except Exception:
            pass

        # Fallback: Pass raw command string (NOT a list) so quotes stay strictly after /select,
        subprocess.Popen(f'explorer.exe /select,"{abs_path}"')
        return True

    return False


class ScannerModule(tk.Frame):
    """Multi-Tab File Scanner & Storage Analyzer Module with Interactive Column Sorting."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.scan_running = False

        # Cached scan results for instant sorting
        self.dup_groups_cache: list[dict] = []
        self.dup_row_meta: dict[str, dict] = {}
        self.dup_sort_col = "Size"
        self.dup_sort_desc = True

        self.large_files_cache: list[tuple[str, int, float]] = []
        self.large_sort_col = "Size"
        self.large_sort_desc = True

        self.type_stats_cache: list[dict] = []
        self.type_total_bytes = 0
        self.type_sort_col = "TotalSize"
        self.type_sort_desc = True

        # Size threshold mapping for Large File Hunter
        self.size_thresholds = {
            "> 50 MB": 50 * 1024 * 1024,
            "> 100 MB": 100 * 1024 * 1024,
            "> 500 MB": 500 * 1024 * 1024,
            "> 1 GB": 1024 * 1024 * 1024,
            "> 5 GB": 5 * 1024 * 1024 * 1024,
        }

        self.init_ui()
        self.switch_subtab("duplicates")

    def init_ui(self):
        create_header(
            self,
            title="File Scanner & Storage Analyzer",
            subtitle="Locate duplicate files side-by-side, hunt down multi-gigabyte files, and analyze storage usage by file type.",
        )

        # --- Sub-Navigation Tab Bar ---
        nav_bar = tk.Frame(self, bg=BG_MAIN)
        nav_bar.pack(fill=tk.X, padx=24, pady=(0, 10))

        self.tab_buttons: dict[str, tk.Button] = {}
        tabs = [
            ("duplicates", "📁 Duplicate Finder"),
            ("large", "🗄️ Large File Hunter"),
            ("types", "📊 Space by File Type"),
        ]
        for key, label in tabs:
            btn = tk.Button(
                nav_bar,
                text=label,
                font=FONT_BOLD,
                width=22,
                bd=0,
                relief="flat",
                pady=7,
                cursor="hand2",
                command=lambda k=key: self.switch_subtab(k),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self.tab_buttons[key] = btn

        # --- Sub-Tab Containers ---
        self.tab_duplicates = tk.Frame(self, bg=BG_MAIN)
        self.tab_large = tk.Frame(self, bg=BG_MAIN)
        self.tab_types = tk.Frame(self, bg=BG_MAIN)

        self._build_duplicates_tab()
        self._build_large_files_tab()
        self._build_file_types_tab()

    def switch_subtab(self, tab_key: str):
        for key, btn in self.tab_buttons.items():
            if key == tab_key:
                btn.config(bg=THEME["accent"], fg="#ffffff")
            else:
                btn.config(bg=BG_CARD, fg=FG_SECONDARY)

        self.tab_duplicates.pack_forget()
        self.tab_large.pack_forget()
        self.tab_types.pack_forget()

        if tab_key == "duplicates":
            self.tab_duplicates.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))
        elif tab_key == "large":
            self.tab_large.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))
        elif tab_key == "types":
            self.tab_types.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))

    # ==========================================================================
    # TAB 1: DUPLICATE FILE FINDER (GROUPED CLUSTER VIEW + SORTING)
    # ==========================================================================
    def _build_duplicates_tab(self):
        ctrl_card = tk.Frame(
            self.tab_duplicates,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        ctrl_card.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Path Input + Browse
        path_row = tk.Frame(ctrl_card, bg=BG_CARD)
        path_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            path_row,
            text="Target Folder:",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
            width=12,
            anchor="w",
        ).pack(side=tk.LEFT)

        self.dup_path_entry = tk.Entry(
            path_row,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.dup_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=5)
        self.dup_path_entry.insert(0, "Select folder to scan...")
        self.dup_path_entry.bind(
            "<FocusIn>",
            lambda _e: self._clear_placeholder(self.dup_path_entry, "Select folder to scan..."),
        )

        create_button(
            path_row,
            text="Browse...",
            command=lambda: self.browse_folder(self.dup_path_entry),
            variant="secondary",
            width=12,
            pady=4,
        ).pack(side=tk.RIGHT)

        # Row 2: Extension Filter + Hash Verification + Scan + Sort Buttons
        opt_row = tk.Frame(ctrl_card, bg=BG_CARD)
        opt_row.pack(fill=tk.X)

        tk.Label(
            opt_row,
            text="Extensions:",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_SMALL,
            width=12,
            anchor="w",
        ).pack(side=tk.LEFT)

        self.ext_entry = tk.Entry(
            opt_row,
            width=22,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.ext_entry.pack(side=tk.LEFT, padx=(0, 12), ipady=4)
        self.ext_entry.insert(0, "e.g. .mp4, .jpg, .pdf")
        self.ext_entry.bind(
            "<FocusIn>",
            lambda _e: self._clear_placeholder(self.ext_entry, "e.g. .mp4, .jpg, .pdf"),
        )

        self.verify_hash_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opt_row,
            text="Verify Byte Hash",
            variable=self.verify_hash_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=FG_PRIMARY,
            font=FONT_SMALL,
            bd=0,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 12))

        self.btn_scan_dup = create_button(
            opt_row,
            text="Scan for Duplicates",
            command=self.toggle_dup_scan,
            variant="primary",
            width=17,
            pady=4,
        )
        self.btn_scan_dup.pack(side=tk.LEFT)

        self.lbl_dup_status = tk.Label(
            opt_row, text="Ready", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL
        )
        self.lbl_dup_status.pack(side=tk.LEFT, padx=10)

        # Quick Sort Button on Right
        create_button(
            opt_row,
            text="⇅ Sort by Size",
            command=lambda: self.sort_duplicates_by("Size"),
            variant="secondary",
            padx=10,
            pady=3,
        ).pack(side=tk.RIGHT)

        # --- Bottom Comparison Inspector Card ---
        inspector_card = tk.Frame(
            self.tab_duplicates,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        inspector_card.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        insp_top = tk.Frame(inspector_card, bg=BG_CARD)
        insp_top.pack(fill=tk.X, pady=(0, 6))

        tk.Label(
            insp_top,
            text="🔍 Selected Duplicate Comparison (Click any column header to sort)",
            fg=THEME["info"],
            bg=BG_CARD,
            font=FONT_BOLD,
        ).pack(side=tk.LEFT)

        create_button(
            insp_top,
            text="🗑 Delete Selected Duplicate",
            command=self.delete_selected_duplicate,
            variant="danger",
            padx=10,
            pady=3,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        create_button(
            insp_top,
            text="📂 Open Original Folder",
            command=self.open_selected_original_location,
            variant="secondary",
            padx=10,
            pady=3,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        create_button(
            insp_top,
            text="📂 Open Selected Folder",
            command=self.open_selected_dup_location,
            variant="primary",
            padx=10,
            pady=3,
        ).pack(side=tk.RIGHT)

        paths_grid = tk.Frame(inspector_card, bg=BG_CARD)
        paths_grid.pack(fill=tk.X)
        paths_grid.columnconfigure(1, weight=1)

        tk.Label(
            paths_grid,
            text="Original (Keep):",
            fg=THEME["success"],
            bg=BG_CARD,
            font=FONT_BOLD,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)

        self.lbl_insp_orig = tk.Label(
            paths_grid,
            text="Select a duplicate row above to compare full folder paths...",
            fg=FG_PRIMARY,
            bg=BG_INPUT,
            font=FONT_MONO,
            anchor="w",
            padx=8,
            pady=3,
        )
        self.lbl_insp_orig.grid(row=0, column=1, sticky="ew", pady=2)

        tk.Label(
            paths_grid,
            text="Duplicate Copy:",
            fg=THEME["warning"],
            bg=BG_CARD,
            font=FONT_BOLD,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)

        self.lbl_insp_dup = tk.Label(
            paths_grid,
            text="-",
            fg=FG_PRIMARY,
            bg=BG_INPUT,
            font=FONT_MONO,
            anchor="w",
            padx=8,
            pady=3,
        )
        self.lbl_insp_dup.grid(row=1, column=1, sticky="ew", pady=2)

        # --- Middle Full-Height Clustered Treeview ---
        tree_frame = tk.Frame(
            self.tab_duplicates,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        tree_frame.pack(fill=tk.BOTH, expand=True)

        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal")
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        cols = ("Role", "FileName", "Size", "Modified", "FullPath")
        self.dup_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
        )
        v_scroll.config(command=self.dup_tree.yview)
        h_scroll.config(command=self.dup_tree.xview)

        self.dup_headers_meta = [
            ("Role", "Group / Copies", 175, "w"),
            ("FileName", "File Name", 220, "w"),
            ("Size", "File Size", 115, "e"),
            ("Modified", "Last Modified", 135, "center"),
            ("FullPath", "Full File Path (Double-click to highlight in Explorer)", 560, "w"),
        ]
        for col, text, width, anchor in self.dup_headers_meta:
            self.dup_tree.heading(
                col,
                text=text,
                anchor=anchor,
                command=lambda c=col: self.sort_duplicates_by(c),
            )
            self.dup_tree.column(col, width=width, minwidth=80, anchor=anchor)

        self._update_dup_heading_arrows()
        self.dup_tree.pack(fill=tk.BOTH, expand=True)

        self.dup_tree.tag_configure(
            "group_hdr",
            background=BG_CARD,
            foreground=THEME["info"],
            font=FONT_BOLD,
        )
        self.dup_tree.tag_configure("original", foreground=THEME["success"])
        self.dup_tree.tag_configure("duplicate", foreground=FG_PRIMARY)

        self.dup_tree.bind("<<TreeviewSelect>>", self._on_dup_row_select)
        self.dup_tree.bind("<Double-1>", lambda _e: self.open_selected_dup_location())

    # ==========================================================================
    # TAB 2: LARGE FILE HUNTER (FULL-HEIGHT + SORTING)
    # ==========================================================================
    def _build_large_files_tab(self):
        ctrl_card = tk.Frame(
            self.tab_large,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        ctrl_card.pack(fill=tk.X, pady=(0, 10))

        # Row 1: Path Input + Browse
        path_row = tk.Frame(ctrl_card, bg=BG_CARD)
        path_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            path_row,
            text="Target Folder:",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
            width=12,
            anchor="w",
        ).pack(side=tk.LEFT)

        self.large_path_entry = tk.Entry(
            path_row,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.large_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=5)
        self.large_path_entry.insert(0, "Select folder to scan...")
        self.large_path_entry.bind(
            "<FocusIn>",
            lambda _e: self._clear_placeholder(self.large_path_entry, "Select folder to scan..."),
        )

        create_button(
            path_row,
            text="Browse...",
            command=lambda: self.browse_folder(self.large_path_entry),
            variant="secondary",
            width=12,
            pady=4,
        ).pack(side=tk.RIGHT)

        # Row 2: Minimum Size Dropdown + Hide System Files + Scan Button
        opt_row = tk.Frame(ctrl_card, bg=BG_CARD)
        opt_row.pack(fill=tk.X)

        tk.Label(
            opt_row,
            text="Min File Size:",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_SMALL,
            width=12,
            anchor="w",
        ).pack(side=tk.LEFT)

        self.size_combo = ttk.Combobox(
            opt_row,
            values=list(self.size_thresholds.keys()),
            state="readonly",
            width=12,
        )
        self.size_combo.set("> 100 MB")
        self.size_combo.pack(side=tk.LEFT, padx=(0, 16))

        self.hide_sys_files_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            opt_row,
            text="Hide Protected OS Files (pagefile.sys, hiberfil.sys)",
            variable=self.hide_sys_files_var,
            bg=BG_CARD,
            fg=FG_PRIMARY,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=FG_PRIMARY,
            font=FONT_SMALL,
            bd=0,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 16))

        self.btn_scan_large = create_button(
            opt_row,
            text="Scan for Large Files",
            command=self.toggle_large_scan,
            variant="primary",
            width=18,
            pady=4,
        )
        self.btn_scan_large.pack(side=tk.LEFT)

        self.lbl_large_status = tk.Label(
            opt_row, text="Ready", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL
        )
        self.lbl_large_status.pack(side=tk.LEFT, padx=10)

        create_button(
            opt_row,
            text="⇅ Sort by Size",
            command=lambda: self.sort_large_files_by("Size"),
            variant="secondary",
            padx=10,
            pady=3,
        ).pack(side=tk.RIGHT)

        # Bottom Action Bar for Large Files
        action_bar = tk.Frame(
            self.tab_large,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=8,
        )
        action_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        tk.Label(
            action_bar,
            text="💡 Tip: Double-click any row to highlight the file in Explorer, or click any column header to sort.",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_SMALL,
        ).pack(side=tk.LEFT)

        create_button(
            action_bar,
            text="🗑 Delete Selected File",
            command=self.delete_selected_large_file,
            variant="danger",
            padx=12,
            pady=4,
        ).pack(side=tk.RIGHT, padx=(8, 0))

        create_button(
            action_bar,
            text="📂 Open File Location",
            command=self.open_selected_large,
            variant="primary",
            padx=12,
            pady=4,
        ).pack(side=tk.RIGHT)

        # Full-Height Large File Treeview
        tree_frame = tk.Frame(
            self.tab_large,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        tree_frame.pack(fill=tk.BOTH, expand=True)

        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal")
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        cols = ("Size", "Extension", "Modified", "FileName", "Path")
        self.large_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
        )
        v_scroll.config(command=self.large_tree.yview)
        h_scroll.config(command=self.large_tree.xview)

        self.large_headers_meta = [
            ("Size", "File Size", 120, "e"),
            ("Extension", "Type", 90, "center"),
            ("Modified", "Last Modified", 140, "center"),
            ("FileName", "File Name", 230, "w"),
            ("Path", "Full File Path", 580, "w"),
        ]
        for col, text, width, anchor in self.large_headers_meta:
            self.large_tree.heading(
                col,
                text=text,
                anchor=anchor,
                command=lambda c=col: self.sort_large_files_by(c),
            )
            self.large_tree.column(col, width=width, minwidth=70, anchor=anchor)

        self._update_large_heading_arrows()
        self.large_tree.pack(fill=tk.BOTH, expand=True)
        self.large_tree.bind("<Double-1>", lambda _e: self.open_selected_large())

    # ==========================================================================
    # TAB 3: SPACE BY FILE TYPE ANALYZER
    # ==========================================================================
    def _build_file_types_tab(self):
        ctrl_card = tk.Frame(
            self.tab_types,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        ctrl_card.pack(fill=tk.X, pady=(0, 10))

        path_row = tk.Frame(ctrl_card, bg=BG_CARD)
        path_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            path_row,
            text="Target Folder:",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
            width=12,
            anchor="w",
        ).pack(side=tk.LEFT)

        self.type_path_entry = tk.Entry(
            path_row,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.type_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=5)
        self.type_path_entry.insert(0, "Select folder to analyze...")
        self.type_path_entry.bind(
            "<FocusIn>",
            lambda _e: self._clear_placeholder(self.type_path_entry, "Select folder to analyze..."),
        )

        create_button(
            path_row,
            text="Browse...",
            command=lambda: self.browse_folder(self.type_path_entry),
            variant="secondary",
            width=12,
            pady=4,
        ).pack(side=tk.RIGHT)

        opt_row = tk.Frame(ctrl_card, bg=BG_CARD)
        opt_row.pack(fill=tk.X)

        self.btn_scan_types = create_button(
            opt_row,
            text="Analyze Storage by File Type",
            command=self.toggle_type_scan,
            variant="primary",
            width=24,
            pady=4,
        )
        self.btn_scan_types.pack(side=tk.LEFT)

        self.lbl_type_status = tk.Label(
            opt_row,
            text="Break down gigabytes consumed by .safetensors, .pak, .mp4, .zip, and other formats.",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_SMALL,
        )
        self.lbl_type_status.pack(side=tk.LEFT, padx=14)

        # Full-Height Extension Breakdown Treeview
        tree_frame = tk.Frame(
            self.tab_types,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        tree_frame.pack(fill=tk.BOTH, expand=True)

        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical")
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ("Extension", "Count", "TotalSize", "Share", "LargestExample")
        self.type_tree = ttk.Treeview(
            tree_frame,
            columns=cols,
            show="headings",
            selectmode="browse",
            yscrollcommand=v_scroll.set,
        )
        v_scroll.config(command=self.type_tree.yview)

        self.type_headers_meta = [
            ("Extension", "File Extension", 140, "w"),
            ("Count", "File Count", 120, "e"),
            ("TotalSize", "Total Space Used", 150, "e"),
            ("Share", "Share of Folder", 200, "w"),
            ("LargestExample", "Largest File of This Type (Double-click to open)", 520, "w"),
        ]
        for col, text, width, anchor in self.type_headers_meta:
            self.type_tree.heading(
                col,
                text=text,
                anchor=anchor,
                command=lambda c=col: self.sort_types_by(c),
            )
            self.type_tree.column(col, width=width, anchor=anchor)

        self._update_type_heading_arrows()
        self.type_tree.pack(fill=tk.BOTH, expand=True)
        self.type_tree.bind("<Double-1>", lambda _e: self.open_selected_type_example())

    # ==========================================================================
    # SHARED HELPERS
    # ==========================================================================
    @staticmethod
    def _clear_placeholder(entry: tk.Entry, placeholder: str):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg=FG_PRIMARY)

    def browse_folder(self, entry_widget: tk.Entry):
        path = filedialog.askdirectory(parent=self)
        if path:
            norm = os.path.abspath(os.path.normpath(path))
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, norm)
            entry_widget.config(fg=FG_PRIMARY)

    def open_file_location(self, filepath: str):
        if not filepath or filepath == "-":
            return
        abs_path = os.path.abspath(os.path.normpath(filepath))
        if not reveal_in_explorer(abs_path):
            messagebox.showerror(
                "File Not Found",
                f"File no longer exists on disk:\n{abs_path}",
                parent=self,
            )

    # ==========================================================================
    # DUPLICATE FINDER LOGIC & SORTING
    # ==========================================================================
    def _update_dup_heading_arrows(self):
        for col, text, _w, _a in self.dup_headers_meta:
            if col == self.dup_sort_col:
                arrow = " ▼" if self.dup_sort_desc else " ▲"
                self.dup_tree.heading(col, text=f"{text}{arrow}")
            else:
                self.dup_tree.heading(col, text=text)

    def sort_duplicates_by(self, col: str):
        if self.dup_sort_col == col:
            self.dup_sort_desc = not self.dup_sort_desc
        else:
            self.dup_sort_col = col
            self.dup_sort_desc = col in ("Size", "Role", "Modified")

        self._update_dup_heading_arrows()
        if self.dup_groups_cache:
            self._render_dup_groups()

    def _on_dup_row_select(self, _event):
        sel = self.dup_tree.selection()
        if not sel:
            return
        meta = self.dup_row_meta.get(sel[0])
        if not meta:
            return
        self.lbl_insp_orig.config(text=meta.get("original", "-"))
        self.lbl_insp_dup.config(text=meta.get("selected", "-"))

    def open_selected_dup_location(self):
        sel = self.dup_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No Row Selected", "Select a file row in the table first.", parent=self
            )
            return
        meta = self.dup_row_meta.get(sel[0])
        if meta and meta.get("selected"):
            self.open_file_location(meta["selected"])

    def open_selected_original_location(self):
        sel = self.dup_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No Row Selected", "Select a file row in the table first.", parent=self
            )
            return
        meta = self.dup_row_meta.get(sel[0])
        if meta and meta.get("original"):
            self.open_file_location(meta["original"])

    def delete_selected_duplicate(self):
        sel = self.dup_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No Duplicate Selected",
                "Select a `[DUPLICATE]` row in the table to delete.",
                parent=self,
            )
            return

        item_id = sel[0]
        meta = self.dup_row_meta.get(item_id)
        if not meta or meta.get("role") != "duplicate":
            messagebox.showwarning(
                "Select a Duplicate Copy",
                "Please select a `[DUPLICATE]` copy row rather than the `[KEEP - Original]` row or group header.",
                parent=self,
            )
            return

        target_path = meta["selected"]
        orig_path = meta["original"]

        if not messagebox.askyesno(
            "Confirm File Deletion",
            f"Permanently delete this duplicate file?\n\n"
            f"DELETE:\n{target_path}\n\n"
            f"KEEPING ORIGINAL:\n{orig_path}",
            parent=self,
        ):
            return

        try:
            os.remove(target_path)
            self.dup_tree.delete(item_id)
            del self.dup_row_meta[item_id]
            self.lbl_insp_dup.config(text="[Deleted]")
        except Exception as e:
            messagebox.showerror("Delete Failed", f"Could not delete file:\n{e}", parent=self)

    def toggle_dup_scan(self):
        if self.scan_running:
            self.scan_running = False
            self.btn_scan_dup.config(text="Stopping...", state="disabled")
        else:
            self.start_duplicate_scan()

    def start_duplicate_scan(self):
        raw_path = self.dup_path_entry.get().strip()
        if not raw_path or raw_path == "Select folder to scan...":
            messagebox.showerror("Invalid Path", "Please select a valid folder directory to scan.", parent=self)
            return

        scan_path = os.path.abspath(os.path.normpath(raw_path))
        if not os.path.isdir(scan_path):
            messagebox.showerror("Invalid Path", f"Directory does not exist:\n{scan_path}", parent=self)
            return

        ext_filter = self.ext_entry.get().strip()
        extensions = None
        if ext_filter and ext_filter != "e.g. .mp4, .jpg, .pdf":
            extensions = {
                f".{e.strip().lstrip('.')}".lower()
                for e in ext_filter.split(",")
                if e.strip()
            }

        verify_hash = self.verify_hash_var.get()

        self.scan_running = True
        self.btn_scan_dup.config(text="Stop Scan", bg=THEME["danger"])
        self.lbl_dup_status.config(text="Scanning file tree...", fg=THEME["info"])

        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)
        self.dup_row_meta.clear()
        self.dup_groups_cache.clear()

        threading.Thread(
            target=self._scan_duplicates_worker,
            args=(scan_path, extensions, verify_hash),
            daemon=True,
        ).start()

    def _scan_duplicates_worker(
        self, scan_path: str, extensions: set[str] | None, verify_hash: bool
    ):
        candidates: dict[tuple[str, int], list[tuple[str, float]]] = {}
        scanned = 0

        for root, _dirs, files in os.walk(scan_path):
            if not self.scan_running:
                break
            for file in files:
                if not self.scan_running:
                    break
                if file.lower() in PROTECTED_SYSTEM_FILES:
                    continue
                if extensions:
                    ext = os.path.splitext(file)[1].lower()
                    if ext not in extensions:
                        continue

                fpath = os.path.abspath(os.path.normpath(os.path.join(root, file)))
                try:
                    stat = os.stat(fpath)
                    if stat.st_size == 0:
                        continue
                    key = (file.lower(), stat.st_size)
                    candidates.setdefault(key, []).append((fpath, stat.st_mtime))
                    scanned += 1

                    if scanned % 400 == 0:
                        self.after(
                            0,
                            lambda c=scanned: self.lbl_dup_status.config(
                                text=f"Scanned {c:,} files..."
                            ),
                        )
                except OSError:
                    continue

        duplicate_groups: list[dict] = []
        total_dup_files = 0
        total_wasted_bytes = 0

        multi_groups = [
            (fname, fsize, items)
            for (fname, fsize), items in candidates.items()
            if len(items) > 1
        ]

        for idx, (_fname, fsize, items) in enumerate(multi_groups):
            if not self.scan_running:
                break

            if verify_hash:
                if idx % 25 == 0:
                    self.after(
                        0,
                        lambda i=idx, t=len(multi_groups): self.lbl_dup_status.config(
                            text=f"Verifying content hashes ({i}/{t})..."
                        ),
                    )
                by_hash: dict[str, list[tuple[str, float]]] = {}
                for fpath, mtime in items:
                    sig = fast_file_signature(fpath, fsize)
                    if sig:
                        by_hash.setdefault(sig, []).append((fpath, mtime))

                subgroups = [g for g in by_hash.values() if len(g) > 1]
            else:
                subgroups = [items]

            for grp in subgroups:
                grp.sort(key=lambda x: x[1])
                wasted = fsize * (len(grp) - 1)
                total_wasted_bytes += wasted
                total_dup_files += len(grp) - 1
                duplicate_groups.append(
                    {
                        "filename": os.path.basename(grp[0][0]),
                        "size": fsize,
                        "wasted": wasted,
                        "mtime": grp[0][1],
                        "path": grp[0][0],
                        "copies": len(grp),
                        "files": grp,
                    }
                )

        if not self.scan_running:
            msg = "Scan stopped."
        else:
            msg = (
                f"Found {total_dup_files:,} duplicates in {len(duplicate_groups):,} groups "
                f"({format_size(total_wasted_bytes)} wasted space)"
            )

        self.after(0, lambda: self._finish_dup_scan(duplicate_groups, msg))

    def _finish_dup_scan(self, groups: list[dict], msg: str):
        self.scan_running = False
        self.btn_scan_dup.config(text="Scan for Duplicates", bg=THEME["accent"], state="normal")
        self.lbl_dup_status.config(
            text=msg, fg=THEME["success"] if groups else FG_SECONDARY
        )
        self.dup_groups_cache = groups
        self._render_dup_groups()

    def _render_dup_groups(self):
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)
        self.dup_row_meta.clear()

        if not self.dup_groups_cache:
            return

        # Sort groups based on active column
        if self.dup_sort_col == "FileName":
            key_fn = lambda g: g["filename"].lower()
        elif self.dup_sort_col == "Modified":
            key_fn = lambda g: g["mtime"]
        elif self.dup_sort_col == "FullPath":
            key_fn = lambda g: g["path"].lower()
        elif self.dup_sort_col == "Role":
            key_fn = lambda g: (g["copies"], g["wasted"])
        else:
            # Default 'Size': sort by individual file size
            key_fn = lambda g: (g["size"], g["wasted"])

        sorted_groups = sorted(
            self.dup_groups_cache, key=key_fn, reverse=self.dup_sort_desc
        )

        for grp_idx, grp in enumerate(sorted_groups[:150], start=1):
            files = grp["files"]
            orig_path, orig_mtime = files[0]
            size_str = format_size(grp["size"])
            wasted_str = format_size(grp["wasted"])

            hdr_id = self.dup_tree.insert(
                "",
                tk.END,
                values=(
                    f"📦 Group #{grp_idx} ({len(files)} copies)",
                    grp["filename"],
                    f"{size_str} ({wasted_str} wasted)",
                    "",
                    f"Original folder: {os.path.dirname(orig_path)}",
                ),
                tags=("group_hdr",),
            )
            self.dup_row_meta[hdr_id] = {
                "role": "header",
                "original": orig_path,
                "selected": files[1][0],
            }

            orig_id = self.dup_tree.insert(
                "",
                tk.END,
                values=(
                    "   ├─ [KEEP - Original]",
                    grp["filename"],
                    size_str,
                    format_mtime(orig_mtime),
                    orig_path,
                ),
                tags=("original",),
            )
            self.dup_row_meta[orig_id] = {
                "role": "original",
                "original": orig_path,
                "selected": orig_path,
            }

            for copy_idx, (dup_path, dup_mtime) in enumerate(files[1:], start=1):
                branch = "   └─" if copy_idx == len(files) - 1 else "   ├─"
                dup_id = self.dup_tree.insert(
                    "",
                    tk.END,
                    values=(
                        f"{branch} [DUPLICATE #{copy_idx}]",
                        os.path.basename(dup_path),
                        size_str,
                        format_mtime(dup_mtime),
                        dup_path,
                    ),
                    tags=("duplicate",),
                )
                self.dup_row_meta[dup_id] = {
                    "role": "duplicate",
                    "original": orig_path,
                    "selected": dup_path,
                }

    # ==========================================================================
    # LARGE FILE HUNTER LOGIC & SORTING
    # ==========================================================================
    def _update_large_heading_arrows(self):
        for col, text, _w, _a in self.large_headers_meta:
            if col == self.large_sort_col:
                arrow = " ▼" if self.large_sort_desc else " ▲"
                self.large_tree.heading(col, text=f"{text}{arrow}")
            else:
                self.large_tree.heading(col, text=text)

    def sort_large_files_by(self, col: str):
        if self.large_sort_col == col:
            self.large_sort_desc = not self.large_sort_desc
        else:
            self.large_sort_col = col
            self.large_sort_desc = col in ("Size", "Modified")

        self._update_large_heading_arrows()
        if self.large_files_cache:
            self._render_large_files()

    def toggle_large_scan(self):
        if self.scan_running:
            self.scan_running = False
            self.btn_scan_large.config(text="Stopping...", state="disabled")
        else:
            self.start_large_scan()

    def start_large_scan(self):
        raw_path = self.large_path_entry.get().strip()
        if not raw_path or raw_path == "Select folder to scan...":
            messagebox.showerror("Invalid Path", "Please select a valid folder directory to scan.", parent=self)
            return

        scan_path = os.path.abspath(os.path.normpath(raw_path))
        if not os.path.isdir(scan_path):
            messagebox.showerror("Invalid Path", f"Directory does not exist:\n{scan_path}", parent=self)
            return

        min_bytes = self.size_thresholds.get(self.size_combo.get(), 100 * 1024 * 1024)
        hide_sys = self.hide_sys_files_var.get()

        self.scan_running = True
        self.btn_scan_large.config(text="Stop Scan", bg=THEME["danger"])
        self.lbl_large_status.config(text="Scanning...", fg=THEME["info"])
        for item in self.large_tree.get_children():
            self.large_tree.delete(item)
        self.large_files_cache.clear()

        threading.Thread(
            target=self._scan_large_worker,
            args=(scan_path, min_bytes, hide_sys),
            daemon=True,
        ).start()

    def _scan_large_worker(self, scan_path: str, min_bytes: int, hide_sys: bool):
        large_files: list[tuple[str, int, float]] = []
        scanned = 0

        for root, _dirs, files in os.walk(scan_path):
            if not self.scan_running:
                break
            for file in files:
                if not self.scan_running:
                    break
                if hide_sys and file.lower() in PROTECTED_SYSTEM_FILES:
                    continue

                fpath = os.path.abspath(os.path.normpath(os.path.join(root, file)))
                scanned += 1
                try:
                    stat = os.stat(fpath)
                    if stat.st_size >= min_bytes:
                        large_files.append((fpath, stat.st_size, stat.st_mtime))
                except OSError:
                    continue

                if scanned % 400 == 0:
                    self.after(
                        0,
                        lambda c=scanned: self.lbl_large_status.config(
                            text=f"Scanned {c:,} files..."
                        ),
                    )

        total_bytes = sum(x[1] for x in large_files)
        msg = (
            "Scan stopped."
            if not self.scan_running
            else f"Found {len(large_files):,} files ({format_size(total_bytes)} total)"
        )
        self.after(0, lambda: self._finish_large_scan(large_files, msg))

    def _finish_large_scan(self, large_files: list[tuple[str, int, float]], msg: str):
        self.scan_running = False
        self.btn_scan_large.config(text="Scan for Large Files", bg=THEME["accent"], state="normal")
        self.lbl_large_status.config(
            text=msg, fg=THEME["success"] if large_files else FG_SECONDARY
        )
        self.large_files_cache = large_files
        self._render_large_files()

    def _render_large_files(self):
        for item in self.large_tree.get_children():
            self.large_tree.delete(item)

        if not self.large_files_cache:
            return

        if self.large_sort_col == "Extension":
            key_fn = lambda x: (os.path.splitext(x[0])[1].lower(), x[1])
        elif self.large_sort_col == "Modified":
            key_fn = lambda x: x[2]
        elif self.large_sort_col == "FileName":
            key_fn = lambda x: os.path.basename(x[0]).lower()
        elif self.large_sort_col == "Path":
            key_fn = lambda x: x[0].lower()
        else:
            # Default: numeric byte size
            key_fn = lambda x: x[1]

        sorted_files = sorted(
            self.large_files_cache, key=key_fn, reverse=self.large_sort_desc
        )

        for fpath, size, mtime in sorted_files[:250]:
            fname = os.path.basename(fpath)
            ext = os.path.splitext(fname)[1].lower() or "(none)"
            self.large_tree.insert(
                "",
                tk.END,
                values=(format_size(size), ext, format_mtime(mtime), fname, fpath),
            )

    def open_selected_large(self):
        sel = self.large_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No File Selected", "Select a file row in the table first.", parent=self
            )
            return
        vals = self.large_tree.item(sel[0], "values")
        if len(vals) >= 5:
            self.open_file_location(vals[4])

    def delete_selected_large_file(self):
        sel = self.large_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No File Selected", "Select a file from the table first.", parent=self
            )
            return

        item_id = sel[0]
        vals = self.large_tree.item(item_id, "values")
        if len(vals) < 5:
            return

        size_str, _ext, _mtime, fname, fpath = vals
        if fname.lower() in PROTECTED_SYSTEM_FILES or fpath.lower().startswith(r"c:\windows"):
            messagebox.showerror(
                "Protected System File",
                f"'{fname}' is a protected Windows file and cannot be deleted.",
                parent=self,
            )
            return

        if not messagebox.askyesno(
            "Confirm Permanent Delete",
            f"Permanently delete this file ({size_str})?\n\n{fpath}",
            parent=self,
        ):
            return

        try:
            os.remove(fpath)
            self.large_tree.delete(item_id)
            self.large_files_cache = [
                item for item in self.large_files_cache if item[0] != fpath
            ]
        except Exception as e:
            messagebox.showerror("Delete Error", f"Could not delete file:\n{e}", parent=self)

    # ==========================================================================
    # TAB 3: SPACE BY FILE TYPE ANALYZER LOGIC & SORTING
    # ==========================================================================
    def _update_type_heading_arrows(self):
        for col, text, _w, _a in self.type_headers_meta:
            if col == self.type_sort_col:
                arrow = " ▼" if self.type_sort_desc else " ▲"
                self.type_tree.heading(col, text=f"{text}{arrow}")
            else:
                self.type_tree.heading(col, text=text)

    def sort_types_by(self, col: str):
        if self.type_sort_col == col:
            self.type_sort_desc = not self.type_sort_desc
        else:
            self.type_sort_col = col
            self.type_sort_desc = col in ("TotalSize", "Count", "Share")

        self._update_type_heading_arrows()
        if self.type_stats_cache:
            self._render_type_stats()

    def toggle_type_scan(self):
        if self.scan_running:
            self.scan_running = False
            self.btn_scan_types.config(text="Stopping...", state="disabled")
        else:
            self.start_type_scan()

    def start_type_scan(self):
        raw_path = self.type_path_entry.get().strip()
        if not raw_path or raw_path == "Select folder to analyze...":
            messagebox.showerror(
                "Invalid Path", "Please select a valid folder directory to analyze.", parent=self
            )
            return

        scan_path = os.path.abspath(os.path.normpath(raw_path))
        if not os.path.isdir(scan_path):
            messagebox.showerror(
                "Invalid Path", f"Directory does not exist:\n{scan_path}", parent=self
            )
            return

        self.scan_running = True
        self.btn_scan_types.config(text="Stop Analysis", bg=THEME["danger"])
        self.lbl_type_status.config(text="Analyzing file types...", fg=THEME["info"])
        for item in self.type_tree.get_children():
            self.type_tree.delete(item)
        self.type_stats_cache.clear()

        threading.Thread(
            target=self._scan_types_worker, args=(scan_path,), daemon=True
        ).start()

    def _scan_types_worker(self, scan_path: str):
        stats: dict[str, dict] = {}
        total_folder_bytes = 0
        scanned = 0

        for root, _dirs, files in os.walk(scan_path):
            if not self.scan_running:
                break
            for file in files:
                if not self.scan_running:
                    break
                if file.lower() in PROTECTED_SYSTEM_FILES:
                    continue

                fpath = os.path.abspath(os.path.normpath(os.path.join(root, file)))
                scanned += 1
                try:
                    fsize = os.path.getsize(fpath)
                except OSError:
                    continue

                ext = os.path.splitext(file)[1].lower() or "(no extension)"
                total_folder_bytes += fsize

                entry = stats.get(ext)
                if entry is None:
                    stats[ext] = {
                        "ext": ext,
                        "count": 1,
                        "total_bytes": fsize,
                        "max_size": fsize,
                        "max_path": fpath,
                    }
                else:
                    entry["count"] += 1
                    entry["total_bytes"] += fsize
                    if fsize > entry["max_size"]:
                        entry["max_size"] = fsize
                        entry["max_path"] = fpath

                if scanned % 500 == 0:
                    self.after(
                        0,
                        lambda c=scanned: self.lbl_type_status.config(
                            text=f"Analyzed {c:,} files..."
                        ),
                    )

        ranked = list(stats.values())
        msg = (
            "Analysis stopped."
            if not self.scan_running
            else f"Analyzed {scanned:,} files ({format_size(total_folder_bytes)} across {len(ranked)} file types)"
        )
        self.after(0, lambda: self._finish_type_scan(ranked, total_folder_bytes, msg))

    def _finish_type_scan(self, ranked: list[dict], total_bytes: int, msg: str):
        self.scan_running = False
        self.btn_scan_types.config(
            text="Analyze Storage by File Type", bg=THEME["accent"], state="normal"
        )
        self.lbl_type_status.config(
            text=msg, fg=THEME["success"] if ranked else FG_SECONDARY
        )
        self.type_stats_cache = ranked
        self.type_total_bytes = total_bytes
        self._render_type_stats()

    def _render_type_stats(self):
        for item in self.type_tree.get_children():
            self.type_tree.delete(item)

        if not self.type_stats_cache:
            return

        if self.type_sort_col == "Extension":
            key_fn = lambda x: x["ext"]
        elif self.type_sort_col == "Count":
            key_fn = lambda x: x["count"]
        elif self.type_sort_col == "LargestExample":
            key_fn = lambda x: x["max_path"].lower()
        else:
            key_fn = lambda x: x["total_bytes"]

        sorted_stats = sorted(
            self.type_stats_cache, key=key_fn, reverse=self.type_sort_desc
        )

        for item in sorted_stats[:120]:
            pct = (
                (item["total_bytes"] / self.type_total_bytes * 100.0)
                if self.type_total_bytes > 0
                else 0.0
            )
            blocks = int(round(pct / 10.0))
            bar_str = ("█" * blocks) + ("░" * (10 - blocks)) + f"  {pct:5.1f}%"

            self.type_tree.insert(
                "",
                tk.END,
                values=(
                    item["ext"],
                    f"{item['count']:,}",
                    format_size(item["total_bytes"]),
                    bar_str,
                    item["max_path"],
                ),
            )

    def open_selected_type_example(self):
        sel = self.type_tree.selection()
        if sel:
            vals = self.type_tree.item(sel[0], "values")
            if len(vals) >= 5:
                self.open_file_location(vals[4])


# Compatibility alias for main.py dynamic routing
FileScannerTab = ScannerModule