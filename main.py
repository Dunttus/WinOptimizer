import customtkinter as ctk
from tkinter import messagebox
import sys

# Import Config and Utils
from utils import is_admin
from ui_manager import Win11UXManager

# Import Modules
from modules.dashboard import DashboardModule
from modules.services import ServicesModule
from modules.scanner import ScannerModule
from modules.startup import StartupModule
from modules.power import PowerModule
from modules.cleaner import CleanerModule
from modules.network import NetworkModule
from modules.processes import ProcessesModule

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class WinOptimizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.ux = Win11UXManager() 

        if not is_admin():
            messagebox.showwarning("Permission Denied", "This app requires Administrator privileges for full functionality.\nPlease run as Admin.")

        self.title("WinOptimize 11 - Wibe Suite")
        self.geometry("1100x800")
        self.minsize(950, 650)
        
        try: self.iconbitmap("icon.ico") 
        except: pass

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkScrollableFrame(self, width=220, corner_radius=0, label_text="Menu")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="System Utility", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

        # Dictionary to store modules and button references
        self.modules = {}
        self.nav_buttons = {} 
        
        # Define Navigation
        self.add_nav_btn("Dashboard", "dashboard")
        self.add_nav_btn("Stop Services", "services")
        self.add_nav_btn("File Scanner", "scanner")
        self.add_nav_btn("Startup Manager", "startup")
        self.add_nav_btn("Power Plans", "power")
        self.add_nav_btn("Temp Cleaner", "cleaner")
        self.add_nav_btn("Network Tools", "network")
        self.add_nav_btn("Process Priority", "processes")

        # Default View
        self.current_module = None
        self.show_module("dashboard")

    def add_nav_btn(self, text, module_key):
        # Create button with initial transparent background
        btn = ctk.CTkButton(self.sidebar, text=text, command=lambda: self.show_module(module_key), 
                            fg_color="transparent", text_color=("gray10", "gray90"), anchor="w",
                            hover_color=("gray70", "gray30"))
        btn.grid(sticky="ew", padx=20, pady=5)
        
        # Store button reference to change color later
        self.nav_buttons[module_key] = btn

    def show_module(self, key):
        # 1. Update Buttons (Visual Feedback)
        for k, btn in self.nav_buttons.items():
            if k == key:
                # Active State: Standard CTK Blue (or theme color)
                btn.configure(fg_color=["#3B8ED0", "#1F6AA5"], text_color="white")
            else:
                # Inactive State: Transparent
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        # 2. Logic to Switch Frames
        if self.current_module and hasattr(self.current_module, 'stop_monitoring'):
            self.current_module.stop_monitoring()

        # Hide all frames
        for mod in self.modules.values():
            mod.frame.pack_forget()

        # Initialize if not exists
        if key not in self.modules:
            if key == "dashboard": self.modules[key] = DashboardModule(self.main_frame)
            elif key == "services": self.modules[key] = ServicesModule(self.main_frame)
            elif key == "scanner": self.modules[key] = ScannerModule(self.main_frame)
            elif key == "startup": self.modules[key] = StartupModule(self.main_frame)
            elif key == "power": self.modules[key] = PowerModule(self.main_frame)
            elif key == "cleaner": self.modules[key] = CleanerModule(self.main_frame)
            elif key == "network": self.modules[key] = NetworkModule(self.main_frame)
            elif key == "processes": self.modules[key] = ProcessesModule(self.main_frame)

        # Show new module
        self.current_module = self.modules[key]
        self.current_module.frame.pack(fill="both", expand=True)
        
        # Start monitoring if applicable
        if hasattr(self.current_module, 'start_monitoring'):
            self.current_module.start_monitoring()

if __name__ == "__main__":
    app = WinOptimizerApp()
    app.mainloop()