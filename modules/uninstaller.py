import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
from config import SAFE_TO_REMOVE_APPS

class ScrollableFrame:
    """Custom standard Tkinter scrollable container."""
    def __init__(self, container, bg_color):
        self.frame = tk.Frame(container, bg=bg_color)
        
        self.canvas = tk.Canvas(self.frame, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas, bg=bg_color)
        
        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if self.inner_frame.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
    def clear(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

    def pack(self, *args, **kwargs):
        self.frame.pack(*args, **kwargs)
        
    def pack_forget(self):
        self.frame.pack_forget()


class UninstallerModule(tk.Frame):
    """Native Tkinter Safe App Uninstaller Module utilizing config.py."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")

        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="Safe App Uninstaller", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Only showing non-critical bloatware that is safe to remove, pulled from config.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Search Bar ---
        search_frame = tk.Frame(self, bg="#1c1c1c")
        search_frame.pack(fill="x", padx=20, pady=10)
        
        self.search_var = tk.StringVar()
        self.entry = tk.Entry(
            search_frame, textvariable=self.search_var, width=40, 
            bg="#111111", fg="#ffffff", insertbackground="white", 
            font=("Segoe UI", 10), bd=1, relief="solid"
        )
        self.entry.pack(side="left", padx=(0, 10), ipady=4)
        self.entry.insert(0, "Filter apps...")
        self.entry.bind("<FocusIn>", lambda e: self.entry.delete(0, 'end') if self.entry.get() == "Filter apps..." else None)
        self.entry.bind("<KeyRelease>", lambda e: self.filter_list())

        tk.Button(
            search_frame, text="Refresh List", command=self.load_apps, 
            bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), 
            bd=0, cursor="hand2", padx=15, pady=4
        ).pack(side="left")

        # --- App List Container ---
        self.scroll = ScrollableFrame(self, bg_color="#1c1c1c")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self.all_apps = [] 
        self.load_apps()

    def load_apps(self):
        self.scroll.clear()

        loading_lbl = tk.Label(
            self.scroll.inner_frame, text="Filtering system packages for safe apps...", 
            fg="gray", bg="#1c1c1c", font=("Segoe UI", 10)
        )
        loading_lbl.pack(pady=20)

        def _fetch():
            cmd = 'powershell -NoProfile -Command "Get-AppxPackage | Select-Object Name, PackageFullName | ConvertTo-Json"'
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                result = subprocess.check_output(
                    cmd, startupinfo=si, shell=True, 
                    text=True, encoding='utf-8', errors='ignore'
                ).strip()
                
                temp_apps = []
                if result:
                    data = json.loads(result)
                    if isinstance(data, dict):
                        data = [data]
                        
                    for item in data:
                        package_name = item.get("Name", "")
                        full_name = item.get("PackageFullName", "")
                        
                        if package_name and full_name:
                            if any(safe_app.lower() in package_name.lower() for safe_app in SAFE_TO_REMOVE_APPS):
                                display_name = package_name.replace("Microsoft.", "").replace("Windows.", "")
                                temp_apps.append((display_name, full_name))
                
                temp_apps = sorted(list(set(temp_apps)))
                self.all_apps = temp_apps
                self.after(0, lambda: self.render_apps(self.all_apps))
            except Exception as e:
                print(f"Fetch Error: {e}")
                self.after(0, lambda: self.render_apps([]))

        threading.Thread(target=_fetch, daemon=True).start()

    def filter_list(self):
        query = self.search_var.get().lower()
        if query == "filter apps...":
            query = ""
            
        filtered = [a for a in self.all_apps if query in a[0].lower()]
        self.render_apps(filtered)

    def render_apps(self, apps):
        self.scroll.clear()
        parent = self.scroll.inner_frame
        
        if not apps:
            tk.Label(
                parent, text="No safe apps found or everything is already clean.", 
                fg="gray", bg="#1c1c1c", font=("Segoe UI", 10)
            ).pack(pady=20)
            return

        for idx, (display_name, full_name) in enumerate(apps):
            bg = "#222222" if idx % 2 == 0 else "#1c1c1c"
            row = tk.Frame(parent, bg=bg)
            row.pack(fill="x", pady=2, padx=5)
            
            tk.Label(
                row, text=display_name, anchor="w", fg="#ffffff", 
                bg=bg, font=("Segoe UI", 9, "bold")
            ).pack(side="left", padx=10, pady=8, fill="x", expand=True)
            
            btn = tk.Button(
                row, text="Uninstall", width=10, bg="#c42b1c", fg="white", 
                font=("Segoe UI", 9, "bold"), activebackground="#A32014", 
                activeforeground="white", bd=0, cursor="hand2"
            )
            btn.configure(command=lambda f=full_name, b=btn: self.uninstall_app(f, b))
            btn.pack(side="right", padx=10, pady=6)

    def uninstall_app(self, full_name, button):
        button.config(text="Removing...", state="disabled", bg="gray30")
        
        def _target():
            cmd = f'powershell -NoProfile -Command "Remove-AppxPackage -Package {full_name}"'
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            try:
                result = subprocess.run(
                    cmd, startupinfo=si, shell=True, capture_output=True, 
                    text=True, encoding='utf-8', errors='ignore'
                )
                
                if result.returncode == 0:
                    self.after(0, lambda: button.config(text="Removed ✓", bg="gray20"))
                else:
                    self.after(0, lambda: button.config(text="Failed", bg="gray20", state="normal"))
            except Exception:
                self.after(0, lambda: button.config(text="Failed", bg="gray20", state="normal"))

        threading.Thread(target=_target, daemon=True).start()

# Compatibility aliases for main.py dynamic loading
BloatUninstallerTab = UninstallerModule