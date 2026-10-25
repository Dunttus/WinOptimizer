import csv
import json
import re
import subprocess
import threading
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
    PRESET_APPS,
    create_header,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000


class WingetModule(tk.Frame):
    """Native Tkinter WinGet GUI Package Manager Module with Multi-Select Uninstall & Inventory Export."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)

        self.installed_cache: list[list[str]] = []
        self.is_loading_installed = False
        self.is_busy = False
        self.preset_vars: dict[str, tk.BooleanVar] = {}

        self.store_placeholder = "Search Microsoft WinGet repository..."
        self.local_placeholder = "Filter installed packages..."

        self.init_ui()
        self.toggle_view("Store Search")

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="WinGet Package Manager",
            subtitle="Search the official Microsoft package repository, batch-uninstall installed software, or export app inventory.",
        )

        # --- Sub-Navigation Tab Switcher ---
        self.switch_frame = tk.Frame(self, bg=BG_MAIN)
        self.switch_frame.pack(fill=tk.X, padx=24, pady=(0, 12))

        self.tab_buttons: dict[str, tk.Button] = {}
        for tab_name in ("Store Search", "My Installed Apps", "Preset Apps"):
            btn = tk.Button(
                self.switch_frame,
                text=tab_name,
                font=FONT_BOLD,
                width=18,
                bd=0,
                relief="flat",
                pady=7,
                cursor="hand2",
                command=lambda n=tab_name: self.toggle_view(n),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            self.tab_buttons[tab_name] = btn

        # --- Shared Bottom Output Console ---
        console_outer = tk.Frame(self, bg=BG_MAIN)
        console_outer.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=(8, 20))

        console_hdr = tk.Frame(console_outer, bg=BG_MAIN)
        console_hdr.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            console_hdr,
            text="WinGet Output Console",
            fg=FG_PRIMARY,
            bg=BG_MAIN,
            font=FONT_BOLD,
        ).pack(side=tk.LEFT)

        create_button(
            console_hdr,
            text="Clear Log",
            command=self.clear_console,
            variant="secondary",
            padx=10,
            pady=2,
        ).pack(side=tk.RIGHT)

        console_box = tk.Frame(
            console_outer,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        console_box.pack(fill=tk.X)

        console_scroll = ttk.Scrollbar(console_box, orient="vertical")
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.console = tk.Text(
            console_box,
            height=7,
            font=FONT_MONO,
            bg=BG_INPUT,
            fg=THEME["success"],
            bd=0,
            padx=12,
            pady=8,
            relief="flat",
            insertbackground=FG_PRIMARY,
            yscrollcommand=console_scroll.set,
            state="disabled",
        )
        self.console.pack(side=tk.LEFT, fill=tk.X, expand=True)
        console_scroll.config(command=self.console.yview)

        # --- Sub-View Containers ---
        self.store_container = tk.Frame(self, bg=BG_MAIN)
        self.installed_container = tk.Frame(self, bg=BG_MAIN)
        self.preset_container = tk.Frame(self, bg=BG_MAIN)

        self.setup_store_ui()
        self.setup_installed_ui()
        self.setup_preset_ui()

        self.log("Ready.")

    def toggle_view(self, view_name: str):
        for name, btn in self.tab_buttons.items():
            if name == view_name:
                btn.config(bg=THEME["accent"], fg="#ffffff")
            else:
                btn.config(bg=BG_CARD, fg=FG_SECONDARY)

        self.store_container.pack_forget()
        self.installed_container.pack_forget()
        self.preset_container.pack_forget()

        if view_name == "Store Search":
            self.store_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=4)
        elif view_name == "My Installed Apps":
            self.installed_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=4)
            if not self.installed_cache and not self.is_loading_installed:
                self.refresh_installed()
        elif view_name == "Preset Apps":
            self.preset_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=4)
            self.refresh_preset_ui()

    # ==========================================================================
    # UI BUILDERS
    # ==========================================================================
    def setup_store_ui(self):
        notice_card = tk.Frame(
            self.store_container,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=8,
        )
        notice_card.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            notice_card,
            text="⚠️ Repository & License Notice: Packages are fetched directly from the official Microsoft WinGet repository. Ensure you hold valid licenses for any proprietary software.",
            fg=THEME["warning"],
            bg=BG_CARD,
            font=FONT_SMALL,
            anchor="w",
        ).pack(fill=tk.X)

        search_bar = tk.Frame(self.store_container, bg=BG_MAIN)
        search_bar.pack(fill=tk.X, pady=(0, 8))

        self.store_search_var = tk.StringVar()
        self.store_entry = tk.Entry(
            search_bar,
            textvariable=self.store_search_var,
            width=40,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.store_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=6)
        self.store_entry.insert(0, self.store_placeholder)
        self.store_entry.bind(
            "<FocusIn>",
            lambda _e: self._clear_placeholder(self.store_entry, self.store_placeholder),
        )
        self.store_entry.bind(
            "<FocusOut>",
            lambda _e: self._restore_placeholder(self.store_entry, self.store_placeholder),
        )
        self.store_entry.bind("<Return>", lambda _e: self.run_store_search())

        create_button(
            search_bar,
            text="Search Store",
            command=self.run_store_search,
            variant="primary",
            pady=5,
        ).pack(side=tk.LEFT, padx=(0, 10))

        create_button(
            search_bar,
            text="Install Selected Package",
            command=self.install_selected_store_app,
            variant="success",
            pady=5,
        ).pack(side=tk.RIGHT)

        table_box = tk.Frame(
            self.store_container,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        table_box.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(table_box, orient="vertical")
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ("Name", "Id", "Version", "Match")
        self.store_tree = ttk.Treeview(
            table_box,
            columns=cols,
            show="headings",
            selectmode="browse",
            yscrollcommand=scroll.set,
        )
        scroll.config(command=self.store_tree.yview)

        for col, title, width in [
            ("Name", "Package Name", 280),
            ("Id", "Package ID", 280),
            ("Version", "Version", 130),
            ("Match", "Match / Source", 140),
        ]:
            self.store_tree.heading(col, text=title, anchor="w")
            self.store_tree.column(col, width=width, anchor="w")

        self.store_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def setup_installed_ui(self):
        tool_bar = tk.Frame(self.installed_container, bg=BG_MAIN)
        tool_bar.pack(fill=tk.X, pady=(0, 8))

        self.local_filter_var = tk.StringVar()
        self.local_entry = tk.Entry(
            tool_bar,
            textvariable=self.local_filter_var,
            width=28,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.local_entry.pack(side=tk.LEFT, padx=(0, 8), ipady=6)
        self.local_entry.insert(0, self.local_placeholder)
        self.local_entry.bind(
            "<FocusIn>",
            lambda _e: self._clear_placeholder(self.local_entry, self.local_placeholder),
        )
        self.local_entry.bind(
            "<FocusOut>",
            lambda _e: self._restore_placeholder(self.local_entry, self.local_placeholder),
        )
        self.local_entry.bind("<KeyRelease>", lambda _e: self.filter_local_apps())

        create_button(
            tool_bar,
            text="↻ Refresh",
            command=self.refresh_installed,
            variant="primary",
            padx=10,
            pady=5,
        ).pack(side=tk.LEFT, padx=(0, 6))

        # Bonus Feature Button: Export Inventory
        create_button(
            tool_bar,
            text="📤 Export Apps",
            command=self.export_installed_apps,
            variant="secondary",
            padx=10,
            pady=5,
        ).pack(side=tk.LEFT, padx=(0, 6))

        create_button(
            tool_bar,
            text="Update All",
            command=self.update_all_apps,
            variant="warning",
            padx=10,
            pady=5,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        create_button(
            tool_bar,
            text="🗑 Uninstall Selected (Multi)",
            command=self.uninstall_selected_local_apps_batch,
            variant="danger",
            padx=12,
            pady=5,
        ).pack(side=tk.RIGHT)

        table_box = tk.Frame(
            self.installed_container,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        table_box.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(table_box, orient="vertical")
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ("Name", "Id", "Version", "Available")
        # selectmode="extended" allows holding Ctrl or Shift to select multiple apps at once
        self.installed_tree = ttk.Treeview(
            table_box,
            columns=cols,
            show="headings",
            selectmode="extended",
            yscrollcommand=scroll.set,
        )
        scroll.config(command=self.installed_tree.yview)

        for col, title, width in [
            ("Name", "Installed Application (Multi-Select Enabled)", 280),
            ("Id", "Package ID", 280),
            ("Version", "Installed Version", 130),
            ("Available", "Update Available", 140),
        ]:
            self.installed_tree.heading(col, text=title, anchor="w")
            self.installed_tree.column(col, width=width, anchor="w")

        self.installed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def setup_preset_ui(self):
        top_card = tk.Frame(
            self.preset_container,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        top_card.pack(fill=tk.X, pady=(0, 10))

        hdr_row = tk.Frame(top_card, bg=BG_CARD)
        hdr_row.pack(fill=tk.X)

        tk.Label(
            hdr_row,
            text="Batch Install Preset Applications (config.py)",
            font=FONT_BOLD,
            fg=FG_PRIMARY,
            bg=BG_CARD,
        ).pack(side=tk.LEFT)

        create_button(
            hdr_row,
            text="Install Selected Presets",
            command=self.install_selected_presets,
            variant="primary",
            pady=5,
        ).pack(side=tk.RIGHT)

        tk.Label(
            top_card,
            text="Select the preset packages below to install silently in batch mode.",
            font=FONT_SMALL,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        ).pack(anchor="w", pady=(2, 0))

        self.preset_grid_card = tk.Frame(
            self.preset_container,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        self.preset_grid_card.pack(fill=tk.BOTH, expand=True)

    # ==========================================================================
    # THREAD-SAFE LOGGING & PLACEHOLDER HELPERS
    # ==========================================================================
    @staticmethod
    def _clear_placeholder(entry: tk.Entry, placeholder: str):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.config(fg=FG_PRIMARY)

    @staticmethod
    def _restore_placeholder(entry: tk.Entry, placeholder: str):
        if not entry.get().strip():
            entry.insert(0, placeholder)
            entry.config(fg=FG_SECONDARY)

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", tk.END)
        self.console.configure(state="disabled")

    def log(self, text: str):
        clean_text = text.strip()
        if not clean_text or clean_text in ("|", "/", "-", "\\"):
            return
        if "MB /" in clean_text:
            return

        if "â–" in clean_text or "█" in clean_text:
            try:
                percent_str = clean_text.split()[-1]
                if "%" in percent_str:
                    val = int(percent_str.replace("%", ""))
                    if val % 10 == 0 or val == 100:
                        self._raw_log(f"Download Progress: {val}%")
            except Exception:
                pass
            return

        self._raw_log(clean_text)

    def _raw_log(self, text: str):
        """Appends a line to the console widget safely on the main GUI thread."""
        if threading.current_thread() is not threading.main_thread():
            self.after(0, self._raw_log, text)
            return

        self.console.configure(state="normal")
        self.console.insert(tk.END, f"> {text}\n")
        self.console.see(tk.END)
        self.console.configure(state="disabled")

    # ==========================================================================
    # WINGET TABLE PARSER (LOCALE-RESILIENT)
    # ==========================================================================
    @staticmethod
    def parse_winget_table(output: str) -> list[list[str]]:
        lines = output.splitlines()
        if not lines:
            return []

        sep_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) >= 15 and set(stripped) <= {"-", " "}:
                sep_idx = i
                break

        if sep_idx < 1:
            return []

        header_line = lines[sep_idx - 1]
        col_starts = [m.start() for m in re.finditer(r"\S+", header_line)]
        if len(col_starts) < 2:
            return []

        slices = col_starts + [len(header_line) + 120]
        results = []

        for line in lines[sep_idx + 1 :]:
            stripped = line.strip()
            if not stripped or "---" in stripped:
                continue
            row_data = []
            for i in range(min(4, len(slices) - 1)):
                val = line[slices[i] : slices[i + 1]].strip()
                row_data.append(val if val else "-")
            while len(row_data) < 4:
                row_data.append("-")
            results.append(row_data[:4])

        return results

    # ==========================================================================
    # STORE SEARCH, INSTALLED APPS & PRESETS LOGIC
    # ==========================================================================
    def run_store_search(self):
        query = self.store_search_var.get().strip()
        if not query or query == self.store_placeholder:
            return

        self.log(f"Searching WinGet repository for '{query}'...")
        for item in self.store_tree.get_children():
            self.store_tree.delete(item)

        def _worker():
            try:
                res = subprocess.run(
                    [
                        "winget",
                        "search",
                        query,
                        "--source",
                        "winget",
                        "--accept-source-agreements",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )
                rows = self.parse_winget_table(res.stdout or "")
                self.after(0, lambda r=rows: self._render_tree(self.store_tree, r))
                self.log(f"Store search finished: {len(rows)} result(s) found.")
            except Exception as e:
                self.log(f"Search error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _render_tree(self, tree: ttk.Treeview, rows: list[list[str]]):
        for item in tree.get_children():
            tree.delete(item)
        for row in rows[:150]:
            tree.insert("", tk.END, values=tuple(row[:4]))

    def install_selected_store_app(self):
        sel = self.store_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No Package Selected",
                "Select a package from the Store Search results to install.",
                parent=self,
            )
            return
        vals = self.store_tree.item(sel[0], "values")
        if len(vals) >= 2 and vals[1] != "-":
            self.execute_action(["install", "--id", vals[1], "-e"])

    def refresh_installed(self):
        if self.is_loading_installed:
            return
        self.is_loading_installed = True
        self.log("Scanning installed applications via WinGet...")

        for item in self.installed_tree.get_children():
            self.installed_tree.delete(item)

        def _worker():
            try:
                res = subprocess.run(
                    ["winget", "list", "--accept-source-agreements"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )
                self.installed_cache = self.parse_winget_table(res.stdout or "")
            except Exception as e:
                self.log(f"Failed to scan installed apps: {e}")
                self.installed_cache = []
            finally:
                self.after(0, self._finish_loading_installed)

        threading.Thread(target=_worker, daemon=True).start()

    def _finish_loading_installed(self):
        self.is_loading_installed = False
        self.log(f"Installed scan complete: {len(self.installed_cache)} packages found.")
        self.filter_local_apps()

    def filter_local_apps(self):
        if self.is_loading_installed:
            return
        query = self.local_filter_var.get().strip().lower()
        if query == self.local_placeholder.lower():
            query = ""

        filtered = [
            app
            for app in self.installed_cache
            if not query or query in app[0].lower() or query in app[1].lower()
        ]
        self._render_tree(self.installed_tree, filtered)

    def uninstall_selected_local_apps_batch(self):
        sel = self.installed_tree.selection()
        if not sel:
            messagebox.showinfo(
                "No Apps Selected",
                "Select one or more installed applications from the table to uninstall.\n"
                "(Hold Ctrl or Shift to select multiple rows.)",
                parent=self,
            )
            return

        packages_to_remove = []
        for item_id in sel:
            vals = self.installed_tree.item(item_id, "values")
            if len(vals) >= 2 and vals[1] != "-":
                packages_to_remove.append((vals[0], vals[1]))

        if not packages_to_remove:
            return

        if not messagebox.askyesno(
            "Confirm Batch Uninstall",
            f"Uninstall {len(packages_to_remove)} selected application(s)?\n\n"
            + "\n".join(f"• {p[0]} ({p[1]})" for p in packages_to_remove[:10])
            + (f"\n...and {len(packages_to_remove) - 10} more" if len(packages_to_remove) > 10 else ""),
            parent=self,
        ):
            return

        self.log(f"Starting batch uninstallation of {len(packages_to_remove)} package(s)...")

        def _batch_uninstall():
            for name, app_id in packages_to_remove:
                self.log("-" * 44)
                self.log(f"Uninstalling: {name} ({app_id})")
                cmd = [
                    "winget",
                    "uninstall",
                    "--id",
                    app_id,
                    "--silent",
                    "--accept-source-agreements",
                ]
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=CREATE_NO_WINDOW,
                    )
                    if proc.stdout:
                        for line in proc.stdout:
                            if line.strip():
                                self.log(line.strip())
                    proc.wait()
                except Exception as e:
                    self.log(f"Failed to uninstall {app_id}: {e}")

            self.log("-" * 44)
            self.log("Batch uninstallation completed.")
            self.after(1000, self.refresh_installed)

        threading.Thread(target=_batch_uninstall, daemon=True).start()

    def export_installed_apps(self):
        """Bonus Feature: Exports the scanned installed applications list to JSON or CSV."""
        if not self.installed_cache:
            messagebox.showwarning(
                "No Data to Export",
                "Refresh or wait for the installed apps scan to finish first.",
                parent=self,
            )
            return

        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Installed Software Inventory",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile="Installed_Apps_Inventory.json",
        )
        if not file_path:
            return

        try:
            if file_path.lower().endswith(".csv"):
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Application Name", "Package ID", "Installed Version", "Update Available"])
                    for row in self.installed_cache:
                        writer.writerow(row[:4])
            else:
                data = [
                    {
                        "name": row[0],
                        "id": row[1],
                        "version": row[2],
                        "available_update": row[3],
                    }
                    for row in self.installed_cache
                ]
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

            messagebox.showinfo(
                "Export Successful",
                f"Successfully exported {len(self.installed_cache)} apps to:\n{file_path}",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export inventory:\n{e}", parent=self)

    def update_all_apps(self):
        self.log("Checking for WinGet package updates...")

        def _batch_process():
            try:
                res = subprocess.run(
                    [
                        "winget",
                        "upgrade",
                        "--include-unknown",
                        "--accept-source-agreements",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )
                upgrades = self.parse_winget_table(res.stdout or "")

                to_update = []
                for u in upgrades:
                    if len(u) > 1 and "Microsoft.AppInstaller" in u[1]:
                        self.log(f"Skipping {u[0]} (WinGet cannot self-update while running)")
                    elif len(u) > 1 and u[1] != "-":
                        to_update.append(u)

                if not to_update:
                    self.log("All WinGet-managed packages are up to date.")
                    return

                self.log(f"Found {len(to_update)} package(s) with available updates.")
                for app in to_update:
                    name, app_id = app[0], app[1]
                    self.log("-" * 44)
                    self.log(f"Upgrading: {name} ({app_id})")
                    cmd = [
                        "winget",
                        "upgrade",
                        "--id",
                        app_id,
                        "--silent",
                        "--accept-package-agreements",
                        "--accept-source-agreements",
                        "--include-unknown",
                    ]
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=CREATE_NO_WINDOW,
                    )
                    if proc.stdout:
                        for line in proc.stdout:
                            if line.strip():
                                self.log(line.strip())
                    proc.wait()

                self.log("-" * 44)
                self.log("Batch update completed.")
                self.after(1000, self.refresh_installed)
            except Exception as e:
                self.log(f"Batch Update Error: {e}")

        threading.Thread(target=_batch_process, daemon=True).start()

    def refresh_preset_ui(self):
        for widget in self.preset_grid_card.winfo_children():
            widget.destroy()
        self.preset_vars.clear()

        if not PRESET_APPS:
            tk.Label(
                self.preset_grid_card,
                text="No preset apps defined in config.py.",
                fg=FG_SECONDARY,
                bg=BG_CARD,
                font=FONT_BODY,
            ).pack(pady=20)
            return

        for idx, item in enumerate(PRESET_APPS):
            app_id = item if isinstance(item, str) else item.get("id", "")
            if not app_id:
                continue
            var = tk.BooleanVar(value=True)
            self.preset_vars[app_id] = var

            col = idx % 3
            row = idx // 3
            self.preset_grid_card.columnconfigure(col, weight=1)

            cb = tk.Checkbutton(
                self.preset_grid_card,
                text=app_id,
                variable=var,
                font=FONT_BODY,
                fg=FG_PRIMARY,
                bg=BG_CARD,
                selectcolor=BG_INPUT,
                activebackground=BG_CARD,
                activeforeground=FG_PRIMARY,
                bd=0,
                cursor="hand2",
            )
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=6)

    def install_selected_presets(self):
        selected_apps = [app_id for app_id, var in self.preset_vars.items() if var.get()]
        if not selected_apps:
            messagebox.showwarning(
                "Preset Apps",
                "Please select at least one preset application to install.",
                parent=self,
            )
            return

        self.log(f"Starting batch installation of {len(selected_apps)} preset package(s)...")

        def _batch_install():
            for app_id in selected_apps:
                self.log("-" * 44)
                self.log(f"Installing Preset: {app_id}")
                cmd = [
                    "winget",
                    "install",
                    "--id",
                    app_id,
                    "-e",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ]
                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        creationflags=CREATE_NO_WINDOW,
                    )
                    if proc.stdout:
                        for line in proc.stdout:
                            if line.strip():
                                self.log(line.strip())
                    proc.wait()
                except Exception as e:
                    self.log(f"Failed to install {app_id}: {e}")

            self.log("-" * 44)
            self.log("Preset batch installation completed.")
            self.after(1000, self.refresh_installed)

        threading.Thread(target=_batch_install, daemon=True).start()

    def execute_action(self, args: list[str]):
        def _worker():
            cmd_list = ["winget"] + args + ["--accept-source-agreements"]
            if "install" in args or "upgrade" in args:
                cmd_list.extend(["--accept-package-agreements", "--silent"])

            self.log(f"Running: {' '.join(cmd_list)}")
            try:
                proc = subprocess.Popen(
                    cmd_list,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )
                if proc.stdout:
                    for line in proc.stdout:
                        if line.strip():
                            self.log(line.strip())
                proc.wait()
                self.log(f"Finished (Exit Code: {proc.returncode}).")
            except Exception as e:
                self.log(f"Command Error: {e}")

            if "uninstall" in args or "upgrade" in args:
                self.after(1000, self.refresh_installed)

        threading.Thread(target=_worker, daemon=True).start()


# Compatibility aliases for main.py dynamic loading
WingetTab = WingetModule
Winget = WingetModule