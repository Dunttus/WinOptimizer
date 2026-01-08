import customtkinter as ctk
import subprocess
import threading
import re
from tkinter import messagebox
from utils import add_info_section

class PowerModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Power Plan Switcher", "Switch to 'High Performance' to prevent CPU throttling during gaming or heavy tasks.")
        
        # Controls
        self.ctrl_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkButton(self.ctrl_frame, text="Refresh Plans", command=self.refresh_plans).pack(side="left")
        
        self.status_label = ctk.CTkLabel(self.ctrl_frame, text="Ready", text_color="gray")
        self.status_label.pack(side="left", padx=20)

        # List Area
        self.plan_list = ctk.CTkScrollableFrame(self.frame, label_text="Available Power Schemes")
        self.plan_list.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Load initially
        self.refresh_plans()

    def refresh_plans(self):
        # Clear list
        for widget in self.plan_list.winfo_children():
            widget.destroy()
            
        self.status_label.configure(text="Reading power configs...")
        threading.Thread(target=self.fetch_plans_thread, daemon=True).start()

    def fetch_plans_thread(self):
        try:
            # Run powercfg /list
            # Hide the console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            output = subprocess.check_output("powercfg /list", startupinfo=startupinfo, text=True)
            
            plans = []
            
            # Parse output line by line
            # Example Line: "Power Scheme GUID: 381b4222...  (Balanced) *"
            for line in output.splitlines():
                if "Power Scheme GUID:" in line:
                    # Regex to capture GUID, Name, and if it's active (*)
                    match = re.search(r"GUID:\s+([a-f0-9\-]+)\s+\((.+?)\)\s*(\*)?", line, re.IGNORECASE)
                    if match:
                        guid = match.group(1)
                        name = match.group(2)
                        is_active = bool(match.group(3))
                        plans.append((name, guid, is_active))

            # Update UI
            self.frame.after(0, lambda: self.display_plans(plans))

        except Exception as e:
            self.frame.after(0, lambda: self.status_label.configure(text=f"Error: {str(e)}"))

    def display_plans(self, plans):
        self.status_label.configure(text=f"Found {len(plans)} plans.")
        
        if not plans:
             ctk.CTkLabel(self.plan_list, text="No power plans found.").pack(pady=20)
             return

        for name, guid, is_active in plans:
            row = ctk.CTkFrame(self.plan_list)
            row.pack(fill="x", pady=5)
            
            # Icon/Indicator
            color = "#00FF00" if is_active else "gray"
            indicator = ctk.CTkLabel(row, text="●" if is_active else "○", text_color=color, font=ctk.CTkFont(size=20))
            indicator.pack(side="left", padx=10)
            
            # Text Info
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)
            
            name_text = f"{name} (Active)" if is_active else name
            ctk.CTkLabel(info, text=name_text, font=ctk.CTkFont(weight="bold" if is_active else "normal")).pack(anchor="w")
            ctk.CTkLabel(info, text=guid, font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
            
            # Activate Button
            state = "disabled" if is_active else "normal"
            btn_text = "Active" if is_active else "Activate"
            fg = "gray40" if is_active else ["#3B8ED0", "#1F6AA5"]
            
            ctk.CTkButton(row, text=btn_text, state=state, fg_color=fg, width=100,
                          command=lambda g=guid: self.activate_plan(g)).pack(side="right", padx=10)

    def activate_plan(self, guid):
        try:
            # powercfg /setactive GUID
            subprocess.run(f"powercfg /setactive {guid}", shell=True, check=True)
            self.status_label.configure(text="Plan activated successfully!")
            
            # Refresh list to update UI
            self.frame.after(500, self.refresh_plans)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to activate plan.\n{e}")