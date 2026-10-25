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
    FONT_MONO,
    create_header,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000


class RepairModule(tk.Frame):
    """Native Tkinter Windows System File & Disk Repair Module."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.is_running = False
        self.action_buttons: list[tuple[tk.Button, str]] = []

        self.init_ui()

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="Windows Repair Tools",
            subtitle="Execute built-in Windows servicing utilities (SFC, DISM, CHKDSK) to repair corrupted system files and disk errors.",
        )

        # --- Tools Card Container ---
        tools_card = tk.Frame(
            self,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        tools_card.pack(fill=tk.X, padx=24, pady=(0, 12))

        tk.Label(
            tools_card,
            text="System Integrity & Disk Maintenance Commands",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
        ).pack(anchor="w", pady=(0, 8))

        tools_list = tk.Frame(tools_card, bg=BG_CARD)
        tools_list.pack(fill=tk.X)

        # 1. System File Checker (SFC)
        self.create_tool_row(
            tools_list,
            title="SFC Scan",
            desc="Scans the integrity of all protected Windows system files and replaces corrupted versions (sfc /scannow).",
            command=self.run_sfc,
            variant="primary",
        )

        # 2. DISM ScanHealth
        self.create_tool_row(
            tools_list,
            title="DISM Check",
            desc="Scans the Windows component store (WinSxS) for image corruption without modifying files.",
            command=self.run_dism_scan,
            variant="primary",
        )

        # 3. DISM RestoreHealth
        self.create_tool_row(
            tools_list,
            title="DISM Repair",
            desc="Downloads clean replacement components from Windows Update to repair a corrupted system image.",
            command=self.run_dism_restore,
            variant="primary",
        )

        # 4. Check Disk (CHKDSK)
        self.create_tool_row(
            tools_list,
            title="Check Disk (C:)",
            desc="Schedules a full file system and sector repair on drive C: for the next system restart.",
            command=self.schedule_chkdsk,
            variant="danger",
        )

        # --- Terminal Header Bar ---
        term_ctrl_frame = tk.Frame(self, bg=BG_MAIN)
        term_ctrl_frame.pack(fill=tk.X, padx=24, pady=(4, 6))

        tk.Label(
            term_ctrl_frame,
            text="Terminal Output",
            fg=FG_PRIMARY,
            bg=BG_MAIN,
            font=FONT_BOLD,
        ).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            term_ctrl_frame,
            text="Idle",
            fg=FG_SECONDARY,
            bg=BG_MAIN,
            font=FONT_BODY,
        )
        self.status_lbl.pack(side=tk.LEFT, padx=(12, 0))

        create_button(
            term_ctrl_frame,
            text="Clear Terminal",
            command=self.clear_terminal,
            variant="secondary",
            padx=12,
            pady=4,
        ).pack(side=tk.RIGHT)

        # --- Terminal Output Window ---
        term_container = tk.Frame(
            self,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        term_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        term_scrollbar = ttk.Scrollbar(term_container, orient="vertical")
        term_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.terminal = tk.Text(
            term_container,
            font=FONT_MONO,
            fg=THEME["success"],
            bg=BG_INPUT,
            insertbackground=FG_PRIMARY,
            bd=0,
            padx=14,
            pady=12,
            highlightthickness=0,
            yscrollcommand=term_scrollbar.set,
            state="disabled",
        )
        self.terminal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        term_scrollbar.config(command=self.terminal.yview)

        self.terminal.tag_config("heading", foreground=THEME["info"], font=(FONT_MONO[0], 10, "bold"))
        self.terminal.tag_config("cmd", foreground=FG_PRIMARY)
        self.terminal.tag_config("warn", foreground=THEME["warning"])
        self.terminal.tag_config("err", foreground=THEME["danger"])
        self.terminal.tag_config("muted", foreground=FG_SECONDARY)

    def create_tool_row(
        self, parent: tk.Frame, title: str, desc: str, command, variant: str = "primary"
    ):
        row = tk.Frame(
            parent,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=10,
            pady=8,
        )
        row.pack(fill=tk.X, pady=4)

        btn = create_button(
            row,
            text=title,
            command=command,
            variant=variant,
            width=16,
            pady=5,
        )
        btn.pack(side=tk.LEFT, padx=(0, 14))
        self.action_buttons.append((btn, variant))

        tk.Label(
            row,
            text=desc,
            font=FONT_BODY,
            fg=FG_SECONDARY,
            bg=BG_INPUT,
            anchor="w",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --------------------------------------------------------------------------
    # Thread-Safe Logging & Button Lock
    # --------------------------------------------------------------------------
    def log(self, text: str, tag: str = ""):
        """Appends text to the terminal window safely from any thread."""
        if threading.current_thread() is not threading.main_thread():
            self.after(0, self.log, text, tag)
            return

        self.terminal.configure(state="normal")
        if tag:
            self.terminal.insert("end", text + "\n", tag)
        else:
            self.terminal.insert("end", text + "\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")

    def _set_busy(self, busy: bool, status_text: str = "Idle"):
        if threading.current_thread() is not threading.main_thread():
            self.after(0, self._set_busy, busy, status_text)
            return

        self.is_running = busy
        self.status_lbl.configure(
            text=status_text,
            fg=THEME["info"] if busy else FG_SECONDARY,
        )
        palette = {
            "primary": (THEME["accent"], "#ffffff"),
            "danger": (THEME["danger"], "#ffffff"),
            "secondary": (THEME["bg_card_hover"], FG_PRIMARY),
        }
        for btn, variant in self.action_buttons:
            if busy:
                btn.configure(state="disabled", bg=BG_CARD, fg=FG_MUTED)
            else:
                bg_col, fg_col = palette.get(variant, palette["primary"])
                btn.configure(state="normal", bg=bg_col, fg=fg_col)

    # --------------------------------------------------------------------------
    # Subprocess Streaming Engine
    # --------------------------------------------------------------------------
    def run_process_stream(self, cmd_args: list[str], title: str):
        """Streams command output line-by-line while stripping UTF-16 null bytes."""
        if self.is_running:
            return

        self._set_busy(True, f"Running {title}...")

        def _worker():
            cmd_str = " ".join(cmd_args)
            self.log(f"\n=== Starting {title} ===", "heading")
            self.log(f"> {cmd_str}", "cmd")
            self.log("Operation in progress. This may take several minutes...\n", "muted")

            try:
                process = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=CREATE_NO_WINDOW,
                )

                if process.stdout:
                    for raw_line in process.stdout:
                        # Clean UTF-16LE null bytes emitted by Windows sfc.exe
                        clean_line = raw_line.replace("\x00", "").strip()
                        if clean_line:
                            self.log(clean_line)

                process.wait()

                if process.returncode == 0:
                    self.log(f"\n=== {title} Completed Successfully ===", "heading")
                else:
                    self.log(
                        f"\n=== {title} Finished (Exit Code: {process.returncode}) ===",
                        "warn",
                    )
            except Exception as e:
                self.log(f"Execution Error: {e}", "err")
            finally:
                self._set_busy(False, "Idle")

        threading.Thread(target=_worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # Repair Actions
    # --------------------------------------------------------------------------
    def run_sfc(self):
        self.run_process_stream(["sfc", "/scannow"], "System File Checker (SFC)")

    def run_dism_scan(self):
        self.run_process_stream(
            ["DISM", "/Online", "/Cleanup-Image", "/ScanHealth"],
            "DISM Image Health Scan",
        )

    def run_dism_restore(self):
        if self.is_running:
            return

        if messagebox.askyesno(
            "Confirm DISM Repair",
            "DISM RestoreHealth will download fresh system files from Windows Update.\n\n"
            "This may take 10–20 minutes depending on your internet connection.\n\nContinue?",
            parent=self,
        ):
            self.run_process_stream(
                ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"],
                "DISM Image RestoreHealth",
            )

    def schedule_chkdsk(self):
        if self.is_running:
            return

        if not messagebox.askyesno(
            "Schedule Check Disk (C:)",
            "Check Disk cannot lock the system drive while Windows is running.\n\n"
            "Do you want to schedule a full disk check (chkdsk C: /f /r) for the NEXT system restart?",
            parent=self,
        ):
            return

        self._set_busy(True, "Scheduling Check Disk...")

        def _worker():
            self.log("\n=== Scheduling Check Disk (C:) ===", "heading")
            self.log("> chkdsk C: /f /r (Auto-confirm: Y)", "cmd")

            try:
                result = subprocess.run(
                    ["chkdsk", "C:", "/f", "/r"],
                    input="Y\n",
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )

                output = (result.stdout or "").replace("\x00", "").strip()
                err_out = (result.stderr or "").replace("\x00", "").strip()

                if output:
                    self.log(output)
                if err_out:
                    self.log(err_out, "err")

                # chkdsk returns 0 or 3 when scheduling on a locked boot volume
                if result.returncode in (0, 3) and output:
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            "Check Disk Scheduled",
                            "Disk Check has been processed for drive C:.\n\n"
                            "Please restart your computer to begin the scan.",
                            parent=self,
                        ),
                    )
                else:
                    self.log(
                        "WARNING: Could not verify CHKDSK schedule. Ensure Wibe Suite is running as Administrator.",
                        "warn",
                    )
            except Exception as e:
                self.log(f"Error scheduling CHKDSK: {e}", "err")
            finally:
                self._set_busy(False, "Idle")

        threading.Thread(target=_worker, daemon=True).start()


# Compatibility aliases for main.py dynamic routing
RepairTab = RepairModule
WindowsRepairTab = RepairModule