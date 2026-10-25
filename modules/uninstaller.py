import json
import subprocess
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
    SAFE_TO_REMOVE_APPS,
    create_header,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000


class UninstallerModule(tk.Frame):
    """Native Tkinter Safe Windows Bloatware Uninstaller Module."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.all_apps: list[tuple[str, str, str]] = []  # (display_name, package_name, full_name)
        self.is_busy = False
        self.placeholder_text = "Filter safe-to-remove apps..."

        self.init_ui()
        self.load_apps()

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="Bloatware Uninstaller",
            subtitle="Scan and remove pre-installed Windows bloatware and Microsoft 365 stub apps using your safe whitelist.",
        )

        # --- Top Controls & Filter Bar ---
        ctrl_frame = tk.Frame(self, bg=BG_MAIN)
        ctrl_frame.pack(fill=tk.X, padx=24, pady=(0, 10))

        self.search_var = tk.StringVar()
        self.entry = tk.Entry(
            ctrl_frame,
            textvariable=self.search_var,
            width=36,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.entry.pack(side=tk.LEFT, padx=(0, 10), ipady=6)
        self.entry.insert(0, self.placeholder_text)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<KeyRelease>", lambda _e: self.filter_list())

        self.btn_refresh = create_button(
            ctrl_frame,
            text="↻ Refresh Scan",
            command=self.load_apps,
            variant="primary",
            pady=5,
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_remove_selected = create_button(
            ctrl_frame,
            text="Uninstall Selected",
            command=self.uninstall_selected,
            variant="danger",
            pady=5,
        )
        self.btn_remove_selected.pack(side=tk.RIGHT)

        self.status_lbl = tk.Label(
            ctrl_frame,
            text="Scanning packages...",
            fg=FG_SECONDARY,
            bg=BG_MAIN,
            font=FONT_SMALL,
        )
        self.status_lbl.pack(side=tk.LEFT, padx=8)

        # --- App Table Container ---
        table_container = tk.Frame(
            self,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        table_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        scrollbar = ttk.Scrollbar(table_container, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("DisplayName", "PackageName", "FullName", "Status")
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            selectmode="extended",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.tree.yview)

        headers = [
            ("DisplayName", "Application Name", 220, "w"),
            ("PackageName", "Package Identifier", 260, "w"),
            ("FullName", "Full Package Name", 340, "w"),
            ("Status", "Status", 120, "center"),
        ]
        for col, text, width, anchor in headers:
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.tag_configure("removed", foreground=THEME["success"])
        self.tree.tag_configure("failed", foreground=THEME["danger"])

    # --------------------------------------------------------------------------
    # Search Placeholder Helpers
    # --------------------------------------------------------------------------
    def _on_focus_in(self, _event):
        if self.entry.get() == self.placeholder_text:
            self.entry.delete(0, tk.END)
            self.entry.config(fg=FG_PRIMARY)

    def _on_focus_out(self, _event):
        if not self.entry.get().strip():
            self.entry.insert(0, self.placeholder_text)
            self.entry.config(fg=FG_SECONDARY)

    def _set_busy(self, busy: bool, status_msg: str):
        self.is_busy = busy
        self.status_lbl.config(
            text=status_msg,
            fg=THEME["info"] if busy else FG_SECONDARY,
        )
        if busy:
            self.btn_refresh.config(state="disabled", bg=BG_CARD, fg=FG_MUTED)
            self.btn_remove_selected.config(state="disabled", bg=BG_CARD, fg=FG_MUTED)
        else:
            self.btn_refresh.config(state="normal", bg=THEME["accent"], fg="#ffffff")
            self.btn_remove_selected.config(state="normal", bg=THEME["danger"], fg="#ffffff")

    # --------------------------------------------------------------------------
    # Package Discovery & Filtering
    # --------------------------------------------------------------------------
    def load_apps(self):
        if self.is_busy:
            return
        self._set_busy(True, "Scanning installed AppX packages...")

        for item in self.tree.get_children():
            self.tree.delete(item)

        def _fetch():
            ps_script = "Get-AppxPackage | Select-Object Name, PackageFullName | ConvertTo-Json -Compress"
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )

                raw_out = (result.stdout or "").strip()
                discovered: list[tuple[str, str, str]] = []

                if raw_out:
                    data = json.loads(raw_out)
                    if isinstance(data, dict):
                        data = [data]

                    seen_full_names = set()
                    for item in data:
                        pkg_name = (item.get("Name") or "").strip()
                        full_name = (item.get("PackageFullName") or "").strip()

                        if not pkg_name or not full_name or full_name in seen_full_names:
                            continue

                        if any(
                            safe_app.lower() in pkg_name.lower()
                            for safe_app in SAFE_TO_REMOVE_APPS
                        ):
                            seen_full_names.add(full_name)
                            display_name = (
                                pkg_name.replace("Microsoft.", "")
                                .replace("Windows.", "")
                                .strip(".")
                            )
                            discovered.append((display_name, pkg_name, full_name))

                discovered.sort(key=lambda x: x[0].lower())
                self.all_apps = discovered
                self.after(0, self._finish_load)
            except Exception as e:
                self.all_apps = []
                self.after(0, lambda err=str(e): self._finish_load(err))

        threading.Thread(target=_fetch, daemon=True).start()

    def _finish_load(self, error_msg: str | None = None):
        if error_msg:
            self._set_busy(False, f"Error scanning packages: {error_msg}")
            return

        self.filter_list()
        count = len(self.all_apps)
        self._set_busy(
            False,
            f"Found {count} removable bloatware package{'s' if count != 1 else ''}",
        )

    def filter_list(self):
        query = self.search_var.get().strip().lower()
        if query == self.placeholder_text.lower():
            query = ""

        filtered = [
            app
            for app in self.all_apps
            if not query or query in app[0].lower() or query in app[1].lower()
        ]
        self.render_apps(filtered)

    def render_apps(self, apps: list[tuple[str, str, str]]):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for display_name, pkg_name, full_name in apps:
            self.tree.insert(
                "",
                tk.END,
                values=(display_name, pkg_name, full_name, "Installed"),
            )

    # --------------------------------------------------------------------------
    # Uninstallation Logic
    # --------------------------------------------------------------------------
    def uninstall_selected(self):
        if self.is_busy:
            return

        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showinfo(
                "No Apps Selected",
                "Select one or more bloatware packages from the table to uninstall.\n"
                "(Hold Ctrl or Shift to select multiple rows.)",
                parent=self,
            )
            return

        targets = []
        for item_id in selected_items:
            vals = self.tree.item(item_id, "values")
            if len(vals) >= 4 and vals[3] != "Removed ✓":
                targets.append((item_id, vals[0], vals[1], vals[2]))

        if not targets:
            return

        if not messagebox.askyesno(
            "Confirm Bloatware Removal",
            f"Uninstall {len(targets)} selected package(s)?\n\n"
            + "\n".join(f"• {t[1]}" for t in targets[:10])
            + (f"\n...and {len(targets) - 10} more" if len(targets) > 10 else ""),
            parent=self,
        ):
            return

        self._set_busy(True, f"Removing {len(targets)} package(s)...")

        def _worker():
            removed_full_names = set()

            for idx, (item_id, disp_name, pkg_name, full_name) in enumerate(targets, start=1):
                self.after(
                    0,
                    lambda i=item_id, d=disp_name, p=pkg_name, f=full_name, n=idx: [
                        self.status_lbl.config(
                            text=f"Removing ({n}/{len(targets)}): {d}..."
                        ),
                        self.tree.item(i, values=(d, p, f, "Removing...")),
                    ],
                )

                ps_cmd = f"Remove-AppxPackage -Package '{full_name}' -ErrorAction Stop"
                try:
                    res = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps_cmd],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=CREATE_NO_WINDOW,
                    )
                    if res.returncode == 0:
                        removed_full_names.add(full_name)
                        self.after(
                            0,
                            lambda i=item_id, d=disp_name, p=pkg_name, f=full_name: self.tree.item(
                                i, values=(d, p, f, "Removed ✓"), tags=("removed",)
                            ),
                        )
                    else:
                        self.after(
                            0,
                            lambda i=item_id, d=disp_name, p=pkg_name, f=full_name: self.tree.item(
                                i, values=(d, p, f, "Failed"), tags=("failed",)
                            ),
                        )
                except Exception:
                    self.after(
                        0,
                        lambda i=item_id, d=disp_name, p=pkg_name, f=full_name: self.tree.item(
                            i, values=(d, p, f, "Failed"), tags=("failed",)
                        ),
                    )

            # Prune removed apps from master cache so filtering stays accurate
            if removed_full_names:
                self.all_apps = [
                    a for a in self.all_apps if a[2] not in removed_full_names
                ]

            self.after(
                0,
                lambda r=len(removed_full_names), t=len(targets): self._set_busy(
                    False, f"Removed {r}/{t} selected package(s)."
                ),
            )

        threading.Thread(target=_worker, daemon=True).start()


# Compatibility aliases for main.py dynamic loading
BloatUninstallerTab = UninstallerModule