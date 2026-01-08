import customtkinter as ctk
import os
import shutil
import threading
from tkinter import messagebox
from utils import add_info_section, format_size
from config import CLEANER_PATHS

class CleanerModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        self.files_to_delete = []
        self.total_size = 0
        
        add_info_section(self.frame, "System Cleaner", "Deep scan and remove temporary files, logs, and prefetch data.")

        # Controls
        self.ctrl_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=20, pady=10)

        self.btn_scan = ctk.CTkButton(self.ctrl_frame, text="Scan Junk Files", command=self.start_scan, width=150)
        self.btn_scan.pack(side="left", padx=5)

        self.btn_clean = ctk.CTkButton(self.ctrl_frame, text="Clean Now", command=self.start_clean, 
                                       fg_color="#c42b1c", hover_color="#8a1c11", state="disabled", width=150)
        self.btn_clean.pack(side="left", padx=5)

        self.status_lbl = ctk.CTkLabel(self.ctrl_frame, text="Ready to scan", text_color="gray")
        self.status_lbl.pack(side="left", padx=20)

        # Progress Bar
        self.progress = ctk.CTkProgressBar(self.frame)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=20, pady=5)

        # Results List
        self.log_area = ctk.CTkTextbox(self.frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_area.pack(fill="both", expand=True, padx=20, pady=10)
        self.log_area.configure(state="disabled")

    def log(self, message):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def start_scan(self):
        self.btn_scan.configure(state="disabled")
        self.btn_clean.configure(state="disabled")
        self.progress.set(0)
        self.log_area.configure(state="normal")
        self.log_area.delete("0.0", "end")
        self.log_area.configure(state="disabled")
        
        threading.Thread(target=self.run_scan, daemon=True).start()

    def run_scan(self):
        self.files_to_delete = []
        self.total_size = 0
        
        self.log("--- Starting Deep Scan ---")
        
        # Use the list from config.py
        for name, path in CLEANER_PATHS:
            if not path or not os.path.exists(path):
                continue
            
            try:
                # Quick permission check
                os.listdir(path)
            except PermissionError:
                self.frame.after(0, lambda n=name: self.log(f"Skipping {n}: Permission Denied"))
                continue

            self.frame.after(0, lambda n=name: self.status_lbl.configure(text=f"Scanning {n}..."))
            
            # Walk through the directory
            for root, dirs, files in os.walk(path):
                for name in files:
                    try:
                        filepath = os.path.join(root, name)
                        
                        # Calculate size
                        size = os.path.getsize(filepath)
                        self.total_size += size
                        self.files_to_delete.append(filepath)
                    except: pass
                    
        self.frame.after(0, self.finish_scan)

    def finish_scan(self):
        self.status_lbl.configure(text=f"Found {len(self.files_to_delete)} files ({format_size(self.total_size)})")
        self.progress.set(1)
        
        self.log(f"\nScan Complete.")
        self.log(f"Total Junk Found: {format_size(self.total_size)}")
        self.log(f"File Count: {len(self.files_to_delete)}")
        
        self.btn_scan.configure(state="normal")
        if self.files_to_delete:
            self.btn_clean.configure(state="normal")

    def start_clean(self):
        if not self.files_to_delete: return
        
        if not messagebox.askyesno("Confirm Clean", f"Are you sure you want to delete {len(self.files_to_delete)} files?\nThis cannot be undone."):
            return

        self.btn_clean.configure(state="disabled")
        self.btn_scan.configure(state="disabled")
        self.progress.set(0)
        
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
            
            # Update Progress every 10 files
            if i % 10 == 0:
                prog = (i + 1) / count if count > 0 else 1
                self.frame.after(0, lambda p=prog, c=i: [
                    self.progress.set(p),
                    self.status_lbl.configure(text=f"Cleaning: {c}/{count}")
                ])

        self.frame.after(0, lambda: self.finish_clean(deleted_size, errors))

    def finish_clean(self, deleted_size, errors):
        self.progress.set(1)
        self.status_lbl.configure(text="Cleaning Complete")
        self.btn_scan.configure(state="normal")
        
        self.log("\n--- Summary ---")
        self.log(f"Cleaned: {format_size(deleted_size)}")
        self.log(f"Skipped (In Use): {errors} files")
        self.log("System is now optimized.")
        
        self.files_to_delete = []
        self.total_size = 0