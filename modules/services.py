import customtkinter as ctk
import subprocess
import threading
from tkinter import messagebox
from utils import add_info_section, is_admin
from ui_manager import Win11UXManager

class ServicesModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Service Booster", "Stop background services and set them to Manual startup to free up RAM.")
        
        # Status Label
        self.status_label = ctk.CTkLabel(self.frame, text="Ready", text_color="gray")
        self.status_label.pack(pady=(0, 5))

        self.booster_list = ctk.CTkScrollableFrame(self.frame, label_text="Select services to optimize")
        self.booster_list.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Expanded List of Services
        self.target_services = [
            {"name": "DiagTrack", "desc": "Connected User Experiences & Telemetry"},
            {"name": "WSearch", "desc": "Windows Search Indexer (High Disk Usage)"},
            {"name": "Spooler", "desc": "Print Spooler (Unnecessary if no printer)"},
            {"name": "TermService", "desc": "Remote Desktop Services"},
            {"name": "DoSvc", "desc": "Windows Update Delivery Optimization"},
            {"name": "MapsBroker", "desc": "Downloaded Maps Manager"},
            {"name": "Fax", "desc": "Fax Service"},
            {"name": "XblAuthManager", "desc": "Xbox Live Auth Manager"},
            {"name": "XblGameSave", "desc": "Xbox Live Game Save"},
            {"name": "XboxNetApiSvc", "desc": "Xbox Live Networking Service"},
            {"name": "WerSvc", "desc": "Windows Error Reporting Service"},
            {"name": "PcaSvc", "desc": "Program Compatibility Assistant"},
            {"name": "RetailDemo", "desc": "Retail Demo Service"},
            {"name": "WMPNetworkSvc", "desc": "Windows Media Player Network Sharing"},
        ]
        
        self.create_service_rows()

    def create_service_rows(self):
        # Clear existing
        for widget in self.booster_list.winfo_children():
            widget.destroy()

        for svc in self.target_services:
            row = ctk.CTkFrame(self.booster_list)
            row.pack(fill="x", pady=2)
            
            # Service Name
            ctk.CTkLabel(row, text=svc['name'], width=120, anchor="w", 
                         font=ctk.CTkFont(weight="bold", family="Consolas")).pack(side="left", padx=10)
            
            # Description
            ctk.CTkLabel(row, text=svc['desc'], anchor="w").pack(side="left", padx=5)
            
            # Stop Button
            btn = ctk.CTkButton(row, text="Stop & Manual", width=100, fg_color="#c42b1c", 
                                hover_color="#8a1c11",
                                command=lambda s=svc['name'], r=row: self.stop_service(s, r))
            btn.pack(side="right", padx=10, pady=5)

    def stop_service(self, service_name, row_widget):
        if not is_admin():
            messagebox.showerror("Permission Error", "Administrator privileges are required to manage services.")
            return

        def _run_optimization():
            self.status_label.configure(text=f"Stopping {service_name}...", text_color="#1E90FF")
            
            try:
                # 1. Set Startup Type to Manual (start= demand)
                # Note: The space after 'start=' is mandatory in 'sc' commands.
                subprocess.run(
                    f'sc config "{service_name}" start= demand', 
                    shell=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False
                )
                
                # 2. Stop the service immediately
                result = subprocess.run(
                    f'net stop "{service_name}" /y', 
                    shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                )

                # Update UI on Main Thread
                if result.returncode == 0 or "not started" in result.stderr.lower():
                    self.frame.after(0, lambda: self._on_success(service_name, row_widget))
                else:
                    self.frame.after(0, lambda: self._on_fail(service_name, result.stderr))
                    
            except Exception as e:
                self.frame.after(0, lambda: self._on_fail(service_name, str(e)))

        # Run in thread to prevent GUI freezing
        threading.Thread(target=_run_optimization, daemon=True).start()

    def _on_success(self, service_name, row_widget):
        self.status_label.configure(text=f"Successfully optimized {service_name}", text_color="#00FF00")
        
        # Visual feedback: Change button to "Done" and disable it
        for child in row_widget.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(text="Stopped", state="disabled", fg_color="gray30")
        
        # Optional: Send Toast Notification
        Win11UXManager.send_notification("Service Stopped", f"{service_name} has been stopped and set to Manual.")

    def _on_fail(self, service_name, error_msg):
        self.status_label.configure(text=f"Failed to stop {service_name}", text_color="#c42b1c")
        print(f"Service Error ({service_name}): {error_msg}")
        messagebox.showerror("Service Error", f"Could not stop {service_name}.\n\nError: {error_msg}")