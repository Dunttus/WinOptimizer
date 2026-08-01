import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox


class NetworkModule(tk.Frame):
    """Native Tkinter Network Diagnostics & Tools Module."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")

        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="Network Tools", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Run common Windows network diagnostics and reset commands.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Tools List Container ---
        tools_container = tk.Frame(self, bg="#1c1c1c", bd=1, relief="solid")
        tools_container.pack(fill="x", padx=20, pady=10)
        
        tk.Label(
            tools_container, text=" Network Commands ", fg="#888888", 
            bg="#1c1c1c", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=10, pady=(8, 0))

        tools_list = tk.Frame(tools_container, bg="#1c1c1c")
        tools_list.pack(fill="x", padx=5, pady=5)

        # 1. Flush DNS
        self.create_tool_row(
            tools_list,
            "Flush DNS", 
            "Clears the DNS resolver cache to fix connection issues.",
            lambda: self.run_cmd("ipconfig /flushdns", "Flushing DNS...")
        )

        # 2. Renew IP
        self.create_tool_row(
            tools_list,
            "Renew IP", 
            "Requests a new IP address from the DHCP server (may briefly disconnect).",
            lambda: self.run_cmd("ipconfig /renew", "Renewing IP...")
        )

        # 3. Ping Google
        self.create_tool_row(
            tools_list,
            "Ping Google", 
            "Checks internet connectivity and measures latency to Google servers.",
            lambda: self.run_cmd("ping -n 4 google.com", "Pinging Google...")
        )

        # 4. Reset Winsock
        self.create_tool_row(
            tools_list,
            "Reset Winsock", 
            "Resets the Winsock Catalog to clean state. Requires Restart.",
            self.reset_winsock,
            color="#c42b1c"
        )

        # 5. WLAN Report
        self.create_tool_row(
            tools_list,
            "WLAN Report", 
            "Generates a detailed wireless connectivity report (requires Admin).",
            self.generate_wlan_report
        )

        # --- Terminal Control Bar ---
        term_ctrl_frame = tk.Frame(self, bg="#1c1c1c")
        term_ctrl_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        tk.Label(term_ctrl_frame, text="Terminal Output:", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(
            term_ctrl_frame, text="Clear Terminal", width=14, bg="#444444", fg="white", 
            font=("Segoe UI", 8, "bold"), activebackground="#555555", activeforeground="white", 
            bd=0, cursor="hand2", padx=5, pady=4, command=self.clear_terminal
        ).pack(side="right")

        # --- Terminal Output Window ---
        term_container = tk.Frame(self, bg="#1c1c1c", bd=1, relief="solid")
        term_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.terminal = tk.Text(
            term_container, font=("Consolas", 10), fg="#00FF00", bg="#111111", 
            insertbackground="white", bd=0, highlightthickness=0
        )
        term_scrollbar = ttk.Scrollbar(term_container, orient="vertical", command=self.terminal.yview)
        self.terminal.configure(yscrollcommand=term_scrollbar.set, state="disabled")

        self.terminal.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        term_scrollbar.pack(side="right", fill="y")

    def create_tool_row(self, parent, title, desc, command, color=None):
        row = tk.Frame(parent, bg="#2a2a2a", bd=1, relief="solid")
        row.pack(fill="x", pady=4, padx=5)
        row.grid_columnconfigure(0, weight=0)
        row.grid_columnconfigure(1, weight=1)
        
        btn_bg = color if color else "#3B8ED0"
        btn_active = "#A32014" if color else "#1F6AA5"

        btn = tk.Button(
            row, text=title, width=16, bg=btn_bg, fg="white", 
            font=("Segoe UI", 9, "bold"), activebackground=btn_active, 
            activeforeground="white", bd=0, cursor="hand2", padx=5, pady=4,
            command=command
        )
        btn.grid(row=0, column=0, padx=12, pady=8, sticky="w")
        
        lbl = tk.Label(row, text=desc, font=("Segoe UI", 9), fg="#cccccc", bg="#2a2a2a", anchor="w")
        lbl.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

    def log(self, text):
        """Append text to the terminal window safely from any thread."""
        def _update():
            self.terminal.configure(state="normal")
            self.terminal.insert("end", text + "\n")
            self.terminal.see("end")
            self.terminal.configure(state="disabled")
        self.after(0, _update)

    def clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")

    def run_cmd(self, command, status_msg):
        """Runs a subprocess command in a thread."""
        def _target():
            self.log(f"\n--- {status_msg} ---")
            self.log(f"> {command}")
            try:
                # Suppress flashing terminal windows on Windows with creationflags
                process = subprocess.Popen(
                    command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                    text=True, creationflags=0x08000000
                )
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
                result = subprocess.run(
                    "netsh wlan show wlanreport", capture_output=True, text=True, 
                    shell=True, creationflags=0x08000000
                )
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

# Compatibility alias for main.py dynamic routing
NetworkToolsTab = NetworkModule