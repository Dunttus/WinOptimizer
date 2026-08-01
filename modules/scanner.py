import os
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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


class ScannerModule(tk.Frame):
    """Unified, single-scroll File Scanner Module (Duplicates & Large Files)."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")
        self.scan_running = False

        # --- Master Single-Scroll Canvas Setup ---
        self.canvas = tk.Canvas(self, bg="#1c1c1c", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas, bg="#1c1c1c")

        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.window_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Make inner frame match window width dynamically
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.window_id, width=e.width))
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Global mousewheel binding for smooth full-page scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ===========================
        # Section 1: Duplicate Finder
        # ===========================
        dup_container = tk.Frame(self.inner_frame, bg="#222222", bd=1, relief="solid")
        dup_container.pack(fill="x", padx=20, pady=15)

        tk.Label(
            dup_container, text="📁 Find Duplicate Files (Name & Size Only)", 
            font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#222222"
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Path Row
        path_row = tk.Frame(dup_container, bg="#222222")
        path_row.pack(fill="x", padx=20, pady=5)
        
        self.dup_path_entry = tk.Entry(path_row, bg="#111111", fg="#ffffff", insertbackground="white", font=("Segoe UI", 10), bd=1, relief="solid")
        self.dup_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=6)
        self.dup_path_entry.insert(0, "Select folder to scan...")
        self.dup_path_entry.bind("<FocusIn>", lambda e: self.dup_path_entry.delete(0, 'end') if self.dup_path_entry.get() == "Select folder to scan..." else None)

        tk.Button(path_row, text="Browse", width=12, command=lambda: self.browse_folder(self.dup_path_entry), bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", pady=6).pack(side="right")

        # Extension Filter Row
        ext_row = tk.Frame(dup_container, bg="#222222")
        ext_row.pack(fill="x", padx=20, pady=5)
        
        tk.Label(ext_row, text="Filter extensions (comma separated):", fg="#b0b0b0", bg="#222222", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        
        self.ext_entry = tk.Entry(ext_row, width=30, bg="#111111", fg="#ffffff", insertbackground="white", font=("Segoe UI", 10), bd=1, relief="solid")
        self.ext_entry.pack(side="left", ipady=4)
        self.ext_entry.insert(0, "e.g. .mp4, jpg, .pdf")
        self.ext_entry.bind("<FocusIn>", lambda e: self.ext_entry.delete(0, 'end') if self.ext_entry.get() == "e.g. .mp4, jpg, .pdf" else None)

        # Control Area
        ctrl_frame = tk.Frame(dup_container, bg="#222222")
        ctrl_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_scan_dup = tk.Button(ctrl_frame, text="Scan for Duplicates", command=self.toggle_dup_scan, bg="#3B8ED0", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", padx=16, pady=6)
        self.btn_scan_dup.pack(side="left")
        
        self.lbl_dup_status = tk.Label(ctrl_frame, text="Ready", fg="#888888", bg="#222222", font=("Segoe UI", 9))
        self.lbl_dup_status.pack(side="left", padx=15)

        # Results Container
        self.dup_results_outer = tk.Frame(dup_container, bg="#1c1c1c", bd=1, relief="solid")
        self.dup_results_outer.pack(fill="x", padx=20, pady=(5, 20))
        tk.Label(self.dup_results_outer, text=" Found Duplicates ", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
        
        self.dup_results_list = tk.Frame(self.dup_results_outer, bg="#1c1c1c")
        self.dup_results_list.pack(fill="x", padx=5, pady=5)

        # ===========================
        # Section 2: Large Files
        # ===========================
        large_container = tk.Frame(self.inner_frame, bg="#222222", bd=1, relief="solid")
        large_container.pack(fill="x", padx=20, pady=(10, 25))

        tk.Label(
            large_container, text="🗄️ Find Large Files (>100MB)", 
            font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#222222"
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Path Row
        large_path_row = tk.Frame(large_container, bg="#222222")
        large_path_row.pack(fill="x", padx=20, pady=5)
        
        self.large_path_entry = tk.Entry(large_path_row, bg="#111111", fg="#ffffff", insertbackground="white", font=("Segoe UI", 10), bd=1, relief="solid")
        self.large_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=6)
        self.large_path_entry.insert(0, "Select folder to scan...")
        self.large_path_entry.bind("<FocusIn>", lambda e: self.large_path_entry.delete(0, 'end') if self.large_path_entry.get() == "Select folder to scan..." else None)

        tk.Button(large_path_row, text="Browse", width=12, command=lambda: self.browse_folder(self.large_path_entry), bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", pady=6).pack(side="right")

        # Control Area
        l_ctrl_frame = tk.Frame(large_container, bg="#222222")
        l_ctrl_frame.pack(fill="x", padx=20, pady=10)

        self.btn_scan_large = tk.Button(l_ctrl_frame, text="Scan for Large Files", command=self.toggle_large_scan, bg="#3B8ED0", fg="white", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", padx=16, pady=6)
        self.btn_scan_large.pack(side="left")
        
        self.lbl_large_status = tk.Label(l_ctrl_frame, text="Ready", fg="#888888", bg="#222222", font=("Segoe UI", 9))
        self.lbl_large_status.pack(side="left", padx=15)

        # Results Container
        self.large_results_outer = tk.Frame(large_container, bg="#1c1c1c", bd=1, relief="solid")
        self.large_results_outer.pack(fill="x", padx=20, pady=(5, 20))
        tk.Label(self.large_results_outer, text=" Files > 100MB ", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 0))

        self.large_results_list = tk.Frame(self.large_results_outer, bg="#1c1c1c")
        self.large_results_list.pack(fill="x", padx=5, pady=5)

    def _on_mousewheel(self, event):
        try:
            if self.winfo_exists():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def clear_container(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

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
            norm_path = os.path.normpath(filepath)
            if os.path.exists(norm_path):
                # Using /select ensures Windows Explorer opens and highlights the target file
                subprocess.run(f'explorer.exe /select, "{norm_path}"', shell=True)
            else:
                messagebox.showerror("Error", f"File not found:\n{norm_path}")
        except Exception as e:
            print(f"Error opening location: {e}")

    # ===========================
    # Duplicate Logic
    # ===========================
    def toggle_dup_scan(self):
        if self.scan_running:
            self.scan_running = False
            self.btn_scan_dup.config(text="Stopping...", state="disabled")
        else:
            self.start_duplicate_scan()

    def start_duplicate_scan(self):
        scan_path = self.dup_path_entry.get()
        if not scan_path or scan_path == "Select folder to scan..." or not os.path.isdir(scan_path):
            messagebox.showerror("Error", "Invalid directory path.")
            return
        
        ext_filter = self.ext_entry.get().strip()
        if ext_filter and ext_filter != "e.g. .mp4, jpg, .pdf":
            extensions = [f".{e.strip().lstrip('.')}" for e in ext_filter.split(',')]
        else:
            extensions = None
        
        self.scan_running = True
        self.btn_scan_dup.config(text="Stop Scan", bg="#c42b1c", fg="white")
        self.lbl_dup_status.config(text="Initializing...", fg="gray")
        
        self.clear_container(self.dup_results_list)

        threading.Thread(target=self.scan_duplicates_thread, args=(scan_path, extensions), daemon=True).start()

    def scan_duplicates_thread(self, scan_path, extensions):
        files_by_name_size = {}
        duplicates = []
        scanned_count = 0
        
        self.after(0, lambda: self.lbl_dup_status.config(text="Scanning file system..."))
        
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
                        self.after(0, lambda c=scanned_count: self.lbl_dup_status.config(text=f"Scanned: {c} files"))
                        
                except OSError:
                    continue

        self.after(0, lambda: self.lbl_dup_status.config(text="Processing duplicates..."))
        
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
            self.btn_scan_dup.config(text="Scan for Duplicates", bg="#3B8ED0", fg="white", state="normal")
            self.lbl_dup_status.config(text=msg)
            
            if not duplicates: return

            duplicates.sort(key=lambda x: x[2], reverse=True)
            display_limit = 100
            
            self.clear_container(self.dup_results_list)

            if len(duplicates) > display_limit:
                 tk.Label(
                     self.dup_results_list, text=f"Showing largest {display_limit} of {len(duplicates)} results...", 
                     fg="#FFA500", bg="#1c1c1c", font=("Segoe UI", 9, "bold")
                 ).pack(pady=8, padx=10, anchor="w")

            for i, (dup_file, original_file, size) in enumerate(duplicates):
                if i >= display_limit: break
                
                row = tk.Frame(self.dup_results_list, bg="#2a2a2a", bd=1, relief="solid")
                row.pack(fill="x", pady=4, padx=5)
                row.grid_columnconfigure(0, weight=1)
                row.grid_columnconfigure(1, weight=0)

                info_frame = tk.Frame(row, bg="#2a2a2a")
                info_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)
                
                top_line = tk.Frame(info_frame, bg="#2a2a2a")
                top_line.pack(fill="x", pady=(0, 2))
                
                tk.Label(top_line, text=os.path.basename(dup_file), font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#2a2a2a").pack(side="left")
                tk.Label(top_line, text=f"({format_size(size)})", font=("Segoe UI", 10, "bold"), fg="#3B8ED0", bg="#2a2a2a").pack(side="left", padx=10)

                tk.Label(info_frame, text=f"Duplicate: {dup_file}", font=("Segoe UI", 9), fg="#cccccc", bg="#2a2a2a", anchor="w").pack(anchor="w", fill="x")
                tk.Label(info_frame, text=f"Original:  {original_file}", font=("Segoe UI", 9), fg="#888888", bg="#2a2a2a", anchor="w").pack(anchor="w", fill="x")
                
                btn_frame = tk.Frame(row, bg="#2a2a2a")
                btn_frame.grid(row=0, column=1, sticky="e", padx=12, pady=8)
                
                tk.Button(btn_frame, text="Open Duplicate", width=14, bg="#383838", fg="white", font=("Segoe UI", 8, "bold"), bd=0, cursor="hand2", padx=5, pady=4, command=lambda p=dup_file: self.open_file_location(p)).pack(pady=3)
                tk.Button(btn_frame, text="Open Original", width=14, bg="#444444", fg="white", font=("Segoe UI", 8, "bold"), bd=0, cursor="hand2", padx=5, pady=4, command=lambda p=original_file: self.open_file_location(p)).pack(pady=3)

        self.after(0, _update_ui)

    # ===========================
    # Large File Logic
    # ===========================
    def toggle_large_scan(self):
        if self.scan_running:
            self.scan_running = False
            self.btn_scan_large.config(text="Stopping...", state="disabled")
        else:
            self.start_large_scan()

    def start_large_scan(self):
        scan_path = self.large_path_entry.get()
        if not scan_path or scan_path == "Select folder to scan..." or not os.path.isdir(scan_path):
            messagebox.showerror("Error", "Invalid directory path.")
            return
            
        self.scan_running = True
        self.btn_scan_large.config(text="Stop Scan", bg="#c42b1c", fg="white")
        self.lbl_large_status.config(text="Scanning...", fg="gray")
        
        self.clear_container(self.large_results_list)
            
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
                     self.after(0, lambda c=scanned_count: self.lbl_large_status.config(text=f"Scanned: {c} files"))
            
        status_msg = "Scan stopped." if not self.scan_running else f"Done. Found {len(large_files)} large files."
        self.finish_large_scan(large_files, status_msg)

    def finish_large_scan(self, large_files, msg):
        self.scan_running = False
        
        def _update_ui():
            self.btn_scan_large.config(text="Scan for Large Files", bg="#3B8ED0", fg="white", state="normal")
            self.lbl_large_status.config(text=msg)
            
            if not large_files: return
             
            large_files.sort(key=lambda x: x[1], reverse=True)
            self.clear_container(self.large_results_list)
            
            display_limit = 100
            if len(large_files) > display_limit:
                 tk.Label(
                     self.large_results_list, text=f"Showing largest {display_limit} of {len(large_files)} results...", 
                     fg="#FFA500", bg="#1c1c1c", font=("Segoe UI", 9, "bold")
                 ).pack(pady=8, padx=10, anchor="w")
            
            for i, (fpath, size) in enumerate(large_files):
                if i >= display_limit: break
                
                row = tk.Frame(self.large_results_list, bg="#2a2a2a", bd=1, relief="solid")
                row.pack(fill="x", pady=4, padx=5)
                row.grid_columnconfigure(0, weight=0)
                row.grid_columnconfigure(1, weight=1)
                row.grid_columnconfigure(2, weight=0)

                size_lbl = tk.Label(
                    row, text=format_size(size), width=12, anchor="e", 
                    font=("Segoe UI", 10, "bold"), fg="#3B8ED0", bg="#2a2a2a"
                )
                size_lbl.grid(row=0, column=0, padx=12, pady=10, sticky="w")
                
                name_lbl = tk.Label(row, text=fpath, anchor="w", fg="#ffffff", bg="#2a2a2a", font=("Segoe UI", 9))
                name_lbl.grid(row=0, column=1, padx=5, sticky="ew")

                btn = tk.Button(
                    row, text="Open Location", width=14, height=1, 
                    bg="#383838", fg="white", font=("Segoe UI", 8, "bold"), bd=0, cursor="hand2", padx=5, pady=4,
                    command=lambda p=fpath: self.open_file_location(p)
                )
                btn.grid(row=0, column=2, padx=12, pady=8, sticky="e")

        self.after(0, _update_ui)

# Compatibility alias for main.py dynamic routing
FileScannerTab = ScannerModule