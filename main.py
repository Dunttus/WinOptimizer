import sys
import os
import ctypes
import subprocess
import importlib
import traceback
import tkinter as tk
from tkinter import ttk, messagebox

# Lock working directory & module search path to main.py's folder
# (Prevents Windows Admin elevation from shifting cwd to C:\Windows\System32)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import (
    THEME,
    BG_MAIN,
    BG_SIDEBAR,
    BG_CARD,
    BG_INPUT,
    FG_PRIMARY,
    FG_SECONDARY,
    FG_MUTED,
    BORDER_COLOR,
    FONT_FAMILY,
    FONT_BODY,
    FONT_BOLD,
    FONT_MONO,
    apply_global_ttk_style,
    create_button,
)

# Sidebar menu configuration: (Display Title, Internal Key, Candidate Module Filenames)
NAV_ITEMS = [
    ("Dashboard",          "dashboard",         ["dashboard"]),
    ("Package Manager",    "winget",            ["winget", "package_manager"]),
    ("Bloat Uninstaller",  "bloat_uninstaller", ["bloat_uninstaller", "uninstaller"]),
    ("Privacy & Tweaks",   "tweaks",            ["tweaks", "privacy_tweaks"]),
    ("System Cleaner",     "cleaner",           ["cleaner", "system_cleaner"]),
    ("File Scanner",       "scanner",           ["scanner", "file_scanner"]),
    ("Startup Manager",    "startup",           ["startup", "startup_manager"]),
    ("Service Manager",    "services",          ["services", "service_manager"]),
    ("Process Priority",   "process_priority",  ["process_priority", "processes"]),
    ("Network Tools",      "network_tools",     ["network_tools", "network"]),
    ("Windows Repair",     "repair",            ["repair", "windows_repair"]),
    ("Power Settings",     "power",             ["power", "power_settings"]),
]


def is_user_admin() -> bool:
    """Checks if the toolkit is running with elevated Administrator privileges."""
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def request_admin_elevation(exit_after: bool = True) -> bool:
    """Triggers the Windows UAC prompt to relaunch main.py as Administrator."""
    if sys.platform != "win32":
        return False

    script_path = os.path.abspath(__file__)
    # Pass along any extra CLI arguments (excluding --no-admin)
    extra_args = [arg for arg in sys.argv[1:] if arg != "--no-admin"]
    params = subprocess.list2cmdline([script_path] + extra_args)

    # Prefer pythonw.exe when available so an extra black console window doesn't stay open
    executable = sys.executable
    if executable.lower().endswith("python.exe"):
        pythonw = executable[:-10] + "pythonw.exe"
        if os.path.exists(pythonw):
            executable = pythonw

    try:
        # ShellExecuteW returns a value > 32 if the elevation request succeeded
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, params, BASE_DIR, 1
        )
        if int(ret) > 32:
            if exit_after:
                sys.exit(0)
            return True
    except Exception:
        pass
    return False


def enable_windows_dpi_and_dark_bar(window: tk.Tk):
    """Enables sharp DPI scaling and Windows 10/11 dark title bar."""
    if sys.platform != "win32":
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass


