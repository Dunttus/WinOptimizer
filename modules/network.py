import os
import subprocess
import threading
import webbrowser
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


class NetworkModule(tk.Frame):
    """Native Tkinter Network Diagnostics & Reset Tools Module."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.is_running = False
        self.action_buttons: list[tuple[tk.Button, str]] = []

        self.init_ui()

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="Network Tools",
            subtitle="Run common Windows network diagnostics, latency checks, and stack reset commands.",
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
            text="Network Diagnostics & Reset Actions",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
        ).pack(anchor="w", pady=(0, 8))

        tools_list = tk.Frame(tools_card, bg=BG_CARD)
        tools_list.pack(fill=tk.X)

        # 1. Flush DNS
        self.create_tool_row(
            tools_list,
            title="Flush DNS",
            desc="Clears the Windows DNS resolver cache to fix stale domain or connection issues.",
            command=lambda: self.run_cmd(
                ["ipconfig", "/flushdns"], "Flushing DNS Resolver Cache..."
            ),
            variant="primary",
        )

        # 2. Renew IP
        self.create_tool_row(
            tools_list,
            title="Renew IP",
            desc="Requests a fresh IPv4/IPv6 lease from the DHCP server (may briefly drop connection).",
            command=lambda: self.run_cmd(
                ["ipconfig", "/renew"], "Renewing DHCP IP Address..."
            ),
            variant="primary",
        )

        # 3. Ping Test
        self.create_tool_row(
            tools_list,
            title="Ping Google",
            desc="Checks external internet reachability and measures round-trip latency to google.com.",
            command=lambda: self.run_cmd(
                ["ping", "-n", "4", "google.com"], "Pinging google.com (4 packets)..."
            ),
            variant="primary",
        )

        # 4. WLAN Report
        self.create_tool_row(
            tools_list,
            title="WLAN Report",
            desc="Generates a detailed Windows wireless connectivity HTML report (requires Administrator).",
            command=self.generate_wlan_report,
            variant="secondary",
        )

        # 5. Reset Winsock
        self.create_tool_row(
            tools_list,
            title="Reset Winsock",
            desc="Resets the Winsock Catalog to a clean default state. Requires a system restart.",
            command=self.reset_winsock,
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
            width=15,
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
    # Thread-Safe Logging & State Management
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
            "secondary": ( THEME["bg_card_hover"], FG_PRIMARY),
        }
        for btn, variant in self.action_buttons:
            if busy:
                btn.configure(state="disabled", bg=BG_CARD, fg=FG_MUTED)
            else:
                bg_col, fg_col = palette.get(variant, palette["primary"])
                btn.configure(state="normal", bg=bg_col, fg=fg_col)

    # --------------------------------------------------------------------------
    # Command Execution Logic
    # --------------------------------------------------------------------------
    def _execute_process(self, cmd_args: list[str], status_msg: str) -> int:
        """Runs a command synchronously inside the current worker thread and logs output."""
        cmd_str = " ".join(cmd_args)
        self.log(f"\n=== {status_msg} ===", "heading")
        self.log(f"> {cmd_str}", "cmd")

        try:
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
            )
            if result.stdout and result.stdout.strip():
                self.log(result.stdout.strip())
            if result.stderr and result.stderr.strip():
                self.log(f"ERROR: {result.stderr.strip()}", "err")
            self.log("-" * 48, "muted")
            return result.returncode
        except Exception as e:
            self.log(f"Execution Error: {e}", "err")
            return -1

    def run_cmd(self, cmd_args: list[str], status_msg: str):
        """Runs a diagnostic command in a background thread."""
        if self.is_running:
            return
        self._set_busy(True, status_msg)

        def _worker():
            try:
                self._execute_process(cmd_args, status_msg)
            finally:
                self._set_busy(False, "Idle")

        threading.Thread(target=_worker, daemon=True).start()

    def reset_winsock(self):
        """Resets Winsock catalog and prompts for restart only after completion."""
        if self.is_running:
            return

        if not messagebox.askyesno(
            "Confirm Winsock Reset",
            "This command (netsh winsock reset) resets your network socket catalog and requires a computer restart to take effect.\n\nProceed?",
            parent=self,
        ):
            return

        self._set_busy(True, "Resetting Winsock Catalog...")

        def _worker():
            try:
                rc = self._execute_process(
                    ["netsh", "winsock", "reset"], "Resetting Winsock Catalog..."
                )
                if rc == 0:
                    self.after(
                        0,
                        lambda: messagebox.showwarning(
                            "Restart Required",
                            "Winsock reset completed successfully.\n\nPlease restart your computer to apply changes.",
                            parent=self,
                        ),
                    )
                else:
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            "Reset Failed",
                            "Winsock reset failed. Ensure Wibe Suite is running as Administrator.",
                            parent=self,
                        ),
                    )
            finally:
                self._set_busy(False, "Idle")

        threading.Thread(target=_worker, daemon=True).start()

    def generate_wlan_report(self):
        """Generates an HTML WLAN diagnostic report and offers to open it on the main thread."""
        if self.is_running:
            return

        self._set_busy(True, "Generating WLAN Report...")

        def _worker():
            try:
                self.log("\n=== Generating WLAN Report ===", "heading")
                self.log("> netsh wlan show wlanreport", "cmd")
                self.log("Collecting wireless events (this may take 15–45 seconds)...", "muted")

                report_path = r"C:\ProgramData\Microsoft\Windows\WlanReport\wlan-report-latest.html"

                if os.path.exists(report_path):
                    try:
                        os.remove(report_path)
                    except OSError:
                        self.log("(Note: Could not remove previous cached report file)", "muted")

                result = subprocess.run(
                    ["netsh", "wlan", "show", "wlanreport"],
                    capture_output=True,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                if result.stdout and result.stdout.strip():
                    self.log(result.stdout.strip())
                if result.stderr and result.stderr.strip():
                    self.log(result.stderr.strip(), "err")

                if os.path.exists(report_path):
                    self.log(f"SUCCESS: Report saved to {report_path}")
                    self.after(0, lambda: self._prompt_open_report(report_path))
                else:
                    self.log("ERROR: Report file was not created.", "err")
                    self.log(
                        "Possible causes: No Wi-Fi adapter present, or not running as Administrator.",
                        "muted",
                    )
            except Exception as e:
                self.log(f"Error generating WLAN report: {e}", "err")
            finally:
                self._set_busy(False, "Idle")

        threading.Thread(target=_worker, daemon=True).start()

    def _prompt_open_report(self, report_path: str):
        if messagebox.askyesno(
            "WLAN Report Ready",
            f"WLAN Report generated successfully:\n{report_path}\n\nOpen it now in your browser?",
            parent=self,
        ):
            try:
                os.startfile(report_path)
            except AttributeError:
                webbrowser.open(report_path)


# Compatibility alias for main.py dynamic routing
NetworkToolsTab = NetworkModule