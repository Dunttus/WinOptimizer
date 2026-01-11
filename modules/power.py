import customtkinter as ctk
import subprocess
import threading
import re
from tkinter import messagebox

class PowerModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True)
        
        # --- Header ---
        header_frame = ctk.CTkFrame(self.frame, corner_radius=10, fg_color="#1f538d")
        header_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(header_frame, text="Power Management", font=("Arial", 18, "bold"), text_color="white").pack(pady=5)
        ctk.CTkLabel(header_frame, text="Optimize performance or extend battery life.", text_color="gray90").pack(pady=(0, 10))

        self.scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
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
        
        # Auto-detect current settings on load
        self.fetch_current_timeouts()

    def _create_plans_ui(self):
        section = ctk.CTkFrame(self.scroll, fg_color="#2b2b2b", corner_radius=10)
        section.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(section, text="ACTIVE POWER PLAN", font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(15, 10))
        
        self.plans_container = ctk.CTkFrame(section, fg_color="transparent")
        self.plans_container.pack(fill="x", padx=10, pady=5)
        
        # Refresh Button
        ctk.CTkButton(section, text="Refresh Plans", height=30, fg_color="#333333", 
                      command=self.load_power_plans).pack(pady=15)

        self.load_power_plans()

    def _create_timeouts_ui(self):
        section = ctk.CTkFrame(self.scroll, fg_color="#2b2b2b", corner_radius=10)
        section.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(section, text="TIMEOUT SETTINGS", font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(section, text="Select duration before turning off screen or sleeping.", text_color="gray").pack(anchor="w", padx=15)

        # Grid for controls
        grid = ctk.CTkFrame(section, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=15)
        grid.grid_columnconfigure((0, 1), weight=1)

        # --- Headers ---
        ctk.CTkLabel(grid, text="ON BATTERY", font=("Arial", 11, "bold"), text_color="#FFA726").grid(row=0, column=0, pady=10)
        ctk.CTkLabel(grid, text="PLUGGED IN", font=("Arial", 11, "bold"), text_color="#00E676").grid(row=0, column=1, pady=10)

        # --- Screen Off ---
        ctk.CTkLabel(grid, text="Turn off screen after:", text_color="gray").grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        self.screen_dc = ctk.CTkComboBox(grid, values=self.time_labels)
        self.screen_dc.set("...") 
        self.screen_dc.grid(row=2, column=0, padx=10, pady=5)

        self.screen_ac = ctk.CTkComboBox(grid, values=self.time_labels)
        self.screen_ac.set("...") 
        self.screen_ac.grid(row=2, column=1, padx=10, pady=5)

        # --- Sleep ---
        ctk.CTkLabel(grid, text="Put computer to sleep after:", text_color="gray").grid(row=3, column=0, columnspan=2, pady=(15, 0))
        
        self.sleep_dc = ctk.CTkComboBox(grid, values=self.time_labels)
        self.sleep_dc.set("...")
        self.sleep_dc.grid(row=4, column=0, padx=10, pady=5)

        self.sleep_ac = ctk.CTkComboBox(grid, values=self.time_labels)
        self.sleep_ac.set("...")
        self.sleep_ac.grid(row=4, column=1, padx=10, pady=5)

        # Apply Button
        ctk.CTkButton(section, text="Apply Timeouts", height=35, fg_color="#1f538d",
                      command=self.apply_timeouts).pack(pady=20)

    # --- Logic: Power Plans ---
    def load_power_plans(self):
        for widget in self.plans_container.winfo_children():
            widget.destroy()

        try:
            # Fetch plans
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
                row.pack(fill="x", pady=2)
                
                rb = ctk.CTkRadioButton(row, text=f"{name}", variable=self.radio_var, value=guid,
                                        command=lambda g=guid: self.set_active_plan(g))
                rb.pack(side="left")
                
                if active:
                    ctk.CTkLabel(row, text="(Active)", text_color="#00E676", font=("Arial", 10, "bold")).pack(side="left", padx=10)

        except Exception as e:
            ctk.CTkLabel(self.plans_container, text=f"Error loading plans: {e}", text_color="red").pack()

    def set_active_plan(self, guid):
        def _task():
            try:
                subprocess.run(f"powercfg /setactive {guid}", shell=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                self.frame.after(0, self.load_power_plans) # Refresh UI to update "(Active)" label
                self.frame.after(0, self.fetch_current_timeouts) # Refresh timeouts as they might change with plan
            except Exception as e:
                print(f"Plan Error: {e}")
        threading.Thread(target=_task, daemon=True).start()

    # --- Logic: Detect & Apply Timeouts ---
    def fetch_current_timeouts(self):
        def _task():
            try:
                # We need to query specific aliases for Monitor (monitor-timeout-ac/dc) and Sleep (standby-timeout-ac/dc)
                # Note: 'powercfg /q' returns hex seconds. 'powercfg /aliases' helps identify them, but direct query is easier.
                
                def get_val(alias, ac_dc):
                    # Alias: SUB_VIDEO VIDEOIDLE, SUB_SLEEP STANDBYIDLE
                    # Simpler method: Use the /Q command and parse the current value in decimal seconds
                    cmd = f"powercfg /query SCHEME_CURRENT {alias} {ac_dc}"
                    out = subprocess.check_output(cmd, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    # Look for "Current AC Power Setting Index: 0x000003c" or similar
                    match = re.search(r"Current.*Index:\s+(0x[0-9a-fA-F]+)", out)
                    if match:
                        seconds = int(match.group(1), 16)
                        return int(seconds / 60) # Return minutes
                    return 0

                # 1. Monitor (VIDEOIDLE)
                # GUIDs for standard settings (subgroup VIDEO, setting VIDEOIDLE)
                # We use aliases for simplicity: monitor-timeout-ac
                
                # Fetching via direct alias reading isn't standard output, so we check aliases first
                # Actually, simplest way is parsing 'powercfg /getactivescheme' then querying specific GUIDs
                # Monitor GUID: 3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e
                # Sleep GUID: 238c9fa8-0aad-41ed-83f4-97be242c8f20
                
                # Helper to convert mins to label
                def get_label(mins):
                    if mins == 0: return "Never"
                    # Find closest match
                    closest = min(self.reverse_time_map.keys(), key=lambda x: abs(x - mins))
                    return self.reverse_time_map.get(closest, "Custom")

                # Parse AC/DC for Screen (Subgroup VIDEO -> VIDEOIDLE)
                # We use powershell for cleaner object return if possible, but regex on powercfg is standard for Python
                
                # VIDEO SUBGROUP
                vid_guid = "7516b95f-f776-4464-8c53-06167f40cc99"
                vid_idle = "3c0bc021-c8a8-4e07-a973-6b14cbcb2b7e"
                
                # SLEEP SUBGROUP
                sleep_guid = "238c9fa8-0aad-41ed-83f4-97be242c8f20"
                sleep_idle = "29f6c1db-86da-48c5-9fdb-f2b67b1f44da"

                # Get Values
                # Screen AC
                scr_ac_mins = get_val(vid_guid, vid_idle) # This likely fails without correct command structure
                # REVISION: The standard command 'powercfg /q SCHEME_CURRENT SUB_VIDEO VIDEOIDLE' works
                
                # Run queries
                # Screen
                out_scr = subprocess.check_output(f"powercfg /q SCHEME_CURRENT {vid_guid} {vid_idle}", text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                ac_hex = re.search(r"Current AC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_scr)
                dc_hex = re.search(r"Current DC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_scr)
                
                scr_ac = int(int(ac_hex.group(1), 16) / 60) if ac_hex else 10
                scr_dc = int(int(dc_hex.group(1), 16) / 60) if dc_hex else 5

                # Sleep
                out_slp = subprocess.check_output(f"powercfg /q SCHEME_CURRENT {sleep_guid} {sleep_idle}", text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                ac_hex_s = re.search(r"Current AC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_slp)
                dc_hex_s = re.search(r"Current DC Power Setting Index:\s+(0x[0-9a-fA-F]+)", out_slp)

                slp_ac = int(int(ac_hex_s.group(1), 16) / 60) if ac_hex_s else 30
                slp_dc = int(int(dc_hex_s.group(1), 16) / 60) if dc_hex_s else 15

                # Update UI
                self.frame.after(0, lambda: self._update_combos(scr_ac, scr_dc, slp_ac, slp_dc))

            except Exception as e:
                print(f"Fetch Timeouts Error: {e}")

        threading.Thread(target=_task, daemon=True).start()

    def _update_combos(self, s_ac, s_dc, sl_ac, sl_dc):
        def get_lbl(m):
            if m == 0: return "Never"
            if m in self.reverse_time_map: return self.reverse_time_map[m]
            return f"{m} Minutes" # Custom

        self.screen_ac.set(get_lbl(s_ac))
        self.screen_dc.set(get_lbl(s_dc))
        self.sleep_ac.set(get_lbl(sl_ac))
        self.sleep_dc.set(get_lbl(sl_dc))

    def apply_timeouts(self):
        def _task():
            try:
                # Map selections to minutes
                def get_mins(val):
                    return self.time_map.get(val, 10) # Default safe fallback

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

                self.frame.after(0, lambda: messagebox.showinfo("Success", "Power timeouts applied successfully."))
            except Exception as e:
                self.frame.after(0, lambda: messagebox.showerror("Error", f"Could not apply settings:\n{e}"))

        threading.Thread(target=_task, daemon=True).start()