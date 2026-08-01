import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Fallback config import if config.py cleaner paths are missing
try:
    from config import CLEANER_PATHS
except ImportError:
    CLEANER_PATHS = [
        ("User Temp", os.environ.get('TEMP')),
        ("System Temp", r"C:\Windows\Temp"),
        ("Prefetch", r"C:\Windows\Prefetch"),
        ("Windows Update Cache", r"C:\Windows\SoftwareDistribution\Download"),
        ("Crash Dumps", r"C:\Windows\Minidump"),
        ("Error Reports", r"C:\ProgramData\Microsoft\Windows\WER"),
    ]

def format_size(size_bytes):
    """Formats raw byte counts into human-readable strings (KB, MB, GB)."""
    try:
        size_bytes = int(size_bytes)
    except (TypeError, ValueError):
        return "0 B"
    
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


class CleanerModule(tk.Frame):
    """Native Tkinter System Cleaner Module."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")
        self.files_to_delete = []
        self.total_size = 0
        
        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="System Cleaner", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Deep scan and remove temporary files, logs, and prefetch data.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Controls Bar ---
        self.ctrl_frame = tk.Frame(self, bg="#1c1c1c")
        self.ctrl_frame.pack(fill="x", padx=20, pady=10)

        self.btn_scan = tk.Button(
            self.ctrl_frame, text="Scan Junk Files", command=self.start_scan, 
            bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), 
            bd=0, cursor="hand2", padx=15, width=14, pady=6
        )
        self.btn_scan.pack(side="left", padx=(0, 10))

        self.btn_clean = tk.Button(
            self.ctrl_frame, text="Clean Now", command=self.start_clean, 
            bg="#303030", fg="#777777", font=("Segoe UI", 9, "bold"), 
            bd=0, state="disabled", padx=15, width=14, pady=6
        )
        self.btn_clean.pack(side="left", padx=(0, 15))

        self.status_lbl = tk.Label(self.ctrl_frame, text="Ready to scan", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 9))
        self.status_lbl.pack(side="left")

        # --- Progress Bar ---
        prog_frame = tk.Frame(self, bg="#1c1c1c")
        prog_frame.pack(fill="x", padx=20, pady=5)
        
        self.progress = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate", length=100)
        self.progress.pack(fill="x", expand=True)
        self.progress["value"] = 0

        # --- Results Console Log Area ---
        log_frame = tk.Frame(self, bg="#1c1c1c")
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.log_area = tk.Text(
            log_frame, bg="#0B0B0E", fg="#00FF00", 
            font=("Consolas", 10), bd=1, relief="flat", insertbackground="white"
        )
        self.log_area.pack(fill="both", expand=True)
        self.log_area.configure(state="disabled")

    def log(self, message):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def start_scan(self):
        self.btn_scan.configure(state="disabled", bg="#303030", fg="#777777")
        self.btn_clean.configure(state="disabled", bg="#303030", fg="#777777")
        self.progress["value"] = 0
        
        self.log_area.configure(state="normal")
        self.log_area.delete("1.0", "end")
        self.log_area.configure(state="disabled")
        
        threading.Thread(target=self.run_scan, daemon=True).start()

    def run_scan(self):
        self.files_to_delete = []
        self.total_size = 0
        
        self.log("--- Starting Deep Scan ---")
        
        for name, path in CLEANER_PATHS:
            if not path or not os.path.exists(path):
                continue
            
            try:
                os.listdir(path)
            except PermissionError:
                self.after(0, lambda n=name: self.log(f"Skipping {n}: Permission Denied"))
                continue

            self.after(0, lambda n=name: self.status_lbl.configure(text=f"Scanning {n}..."))
            
            for root, dirs, files in os.walk(path):
                for filename in files:
                    try:
                        filepath = os.path.join(root, filename)
                        size = os.path.getsize(filepath)
                        self.total_size += size
                        self.files_to_delete.append(filepath)
                    except Exception:
                        pass
                
        self.after(0, self.finish_scan)

    def finish_scan(self):
        self.status_lbl.configure(text=f"Found {len(self.files_to_delete)} files ({format_size(self.total_size)})")
        self.progress["value"] = 100
        
        self.log(f"\nScan Complete.")
        self.log(f"Total Junk Found: {format_size(self.total_size)}")
        self.log(f"File Count: {len(self.files_to_delete)}")
        
        if self.files_to_delete:
            self.log("\n--- Files Queued for Removal ---")
            # Display up to 100 files in the log console as a preview
            for filepath in self.files_to_delete[:100]:
                self.log(f"  • {filepath}")
            if len(self.files_to_delete) > 100:
                self.log(f"  ... and {len(self.files_to_delete) - 100} more files.")
            self.log("--------------------------------")
        
        self.btn_scan.configure(state="normal", bg="#3B8ED0", fg="white")
        if self.files_to_delete:
            self.btn_clean.configure(state="normal", bg="#c42b1c", fg="white")

    def start_clean(self):
        if not self.files_to_delete: 
            return
        
        if not messagebox.askyesno("Confirm Clean", f"Are you sure you want to delete {len(self.files_to_delete)} files?\nThis cannot be undone."):
            return

        self.btn_clean.configure(state="disabled", bg="#303030", fg="#777777")
        self.btn_scan.configure(state="disabled", bg="#303030", fg="#777777")
        self.progress["value"] = 0
        
        threading.Thread(target=self.run_clean, daemon=True).start()

    def run_clean(self):
        deleted_size = 0
        errors = 0
        count = len(self.files_to_delete)
        
        self.log("\n--- Cleaning Started ---")
        
        for i, filepath in enumerate(self.files_to_delete):
            try:
                size = os.path.getsize(filepath)
                os.remove(filepath)
                deleted_size += size
            except Exception:
                errors += 1  
            
            # Update progress every 10 files
            if i % 10 == 0:
                prog_val = int(((i + 1) / count) * 100) if count > 0 else 100
                self.after(0, lambda p=prog_val, c=i: [
                    self.progress.configure(value=p),
                    self.status_lbl.configure(text=f"Cleaning: {c}/{count}")
                ])

        self.after(0, lambda: self.finish_clean(deleted_size, errors))

    def finish_clean(self, deleted_size, errors):
        self.progress["value"] = 100
        self.status_lbl.configure(text="Cleaning Complete")
        self.btn_scan.configure(state="normal", bg="#3B8ED0", fg="white")
        
        self.log("\n--- Summary ---")
        self.log(f"Cleaned: {format_size(deleted_size)}")
        self.log(f"Skipped (In Use): {errors} files")
        self.log("System is now optimized.")
        
        self.files_to_delete = []
        self.total_size = 0

# Compatibility alias for main.py dynamic routing
SystemCleanerTab = CleanerModule