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
        
        # --- Tools List Container ---
        self.tools_frame = ctk.CTkScrollableFrame(self.frame, label_text="Network Commands")
        self.tools_frame.pack(fill="x", expand=False, padx=20, pady=10, ipady=10)

        # 1. Flush DNS
        self.create_tool_row(
            "Flush DNS", 
            "Clears the DNS resolver cache to fix connection issues.",
            lambda: self.run_cmd("ipconfig /flushdns", "Flushing DNS...")
        )

        # 2. Renew IP
        self.create_tool_row(
            "Renew IP", 
            "Requests a new IP address from the DHCP server (may briefly disconnect).",
            lambda: self.run_cmd("ipconfig /renew", "Renewing IP...")
        )

        # 3. Ping Google
        self.create_tool_row(
            "Ping Google", 
            "Checks internet connectivity and measures latency to Google servers.",
            lambda: self.run_cmd("ping -n 4 google.com", "Pinging Google...")
        )

        # 4. Reset Winsock
        self.create_tool_row(
            "Reset Winsock", 
            "Resets the Winsock Catalog to clean state. Requires Restart.",
            self.reset_winsock,
            color="#c42b1c"
        )

        # 5. WLAN Report
        self.create_tool_row(
            "WLAN Report", 
            "Generates a detailed wireless connectivity report (requires Admin).",
            self.generate_wlan_report
        )

        # --- Terminal Control Bar ---
        term_ctrl_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        term_ctrl_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        ctk.CTkLabel(term_ctrl_frame, text="Terminal Output:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(term_ctrl_frame, text="Clear Terminal", width=120, fg_color="gray", command=self.clear_terminal).pack(side="right")

        # --- Terminal Output Window ---
        self.terminal = ctk.CTkTextbox(self.frame, font=ctk.CTkFont(family="Consolas", size=12), text_color="#00FF00", fg_color="black")
        self.terminal.pack(fill="both", expand=True, padx=20, pady=5)
        self.terminal.configure(state="disabled")

    def create_tool_row(self, title, desc, command, color=None):
        row = ctk.CTkFrame(self.tools_frame, fg_color="transparent")
        row.pack(fill="x", pady=5)
        
        # Button
        btn_color = color if color else ["#3B8ED0", "#1F6AA5"]
        ctk.CTkButton(row, text=title, width=140, command=command, fg_color=btn_color).pack(side="left", padx=10)
        
        # Description
        ctk.CTkLabel(row, text=desc, text_color="gray", anchor="w").pack(side="left", fill="x", expand=True)

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
            self.log(f"\n--- {status_msg} ---")
            self.log(f"> {command}")
            try:
                # Capture Output
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                
                if stdout: self.log(stdout)
                if stderr: self.log(f"ERROR: {stderr}")
                self.log("-" * 40)
            except Exception as e:
                self.log(f"Execution Error: {e}")

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
            
            if os.path.exists(report_path):
                try:
                    os.remove(report_path)
                except:
                    self.log("(Note: Could not delete previous report file)")

            try:
                result = subprocess.run("netsh wlan show wlanreport", capture_output=True, text=True, shell=True)
                self.log(result.stdout)
                
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