import os
import webbrowser
import subprocess
import threading
import re
import customtkinter as ctk
from tkinter import messagebox

class PowerModule(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, fg_color="#1c1c1c", *args, **kwargs)
        self.pack(fill="both", expand=True)
        
        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header_frame, text="Power Management", font=("Segoe UI", 18, "bold"), text_color="#ffffff").pack(anchor="w")
        ctk.CTkLabel(header_frame, text="Optimize performance, manage timeouts, and view battery diagnostics.", font=("Segoe UI", 10), text_color="#888888").pack(anchor="w")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=5)

        # Time Mapping (Label -> Minutes)
        self.time_map = {
            "1 Minute": 1, "2 Minutes": 2, "3 Minutes": 3, "5 Minutes": 5,
            "10 Minutes": 10, "15 Minutes": 15, "20 Minutes": 20, "30 Minutes": 30,
            "45 Minutes": 45, "1 Hour": 60, "2 Hours": 120, "3 Hours": 180,
            "4 Hours": 240, "5 Hours": 300, "Never": 0
        }
        # Reverse map for detecting settings (Minutes -> Label)
        self.reverse_time_map = {v: k for k, v in self.time_map.items()}
        self.time_labels = list(self.time_map.keys())

        # --- SECTIONS ---
        self._create_plans_ui()
        self._create_timeouts_ui()
        self._create_battery_report_ui()
        
        # Auto-detect current settings on load
        self.fetch_current_timeouts()

    def _create_plans_ui(self):
        section = ctk.CTkFrame(self.scroll, fg_color="#222222", corner_radius=8)
        section.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(section, text="ACTIVE POWER PLAN", font=("Segoe UI", 12, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(15, 10))
        
        self.plans_container = ctk.CTkFrame(section, fg_color="transparent")
        self.plans_container.pack(fill="x", padx=15, pady=5)
        
        # Refresh Button
        ctk.CTkButton(section, text="Refresh Plans", height=30, fg_color="#333333", hover_color="#444444",
                      command=self.load_power_plans).pack(anchor="w", padx=15, pady=15)

        self.load_power_plans()

    def _create_timeouts_ui(self):
        section = ctk.CTkFrame(self.scroll, fg_color="#222222", corner_radius=8)
        section.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(section, text="TIMEOUT SETTINGS", font=("Segoe UI", 12, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(section, text="Select duration before turning off screen or sleeping.", font=("Segoe UI", 10), text_color="#888888").pack(anchor="w", padx=15)

        # Grid for controls
        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=15)
        grid.grid_columnconfigure((0, 1), weight=1)

        # --- Headers ---
        ctk.CTkLabel(grid, text="ON BATTERY", font=("Segoe UI", 11, "bold"), text_color="#FFA726").grid(row=0, column=0, pady=10)
        ctk.CTkLabel(grid, text="PLUGGED IN", font=("Segoe UI", 11, "bold"), text_color="#00E676").grid(row=0, column=1, pady=10)

        # --- Screen Off ---
        ctk.CTkLabel(grid, text="Turn off screen after:", font=("Segoe UI", 10), text_color="#888888").grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        self.screen_dc = ctk.CTkComboBox(grid, values=self.time_labels, fg_color="#111111", border_color="#333333", button_color="#3B8ED0")
        self.screen_dc.set("...") 
        self.screen_dc.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.screen_ac = ctk.CTkComboBox(grid, values=self.time_labels, fg_color="#111111", border_color="#333333", button_color="#3B8ED0")
        self.screen_ac.set("...") 
        self.screen_ac.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # --- Sleep ---
        ctk.CTkLabel(grid, text="Put computer to sleep after:", font=("Segoe UI", 10), text_color="#888888").grid(row=3, column=0, columnspan=2, pady=(15, 0))
        
        self.sleep_dc = ctk.CTkComboBox(grid, values=self.time_labels, fg_color="#111111", border_color="#333333", button_color="#3B8ED0")
        self.sleep_dc.set("...")
        self.sleep_dc.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

        self.sleep_ac = ctk.CTkComboBox(grid, values=self.time_labels, fg_color="#111111", border_color="#333333", button_color="#3B8ED0")
        self.sleep_ac.set("...")
        self.sleep_ac.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        # Apply Button
        ctk.CTkButton(section, text="Apply Timeouts", height=35, fg_color="#3B8ED0", hover_color="#2b7ab0",
                      command=self.apply_timeouts).pack(anchor="w", padx=15, pady=20)

    def _create_battery_report_ui(self):
        section = ctk.CTkFrame(self.scroll, fg_color="#222222", corner_radius=8)
        section.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(section, text="BATTERY HEALTH REPORT", font=("Segoe UI", 12, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(section, text="Generate an official Windows HTML battery health, capacity, and usage report.", font=("Segoe UI", 10), text_color="#888888").pack(anchor="w", padx=15)

        ctk.CTkButton(section, text="Generate & Open Battery Report", height=35, fg_color="#3B8ED0", hover_color="#2b7ab0",
                      command=self.generate_battery_report).pack(anchor="w", padx=15, pady=15)

    # --- Logic: Power Plans ---
    def load_power_plans(self):
        for widget in self.plans_container.winfo_children():
            widget.destroy()

        try:
            output = subprocess.check_output("powercfg /list", text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            active_guid = None
            plans = []
            
            for line in output.splitlines():
                if "GUID" in line:
                    guid = line.split(":")[1].split("(")[0].strip()
                    name = line.split("(")[1].split(")")[0].strip()
                    is_active = "*" in line
                    plans.append((name, guid, is_active))
                    if is_active: active_guid = guid

            self.radio_var = ctk.StringVar(value=active_guid)

            for name, guid, active in plans:
                row = ctk.CTkFrame(self.plans_container, fg_color="transparent")
                row.pack(fill="x", pady=4)
                
                rb = ctk.CTkRadioButton(row, text=f"{name}", variable=self.radio_var, value=guid,
                                      command=lambda g=guid: self.set_active_plan(g),
                                      font=("Segoe UI", 10), text_color="#ffffff", fg_color="#3B8ED0")
                rb.pack(side="left")
                
                if active:
                    ctk.CTkLabel(row, text="(Active)", text_color="#00E676", font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)

        except Exception as e:
            ctk.CTkLabel(self.plans_container, text=f"Error loading plans: {e}", text_color="red").pack()

    def set_active_plan(self, guid):
        def _task():
            try:
                subprocess.run(f"powercfg /setactive {guid}", shell=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                self.after(0, self.load_power_plans)
                self.after(0, self.fetch_current_timeouts)
            except Exception as e:
                print(f"Plan Error: {e}")
        threading.Thread(target=_task, daemon=True).start()

    # --- Logic: Detect & Apply Timeouts ---
    def fetch_current_timeouts(self):
        def _task():
            try:
                vid_guid = "7516b95f-f776-4464-8c53-06167f40cc99"
                vid_idle = "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e"
                
                sleep_guid = "238c9fa8-0aad-41ed-83f4-97be242c8f20"
                sleep_idle = "29f6c1db-86da-48c5-9fdb-f2b67b1f44da"

                out_scr = subprocess.check_output(f"powercfg /q SCHEME_CURRENT {vid_guid} {vid_idle}", text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                ac_hex = re.search(r"Current AC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_scr)
                dc_hex = re.search(r"Current DC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_scr)
                
                scr_ac = int(int(ac_hex.group(1), 16) / 60) if ac_hex else 10
                scr_dc = int(int(dc_hex.group(1), 16) / 60) if dc_hex else 5

                out_slp = subprocess.check_output(f"powercfg /q SCHEME_CURRENT {sleep_guid} {sleep_idle}", text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                ac_hex_s = re.search(r"Current AC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_slp)
                dc_hex_s = re.search(r"Current DC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_slp)

                slp_ac = int(int(ac_hex_s.group(1), 16) / 60) if ac_hex_s else 30
                slp_dc = int(int(dc_hex_s.group(1), 16) / 60) if dc_hex_s else 15

                self.after(0, lambda: self._update_combos(scr_ac, scr_dc, slp_ac, slp_dc))

            except Exception as e:
                print(f"Fetch Timeouts Error: {e}")

        threading.Thread(target=_task, daemon=True).start()

    def _update_combos(self, s_ac, s_dc, sl_ac, sl_dc):
        def get_lbl(m):
            if m == 0: return "Never"
            if m in self.reverse_time_map: return self.reverse_time_map[m]
            return f"{m} Minutes"

        self.screen_ac.set(get_lbl(s_ac))
        self.screen_dc.set(get_lbl(s_dc))
        self.sleep_ac.set(get_lbl(sl_ac))
        self.sleep_dc.set(get_lbl(sl_dc))

    def apply_timeouts(self):
        def _task():
            try:
                def get_mins(val):
                    return self.time_map.get(val, 10)

                m_screen_ac = get_mins(self.screen_ac.get())
                m_screen_dc = get_mins(self.screen_dc.get())
                m_sleep_ac = get_mins(self.sleep_ac.get())
                m_sleep_dc = get_mins(self.sleep_dc.get())

                cmds = [
                    f"powercfg /change monitor-timeout-ac {m_screen_ac}",
                    f"powercfg /change monitor-timeout-dc {m_screen_dc}",
                    f"powercfg /change standby-timeout-ac {m_sleep_ac}",
                    f"powercfg /change standby-timeout-dc {m_sleep_dc}"
                ]

                for cmd in cmds:
                    subprocess.run(cmd, shell=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)

                self.after(0, lambda: messagebox.showinfo("Success", "Power timeouts applied successfully."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Could not apply settings:\n{e}"))

        threading.Thread(target=_task, daemon=True).start()

    def generate_battery_report(self):
        def _task():
            try:
                report_path = os.path.join(os.path.expanduser("~"), "battery-report.html")
                cmd = f'powercfg /batteryreport /output "{report_path}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0 and os.path.exists(report_path):
                    def _prompt():
                        if messagebox.askyesno("Battery Report Ready", f"Battery report generated successfully at:\n{report_path}\n\nWould you like to open it in your web browser now?"):
                            webbrowser.open(report_path)
                    self.after(0, _prompt)
                else:
                    err_msg = result.stderr.strip() if result.stderr else "Unknown error or device has no supported battery."
                    self.after(0, lambda: messagebox.showerror("Error", f"Failed to generate battery report:\n{err_msg}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"An error occurred:\n{e}"))

        threading.Thread(target=_task, daemon=True).start()

# Compatibility aliases for main.py dynamic loading
PowerTab = PowerModule
Power = PowerModule
PowerSettingsTab = PowerModule