class MainWindow(tk.Tk):
    """Main Application Container for Windows toolkit - Wibe Suite."""

    def __init__(self):
        super().__init__()
        self.title("Windows Toolkit — Wibe Suite")
        self.geometry("1220x780")
        self.minsize(1000, 680)
        self.configure(bg=BG_MAIN)

        apply_global_ttk_style(self)
        enable_windows_dpi_and_dark_bar(self)

        self.views = {}
        self.nav_buttons = {}
        self.active_key = None

        self.init_ui()

    def init_ui(self):
        # ------------------ SIDEBAR ------------------
        sidebar = tk.Frame(
            self,
            bg=BG_SIDEBAR,
            width=225,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # App Brand Header
        brand_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        brand_frame.pack(fill=tk.X, padx=18, pady=(20, 14))

        tk.Label(
            brand_frame,
            text="WIBE SUITE",
            fg=FG_PRIMARY,
            bg=BG_SIDEBAR,
            font=(FONT_FAMILY, 13, "bold"),
        ).pack(anchor="w")

        tk.Label(
            brand_frame,
            text="Windows System Toolkit",
            fg=FG_MUTED,
            bg=BG_SIDEBAR,
            font=(FONT_FAMILY, 9),
        ).pack(anchor="w", pady=(1, 0))

        # Subtle Divider
        tk.Frame(sidebar, bg=BORDER_COLOR, height=1).pack(fill=tk.X, padx=14, pady=(0, 10))

        # Navigation Buttons Container
        nav_container = tk.Frame(sidebar, bg=BG_SIDEBAR)
        nav_container.pack(fill=tk.BOTH, expand=True, padx=8)

        # Bottom Admin Status Badge
        self.build_privilege_footer(sidebar)

        # ------------------ MAIN CONTENT AREA ------------------
        self.content_container = tk.Frame(self, bg=BG_MAIN)
        self.content_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Build Navigation Buttons & Load Module Views
        for title, mod_key, candidates in NAV_ITEMS:
            btn = tk.Button(
                nav_container,
                text=f"  {title}",
                fg=FG_SECONDARY,
                bg=BG_SIDEBAR,
                activebackground=THEME["bg_active"],
                activeforeground=FG_PRIMARY,
                font=FONT_BODY,
                anchor="w",
                bd=0,
                relief="flat",
                padx=12,
                pady=8,
                cursor="hand2",
                command=lambda k=mod_key: self.switch_view(k),
            )
            btn.pack(fill=tk.X, pady=1)

            btn.bind("<Enter>", lambda _e, k=mod_key, b=btn: self._on_nav_hover(k, b, True))
            btn.bind("<Leave>", lambda _e, k=mod_key, b=btn: self._on_nav_hover(k, b, False))

            self.nav_buttons[mod_key] = btn

            view_widget = self.load_module_view(title, candidates)
            self.views[mod_key] = view_widget

        # Select Dashboard by default
        self.switch_view("dashboard")

    def build_privilege_footer(self, sidebar: tk.Frame):
        """Shows Admin status; if running without Admin, clicking it elevates the app."""
        footer = tk.Frame(sidebar, bg=BG_SIDEBAR)
        footer.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=14)

        admin = is_user_admin()
        dot_color = THEME["success"] if admin else THEME["warning"]
        status_text = "Administrator Mode" if admin else "Elevate to Admin ↗"
        cursor_style = "arrow" if admin else "hand2"

        badge = tk.Frame(
            footer,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=10,
            pady=6,
            cursor=cursor_style,
        )
        badge.pack(fill=tk.X)

        dot_lbl = tk.Label(
            badge, text="●", fg=dot_color, bg=BG_CARD,
            font=(FONT_FAMILY, 10, "bold"), cursor=cursor_style
        )
        dot_lbl.pack(side=tk.LEFT, padx=(0, 6))

        txt_lbl = tk.Label(
            badge, text=status_text, fg=FG_SECONDARY, bg=BG_CARD,
            font=(FONT_FAMILY, 9, "bold"), cursor=cursor_style
        )
        txt_lbl.pack(side=tk.LEFT)

        if not admin:
            for widget in (badge, dot_lbl, txt_lbl):
                widget.bind("<Button-1>", lambda _e: self._relaunch_as_admin())

    def _relaunch_as_admin(self):
        if request_admin_elevation(exit_after=False):
            self.destroy()
            sys.exit(0)
        else:
            messagebox.showwarning(
                "Elevation Cancelled",
                "Administrator permission was not granted.",
                parent=self,
            )

    def _on_nav_hover(self, key: str, btn: tk.Button, entering: bool):
        if key == self.active_key:
            return
        if entering:
            btn.config(bg=BG_CARD, fg=FG_PRIMARY)
        else:
            btn.config(bg=BG_SIDEBAR, fg=FG_SECONDARY)

    def load_module_view(self, title: str, candidate_names: list[str]) -> tk.Widget:
        """Attempts to load a module from candidate filenames and instantiate its main Frame."""
        last_error_trace = None
        last_failed_mod = None

        for target_mod in candidate_names:
            try:
                mod = importlib.import_module(f"modules.{target_mod}")
                return self._instantiate_module_widget(mod, target_mod)

            except ModuleNotFoundError as e:
                if e.name == f"modules.{target_mod}":
                    continue
                last_failed_mod = target_mod
                last_error_trace = traceback.format_exc()
                break
            except Exception:
                last_failed_mod = target_mod
                last_error_trace = traceback.format_exc()
                break

        if last_error_trace:
            return self.create_error_view(title, last_failed_mod, candidate_names, last_error_trace)

        return self.create_placeholder_view(title, candidate_names)

    def _instantiate_module_widget(self, mod, target_mod: str) -> tk.Widget:
        """Finds and instantiates the primary view class or builder function inside a module."""
        frame_classes = []
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, tk.Widget)
                and attr not in (tk.Frame, ttk.Frame, tk.Widget, tk.LabelFrame)
                and attr.__module__ == mod.__name__
            ):
                frame_classes.append((attr_name, attr))

        if frame_classes:
            def class_priority(item):
                name, cls = item
                score = 0
                if issubclass(cls, (tk.Frame, ttk.Frame)):
                    score += 10
                if name.endswith(("Tab", "View", "Module", "Page", "Manager", "Panel")):
                    score += 20
                elif name.endswith("Frame") and "Scroll" not in name and "Card" not in name:
                    score += 10
                return score

            frame_classes.sort(key=class_priority, reverse=True)
            best_cls = frame_classes[0][1]
            return best_cls(self.content_container)

        for func_name in ("create_tab", "create_frame", "get_view", "main"):
            if hasattr(mod, func_name):
                func = getattr(mod, func_name)
                if callable(func):
                    res = func(self.content_container)
                    if isinstance(res, tk.Widget):
                        return res

        raise RuntimeError(
            f"Module 'modules/{target_mod}.py' loaded, but no compatible tk.Frame subclass or builder function was found."
        )

    def reload_single_module(self, mod_key: str, title: str, candidate_names: list[str]):
        """Hot-reloads a module if the user clicks Reload on an error screen."""
        for name in candidate_names:
            full_name = f"modules.{name}"
            if full_name in sys.modules:
                try:
                    importlib.reload(sys.modules[full_name])
                except Exception:
                    pass

        old_view = self.views.get(mod_key)
        if old_view:
            old_view.destroy()

        self.views[mod_key] = self.load_module_view(title, candidate_names)
        self.switch_view(mod_key)

    def create_placeholder_view(self, title: str, candidate_names: list[str]) -> tk.Frame:
        """Fallback view shown if a module file is not yet created."""
        frame = tk.Frame(self.content_container, bg=BG_MAIN)
        card = tk.Frame(
            frame,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=36,
            pady=30,
        )
        card.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(
            card, text=f"{title} Module", fg=FG_PRIMARY, bg=BG_CARD, font=(FONT_FAMILY, 16, "bold")
        ).pack(pady=(0, 6))

        expected = " or ".join(f"modules/{n}.py" for n in candidate_names)
        tk.Label(
            card,
            text=f"Module file not found yet.\nExpected: {expected}",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_BODY,
            justify="center",
        ).pack()

        return frame

    def create_error_view(
        self, title: str, mod_name: str, candidate_names: list[str], trace: str
    ) -> tk.Frame:
        """Displays formatted traceback and a retry button if a module crashes on load."""
        frame = tk.Frame(self.content_container, bg=BG_MAIN)

        header_row = tk.Frame(frame, bg=BG_MAIN)
        header_row.pack(fill=tk.X, padx=24, pady=(24, 10))

        tk.Label(
            header_row,
            text=f"Failed to load modules/{mod_name}.py",
            fg=THEME["danger"],
            bg=BG_MAIN,
            font=(FONT_FAMILY, 14, "bold"),
        ).pack(side=tk.LEFT)

        mod_key = next((k for t, k, _c in NAV_ITEMS if t == title), None)
        if mod_key:
            create_button(
                header_row,
                text="↻ Reload Module",
                variant="secondary",
                command=lambda: self.reload_single_module(mod_key, title, candidate_names),
            ).pack(side=tk.RIGHT)

        txt = tk.Text(
            frame,
            bg=BG_INPUT,
            fg=FG_PRIMARY,
            font=FONT_MONO,
            bd=0,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        txt.insert("1.0", trace)
        txt.config(state="disabled")
        txt.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 24))
        return frame

    def switch_view(self, view_key: str):
        """Switches visible content frame and updates active navigation state."""
        self.active_key = view_key

        for frame in self.views.values():
            if frame:
                frame.pack_forget()

        if view_key in self.views and self.views[view_key]:
            self.views[view_key].pack(fill=tk.BOTH, expand=True)

        for key, btn in self.nav_buttons.items():
            if key == view_key:
                btn.config(
                    bg=THEME["accent"],
                    fg="#ffffff",
                    font=FONT_BOLD,
                )
            else:
                btn.config(
                    bg=BG_SIDEBAR,
                    fg=FG_SECONDARY,
                    font=FONT_BODY,
                )


if __name__ == "__main__":
    # 1. Automatically ask for Administrator privileges on launch
    #    (Use `python main.py --no-admin` if you ever want to skip UAC during testing)
    if sys.platform == "win32" and not is_user_admin() and "--no-admin" not in sys.argv:
        request_admin_elevation(exit_after=True)

    # 2. Set Windows High-DPI awareness before creating the root Tk window
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = MainWindow()
    app.mainloop()