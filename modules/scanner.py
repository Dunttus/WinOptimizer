import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
import subprocess
from utils import format_size

class ScannerModule:
    def __init__(self, parent):
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.scan_running = False
        
        # ===========================
        # Section 1: Duplicate Finder
        # ===========================
        dup_container = ctk.CTkFrame(self.frame)
        dup_container.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(dup_container, text="Find Duplicate Files (Name & Size Only)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))

        # Path & Filter
        path_row = ctk.CTkFrame(dup_container, fg_color="transparent")
        path_row.pack(fill="x", padx=10, pady=5)
        self.dup_path_entry = ctk.CTkEntry(path_row, placeholder_text="Select folder to scan...", width=300)
        self.dup_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(path_row, text="Browse", width=80, command=lambda: self.browse_folder(self.dup_path_entry)).pack(side="right")

        ext_row = ctk.CTkFrame(dup_container, fg_color="transparent")
        ext_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(ext_row, text="Filter extensions (comma separated):").pack(side="left", padx=(0, 10))
        self.ext_entry = ctk.CTkEntry(ext_row, placeholder_text="e.g. .mp4, jpg, .pdf", width=200)
        self.ext_entry.pack(side="left")

        # Control Area
        ctrl_frame = ctk.CTkFrame(dup_container, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_scan_dup = ctk.CTkButton(ctrl_frame, text="Scan for Duplicates", command=self.toggle_dup_scan)
        self.btn_scan_dup.pack(side="left")
        
        self.lbl_dup_status = ctk.CTkLabel(ctrl_frame, text="Ready", text_color="gray")
        self.lbl_dup_status.pack(side="left", padx=20)

        # Results
        self.dup_results_frame = ctk.CTkScrollableFrame(dup_container, height=250, label_text="Found Duplicates")
        self.dup_results_frame.pack(fill="x", padx=20, pady=(10, 20))

        # ===========================
        # Section 2: Large Files
        # ===========================
        large_container = ctk.CTkFrame(self.frame)
        large_container.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(large_container, text="Find Large Files (>100MB)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))

        # Path
        large_path_row = ctk.CTkFrame(large_container, fg_color="transparent")
        large_path_row.pack(fill="x", padx=10, pady=5)
        self.large_path_entry = ctk.CTkEntry(large_path_row, placeholder_text="Select folder to scan...", width=300)
        self.large_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(large_path_row, text="Browse", width=80, command=lambda: self.browse_folder(self.large_path_entry)).pack(side="right")

        # Control Area
        l_ctrl_frame = ctk.CTkFrame(large_container, fg_color="transparent")
        l_ctrl_frame.pack(fill="x", padx=10, pady=5)

        self.btn_scan_large = ctk.CTkButton(l_ctrl_frame, text="Scan for Large Files", command=self.toggle_large_scan)
        self.btn_scan_large.pack(side="left")
        
        self.lbl_large_status = ctk.CTkLabel(l_ctrl_frame, text="Ready", text_color="gray")
        self.lbl_large_status.pack(side="left", padx=20)

        # Results
        self.large_results_frame = ctk.CTkScrollableFrame(large_container, height=250, label_text="Files > 100MB")
        self.large_results_frame.pack(fill="x", padx=20, pady=10)

    # ===========================
    # Helpers
    # ===========================
    def browse_folder(self, entry_widget):
        path = filedialog.askdirectory()
        if path:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, path)

    def open_file_location(self, filepath):
        try:
            filepath = os.path.normpath(filepath)
            subprocess.Popen(f'explorer /select,"{filepath}"')
        except Exception as e:
            print(f"Error opening location: {e}")

    # ===========================
    # Duplicate Logic
    # ===========================
    def toggle_dup_scan(self):
        if self.scan_running:
            self.scan_running = False
            self.btn_scan_dup.configure(text="Stopping...", state="disabled")
        else:
            self.start_duplicate_scan()

    def start_duplicate_scan(self):
        scan_path = self.dup_path_entry.get()
        if not scan_path or not os.path.isdir(scan_path):
            messagebox.showerror("Error", "Invalid directory path.")
            return
        
        ext_filter = self.ext_entry.get().strip()
        if ext_filter:
            extensions = [f".{e.strip().lstrip('.')}" for e in ext_filter.split(',')]
        else:
            extensions = None
        
        self.scan_running = True
        self.btn_scan_dup.configure(text="Stop Scan", fg_color="#c42b1c", hover_color="#8a1c11")
        self.lbl_dup_status.configure(text="Initializing...", text_color="gray")
        
        for widget in self.dup_results_frame.winfo_children():
            widget.destroy()

        threading.Thread(target=self.scan_duplicates_thread, args=(scan_path, extensions), daemon=True).start()

    def scan_duplicates_thread(self, scan_path, extensions):
        files_by_name_size = {}
        duplicates = []
        scanned_count = 0
        
        self.frame.after(0, lambda: self.lbl_dup_status.configure(text="Scanning file system..."))
        
        for root, _, files in os.walk(scan_path):
            if not self.scan_running: break
            
            for file in files:
                if extensions:
                    if not any(file.lower().endswith(ext.lower()) for ext in extensions):
                        continue
                
                full_path = os.path.join(root, file)
                
                try:
                    file_size = os.path.getsize(full_path)
                    key = (file, file_size)
                    
                    if key in files_by_name_size:
                        files_by_name_size[key].append(full_path)
                    else:
                        files_by_name_size[key] = [full_path]
                        
                    scanned_count += 1
                    
                    if scanned_count % 200 == 0:
                        self.frame.after(0, lambda c=scanned_count: self.lbl_dup_status.configure(text=f"Scanned: {c} files"))
                        
                except OSError:
                    continue

        self.frame.after(0, lambda: self.lbl_dup_status.configure(text="Processing duplicates..."))
        
        for key, paths in files_by_name_size.items():
            if not self.scan_running: break
            
            if len(paths) > 1:
                file_size = key[1]
                original = paths[0]
                for duplicate in paths[1:]:
                    duplicates.append((duplicate, original, file_size))
            
        status_msg = "Scan stopped." if not self.scan_running else f"Done. Found {len(duplicates)} duplicates."
        self.finish_dup_scan(duplicates, status_msg)

    def finish_dup_scan(self, duplicates, msg):
        self.scan_running = False
        
        def _update_ui():
            self.btn_scan_dup.configure(text="Scan for Duplicates", fg_color=["#3B8ED0", "#1F6AA5"], state="normal")
            self.lbl_dup_status.configure(text=msg)
            
            if not duplicates: return

            duplicates.sort(key=lambda x: x[2], reverse=True)
            display_limit = 100
            
            if len(duplicates) > display_limit:
                 ctk.CTkLabel(self.dup_results_frame, 
                              text=f"Showing largest {display_limit} of {len(duplicates)} results...", 
                              text_color="#FFA500", font=ctk.CTkFont(weight="bold")).pack(pady=5)

            for i, (dup_file, original_file, size) in enumerate(duplicates):
                if i >= display_limit: break
                
                row = ctk.CTkFrame(self.dup_results_frame)
                row.pack(fill="x", pady=2)
                
                info_frame = ctk.CTkFrame(row, fg_color="transparent")
                info_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
                
                top_line = ctk.CTkFrame(info_frame, fg_color="transparent")
                top_line.pack(fill="x")
                ctk.CTkLabel(top_line, text=os.path.basename(dup_file), font=ctk.CTkFont(weight="bold")).pack(side="left")
                ctk.CTkLabel(top_line, text=f"({format_size(size)})", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F6AA5").pack(side="left", padx=10)

                ctk.CTkLabel(info_frame, text=f"Duplicate: {dup_file}", font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
                ctk.CTkLabel(info_frame, text=f"Original:  {original_file}", font=ctk.CTkFont(size=10), text_color="gray").pack(anchor="w")
                
                btn_frame = ctk.CTkFrame(row, fg_color="transparent")
                btn_frame.pack(side="right", padx=5)
                
                ctk.CTkButton(btn_frame, text="Open Duplicate", width=100, height=24,
                              command=lambda p=dup_file: self.open_file_location(p)).pack(pady=2)
                ctk.CTkButton(btn_frame, text="Open Original", width=100, height=24, fg_color="gray",
                              command=lambda p=original_file: self.open_file_location(p)).pack(pady=2)

        self.frame.after(0, _update_ui)

    # ===========================
    # Large File Logic
    # ===========================
    def toggle_large_scan(self):
        if self.scan_running:
            self.scan_running = False
            self.btn_scan_large.configure(text="Stopping...", state="disabled")
        else:
            self.start_large_scan()

    def start_large_scan(self):
        scan_path = self.large_path_entry.get()
        if not scan_path or not os.path.isdir(scan_path):
            messagebox.showerror("Error", "Invalid directory path.")
            return
            
        self.scan_running = True
        self.btn_scan_large.configure(text="Stop Scan", fg_color="#c42b1c", hover_color="#8a1c11")
        self.lbl_large_status.configure(text="Scanning...", text_color="gray")
        
        for widget in self.large_results_frame.winfo_children():
            widget.destroy()
            
        threading.Thread(target=self.scan_large_files_thread, args=(scan_path,), daemon=True).start()

    def scan_large_files_thread(self, scan_path):
        large_files = []
        limit_bytes = 100 * 1024 * 1024 # 100 MB
        scanned_count = 0
        
        for root, _, files in os.walk(scan_path):
            if not self.scan_running: break
            
            for file in files:
                if not self.scan_running: break
                
                fpath = os.path.join(root, file)
                scanned_count += 1
                
                try:
                    size = os.path.getsize(fpath)
                    if size > limit_bytes:
                        large_files.append((fpath, size))
                except (OSError, PermissionError):
                    continue
                
                if scanned_count % 200 == 0:
                     self.frame.after(0, lambda c=scanned_count: self.lbl_large_status.configure(text=f"Scanned: {c} files"))
            
        status_msg = "Scan stopped." if not self.scan_running else f"Done. Found {len(large_files)} large files."
        self.finish_large_scan(large_files, status_msg)

    def finish_large_scan(self, large_files, msg):
        self.scan_running = False
        
        def _update_ui():
            self.btn_scan_large.configure(text="Scan for Large Files", fg_color=["#3B8ED0", "#1F6AA5"], state="normal")
            self.lbl_large_status.configure(text=msg)
            
            if not large_files: return
             
            large_files.sort(key=lambda x: x[1], reverse=True)
            
            display_limit = 100
            if len(large_files) > display_limit:
                 ctk.CTkLabel(self.large_results_frame, 
                              text=f"Showing largest {display_limit} of {len(large_files)} results...", 
                              text_color="#FFA500", font=ctk.CTkFont(weight="bold")).pack(pady=5)
            
            for i, (fpath, size) in enumerate(large_files):
                if i >= display_limit: break
                
                row = ctk.CTkFrame(self.large_results_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                size_lbl = ctk.CTkLabel(row, text=format_size(size), width=90, anchor="e", 
                                      font=ctk.CTkFont(weight="bold"), text_color="#1F6AA5")
                size_lbl.pack(side="left", padx=5)
                
                name_lbl = ctk.CTkLabel(row, text=fpath, anchor="w", wraplength=550)
                name_lbl.pack(side="left", padx=5, fill="x", expand=True)

                btn = ctk.CTkButton(row, text="Open Location", width=100, height=24, 
                                    command=lambda p=fpath: self.open_file_location(p))
                btn.pack(side="right", padx=5)

        self.frame.after(0, _update_ui)