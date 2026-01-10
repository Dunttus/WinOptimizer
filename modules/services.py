import customtkinter as ctk
import subprocess
import threading
from utils import add_info_section

class ServicesModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Service Manager", "Disable unnecessary background services to free up RAM and CPU.")

        # --- Warning ---
        warning_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        warning_frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(warning_frame, text="⚠️ Note: Services listed below are safe to disable for most users, but some may be locked by Windows.", 
                     text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w")

        # --- Services List ---
        self.scroll = ctk.CTkScrollableFrame(self.frame, label_text="Debloat Services")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Service Definitions: (Display Name, Real Service Name, Description)
        self.services = [
            ("Connected User Exp (Telemetry)", "DiagTrack", "Tracks usage data and sends it to Microsoft."),
            ("SysMain (Superfetch)", "SysMain", "Preloads apps to RAM. Can cause high disk usage on HDDs."),
            ("Remote Desktop (TermService)", "TermService", "Allows remote connections. Safe to disable if not used."),
            ("Xbox Accessories", "XboxGipSvc", "Drivers for Xbox controllers."),
            ("Xbox Live Auth", "XblAuthManager", "Authentication for Xbox Live."),
            ("Downloaded Maps Manager", "MapsBroker", "Updates offline maps."),
            ("Fax Service", "Fax", "Legacy service for sending faxes."),
            ("Touch Keyboard Service", "TabletInputService", "On-screen keyboard (disable if not using touch)."),
            ("Windows Insider Service", "wisvc", "Beta testing service for Windows updates.")
        ]

        # Create Rows
        for title, service_name, desc in self.services:
            self.create_row(title, service_name, desc)

    def create_row(self, title, service_name, desc):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=5)
        
        # Text Info
        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(text_frame, text=title, font=ctk.CTkFont(weight="bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(text_frame, text=desc, text_color="gray", font=ctk.CTkFont(size=11), anchor="w").pack(fill="x")

        # Action Button
        btn = ctk.CTkButton(row, text="Disable", width=120, fg_color=("#3B8ED0", "#1F6AA5"))
        btn.configure(command=lambda b=btn, s=service_name: self.disable_service(s, b))
        btn.pack(side="right", padx=10)

    def disable_service(self, service_name, button):
        """Disables service and updates button with specific status."""
        
        # 1. Processing State
        button.configure(text="Processing...", state="disabled", fg_color="gray30")
        
        def _target():
            try:
                # A. Stop Service (Ignore errors if already stopped)
                subprocess.run(f"net stop {service_name} /y", shell=True, capture_output=True)

                # B. Disable Service (Critical Step)
                cmd = f"sc config {service_name} start= disabled"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

                if result.returncode == 0:
                    # SUCCESS
                    new_text = "Disabled ✓"
                    new_color = "gray30"  # Gray as requested
                else:
                    # FAILURE - Analyze specific errors
                    err = result.stderr.strip()
                    
                    if "Access is denied" in err:
                        new_text = "Access Denied" # Needs Admin
                    elif "OpenService FAILED 1060" in err:
                        new_text = "Not Installed" # Service doesn't exist on this PC
                    elif "OpenService FAILED 5" in err:
                        new_text = "System Locked" # Windows protected service
                    elif "OpenService FAILED" in err:
                        new_text = "Protected"     # Generic protection
                    else:
                        new_text = "Failed"

                    new_color = "gray30" # Still turn gray to show we tried

                # Update UI safely
                self.frame.after(0, lambda: button.configure(text=new_text, fg_color=new_color, state="disabled"))

            except Exception as e:
                print(f"Service Error: {e}")
                self.frame.after(0, lambda: button.configure(text="Script Error", fg_color="gray30", state="disabled"))

        threading.Thread(target=_target, daemon=True).start()