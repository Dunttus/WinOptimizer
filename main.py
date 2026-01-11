import customtkinter as ctk
import sys
import os
import traceback # Added for debugging

# --- Import Utils ---
try:
    from utils import is_admin
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import 'utils.py'.\n{e}")
    input("Press Enter to exit...")
    sys.exit()

# --- Module Imports (Safe Mode) ---
def safe_import(module_path, class_name):
    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    except Exception as e:
        print(f"ERROR Loading {module_path}: {e}")
        traceback.print_exc()
        return None

# Import all modules safely
DashboardModule = safe_import("modules.dashboard", "DashboardModule")
HardwareModule = safe_import("modules.hardware", "HardwareModule")
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

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class WinOptimizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Configuration
        self.title("Win11 Optimize - Wibe Suite")
        self.geometry("1150x750")

        if not is_admin():
            self.withdraw()
            from tkinter import messagebox
            messagebox.showwarning("Admin Required", 
                "This application requires Administrator privileges.\nPlease restart as Admin.")
            sys.exit()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar Container ---
        self.sidebar_container = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar_container.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_container, text="WIN11 OPTIMIZE", 
                                       font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(pady=(30, 20))

        # --- Scrollable Navigation Area ---
        self.sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar_container, fg_color="transparent", corner_radius=0)
        self.sidebar_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self.modules = {}
        self.current_module_key = None
        self.nav_buttons = {}
        
        # --- Menu Structure Definition (Boxed Sections) ---
        self.menu_structure = [
            {
                'header': 'Overview',
                'items': [
                    ('Dashboard', 'dashboard', DashboardModule),
                    ('Hardware Health', 'hardware', HardwareModule)
                ]
            },
            {
                'header': 'Software Management',
                'items': [
                    ('Package Manager', 'winget', WingetModule),
                    ('Bloat Uninstaller', 'uninstaller', UninstallerModule)
                ]
            },
            {
                'header': 'System Optimization',
                'items': [
                    ('Privacy & Tweaks', 'tweaks', TweaksModule),
                    ('System Cleaner', 'cleaner', CleanerModule),
                    ('File Scanner', 'scanner', ScannerModule),
                    ('Startup Manager', 'startup', StartupModule),
                    ('Service Manager', 'services', ServicesModule),
                    ('Process Priority', 'processes', ProcessesModule)
                ]
            },
            {
                'header': 'Diagnostics & Repair',
                'items': [
                    ('Network Tools', 'network', NetworkModule),
                    ('Windows Repair', 'repair', RepairModule)
                ]
            }
        ]

        first_module_key = None
        
        # Build the Boxed Sidebar UI
        for section in self.menu_structure:
            # Create a box (Frame) for each category
            section_box = ctk.CTkFrame(self.sidebar_scroll, fg_color="#2b2b2b", border_width=1, border_color="#3d3d3d")
            section_box.pack(fill="x", pady=(0, 15), padx=5)

            # Add Header inside the box
            header_lbl = ctk.CTkLabel(section_box, text=section['header'].upper(), 
                                      font=ctk.CTkFont(size=11, weight="bold"),
                                      text_color="gray60")
            header_lbl.pack(fill="x", padx=10, pady=(10, 5), anchor="w")

            # Add Buttons inside the box
            for name, key, mod_class in section['items']:
                if mod_class:
                    btn = self.create_nav_btn(section_box, name, key, mod_class)
                    if first_module_key is None:
                        first_module_key = key
                else:
                    print(f"Skipped {name}: Module load error.")

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        if first_module_key:
            self.show_module(first_module_key)

    def create_nav_btn(self, parent, text, key, mod_class):
        """Creates and stores a navigation button."""
        btn = ctk.CTkButton(parent, text=text, corner_radius=6, height=35, 
                            fg_color="transparent", text_color="gray90", 
                            hover_color="#3d3d3d", anchor="w", 
                            command=lambda k=key: self.show_module(k))
        btn.pack(fill="x", padx=5, pady=2)
        self.nav_buttons[key] = btn
        # Store module class reference for lazy loading
        self.nav_buttons[key].mod_class = mod_class
        return btn

    def show_module(self, key):
        """Switches between modules and triggers background loading."""
        # 1. Stop background threads
        if self.current_module_key == "dashboard" and "dashboard" in self.modules:
            if hasattr(self.modules["dashboard"], "stop_monitoring"):
                self.modules["dashboard"].stop_monitoring()

        # 2. Hide current frame
        if self.current_module_key and self.current_module_key in self.modules:
            self.modules[self.current_module_key].frame.pack_forget()

        # 3. Update Button Styles
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color="#1f538d", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="gray90")

        # 4. Initialize module (Lazy Load)
        if key not in self.modules:
            try:
                mod_class = self.nav_buttons[key].mod_class
                self.modules[key] = mod_class(self.main_frame)
            except Exception as e:
                print(f"Error initializing {key}: {e}")
                traceback.print_exc()
                return

        # 5. Show frame
        if key in self.modules:
            self.modules[key].frame.pack(fill="both", expand=True)

            # 6. ASYNC LOADING TRIGGERS
            if key == "dashboard" and hasattr(self.modules[key], "start_monitoring"):
                self.modules[key].start_monitoring()
            
            # FIX: Trigger async load for Hardware Health to prevent freezing
            if key == "hardware" and hasattr(self.modules[key], "start_load"):
                self.modules[key].start_load()
                
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