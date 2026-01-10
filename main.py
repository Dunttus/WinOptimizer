import customtkinter as ctk
import sys
import os
import traceback # Added for debugging

# --- Import Utils ---
# We try to import utils first. If this fails, the app cannot run.
try:
    from utils import is_admin
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import 'utils.py'.\n{e}")
    input("Press Enter to exit...")
    sys.exit()

# --- Module Imports (Safe Mode) ---
# We wrap these in try/except so the app launches even if one module is broken.
modules_status = {}

def safe_import(module_path, class_name):
    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    except Exception as e:
        print(f"❌ ERROR Loading {module_path}: {e}")
        # Print full traceback to help identify syntax errors
        traceback.print_exc()
        return None

# Import all modules safely
DashboardModule = safe_import("modules.dashboard", "DashboardModule")
WingetModule = safe_import("modules.winget", "WingetModule")
UninstallerModule = safe_import("modules.uninstaller", "UninstallerModule")
TweaksModule = safe_import("modules.tweaks", "TweaksModule")
CleanerModule = safe_import("modules.cleaner", "CleanerModule")
ScannerModule = safe_import("modules.scanner", "ScannerModule")
StartupModule = safe_import("modules.startup", "StartupModule")
ServicesModule = safe_import("modules.services", "ServicesModule")
ProcessesModule = safe_import("modules.processes", "ProcessesModule")
NetworkModule = safe_import("modules.network", "NetworkModule")
RepairModule = safe_import("modules.repair", "RepairModule")

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
                "This application requires Administrator privileges.\nPlease restart as Admin.")
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
        
        # --- LOGICAL MENU SORTING ---
        # Only add buttons for modules that successfully loaded
        self.menu_items = []
        
        # Helper to add item if module exists
        def add_item(name, key, module_class):
            if module_class:
                self.menu_items.append((name, key))
            else:
                print(f"⚠️ Skipped Menu Item '{name}' because module failed to load.")

        add_item("Dashboard", "dashboard", DashboardModule)
        add_item("Package Manager", "winget", WingetModule)
        add_item("Bloat Uninstaller", "uninstaller", UninstallerModule)
        add_item("Privacy & Tweaks", "tweaks", TweaksModule)
        add_item("System Cleaner", "cleaner", CleanerModule)
        add_item("File Scanner", "scanner", ScannerModule)
        add_item("Startup Manager", "startup", StartupModule)
        add_item("Service Manager", "services", ServicesModule)
        add_item("Process Priority", "processes", ProcessesModule)
        add_item("Network Tools", "network", NetworkModule)
        add_item("Windows Repair", "repair", RepairModule)

        # Create Buttons
        for name, key in self.menu_items:
            self.add_nav_btn(name, key)

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # Load Default Module (Dashboard)
        if DashboardModule:
            self.show_module("dashboard")
        elif self.menu_items:
            # If dashboard failed, load the first available module
            self.show_module(self.menu_items[0][1])

    def add_nav_btn(self, name, key):
        """Creates a sidebar button."""
        btn = ctk.CTkButton(self.sidebar, text=name, corner_radius=0, height=45, 
                            border_spacing=10, fg_color="transparent", 
                            text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), 
                            anchor="w", command=lambda k=key: self.show_module(k))
        btn.pack(fill="x", pady=2) 
        self.nav_buttons[key] = btn

    def show_module(self, key):
        """Switches between tabs."""
        
        # 1. Stop background threads if leaving Dashboard
        if self.current_module_key == "dashboard" and "dashboard" in self.modules:
            if hasattr(self.modules["dashboard"], "stop_monitoring"):
                self.modules["dashboard"].stop_monitoring()

        # 2. Hide current frame
        if self.current_module_key and self.current_module_key in self.modules:
            self.modules[self.current_module_key].frame.pack_forget()

        # 3. Highlight Buttons
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=("gray75", "gray25"), text_color=("blue", "white"))
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        # 4. Initialize module (Lazy Load)
        if key not in self.modules:
            try:
                if key == "dashboard": self.modules[key] = DashboardModule(self.main_frame)
                elif key == "winget": self.modules[key] = WingetModule(self.main_frame)
                elif key == "uninstaller": self.modules[key] = UninstallerModule(self.main_frame)
                elif key == "tweaks": self.modules[key] = TweaksModule(self.main_frame)
                elif key == "cleaner": self.modules[key] = CleanerModule(self.main_frame)
                elif key == "scanner": self.modules[key] = ScannerModule(self.main_frame)
                elif key == "startup": self.modules[key] = StartupModule(self.main_frame)
                elif key == "services": self.modules[key] = ServicesModule(self.main_frame)
                elif key == "processes": self.modules[key] = ProcessesModule(self.main_frame)
                elif key == "network": self.modules[key] = NetworkModule(self.main_frame)
                elif key == "repair": self.modules[key] = RepairModule(self.main_frame)
            except Exception as e:
                print(f"🔥 Error initializing {key}: {e}")
                traceback.print_exc()
                return

        # 5. Show frame
        if key in self.modules:
            self.modules[key].frame.pack(fill="both", expand=True)

            # 6. Start Dashboard threads if needed
            if key == "dashboard" and hasattr(self.modules[key], "start_monitoring"):
                self.modules[key].start_monitoring()
                
            self.current_module_key = key

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    try:
        app = WinOptimizerApp()
        app.mainloop()
    except Exception as e:
        print(f"CRITICAL APP CRASH: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")