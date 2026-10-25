import os
import winreg
import ctypes
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    THEME,
    BG_MAIN,
    BG_CARD,
    BG_INPUT,
    FG_PRIMARY,
    FG_SECONDARY,
    BORDER_COLOR,
    FONT_BODY,
    FONT_BOLD,
    FONT_SMALL,
    create_header,
    create_button,
)


def is_admin() -> bool:
    """Checks if the script is running with administrative privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class StartupModule(tk.Frame):
    """Native Tkinter Startup Manager Module (Registry Run Keys & Startup Folders)."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.startup_entries: dict[str, dict] = {}

        self.init_ui()
        self.load_startup_items()

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="Startup Manager",
            subtitle="Inspect and remove applications configured to launch automatically when Windows starts.",
        )

        # --- Top Action Bar ---
        ctrl_frame = tk.Frame(self, bg=BG_MAIN)
        ctrl_frame.pack(fill=tk.X, padx=24, pady=(0, 10))

        create_button(
            ctrl_frame,
            text="↻ Refresh List",
            command=self.load_startup_items,
            variant="primary",
            pady=5,
        ).pack(side=tk.LEFT, padx=(0, 10))

        create_button(
            ctrl_frame,
            text="Open User Startup Folder",
            command=self.open_user_startup_folder,
            variant="secondary",
            pady=5,
        ).pack(side=tk.LEFT, padx=(0, 10))

        create_button(
            ctrl_frame,
            text="Remove Selected Item",
            command=self.remove_selected_item,
            variant="danger",
            pady=5,
        ).pack(side=tk.RIGHT)

        self.status_lbl = tk.Label(
            ctrl_frame,
            text="",
            fg=FG_SECONDARY,
            bg=BG_MAIN,
            font=FONT_SMALL,
        )
        self.status_lbl.pack(side=tk.LEFT, padx=8)

        # --- Startup Items Treeview Table ---
        table_container = tk.Frame(
            self,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        table_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        scrollbar = ttk.Scrollbar(table_container, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Name", "Scope", "Command")
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.tree.yview)

        headers = [
            ("Name", "Application / Entry Name", 230, "w"),
            ("Scope", "Startup Location", 180, "w"),
            ("Command", "Target Path / Command", 480, "w"),
        ]
        for col, text, width, anchor in headers:
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree.tag_configure("user", foreground=FG_PRIMARY)
        self.tree.tag_configure("system", foreground=THEME["info"])

    # --------------------------------------------------------------------------
    # Enumeration Logic (Registry + Startup Folders)
    # --------------------------------------------------------------------------
    def load_startup_items(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.startup_entries.clear()

        reg_locations = [
            (
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                "Registry (Current User)",
                winreg.KEY_READ,
                False,
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                "Registry (System 64-bit)",
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                True,
            ),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                "Registry (System 32-bit)",
                winreg.KEY_READ | winreg.KEY_WOW64_32KEY,
                True,
            ),
        ]

        # 1. Scan Registry Run Keys
        for hkey, reg_path, scope_label, access_mask, needs_admin in reg_locations:
            try:
                with winreg.OpenKey(hkey, reg_path, 0, access_mask) as key:
                    idx = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, idx)
                            self._insert_entry(
                                name=name,
                                scope=scope_label,
                                command=str(value),
                                meta={
                                    "kind": "registry",
                                    "name": name,
                                    "hkey": hkey,
                                    "reg_path": reg_path,
                                    "write_mask": (
                                        winreg.KEY_SET_VALUE | (access_mask & (winreg.KEY_WOW64_64KEY | winreg.KEY_WOW64_32KEY))
                                    ),
                                    "needs_admin": needs_admin,
                                },
                            )
                            idx += 1
                        except OSError:
                            break
            except (PermissionError, FileNotFoundError):
                pass

        # 2. Scan Windows Startup Folders
        appdata = os.environ.get("APPDATA", "")
        progdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        folder_locations = [
            (
                os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup"),
                "Startup Folder (User)",
                False,
            ),
            (
                os.path.join(progdata, r"Microsoft\Windows\Start Menu\Programs\Startup"),
                "Startup Folder (All Users)",
                True,
            ),
        ]

        for folder_path, scope_label, needs_admin in folder_locations:
            if folder_path and os.path.isdir(folder_path):
                try:
                    for fname in sorted(os.listdir(folder_path)):
                        if fname.lower() == "desktop.ini":
                            continue
                        full_path = os.path.join(folder_path, fname)
                        if os.path.isfile(full_path):
                            self._insert_entry(
                                name=fname,
                                scope=scope_label,
                                command=full_path,
                                meta={
                                    "kind": "file",
                                    "name": fname,
                                    "filepath": full_path,
                                    "needs_admin": needs_admin,
                                },
                            )
                except OSError:
                    pass

        count = len(self.startup_entries)
        self.status_lbl.config(text=f"Found {count} startup item{'s' if count != 1 else ''}")

    def _insert_entry(self, name: str, scope: str, command: str, meta: dict):
        tag = "system" if meta.get("needs_admin") else "user"
        item_id = self.tree.insert(
            "",
            tk.END,
            values=(name, scope, command),
            tags=(tag,),
        )
        self.startup_entries[item_id] = meta

    # --------------------------------------------------------------------------
    # Actions
    # --------------------------------------------------------------------------
    def open_user_startup_folder(self):
        appdata = os.environ.get("APPDATA", "")
        folder = os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
        if os.path.isdir(folder):
            subprocess.Popen(["explorer.exe", folder])
        else:
            messagebox.showwarning("Not Found", f"Startup folder not found:\n{folder}", parent=self)

    def remove_selected_item(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(
                "No Selection",
                "Please select a startup item from the table to remove.",
                parent=self,
            )
            return

        item_id = sel[0]
        meta = self.startup_entries.get(item_id)
        if not meta:
            return

        name = meta["name"]
        if meta.get("needs_admin") and not is_admin():
            messagebox.showerror(
                "Permission Error",
                f"Administrator privileges are required to remove system-wide startup item '{name}'.\n\n"
                "Click the 'Elevate to Admin' badge in the sidebar to restart with Administrator rights.",
                parent=self,
            )
            return

        if not messagebox.askyesno(
            "Confirm Startup Removal",
            f"Are you sure you want to stop '{name}' from starting automatically with Windows?\n\n"
            "This will permanently delete the startup entry.",
            parent=self,
        ):
            return

        try:
            if meta["kind"] == "registry":
                with winreg.OpenKey(
                    meta["hkey"], meta["reg_path"], 0, meta["write_mask"]
                ) as key:
                    winreg.DeleteValue(key, name)
            elif meta["kind"] == "file":
                os.remove(meta["filepath"])

            self.load_startup_items()
            messagebox.showinfo("Removed", f"Successfully removed '{name}' from startup.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not remove startup item '{name}':\n{e}", parent=self)


# Compatibility alias for main.py dynamic routing
StartupManagerTab = StartupModule