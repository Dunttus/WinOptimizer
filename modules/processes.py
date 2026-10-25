import ctypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

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
    CRITICAL_PROCESS_NAMES,
    create_header,
    create_button,
)

PRIORITY_CLASSES = {
    "Low (Idle)": psutil.IDLE_PRIORITY_CLASS,
    "Below Normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
    "Normal": psutil.NORMAL_PRIORITY_CLASS,
    "Above Normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    "High": psutil.HIGH_PRIORITY_CLASS,
}

PRIORITY_LABELS = {
    psutil.IDLE_PRIORITY_CLASS: "Low (Idle)",
    psutil.BELOW_NORMAL_PRIORITY_CLASS: "Below Normal",
    psutil.NORMAL_PRIORITY_CLASS: "Normal",
    psutil.ABOVE_NORMAL_PRIORITY_CLASS: "Above Normal",
    psutil.HIGH_PRIORITY_CLASS: "High",
    psutil.REALTIME_PRIORITY_CLASS: "Realtime",
}

CRITICAL_LOWER = {name.lower() for name in CRITICAL_PROCESS_NAMES}


def is_admin() -> bool:
    """Checks if the script is running with administrative privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class ProcessesModule(tk.Frame):
    """Native Tkinter Process Priority Manager Module."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.placeholder_text = "Search process name or PID..."
        self.hide_system_var = tk.BooleanVar(value=True)

        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="Process Priority Manager",
            subtitle="Inspect and adjust CPU scheduling priorities for active foreground applications (games, IDEs, renderers).",
        )

        # --- Safety Guidelines Banner ---
        warning_card = tk.Frame(
            self,
            bg="#26191c",
            highlightbackground=THEME["danger"],
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        warning_card.pack(fill=tk.X, padx=24, pady=(0, 12))

        tk.Label(
            warning_card,
            text="⚠️ PROCESS PRIORITY GUIDELINES",
            fg=THEME["danger"],
            bg="#26191c",
            font=FONT_BOLD,
        ).pack(anchor="w", pady=(0, 4))

        guidelines = (
            "• Scope of Use: Modify priority only for active user applications (Games, CAD/Video Renderers, IDEs). Critical Windows processes are automatically locked.\n"
            "• Stability Risk: Setting heavy multi-threaded apps to 'High' can starve audio or input drivers, causing mouse stutter or audio dropouts.\n"
            "• Anti-Cheat Protection: Games protected by kernel anti-cheat (Vanguard, EAC, BattlEye) isolate their process handles and will reject priority changes."
        )
        tk.Label(
            warning_card,
            text=guidelines,
            fg=FG_PRIMARY,
            bg="#26191c",
            font=FONT_SMALL,
            justify="left",
            anchor="w",
        ).pack(fill=tk.X)

        # --- Search & Filter Bar ---
        ctrl_frame = tk.Frame(self, bg=BG_MAIN)
        ctrl_frame.pack(fill=tk.X, padx=24, pady=(0, 10))

        self.search_entry = tk.Entry(
            ctrl_frame,
            bg=BG_INPUT,
            fg=FG_SECONDARY,
            insertbackground=FG_PRIMARY,
            font=FONT_BODY,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            width=34,
        )
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=6)
        self.search_entry.insert(0, self.placeholder_text)
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)
        self.search_entry.bind("<Return>", lambda _e: self.refresh_list())
        self.search_entry.bind("<KeyRelease>", lambda _e: self.refresh_list())

        create_button(
            ctrl_frame,
            text="↻ Refresh List",
            command=self.refresh_list,
            variant="primary",
            pady=5,
        ).pack(side=tk.LEFT, padx=(0, 14))

        hide_sys_cb = tk.Checkbutton(
            ctrl_frame,
            text="Hide Protected System Processes",
            variable=self.hide_system_var,
            command=self.refresh_list,
            bg=BG_MAIN,
            fg=FG_SECONDARY,
            selectcolor=BG_INPUT,
            activebackground=BG_MAIN,
            activeforeground=FG_PRIMARY,
            font=FONT_SMALL,
            bd=0,
            cursor="hand2",
        )
        hide_sys_cb.pack(side=tk.LEFT, padx=(0, 14))

        self.status_lbl = tk.Label(
            ctrl_frame, text="", fg=FG_SECONDARY, bg=BG_MAIN, font=FONT_SMALL
        )
        self.status_lbl.pack(side=tk.RIGHT)

        # --- Priority Action Bar ---
        action_card = tk.Frame(
            self,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=8,
        )
        action_card.pack(fill=tk.X, padx=24, pady=(0, 10))

        tk.Label(
            action_card,
            text="Set Selected Process Priority:",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
        ).pack(side=tk.LEFT, padx=(0, 12))

        for label, prio_const in [
            ("High", psutil.HIGH_PRIORITY_CLASS),
            ("Above Normal", psutil.ABOVE_NORMAL_PRIORITY_CLASS),
            ("Normal", psutil.NORMAL_PRIORITY_CLASS),
            ("Below Normal", psutil.BELOW_NORMAL_PRIORITY_CLASS),
            ("Low (Idle)", psutil.IDLE_PRIORITY_CLASS),
        ]:
            variant = "primary" if label == "High" else "secondary"
            create_button(
                action_card,
                text=label,
                command=lambda p=prio_const, l=label: self.apply_selected_priority(p, l),
                variant=variant,
                padx=12,
                pady=4,
            ).pack(side=tk.LEFT, padx=4)

        # --- Process Treeview Table ---
        table_container = tk.Frame(
            self,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        table_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        scrollbar = ttk.Scrollbar(table_container, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Name", "PID", "Memory", "Priority", "Safety")
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            selectmode="browse",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.tree.yview)

        headers = [
            ("Name", "Process Name", 280, "w"),
            ("PID", "PID", 90, "e"),
            ("Memory", "Memory (RAM)", 120, "e"),
            ("Priority", "Current Priority", 140, "center"),
            ("Safety", "Status", 140, "center"),
        ]
        for col, text, width, anchor in headers:
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Row color tags
        self.tree.tag_configure("high", foreground=THEME["success"])
        self.tree.tag_configure("above", foreground=THEME["info"])
        self.tree.tag_configure("protected", foreground=FG_MUTED)

    # --------------------------------------------------------------------------
    # Search Entry Placeholder Handlers
    # --------------------------------------------------------------------------
    def _on_search_focus_in(self, _event):
        if self.search_entry.get() == self.placeholder_text:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=FG_PRIMARY)

    def _on_search_focus_out(self, _event):
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, self.placeholder_text)
            self.search_entry.config(fg=FG_SECONDARY)

    # --------------------------------------------------------------------------
    # Process Enumeration & Filtering
    # --------------------------------------------------------------------------
    @staticmethod
    def _is_protected_process(pid: int, name: str) -> bool:
        if pid <= 4:
            return True
        return name.lower() in CRITICAL_LOWER

    def refresh_list(self):
        search_text = self.search_entry.get().strip()
        if search_text == self.placeholder_text:
            search_text = ""
        search_text = search_text.lower()
        hide_protected = self.hide_system_var.get()

        self.status_lbl.config(text="Scanning processes...")
        threading.Thread(
            target=self._fetch_and_display,
            args=(search_text, hide_protected),
            daemon=True,
        ).start()

    def _fetch_and_display(self, search_text: str, hide_protected: bool):
        procs = []
        try:
            for p in psutil.process_iter(["pid", "name", "nice", "memory_info"]):
                try:
                    p_info = p.info
                    pid = p_info.get("pid", 0)
                    name = (p_info.get("name") or "").strip()
                    if not name:
                        continue

                    protected = self._is_protected_process(pid, name)
                    if hide_protected and protected:
                        continue

                    if search_text and (
                        search_text not in name.lower() and search_text not in str(pid)
                    ):
                        continue

                    mem_info = p_info.get("memory_info")
                    ram_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0

                    procs.append(
                        {
                            "pid": pid,
                            "name": name,
                            "nice": p_info.get("nice"),
                            "ram_mb": ram_mb,
                            "protected": protected,
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

        procs.sort(key=lambda x: (x["protected"], x["name"].lower(), x["pid"]))
        self.after(0, lambda: self._render_rows(procs))

    def _render_rows(self, procs: list[dict]):
        selected_pid = self._get_selected_pid()

        for item in self.tree.get_children():
            self.tree.delete(item)

        for p in procs:
            curr_nice = p["nice"]
            prio_name = PRIORITY_LABELS.get(curr_nice, "Normal")
            status_str = "Protected (Locked)" if p["protected"] else "Modifiable"

            tag = ""
            if p["protected"]:
                tag = "protected"
            elif curr_nice in (psutil.HIGH_PRIORITY_CLASS, psutil.REALTIME_PRIORITY_CLASS):
                tag = "high"
            elif curr_nice == psutil.ABOVE_NORMAL_PRIORITY_CLASS:
                tag = "above"

            item_id = self.tree.insert(
                "",
                tk.END,
                values=(
                    p["name"],
                    p["pid"],
                    f"{p['ram_mb']:,.1f} MB",
                    prio_name,
                    status_str,
                ),
                tags=(tag,) if tag else (),
            )
            if selected_pid is not None and p["pid"] == selected_pid:
                self.tree.selection_set(item_id)
                self.tree.see(item_id)

        self.status_lbl.config(text=f"Showing {len(procs):,} processes")

    def _get_selected_pid(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        if len(values) >= 2:
            try:
                return int(values[1])
            except ValueError:
                return None
        return None

    # --------------------------------------------------------------------------
    # Priority Modification
    # --------------------------------------------------------------------------
    def apply_selected_priority(self, prio_class: int, prio_label: str):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(
                "No Process Selected",
                "Please select a process from the table first.",
                parent=self,
            )
            return

        values = self.tree.item(sel[0], "values")
        name = values[0]
        pid = int(values[1])

        if self._is_protected_process(pid, name):
            messagebox.showwarning(
                "Protected System Process",
                f"'{name}' (PID: {pid}) is a critical Windows system process and cannot be modified.",
                parent=self,
            )
            return

        if not is_admin():
            messagebox.showwarning(
                "Administrator Required",
                "Changing process CPU priority requires Administrator privileges.\n"
                "Please elevate Wibe Suite using the sidebar badge.",
                parent=self,
            )
            return

        try:
            proc = psutil.Process(pid)
            proc.nice(prio_class)
            self.status_lbl.config(
                text=f"Updated '{name}' (PID {pid}) → {prio_label}",
                fg=THEME["success"],
            )
            self.refresh_list()
        except psutil.AccessDenied:
            messagebox.showerror(
                "Access Denied",
                f"Could not change priority for '{name}' (PID: {pid}).\n\n"
                "Possible causes:\n"
                "1. Protected system or service process.\n"
                "2. Kernel-level Anti-Cheat protection (Vanguard, EAC, BattlEye).",
                parent=self,
            )
        except psutil.NoSuchProcess:
            messagebox.showerror(
                "Process Exited",
                f"Process '{name}' (PID: {pid}) is no longer running.",
                parent=self,
            )
            self.refresh_list()
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to set priority for '{name}':\n{e}",
                parent=self,
            )


# Compatibility aliases for main.py dynamic routing
ProcessPriorityTab = ProcessesModule