import os
import re
import webbrowser
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
    create_header,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000

# Subgroup and Setting GUIDs for Screen & Sleep Timeouts
GUID_VIDEO_SUBGROUP = "7516b95f-f776-4464-8c53-06167f40cc99"
GUID_VIDEO_IDLE = "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e"

GUID_SLEEP_SUBGROUP = "238c9fa8-0aad-41ed-83f4-97be242c8f20"
GUID_SLEEP_IDLE = "29f6c1db-86da-48c5-9fdb-f2b67b1f44da"

UUID_PATTERN = re.compile(
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


class PowerModule(tk.Frame):
    """Native Tkinter Power Plans, Timeout Settings & Battery Report Module."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)

        # Time Mapping (Label -> Minutes)
        self.time_map = {
            "1 Minute": 1,
            "2 Minutes": 2,
            "3 Minutes": 3,
            "5 Minutes": 5,
            "10 Minutes": 10,
            "15 Minutes": 15,
            "20 Minutes": 20,
            "30 Minutes": 30,
            "45 Minutes": 45,
            "1 Hour": 60,
            "2 Hours": 120,
            "3 Hours": 180,
            "4 Hours": 240,
            "5 Hours": 300,
            "Never": 0,
        }
        self.reverse_time_map = {v: k for k, v in self.time_map.items()}
        self.time_labels = list(self.time_map.keys())
        self.radio_var = tk.StringVar(value="")

        self.init_ui()

        # Load current plans and timeouts asynchronously
        self.load_power_plans()
        self.fetch_current_timeouts()

    def init_ui(self):
        create_header(
            self,
            title="Power Settings",
            subtitle="Switch active Windows power plans, configure screen and sleep timeouts, and inspect battery health.",
        )

        content = tk.Frame(self, bg=BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        self._create_plans_ui(content)
        self._create_timeouts_ui(content)
        self._create_battery_report_ui(content)

    def _create_card(self, parent: tk.Widget) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=18,
            pady=14,
        )
        card.pack(fill=tk.X, pady=(0, 12))
        return card

    def _create_plans_ui(self, parent: tk.Widget):
        section = self._create_card(parent)

        header_row = tk.Frame(section, bg=BG_CARD)
        header_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            header_row,
            text="ACTIVE POWER PLAN",
            font=FONT_BOLD,
            fg=THEME["info"],
            bg=BG_CARD,
        ).pack(side=tk.LEFT)

        create_button(
            header_row,
            text="↻ Refresh Plans",
            command=self.load_power_plans,
            variant="secondary",
            padx=10,
            pady=4,
        ).pack(side=tk.RIGHT)

        self.plans_container = tk.Frame(section, bg=BG_CARD)
        self.plans_container.pack(fill=tk.X, pady=4)

    def _create_timeouts_ui(self, parent: tk.Widget):
        section = self._create_card(parent)

        tk.Label(
            section,
            text="TIMEOUT SETTINGS",
            font=FONT_BOLD,
            fg=THEME["info"],
            bg=BG_CARD,
        ).pack(anchor="w")

        tk.Label(
            section,
            text="Select duration of inactivity before turning off the display or putting the PC to sleep.",
            font=FONT_SMALL,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        ).pack(anchor="w", pady=(2, 12))

        grid = tk.Frame(section, bg=BG_CARD)
        grid.pack(fill=tk.X)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_columnconfigure(2, weight=1)

        # Column Headers
        tk.Label(grid, text="Setting", font=FONT_BOLD, fg=FG_SECONDARY, bg=BG_CARD, anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 20), pady=(0, 8)
        )
        tk.Label(grid, text="On Battery (DC)", font=FONT_BOLD, fg=THEME["warning"], bg=BG_CARD, anchor="w").grid(
            row=0, column=1, sticky="w", padx=8, pady=(0, 8)
        )
        tk.Label(grid, text="Plugged In (AC)", font=FONT_BOLD, fg=THEME["success"], bg=BG_CARD, anchor="w").grid(
            row=0, column=2, sticky="w", padx=8, pady=(0, 8)
        )

        # Row 1: Screen Off
        tk.Label(
            grid, text="Turn off screen after:", font=FONT_BODY, fg=FG_PRIMARY, bg=BG_CARD
        ).grid(row=1, column=0, sticky="w", padx=(0, 20), pady=6)

        self.screen_dc = ttk.Combobox(grid, values=self.time_labels, state="readonly")
        self.screen_dc.set("Loading...")
        self.screen_dc.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        self.screen_ac = ttk.Combobox(grid, values=self.time_labels, state="readonly")
        self.screen_ac.set("Loading...")
        self.screen_ac.grid(row=1, column=2, sticky="ew", padx=8, pady=6)

        # Row 2: Sleep
        tk.Label(
            grid, text="Put computer to sleep after:", font=FONT_BODY, fg=FG_PRIMARY, bg=BG_CARD
        ).grid(row=2, column=0, sticky="w", padx=(0, 20), pady=6)

        self.sleep_dc = ttk.Combobox(grid, values=self.time_labels, state="readonly")
        self.sleep_dc.set("Loading...")
        self.sleep_dc.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        self.sleep_ac = ttk.Combobox(grid, values=self.time_labels, state="readonly")
        self.sleep_ac.set("Loading...")
        self.sleep_ac.grid(row=2, column=2, sticky="ew", padx=8, pady=6)

        btn_row = tk.Frame(section, bg=BG_CARD)
        btn_row.pack(fill=tk.X, pady=(12, 0))

        create_button(
            btn_row,
            text="Apply Timeouts",
            command=self.apply_timeouts,
            variant="primary",
        ).pack(side=tk.LEFT)

    def _create_battery_report_ui(self, parent: tk.Widget):
        section = self._create_card(parent)

        tk.Label(
            section,
            text="BATTERY HEALTH REPORT",
            font=FONT_BOLD,
            fg=THEME["info"],
            bg=BG_CARD,
        ).pack(anchor="w")

        tk.Label(
            section,
            text="Generate an official Windows HTML battery health, wear level, and usage history report.",
            font=FONT_SMALL,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        ).pack(anchor="w", pady=(2, 12))

        create_button(
            section,
            text="Generate & Open Battery Report",
            command=self.generate_battery_report,
            variant="primary",
        ).pack(anchor="w")

    # --------------------------------------------------------------------------
    # Logic: Power Plans
    # --------------------------------------------------------------------------
    def load_power_plans(self):
        def _worker():
            try:
                output = subprocess.check_output(
                    ["powercfg", "/list"],
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                plans = []
                active_guid = ""

                for line in output.splitlines():
                    match = UUID_PATTERN.search(line)
                    if match:
                        guid = match.group(1)
                        is_active = line.strip().endswith("*")
                        # Extract plan name inside parentheses if present
                        name_match = re.search(r"\(([^)]+)\)", line[match.end():])
                        name = name_match.group(1).strip() if name_match else guid
                        plans.append((name, guid, is_active))
                        if is_active:
                            active_guid = guid

                self.after(0, lambda: self._render_power_plans(plans, active_guid))
            except Exception as e:
                self.after(0, lambda err=str(e): self._render_plan_error(err))

        threading.Thread(target=_worker, daemon=True).start()

    def _render_power_plans(self, plans: list[tuple[str, str, bool]], active_guid: str):
        for widget in self.plans_container.winfo_children():
            widget.destroy()

        if not plans:
            tk.Label(
                self.plans_container,
                text="No power plans found.",
                fg=FG_SECONDARY,
                bg=BG_CARD,
                font=FONT_BODY,
            ).pack(anchor="w")
            return

        self.radio_var.set(active_guid)

        for name, guid, is_active in plans:
            row = tk.Frame(
                self.plans_container,
                bg=BG_INPUT,
                highlightbackground=THEME["accent"] if is_active else BORDER_COLOR,
                highlightthickness=1,
                padx=12,
                pady=6,
            )
            row.pack(fill=tk.X, pady=3)

            rb = tk.Radiobutton(
                row,
                text=name,
                variable=self.radio_var,
                value=guid,
                command=lambda g=guid: self.set_active_plan(g),
                font=FONT_BOLD if is_active else FONT_BODY,
                fg=FG_PRIMARY,
                bg=BG_INPUT,
                selectcolor=BG_CARD,
                activebackground=BG_INPUT,
                activeforeground=FG_PRIMARY,
                bd=0,
                cursor="hand2",
            )
            rb.pack(side=tk.LEFT)

            if is_active:
                tk.Label(
                    row,
                    text="● Active Plan",
                    fg=THEME["success"],
                    bg=BG_INPUT,
                    font=FONT_SMALL,
                ).pack(side=tk.RIGHT)

    def _render_plan_error(self, err_msg: str):
        for widget in self.plans_container.winfo_children():
            widget.destroy()
        tk.Label(
            self.plans_container,
            text=f"Error loading power plans: {err_msg}",
            fg=THEME["danger"],
            bg=BG_CARD,
            font=FONT_BODY,
        ).pack(anchor="w")

    def set_active_plan(self, guid: str):
        def _worker():
            try:
                subprocess.run(
                    ["powercfg", "/setactive", guid],
                    check=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                self.load_power_plans()
                self.fetch_current_timeouts()
            except Exception as e:
                self.after(
                    0,
                    lambda err=str(e): messagebox.showerror(
                        "Power Plan Error",
                        f"Failed to activate selected power plan:\n{err}",
                        parent=self,
                    ),
                )

        threading.Thread(target=_worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # Logic: Detect & Apply Timeouts (Locale-Independent)
    # --------------------------------------------------------------------------
    @staticmethod
    def _parse_ac_dc_minutes(query_output: str, default_ac: int, default_dc: int) -> tuple[int, int]:
        """Extracts AC and DC timeout minutes from `powercfg /q` output regardless of Windows language."""
        hex_matches = re.findall(r"0x[0-9a-fA-F]{8}", query_output)
        if len(hex_matches) >= 2:
            ac_seconds = int(hex_matches[-2], 16)
            dc_seconds = int(hex_matches[-1], 16)
            return ac_seconds // 60, dc_seconds // 60
        return default_ac, default_dc

    def fetch_current_timeouts(self):
        def _worker():
            try:
                out_scr = subprocess.check_output(
                    ["powercfg", "/q", "SCHEME_CURRENT", GUID_VIDEO_SUBGROUP, GUID_VIDEO_IDLE],
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                scr_ac, scr_dc = self._parse_ac_dc_minutes(out_scr, 10, 5)

                out_slp = subprocess.check_output(
                    ["powercfg", "/q", "SCHEME_CURRENT", GUID_SLEEP_SUBGROUP, GUID_SLEEP_IDLE],
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                slp_ac, slp_dc = self._parse_ac_dc_minutes(out_slp, 30, 15)

                self.after(0, lambda: self._update_combos(scr_ac, scr_dc, slp_ac, slp_dc))
            except Exception:
                self.after(0, lambda: self._update_combos(10, 5, 30, 15))

        threading.Thread(target=_worker, daemon=True).start()

    def _update_combos(self, s_ac: int, s_dc: int, sl_ac: int, sl_dc: int):
        def get_lbl(m: int) -> str:
            if m <= 0:
                return "Never"
            if m in self.reverse_time_map:
                return self.reverse_time_map[m]
            return f"{m} Minutes"

        self.screen_ac.set(get_lbl(s_ac))
        self.screen_dc.set(get_lbl(s_dc))
        self.sleep_ac.set(get_lbl(sl_ac))
        self.sleep_dc.set(get_lbl(sl_dc))

    def _parse_minutes_label(self, label: str, fallback: int = 10) -> int:
        if label in self.time_map:
            return self.time_map[label]
        if label.strip().lower() == "never":
            return 0
        m = re.search(r"(\d+)", label)
        if m:
            return int(m.group(1))
        return fallback

    def apply_timeouts(self):
        m_screen_ac = self._parse_minutes_label(self.screen_ac.get(), 10)
        m_screen_dc = self._parse_minutes_label(self.screen_dc.get(), 5)
        m_sleep_ac = self._parse_minutes_label(self.sleep_ac.get(), 30)
        m_sleep_dc = self._parse_minutes_label(self.sleep_dc.get(), 15)

        def _worker():
            try:
                cmds = [
                    ["powercfg", "/change", "monitor-timeout-ac", str(m_screen_ac)],
                    ["powercfg", "/change", "monitor-timeout-dc", str(m_screen_dc)],
                    ["powercfg", "/change", "standby-timeout-ac", str(m_sleep_ac)],
                    ["powercfg", "/change", "standby-timeout-dc", str(m_sleep_dc)],
                ]
                for cmd in cmds:
                    subprocess.run(cmd, check=True, creationflags=CREATE_NO_WINDOW)

                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "Timeouts Updated",
                        "Screen and sleep timeouts applied to the active power plan.",
                        parent=self,
                    ),
                )
            except Exception as e:
                self.after(
                    0,
                    lambda err=str(e): messagebox.showerror(
                        "Error Applying Timeouts",
                        f"Could not apply timeout settings:\n{err}",
                        parent=self,
                    ),
                )

        threading.Thread(target=_worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # Logic: Battery Health Report
    # --------------------------------------------------------------------------
    def generate_battery_report(self):
        def _worker():
            try:
                report_path = os.path.join(os.path.expanduser("~"), "battery-report.html")
                result = subprocess.run(
                    ["powercfg", "/batteryreport", "/output", report_path],
                    capture_output=True,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )

                if result.returncode == 0 and os.path.exists(report_path):
                    self.after(0, lambda: self._prompt_open_battery_report(report_path))
                else:
                    err_msg = (
                        result.stderr.strip()
                        if result.stderr and result.stderr.strip()
                        else result.stdout.strip() or "No supported system battery detected on this PC."
                    )
                    self.after(
                        0,
                        lambda msg=err_msg: messagebox.showwarning(
                            "Battery Report Unavailable",
                            f"Could not generate battery report:\n{msg}",
                            parent=self,
                        ),
                    )
            except Exception as e:
                self.after(
                    0,
                    lambda err=str(e): messagebox.showerror(
                        "Error",
                        f"An unexpected error occurred:\n{err}",
                        parent=self,
                    ),
                )

        threading.Thread(target=_worker, daemon=True).start()

    def _prompt_open_battery_report(self, report_path: str):
        if messagebox.askyesno(
            "Battery Report Ready",
            f"Battery report generated successfully at:\n{report_path}\n\nOpen it in your web browser now?",
            parent=self,
        ):
            try:
                os.startfile(report_path)
            except AttributeError:
                webbrowser.open(report_path)


# Compatibility aliases for main.py dynamic loading
PowerTab = PowerModule
Power = PowerModule
PowerSettingsTab = PowerModule