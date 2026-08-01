import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox


class RepairModule(tk.Frame):
    """Native Tkinter Windows Repair Tools Module."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")

        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="Windows Repair Tools", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Execute built-in Windows commands to repair system files and disk errors.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Tools List Container ---
        tools_container = tk.Frame(self, bg="#1c1c1c", bd=1, relief="solid")
        tools_container.pack(fill="x", padx=20, pady=10)
        
        tk.Label(
            tools_container, text=" Repair Commands ", fg="#888888", 
            bg="#1c1c1c", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=10, pady=(8, 0))

        tools_list = tk.Frame(tools_container, bg="#1c1c1c")
        tools_list.pack(fill="x", padx=5, pady=5)

        # 1. System File Checker
        self.create_tool_row(
            tools_list,
            "SFC Scan", 
            "Scans integrity of all protected system files and repairs corrupted files.",
            self.run_sfc
        )

        # 2. DISM Scan (Check Health)
        self.create_tool_row(
            tools_list,
            "DISM Check", 
            "Scans the Windows image for corruption (Does not fix, just checks).",
            self.run_dism_scan
        )

        # 3. DISM Restore (Restore Health)
        self.create_tool_row(
            tools_list,
            "DISM Repair", 
            "Downloads fresh files from Windows Update to fix a corrupted Windows image.",
            self.run_dism_restore
        )

        # 4. Check Disk - RED
        self.create_tool_row(
            tools_list,
            "Check Disk (C:)", 
            "Checks file system metadata and disk errors. Requires a Restart.",
            self.schedule_chkdsk,
            color="#c42b1c"
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

    def run_process_stream(self, command, title):
        """Generic helper to run commands and stream output."""
        def _target():
            self.log(f"\n--- Starting {title} ---")
            self.log(f"> {command}")
            self.log("Please wait...\n")
            
            try:
                process = subprocess.Popen(
                    command, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    bufsize=1, 
                    universal_newlines=True,
                    creationflags=0x08000000  # Suppress command prompt flash
                )
                
                for line in process.stdout:
                    self.log(line.rstrip())
                
                process.wait()
                
                if process.returncode == 0:
                    self.log(f"\n--- {title} Completed Successfully ---")
                else:
                    self.log(f"\n--- {title} Finished (Check output for errors) ---")

            except Exception as e:
                self.log(f"Execution Error: {e}")

        threading.Thread(target=_target, daemon=True).start()

    # --- Command Logic ---

    def run_sfc(self):
        self.run_process_stream("sfc /scannow", "System File Checker")

    def run_dism_scan(self):
        self.run_process_stream("DISM /Online /Cleanup-Image /ScanHealth", "DISM Health Check")

    def run_dism_restore(self):
        if messagebox.askyesno("Confirm DISM Repair", "DISM RestoreHealth will download fresh system files from Windows Update.\n\nThis may take 10-20 minutes depending on your internet speed.\n\nContinue?"):
            self.run_process_stream("DISM /Online /Cleanup-Image /RestoreHealth", "DISM Image Repair")

    def schedule_chkdsk(self):
        if messagebox.askyesno("Schedule CHKDSK", "Check Disk cannot run while Windows is using the drive.\n\nDo you want to schedule a check for the NEXT system restart?"):
            def _target():
                cmd = "echo y | chkdsk C: /f /r"
                self.log("\n--- Scheduling Check Disk ---")
                self.log(f"> {cmd}")
                
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000
                    )
                    self.log(result.stdout)
                    
                    if "next time the system restarts" in result.stdout:
                        messagebox.showinfo("Success", "Disk Check scheduled successfully!\n\nPlease restart your computer to begin the scan.")
                    else:
                        self.log("WARNING: Could not verify schedule. Check output above.")
                         
                except Exception as e:
                    self.log(f"Error: {e}")

            threading.Thread(target=_target, daemon=True).start()

# Compatibility alias for main.py dynamic routing
RepairTab = RepairModule