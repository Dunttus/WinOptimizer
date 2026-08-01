import sys
import os
import importlib
import traceback
import tkinter as tk
from modules.dashboard import DashboardTab

# Sidebar menu configuration mapping titles to internal identifiers
NAV_ITEMS = [
    ("Dashboard", "dashboard"),
    ("Package Manager", "winget"),
    ("Bloat Uninstaller", "bloat_uninstaller"),
    ("Privacy & Tweaks", "tweaks"),
    ("System Cleaner", "cleaner"),
    ("File Scanner", "scanner"),
    ("Startup Manager", "startup"),
    ("Service Manager", "services"),
    ("Process Priority", "process_priority"),
    ("Network Tools", "network_tools"),
    ("Windows Repair", "repair"),
]


class MainWindow(tk.Tk):
    """Main Application Container for WinOptimize 11 - Wibe Suite."""
    def __init__(self):
        super().__init__()
        self.title("WinOptimize 11 - Wibe Suite")
        self.geometry("1180x760")
        self.minsize(980, 660)
        self.configure(bg="#1c1c1c")

        self.views = {}
        self.nav_buttons = {}

        self.init_ui()

    def init_ui(self):
        # ------------------ SIDEBAR ------------------
        sidebar = tk.Frame(self, bg="#1e1e1e", width=210, highlightbackground="#2b2b2b", highlightthickness=1)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # "MENU" Header
        brand_lbl = tk.Label(
            sidebar, text="MENU", fg="#ffffff", bg="#1e1e1e",
            font=("Segoe UI", 12, "bold")
        )
        brand_lbl.pack(anchor="w", padx=20, pady=(20, 16))

        # ------------------ MAIN CONTENT AREA ------------------
        self.content_container = tk.Frame(self, bg="#1c1c1c")
        self.content_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Build Navigation Buttons & Load Views
        for title, mod_key in NAV_ITEMS:
            btn = tk.Button(
                sidebar, text=title, fg="#a0a0a0", bg="#1e1e1e",
                activebackground="#333333", activeforeground="#ffffff",
                font=("Segoe UI", 10), anchor="w", bd=0, padx=16, pady=8,
                cursor="hand2", command=lambda k=mod_key: self.switch_view(k)
            )
            btn.pack(fill=tk.X, padx=0, pady=1)
            self.nav_buttons[mod_key] = btn

            # Load module view
            view_widget = self.load_module_view(mod_key)
            if view_widget is None:
                view_widget = self.create_placeholder_view(title)
            
            self.views[mod_key] = view_widget

        # Select Dashboard by default
        self.switch_view("dashboard")

    def load_module_view(self, mod_key):
        """Maps suite keys to correct module files and loads their Tkinter frame classes."""
        if mod_key == "dashboard":
            return DashboardTab(self.content_container)

        # Explicit mapping from menu keys to actual module filenames in modules/
        file_mapping = {
            "winget": "winget",
            "bloat_uninstaller": "uninstaller",
            "privacy_tweaks": "tweaks",
            "system_cleaner": "system_cleaner",
            "file_scanner": "file_scanner",
            "startup_manager": "startup_manager",
            "service_manager": "service_manager",
            "process_priority": "processes",
            "network_tools": "network",
            "windows_repair": "windows_repair"
        }
        
        target_mod = file_mapping.get(mod_key, mod_key)

        try:
            mod = importlib.import_module(f"modules.{target_mod}")
            
            # 1. Look for any class inside the file that inherits from tk.Widget
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type) and issubclass(attr, tk.Widget) and attr is not tk.Frame and attr is not tk.Widget:
                    if attr.__module__ == mod.__name__:
                        return attr(self.content_container)
            
            # 2. Look for common builder function names
            for func_name in ["create_tab", "create_frame", "get_view", "main"]:
                if hasattr(mod, func_name):
                    func = getattr(mod, func_name)
                    res = func(self.content_container)
                    if isinstance(res, tk.Widget):
                        return res

            raise Exception(f"File 'modules/{target_mod}.py' loaded, but no compatible tk.Frame class found.")

        except ModuleNotFoundError as e:
            if e.name == f"modules.{target_mod}":
                return None
            else:
                return self.create_error_view(target_mod, traceback.format_exc())
        except Exception:
            return self.create_error_view(target_mod, traceback.format_exc())

    def create_placeholder_view(self, title):
        """Fallback view shown if a module file is missing."""
        frame = tk.Frame(self.content_container, bg="#1c1c1c")
        lbl = tk.Label(
            frame, text=f"{title} Module", fg="#666666", bg="#1c1c1c",
            font=("Segoe UI", 16, "bold")
        )
        lbl.pack(expand=True)
        return frame

    def create_error_view(self, mod_name, trace):
        """Displays error info if a module crashes on load."""
        frame = tk.Frame(self.content_container, bg="#1c1c1c")
        lbl = tk.Label(
            frame, text=f"⚠️ Crash while loading modules/{mod_name}.py", 
            fg="#ff5555", bg="#1c1c1c", font=("Segoe UI", 14, "bold")
        )
        lbl.pack(anchor="w", padx=20, pady=(20, 5))
        txt = tk.Text(frame, bg="#111111", fg="#cccccc", font=("Consolas", 10), bd=0, padx=10, pady=10)
        txt.insert("1.0", trace)
        txt.config(state="disabled")
        txt.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        return frame

    def switch_view(self, view_key):
        """Switches visible content frame and updates active button state."""
        for frame in self.views.values():
            if frame:
                frame.pack_forget()

        if view_key in self.views and self.views[view_key]:
            self.views[view_key].pack(fill=tk.BOTH, expand=True)

        for key, btn in self.nav_buttons.items():
            if key == view_key:
                btn.config(bg="#383838", fg="#ffffff", font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg="#1e1e1e", fg="#a0a0a0", font=("Segoe UI", 10))


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()