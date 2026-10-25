import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

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
    CLEANER_PATHS,
    SAFE_JUNK_EXTENSIONS,
    create_header,
    create_button,
)


def format_size(size_bytes: int) -> str:
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


class CleanerModule(tk.Frame):
    """System Cleaner Module with category selection and thread-safe logging."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.files_to_delete: list[tuple[str, int]] = []
        self.total_size = 0
        self.is_busy = False

        # Category selection variables: {name: (BooleanVar, path)}
        self.category_vars: dict[str, tuple[tk.BooleanVar, str]] = {}
        self.strict_ext_var = tk.BooleanVar(value=False)

        self.init_ui()

    def init_ui(self):
        # --- Standard Module Header ---
        create_header(
            self,
            title="System Cleaner",
            subtitle="Deep scan and remove temporary files, update caches, logs, and prefetch data.",
        )

        # --- Target Categories Card ---
        cat_card = tk.Frame(
            self,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        cat_card.pack(fill=tk.X, padx=24, pady=(0, 12))

        top_cat_row = tk.Frame(cat_card, bg=BG_CARD)
        top_cat_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            top_cat_row,
            text="Target Locations",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
        ).pack(side=tk.LEFT)

        # Optional strict extension filter checkbox
        strict_cb = tk.Checkbutton(
            top_cat_row,
            text="Strict Safe Extensions Only (.tmp, .log, .dmp, .pf, .bak, .old)",
            variable=self.strict_ext_var,
            bg=BG_CARD,
            fg=FG_SECONDARY,
            selectcolor=BG_INPUT,
            activebackground=BG_CARD,
            activeforeground=FG_PRIMARY,
            font=FONT_SMALL,
            bd=0,
            cursor="hand2",
        )
        strict_cb.pack(side=tk.RIGHT)

        grid_frame = tk.Frame(cat_card, bg=BG_CARD)
        grid_frame.pack(fill=tk.X)

        for idx, (name, path) in enumerate(CLEANER_PATHS):
            # Default Crash Dumps off so users don't accidentally wipe BSOD logs unless wanted
            default_checked = name != "Crash Dumps"
            var = tk.BooleanVar(value=default_checked)
            self.category_vars[name] = (var, path)

            col = idx % 3
            row = idx // 3
            grid_frame.columnconfigure(col, weight=1)

            cb = tk.Checkbutton(
                grid_frame,
                text=f"{name}",
                variable=var,
                bg=BG_CARD,
                fg=FG_PRIMARY,
                selectcolor=BG_INPUT,
                activebackground=BG_CARD,
                activeforeground=FG_PRIMARY,
                font=FONT_BODY,
                anchor="w",
                bd=0,
                cursor="hand2",
            )
            cb.grid(row=row, column=col, sticky="w", padx=(0, 12), pady=3)

        # --- Controls & Action Bar ---
        ctrl_frame = tk.Frame(self, bg=BG_MAIN)
        ctrl_frame.pack(fill=tk.X, padx=24, pady=(0, 8))

        self.btn_scan = create_button(
            ctrl_frame,
            text="Scan Junk Files",
            command=self.start_scan,
            variant="primary",
            width=16,
        )
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_clean = create_button(
            ctrl_frame,
            text="Clean Now",
            command=self.start_clean,
            variant="danger",
            width=16,
            state="disabled",
        )
        self.btn_clean.pack(side=tk.LEFT, padx=(0, 16))

        self.status_lbl = tk.Label(
            ctrl_frame,
            text="Ready to scan",
            fg=FG_SECONDARY,
            bg=BG_MAIN,
            font=FONT_BODY,
        )
        self.status_lbl.pack(side=tk.LEFT)

        # --- Progress Bar ---
        prog_frame = tk.Frame(self, bg=BG_MAIN)
        prog_frame.pack(fill=tk.X, padx=24, pady=(0, 10))

        self.progress = ttk.Progressbar(
            prog_frame, orient="horizontal", mode="determinate", length=100
        )
        self.progress.pack(fill=tk.X, expand=True)
        self.progress["value"] = 0

        # --- Results Console Log Area ---
        log_frame = tk.Frame(
            self,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_area = tk.Text(
            log_frame,
            bg=BG_INPUT,
            fg=THEME["success"],
            font=FONT_MONO,
            bd=0,
            padx=14,
            pady=12,
            relief="flat",
            insertbackground=FG_PRIMARY,
            yscrollcommand=scrollbar.set,
             state="disabled",
        )
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_area.yview)

        # Text color tags for cleaner output
        self.log_area.tag_config("heading", foreground=THEME["info"], font=(FONT_MONO[0], 10, "bold"))
        self.log_area.tag_config("warn", foreground=THEME["warning"])
        self.log_area.tag_config("muted", foreground=FG_SECONDARY)
        self.log_area.tag_config("success", foreground=THEME["success"])

    # --------------------------------------------------------------------------
    # Thread-Safe UI Helpers
    # --------------------------------------------------------------------------
    def log(self, message: str, tag: str = ""):
        """Appends a line to the console log on the main thread."""
        if threading.current_thread() is not threading.main_thread():
            self.after(0, self.log, message, tag)
            return

        self.log_area.configure(state="normal")
        if tag:
            self.log_area.insert("end", message + "\n", tag)
        else:
            self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def clear_log(self):
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")

    def _set_buttons_busy(self, busy: bool, allow_clean: bool = False):
        self.is_busy = busy
        if busy:
            self.btn_scan.configure(state="disabled", bg=BG_CARD, fg=FG_MUTED)
            self.btn_clean.configure(state="disabled", bg=BG_CARD, fg=FG_MUTED)
        else:
            self.btn_scan.configure(state="normal", bg=THEME["accent"], fg="#ffffff")
            if allow_clean:
                self.btn_clean.configure(state="normal", bg=THEME["danger"], fg="#ffffff")
            else:
                self.btn_clean.configure(state="disabled", bg=BG_CARD, fg=FG_MUTED)

    # --------------------------------------------------------------------------
    # Scanning Logic
    # --------------------------------------------------------------------------
    def start_scan(self):
        if self.is_busy:
            return

        selected_targets = [
            (name, path)
            for name, (var, path) in self.category_vars.items()
            if var.get()
        ]
        if not selected_targets:
            messagebox.showinfo(
                "No Targets Selected",
                "Please select at least one target location to scan.",
                parent=self,
            )
            return

        self._set_buttons_busy(True)
        self.progress["value"] = 0
        self.clear_log()

        strict_only = self.strict_ext_var.get()
        threading.Thread(
            target=self.run_scan,
            args=(selected_targets, strict_only),
            daemon=True,
        ).start()

    def run_scan(self, targets: list[tuple[str, str]], strict_only: bool):
        self.files_to_delete = []
        self.total_size = 0
        total_targets = len(targets)

        self.log("=== Starting System Junk Scan ===", "heading")
        if strict_only:
            self.log("Filter mode: Strict Safe Extensions Only", "muted")

        for idx, (name, path) in enumerate(targets):
            prog = int((idx / total_targets) * 100)
            self.after(
                0,
                lambda n=name, p=prog: [
                    self.status_lbl.configure(text=f"Scanning {n}..."),
                    self.progress.configure(value=p),
                ],
            )

            if not path or not os.path.exists(path):
                self.log(f"[Skip] {name}: Path not found ({path})", "muted")
                continue

            try:
                os.listdir(path)
            except PermissionError:
                self.log(f"[Denied] {name}: Administrator permission required ({path})", "warn")
                continue
            except OSError as e:
                self.log(f"[Error] {name}: {e}", "warn")
                continue

            cat_count = 0
            cat_bytes = 0

            for root, _dirs, files in os.walk(path):
                for filename in files:
                    if strict_only:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext not in SAFE_JUNK_EXTENSIONS:
                            continue

                    filepath = os.path.join(root, filename)
                    try:
                        if os.path.islink(filepath):
                            continue
                        size = os.path.getsize(filepath)
                        self.total_size += size
                        cat_bytes += size
                        cat_count += 1
                        self.files_to_delete.append((filepath, size))
                    except OSError:
                        pass

            self.log(f"  ✓ {name:<24} {cat_count:>6} files  ({format_size(cat_bytes)})")

        self.after(0, self.finish_scan)

    def finish_scan(self):
        count = len(self.files_to_delete)
        self.status_lbl.configure(
            text=f"Found {count:,} files ({format_size(self.total_size)})"
        )
        self.progress["value"] = 100

        self.log("\n=== Scan Summary ===", "heading")
        self.log(f"Total Junk Found : {format_size(self.total_size)}", "success")
        self.log(f"Total File Count : {count:,}")

        if self.files_to_delete:
            self.log("\n--- Sample Files Queued for Removal (First 100) ---", "muted")
            for filepath, fsize in self.files_to_delete[:100]:
                self.log(f"  • [{format_size(fsize):>9}] {filepath}", "muted")
            if count > 100:
                self.log(f"  ... and {count - 100:,} additional files.", "muted")

        self._set_buttons_busy(False, allow_clean=bool(self.files_to_delete))

    # --------------------------------------------------------------------------
    # Cleaning Logic
    # --------------------------------------------------------------------------
    def start_clean(self):
        if self.is_busy or not self.files_to_delete:
            return

        count = len(self.files_to_delete)
        if not messagebox.askyesno(
            "Confirm System Clean",
            f"Permanently delete {count:,} temporary files ({format_size(self.total_size)})?\n\n"
            "Files currently locked by running processes will be safely skipped.",
            parent=self,
        ):
            return

        self._set_buttons_busy(True)
        self.progress["value"] = 0

        threading.Thread(target=self.run_clean, daemon=True).start()

    def run_clean(self):
        deleted_size = 0
        deleted_count = 0
        skipped_count = 0
        total_count = len(self.files_to_delete)

        self.log("\n=== Cleaning Started ===", "heading")

        step = max(1, total_count // 50)
        for i, (filepath, cached_size) in enumerate(self.files_to_delete):
            try:
                os.remove(filepath)
                deleted_size += cached_size
                deleted_count += 1
            except OSError:
                skipped_count += 1

            if i % step == 0 or i == total_count - 1:
                prog_val = int(((i + 1) / total_count) * 100) if total_count > 0 else 100
                self.after(
                    0,
                    lambda p=prog_val, c=i + 1: [
                        self.progress.configure(value=p),
                        self.status_lbl.configure(text=f"Cleaning: {c:,}/{total_count:,}"),
                    ],
                )

        # Clean up empty subdirectories inside selected Temp folders
        for _name, (var, path) in self.category_vars.items():
            if var.get() and path and os.path.exists(path):
                for root, dirs, _files in os.walk(path, topdown=False):
                    for d in dirs:
                        dir_path = os.path.join(root, d)
                        try:
                            if not os.listdir(dir_path):
                                os.rmdir(dir_path)
                        except OSError:
                            pass

        self.after(
            0, lambda: self.finish_clean(deleted_size, deleted_count, skipped_count)
        )

    def finish_clean(self, deleted_size: int, deleted_count: int, skipped_count: int):
        self.progress["value"] = 100
        self.status_lbl.configure(
            text=f"Cleaned {format_size(deleted_size)} ({deleted_count:,} files removed)"
        )
        self._set_buttons_busy(False, allow_clean=False)

        self.log("\n=== Cleanup Complete ===", "heading")
        self.log(f"Space Recovered       : {format_size(deleted_size)}", "success")
        self.log(f"Files Removed         : {deleted_count:,}")
        self.log(f"Skipped (Locked/In Use): {skipped_count:,}", "muted")

        self.files_to_delete = []
        self.total_size = 0


# Compatibility alias for main.py dynamic routing
SystemCleanerTab = CleanerModule