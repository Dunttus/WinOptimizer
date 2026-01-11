import customtkinter as ctk
import sys
import os
import traceback

# --- Import Utils ---
try:
    from utils import is_admin
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import 'utils.py'.\n{e}")
    input("Press Enter to exit...")
    sys.exit()

# --- Smart Import Function ---
def safe_import(possible_names, class_name):
    """
    Tries to import a class from a list of possible module names.
    Example: tries 'modules.uninstaller', if missing, tries 'modules.uninstall'
    """
    if isinstance(possible_names, str):
        possible_names = [possible_names]

    for name in possible_names:
        try:
            module = __import__(name, fromlist=[class_name])
            return getattr(module, class_name)
        except ImportError:
            continue # Try the next name in the list
        except Exception as e:
            print(f"ERROR Loading {name}: {e}")
            return None
            
    print(f"ERROR: Could not find module for {class_name} (Checked: {possible_names})")
    return None

# --- LOAD MODULES (Try both naming conventions) ---

DashboardModule = safe_import("modules.dashboard", "DashboardModule")
HardwareModule = safe_import("modules.hardware", "HardwareModule")
WingetModule = safe_import("modules.winget", "WingetModule")

# TRY: 'uninstaller.py' OR 'uninstall.py'
UninstallerModule = safe_import(["modules.uninstaller", "modules.uninstall"], "UninstallerModule")

TweaksModule = safe_import("modules.tweaks", "TweaksModule")
CleanerModule = safe_import("modules.cleaner", "CleanerModule")

# TRY: 'scanner.py' OR 'scanning.py'
ScannerModule = safe_import(["modules.scanner", "modules.scanning"], "ScannerModule")

StartupModule = safe_import("modules.startup", "StartupModule")
ServicesModule = safe_import("modules.services", "ServicesModule")
ProcessesModule = safe_import("modules.processes", "ProcessesModule")
PowerModule = safe_import("modules.power", "PowerModule")
RepairModule = safe_import("modules.repair", "RepairModule")
NetworkModule = safe_import("modules.network", "NetworkModule")

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

        # --- Sidebar ---
        self.sidebar_container = ctk.CTkFrame(self, width=260, corner_radius=0)
        self.sidebar_container.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar_container, text="WIN11 OPTIMIZE", 
                                       font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(pady=(30, 20))

        self.sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar_container, fg_color="transparent", corner_radius=0)
        self.sidebar_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        self.modules = {}
        self.current_module_key = None
        self.nav_buttons = {}
        
        # --- Menu Structure ---
        # Note: 'items' contains (Name, Internal_Key, Module_Class)
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
                    ('Process Priority', 'processes', ProcessesModule),
                    ('Power Plans', 'power', PowerModule)
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
        
        # Build Sidebar
        for section in self.menu_structure:
            section_box = ctk.CTkFrame(self.sidebar_scroll, fg_color="#2b2b2b", border_width=1, border_color="#3d3d3d")
            section_box.pack(fill="x", pady=(0, 15), padx=5)

            header_lbl = ctk.CTkLabel(section_box, text=section['header'].upper(), 
                                      font=ctk.CTkFont(size=11, weight="bold"),
                                      text_color="gray60")
            header_lbl.pack(fill="x", padx=10, pady=(10, 5), anchor="w")

            for name, key, mod_class in section['items']:
                # Only create button if module loaded successfully
                if mod_class:
                    btn = self.create_nav_btn(section_box, name, key, mod_class)
                    if first_module_key is None:
                        first_module_key = key

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        if first_module_key:
            self.show_module(first_module_key)

    def create_nav_btn(self, parent, text, key, mod_class):
        btn = ctk.CTkButton(parent, text=text, corner_radius=6, height=35, 
                            fg_color="transparent", text_color="gray90", 
                            hover_color="#3d3d3d", anchor="w", 
                            command=lambda k=key: self.show_module(k))
        btn.pack(fill="x", padx=5, pady=2)
        self.nav_buttons[key] = btn
        self.nav_buttons[key].mod_class = mod_class
        return btn

    def show_module(self, key):
        # 1. Stop background threads (Dashboard)
        if self.current_module_key == "dashboard" and "dashboard" in self.modules:
            if hasattr(self.modules["dashboard"], "stop_monitoring"):
                self.modules["dashboard"].stop_monitoring()

        # 2. Hide current frame
        if self.current_module_key and self.current_module_key in self.modules:
            self.modules[self.current_module_key].frame.pack_forget()

        # 3. Update Styles
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color="#1f538d", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="gray90")

        # 4. Initialize (Lazy Load)
        if key not in self.modules:
            try:
                mod_class = self.nav_buttons[key].mod_class
                self.modules[key] = mod_class(self.main_frame)
            except Exception as e:
                print(f"Error initializing {key}: {e}")
                traceback.print_exc()
                return

        # 5. Show Frame
        if key in self.modules:
            self.modules[key].frame.pack(fill="both", expand=True)

            # 6. Async Triggers
            if key == "dashboard" and hasattr(self.modules[key], "start_monitoring"):
                self.modules[key].start_monitoring()
            
            if key == "hardware" and hasattr(self.modules[key], "start_load"):
                self.modules[key].start_load()
            
            if key == "power" and hasattr(self.modules[key], "load_power_plans"):
                self.modules[key].load_power_plans()
                if hasattr(self.modules[key], "fetch_current_timeouts"):
                     self.modules[key].fetch_current_timeouts()

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