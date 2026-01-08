import customtkinter as ctk
import subprocess
import threading
import os
from tkinter import messagebox
from utils import add_info_section

class NetworkModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Network Tools", "Run common Windows network diagnostics and reset commands.")
        
        # --- Control Area (Buttons) ---
        self.ctrl_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=20, pady=10)
        
        # Column 1
        self.col1 = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.col1.pack(side="left", fill="both", expand=True, padx=5)
        
        ctk.CTkButton(self.col1, text="Flush DNS Cache", command=lambda: self.run_cmd("ipconfig /flushdns", "Flushing DNS...")).pack(fill="x", pady=5)
        ctk.CTkButton(self.col1, text="Renew IP Address", command=lambda: self.run_cmd("ipconfig /renew", "Renewing IP (this may take a moment)...")).pack(fill="x", pady=5)
        ctk.CTkButton(self.col1, text="Ping Google (Latency)", command=lambda: self.run_cmd("ping -n 4 google.com", "Pinging Google...")).pack(fill="x", pady=5)

        # Column 2
        self.col2 = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.col2.pack(side="left", fill="both", expand=True, padx=5)
        
        ctk.CTkButton(self.col2, text="Reset Winsock Catalog", fg_color="#c42b1c", hover_color="#8a1c11",
                      command=self.reset_winsock).pack(fill="x", pady=5)
        ctk.CTkButton(self.col2, text="Generate WLAN Report", command=self.generate_wlan_report).pack(fill="x", pady=5)
        ctk.CTkButton(self.col2, text="Clear Terminal", fg_color="gray", command=self.clear_terminal).pack(fill="x", pady=5)

        # --- Terminal Output Window ---
        ctk.CTkLabel(self.frame, text="Terminal Output:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 0))
        
        self.terminal = ctk.CTkTextbox(self.frame, font=ctk.CTkFont(family="Consolas", size=12), text_color="#00FF00", fg_color="black")
        self.terminal.pack(fill="both", expand=True, padx=20, pady=10)
        self.terminal.configure(state="disabled")

    def log(self, text):
        """Append text to the terminal window."""
        self.terminal.configure(state="normal")
        self.terminal.insert("end", text + "\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("0.0", "end")
        self.terminal.configure(state="disabled")

    def run_cmd(self, command, status_msg):
        """Runs a subprocess command in a thread."""
        def _target():
            self.log(f"\n> {command}")
            try:
                # Capture Output
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                
                if stdout: self.log(stdout)
                if stderr: self.log(f"ERROR: {stderr}")
                self.log("-" * 40)
            except Exception as e:
                self.log(f"Execution Error: {e}")

        self.log(f"\n--- {status_msg} ---")
        threading.Thread(target=_target, daemon=True).start()

    def reset_winsock(self):
        """Reset Winsock and prompt for restart."""
        if messagebox.askyesno("Confirm Reset", "This command (netsh winsock reset) requires a computer restart to take effect.\n\nProceed?"):
            def _target():
                self.run_cmd("netsh winsock reset", "Resetting Winsock Catalog...")
                messagebox.showwarning("Restart Required", "Winsock reset completed successfully.\n\nPlease restart your computer to apply changes.")
            
            threading.Thread(target=_target, daemon=True).start()

    def generate_wlan_report(self):
        """Generates WLAN report and offers to open it."""
        def _target():
            self.log("\n--- Generating WLAN Report ---")
            self.log("> netsh wlan show wlanreport")
            self.log("This may take up to 60 seconds...")
            
            report_path = r"C:\ProgramData\Microsoft\Windows\WlanReport\wlan-report-latest.html"
            
            # Remove old report if it exists to verify new one is created
            if os.path.exists(report_path):
                try:
                    os.remove(report_path)
                except:
                    self.log("(Note: Could not delete previous report file before generating new one)")

            try:
                # Run the command
                result = subprocess.run("netsh wlan show wlanreport", capture_output=True, text=True, shell=True)
                self.log(result.stdout)
                
                # Check FILE EXISTENCE instead of parsing text
                if os.path.exists(report_path):
                    self.log(f"SUCCESS: Report found at {report_path}")
                    
                    if messagebox.askyesno("Report Ready", "WLAN Report generated successfully.\nOpen it now in your browser?"):
                         subprocess.Popen(f'explorer "{report_path}"', shell=True)
                else:
                    self.log("ERROR: Report file was not created.")
                    self.log("Possible causes: No WiFi adapter, or not running as Administrator.")
                    
            except Exception as e:
                self.log(f"Error: {e}")

        threading.Thread(target=_target, daemon=True).start()