import customtkinter as ctk
import subprocess
import threading
from tkinter import messagebox
from utils import add_info_section

class RepairModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Windows Repair Tools", "Execute built-in Windows commands to repair system files and disk errors.")
        
        # --- Tools List Container ---
        self.tools_frame = ctk.CTkScrollableFrame(self.frame, label_text="Repair Commands")
        self.tools_frame.pack(fill="x", expand=False, padx=20, pady=10, ipady=10)

        # 1. System File Checker
        self.create_tool_row(
            "SFC Scan", 
            "Scans integrity of all protected system files and repairs corrupted files.",
            self.run_sfc
        )

        # 2. DISM Scan (Check Health)
        self.create_tool_row(
            "DISM Check", 
            "Scans the Windows image for corruption (Does not fix, just checks).",
            self.run_dism_scan
        )

        # 3. DISM Restore (Restore Health) - SWAPPED TO BLUE
        self.create_tool_row(
            "DISM Repair", 
            "Downloads fresh files from Windows Update to fix a corrupted Windows image.",
            self.run_dism_restore
        )

        # 4. Check Disk - SWAPPED TO RED
        self.create_tool_row(
            "Check Disk (C:)", 
            "Checks file system metadata and disk errors. Requires a Restart.",
            self.schedule_chkdsk,
            color="#c42b1c" 
        )

        # --- Terminal Control ---
        ctrl_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkButton(ctrl_frame, text="Clear Terminal", width=120, fg_color="gray", command=self.clear_terminal).pack(side="right")
        ctk.CTkLabel(ctrl_frame, text="Terminal Output:", font=ctk.CTkFont(weight="bold")).pack(side="left")

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
        self.terminal.configure(state="normal")
        self.terminal.insert("end", text + "\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def clear_terminal(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("0.0", "end")
        self.terminal.configure(state="disabled")

    def run_process_stream(self, command, title):
        """Generic helper to run commands and stream output."""
        def _target():
            self.log(f"\n--- Starting {title} ---")
            self.log(f"> {command}")
            self.log("Please wait...\n")
            
            try:
                # Use Popen to capture real-time output
                process = subprocess.Popen(
                    command, 
                    shell=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    bufsize=1, 
                    universal_newlines=True
                )
                
                for line in process.stdout:
                    self.terminal.configure(state="normal")
                    self.terminal.insert("end", line)
                    self.terminal.see("end")
                    self.terminal.configure(state="disabled")
                
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
                # Echo y to automatically answer the schedule prompt
                cmd = "echo y | chkdsk C: /f /r"
                self.log("\n--- Scheduling Check Disk ---")
                self.log(f"> {cmd}")
                
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    self.log(result.stdout)
                    
                    if "next time the system restarts" in result.stdout:
                        messagebox.showinfo("Success", "Disk Check scheduled successfully!\n\nPlease restart your computer to begin the scan.")
                    else:
                         self.log("WARNING: Could not verify schedule. Check output above.")
                         
                except Exception as e:
                    self.log(f"Error: {e}")

            threading.Thread(target=_target, daemon=True).start()