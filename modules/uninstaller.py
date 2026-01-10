import customtkinter as ctk
import subprocess
import threading
from utils import add_info_section
from config import SAFE_APP_WHITELIST

class UninstallerModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Safe App Uninstaller", 
                         "Only showing non-critical bloatware that is safe to remove.")

        # --- Search Bar ---
        search_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=10)
        
        self.search_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(search_frame, placeholder_text="Filter apps...", 
                                   textvariable=self.search_var, width=300)
        self.entry.pack(side="left", padx=(0, 10))
        self.entry.bind("<KeyRelease>", lambda e: self.filter_list()) # Real-time filtering

        ctk.CTkButton(search_frame, text="Refresh List", command=self.load_apps).pack(side="left")

        # --- App List ---
        self.scroll = ctk.CTkScrollableFrame(self.frame, label_text="Safe-to-Remove Bloatware")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=10)

        self.all_apps = [] # Storage for filtering
        self.load_apps()

    def load_apps(self):
        for widget in self.scroll.winfo_children():
            widget.destroy()

        loading_lbl = ctk.CTkLabel(self.scroll, text="Filtering system packages for safe apps...")
        loading_lbl.pack(pady=20)

        def _fetch():
            # Get all installed packages for current user
            cmd = 'powershell "Get-AppxPackage | Select-Object Name, PackageFullName"'
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                result = subprocess.check_output(cmd, startupinfo=si, shell=True).decode().strip()
                lines = result.split('\n')[2:] 
                
                self.all_apps = []
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        full_name = parts[-1]
                        package_name = parts[0]
                        
                        # CHECK AGAINST WHITELIST
                        if any(safe_app in package_name for safe_app in SAFE_APP_WHITELIST):
                            display_name = package_name.replace("Microsoft.", "").replace("Windows.", "")
                            self.all_apps.append((display_name, full_name))
                
                self.all_apps.sort()
                self.frame.after(0, lambda: self.render_apps(self.all_apps, loading_lbl))
            except Exception as e:
                print(f"Fetch Error: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def filter_list(self):
        """Filters the already loaded list locally (very fast)."""
        query = self.search_var.get().lower()
        filtered = [a for a in self.all_apps if query in a[0].lower()]
        
        # Clear and re-render
        for widget in self.scroll.winfo_children():
            widget.destroy()
        self.render_apps(filtered)

    def render_apps(self, apps, loading_lbl=None):
        if loading_lbl: loading_lbl.destroy()
        
        if not apps:
            ctk.CTkLabel(self.scroll, text="No safe apps found or everything is already clean.", text_color="gray").pack(pady=20)
            return

        for display_name, full_name in apps:
            row = ctk.CTkFrame(self.scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=display_name, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, fill="x", expand=True)
            
            btn = ctk.CTkButton(row, text="Uninstall", width=100, fg_color="#c42b1c", hover_color="#8a1c11")
            btn.configure(command=lambda b=btn, f=full_name: self.uninstall_app(f, b))
            btn.pack(side="right", padx=10)

    def uninstall_app(self, full_name, button):
        button.configure(text="Removing...", state="disabled", fg_color="gray30")
        
        def _target():
            cmd = f'powershell "Remove-AppxPackage -Package {full_name}"'
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, startupinfo=si, shell=True, capture_output=True)
            
            if result.returncode == 0:
                self.frame.after(0, lambda: button.configure(text="Removed ✓", fg_color="gray20"))
            else:
                self.frame.after(0, lambda: button.configure(text="Failed", fg_color="gray20"))

        threading.Thread(target=_target, daemon=True).start()