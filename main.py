import customtkinter as ctk
import sys
import os

# --- Import Modules ---
from modules.dashboard import DashboardModule
from modules.cleaner import CleanerModule
from modules.scanner import ScannerModule
from modules.startup import StartupModule
from modules.services import ServicesModule
from modules.processes import ProcessesModule
from modules.network import NetworkModule
from modules.repair import RepairModule
from modules.uninstaller import UninstallerModule
from modules.winget import WingetModule
from utils import is_admin

# Appearance Settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class WinOptimizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("WinOptimize 11 - Wibe Suite")
        self.geometry("1150x750")

        # Admin Enforcement
        if not is_admin():
            self.withdraw()
            from tkinter import messagebox
            messagebox.showwarning("Admin Required", 
                "This application requires Administrator privileges to modify system services, "
                "repair Windows, and uninstall protected apps.\n\nPlease restart as Admin.")
            sys.exit()

        # --- Layout Structure ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar Frame
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo / Title
        self.logo_label = ctk.CTkLabel(self.sidebar, text="MENU", 
                                       font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=25)

        # Navigation State
        self.modules = {}
        self.current_module_key = None
        self.nav_buttons = {}
        
        # --- NEW LOGICAL SORTING ---
        menu_items = [
            # 1. Overview
            ("Dashboard", "dashboard"),
            
            # 2. Software & Apps (Grouped)
            ("Package Manager", "winget"),
            ("Bloat Uninstaller", "uninstaller"),
            
            # 3. Cleaning & Scanning (Grouped)
            ("System Cleaner", "cleaner"),
            ("File Scanner", "scanner"),
            
            # 4. Deep System Optimization (Grouped)
            ("Startup Manager", "startup"),
            ("Service Manager", "services"),
            ("Process Priority", "processes"),
            
            # 5. Maintenance & Repair (Grouped)
            ("Network Tools", "network"),
            ("Windows Repair", "repair")
        ]

        # Create Buttons
        for name, key in menu_items:
            self.add_nav_btn(name, key)

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Load Default Module
        self.show_module("dashboard")

    def add_nav_btn(self, name, key):
        """Creates a sidebar button with highlighting logic."""
        # Add a visual separator if starting a new group? (Optional logic could go here)
        btn = ctk.CTkButton(self.sidebar, text=name, corner_radius=0, height=45, 
                            border_spacing=10, fg_color="transparent", 
                            text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), 
                            anchor="w", command=lambda k=key: self.show_module(k))
        btn.pack(fill="x", pady=2) # Slight padding between buttons
        self.nav_buttons[key] = btn

    def show_module(self, key):
        """Switches between tabs and manages resource threads."""
        
        # 1. Stop background threads if leaving Dashboard
        if self.current_module_key == "dashboard" and "dashboard" in self.modules:
            self.modules["dashboard"].stop_monitoring()

        # 2. Hide the current frame
        if self.current_module_key and self.current_module_key in self.modules:
            self.modules[self.current_module_key].frame.pack_forget()

        # 3. Update Sidebar Button Highlighting
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=("gray75", "gray25"), text_color=("blue", "white"))
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        # 4. Initialize module if it's the first time visiting
        if key not in self.modules:
            if key == "dashboard": self.modules[key] = DashboardModule(self.main_frame)
            elif key == "winget": self.modules[key] = WingetModule(self.main_frame)
            elif key == "uninstaller": self.modules[key] = UninstallerModule(self.main_frame)
            elif key == "cleaner": self.modules[key] = CleanerModule(self.main_frame)
            elif key == "scanner": self.modules[key] = ScannerModule(self.main_frame)
            elif key == "startup": self.modules[key] = StartupModule(self.main_frame)
            elif key == "services": self.modules[key] = ServicesModule(self.main_frame)
            elif key == "processes": self.modules[key] = ProcessesModule(self.main_frame)
            elif key == "network": self.modules[key] = NetworkModule(self.main_frame)
            elif key == "repair": self.modules[key] = RepairModule(self.main_frame)

        # 5. Show the new frame
        self.modules[key].frame.pack(fill="both", expand=True)

        # 6. Restart background threads if entering Dashboard
        if key == "dashboard":
            self.modules[key].start_monitoring()
            
        self.current_module_key = key

if __name__ == "__main__":
    # Ensure standard DPI awareness for Windows (Fixes blurry text on 4K screens)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = WinOptimizerApp()
    app.mainloop()