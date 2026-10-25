import time
import winreg
import ctypes
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    THEME,
    BG_MAIN,
    BG_CARD,
    BG_INPUT,
    FG_PRIMARY,
    FG_SECONDARY,
    FG_MUTED,
    BORDER_COLOR,
    FONT_BODY,
    FONT_BOLD,
    FONT_SMALL,
    create_header,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02
COLOR_DESKTOP = 1


class ToggleSwitch(tk.Canvas):
    """Custom sliding pill switch widget with automatic BooleanVar trace synchronization."""

    def __init__(
        self,
        parent,
        variable: tk.BooleanVar,
        command=None,
        width: int = 46,
        height: int = 24,
        bg_color: str = BG_CARD,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=bg_color,
            highlightthickness=0,
            cursor="hand2",
        )
        self.variable = variable
        self.command = command
        self.width = width
        self.height = height

        # Automatically redraw whenever BooleanVar changes (including on error rollback)
        self.variable.trace_add("write", lambda *_: self.draw())
        self.bind("<Button-1>", self._on_click)
        self.draw()

    def draw(self):
        if not self.winfo_exists():
            return
        self.delete("all")
        val = bool(self.variable.get())

        track_bg = THEME["accent"] if val else BG_INPUT
        border_col = THEME["accent"] if val else BORDER_COLOR
        thumb_fill = "#ffffff" if val else FG_SECONDARY

        r = self.height / 2
        # Pill-shaped track
        self.create_oval(1, 1, self.height - 1, self.height - 1, fill=track_bg, outline=border_col)
        self.create_oval(
            self.width - self.height + 1,
            1,
            self.width - 1,
            self.height - 1,
            fill=track_bg,
            outline=border_col,
        )
        self.create_rectangle(
            r, 1, self.width - r, self.height - 1, fill=track_bg, outline=track_bg
        )

        # Sliding circular thumb
        pad = 4
        thumb_d = self.height - (pad * 2)
        if val:
            x0 = self.width - thumb_d - pad
            x1 = self.width - pad
        else:
            x0 = pad
            x1 = thumb_d + pad

        self.create_oval(x0, pad, x1, self.height - pad, fill=thumb_fill, outline=thumb_fill)

    def _on_click(self, _event):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()


class TweaksModule(tk.Frame):
    """Native Tkinter Privacy & System UI Tweaks Module."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.switches: list[tuple[ToggleSwitch, tk.BooleanVar, dict]] = []

        self.tweaks = [
            {
                "name": "Taskbar Alignment (Left)",
                "desc": "Moves the Windows 11 Start button and taskbar icons to the left (Windows 10 style).",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "TaskbarAl",
                "type": winreg.REG_DWORD,
                "on_val": 0,
                "off_val": 1,
            },
            {
                "name": "Restore Classic Context Menu (Windows 11)",
                "desc": "Restores the full classic right-click context menu without clicking 'Show more options'. (Restart Explorer)",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32",
                "parent_path": r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}",
                "value": "",
                "type": winreg.REG_SZ,
                "on_val": "",
                "off_val": None,
                "is_special": "context_menu",
            },
            {
                "name": "Always Show File Extensions",
                "desc": "Displays file type extensions (.exe, .py, .txt, .png) in File Explorer.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "HideFileExt",
                "type": winreg.REG_DWORD,
                "on_val": 0,
                "off_val": 1,
            },
            {
                "name": "Open File Explorer to 'This PC'",
                "desc": "Opens File Explorer directly to 'This PC' instead of 'Home / Quick Access'.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "LaunchTo",
                "type": winreg.REG_DWORD,
                "on_val": 1,
                "off_val": 2,
            },
            {
                "name": "Disable Advertising ID",
                "desc": "Prevents Windows and Microsoft Store apps from using your Advertising ID for targeted ads.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                "value": "Enabled",
                "type": winreg.REG_DWORD,
                "on_val": 0,
                "off_val": 1,
            },
            {
                "name": "Disable Bing Web Search in Start Menu",
                "desc": "Disables slow Bing web results when searching for local files and apps in the Start Menu.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Search",
                "value": "BingSearchEnabled",
                "type": winreg.REG_DWORD,
                "on_val": 0,
                "off_val": 1,
            },
            {
                "name": "Disable Windows Copilot",
                "desc": "Disables and hides the Windows Copilot AI sidebar and taskbar button.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Policies\Microsoft\Windows\WindowsCopilot",
                "value": "TurnOffWindowsCopilot",
                "type": winreg.REG_DWORD,
                "on_val": 1,
                "off_val": 0,
            },
            {
                "name": "Disable Lock Screen Tips & Ads",
                "desc": "Stops Windows Spotlight from showing promotional tips and 'fun facts' on the lock screen.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                "value": "RotatingLockScreenEnabled",
                "type": winreg.REG_DWORD,
                "on_val": 0,
                "off_val": 1,
            },
            {
                "name": "Disable 'Aero Shake' Window Minimize",
                "desc": "Prevents background windows from minimizing when you shake the active window title bar.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "DisallowShaking",
                "type": winreg.REG_DWORD,
                "on_val": 1,
                "off_val": 0,
            },
            {
                "name": "Disable Snap Assist Flyout Without Edge Drag",
                "desc": "Stops windows from triggering snap layouts unless dragged all the way to the screen edge.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "DITest",
                "type": winreg.REG_DWORD,
                "on_val": 0,
                "off_val": 1,
            },
            {
                "name": "Disable Diagnostic Telemetry (Policy)",
                "desc": "Restricts Windows diagnostic data collection to the minimum security level. (Requires Admin)",
                "hive": winreg.HKEY_LOCAL_MACHINE,
                "path": r"Software\Policies\Microsoft\Windows\DataCollection",
                "value": "AllowTelemetry",
                "type": winreg.REG_DWORD,
                "on_val": 0,
                "off_val": 1,
            },
            {
                "name": "Set Desktop Background to Solid Black",
                "desc": "Removes wallpaper image and sets the desktop background to pure solid black (RGB 0, 0, 0).",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Control Panel\Colors",
                "value": "Background",
                "type": winreg.REG_SZ,
                "on_val": "0 0 0",
                "off_val": "58 110 165",
                "is_special": "solid_black",
            },
        ]

        self.init_ui()

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="Privacy & System Tweaks",
            subtitle="Customize Windows 10/11 behavior and privacy policies. Toggle switches apply changes immediately.",
        )

        # --- Bottom Bar (Restart Explorer) ---
        bottom_bar = tk.Frame(
            self,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=24, pady=(8, 20))

        tk.Label(
            bottom_bar,
            text="ℹ️ Note: Shell tweaks (Context Menu, Taskbar, File Extensions) require restarting Windows Explorer to take effect.",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_SMALL,
        ).pack(side=tk.LEFT)

        create_button(
            bottom_bar,
            text="Restart Explorer",
            command=self.restart_explorer,
            variant="danger",
            padx=14,
            pady=5,
        ).pack(side=tk.RIGHT)

        # --- Scrollable Tweak List Container ---
        list_outer = tk.Frame(self, bg=BG_MAIN)
        list_outer.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 4))

        self.canvas = tk.Canvas(list_outer, bg=BG_MAIN, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas, bg=BG_MAIN)

        self.inner_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.window_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Ensure tweak cards always stretch to the full width of the canvas
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.window_id, width=e.width),
        )

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Scoped mousewheel scrolling
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        self.render_tweaks()

    def _bind_mousewheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _on_mousewheel(self, event):
        try:
            if self.winfo_ismapped() and self.inner_frame.winfo_height() > self.canvas.winfo_height():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # Rendering & Registry Logic
    # --------------------------------------------------------------------------
    def render_tweaks(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()
        self.switches.clear()

        for tweak in self.tweaks:
            card = tk.Frame(
                self.inner_frame,
                bg=BG_CARD,
                highlightbackground=BORDER_COLOR,
                highlightthickness=1,
                padx=16,
                pady=10,
            )
            card.pack(fill=tk.X, pady=4, padx=(0, 6))

            text_frame = tk.Frame(card, bg=BG_CARD)
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

            tk.Label(
                text_frame,
                text=tweak["name"],
                font=FONT_BOLD,
                fg=FG_PRIMARY,
                bg=BG_CARD,
                anchor="w",
            ).pack(anchor="w")

            tk.Label(
                text_frame,
                text=tweak["desc"],
                font=FONT_SMALL,
                fg=FG_SECONDARY,
                bg=BG_CARD,
                anchor="w",
            ).pack(anchor="w", pady=(2, 0))

            switch_var = tk.BooleanVar(value=self.check_tweak_state(tweak))
            switch = ToggleSwitch(
                card,
                variable=switch_var,
                command=lambda t=tweak, v=switch_var: self.toggle_tweak(t, v),
                bg_color=BG_CARD,
            )
            switch.pack(side=tk.RIGHT, padx=4)
            self.switches.append((switch, switch_var, tweak))

    def check_tweak_state(self, tweak: dict) -> bool:
        try:
            if tweak.get("is_special") == "solid_black":
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Control Panel\Colors", 0, winreg.KEY_READ
                ) as k1:
                    bg_val, _ = winreg.QueryValueEx(k1, "Background")

                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_READ
                ) as k2:
                    wp_val, _ = winreg.QueryValueEx(k2, "Wallpaper")

                return str(bg_val).strip() == "0 0 0" and str(wp_val).strip() == ""

            with winreg.OpenKey(tweak["hive"], tweak["path"], 0, winreg.KEY_READ) as key:
                if tweak.get("is_special") == "context_menu":
                    return True
                val, _ = winreg.QueryValueEx(key, tweak["value"])
                return val == tweak["on_val"]

        except FileNotFoundError:
            return False
        except Exception:
            return False

    def toggle_tweak(self, tweak: dict, var: tk.BooleanVar):
        state = bool(var.get())
        target_val = tweak["on_val"] if state else tweak["off_val"]

        try:
            if tweak.get("is_special") == "solid_black":
                rgb_str = "0 0 0" if state else "58 110 165"
                color_ref = 0x00000000 if state else (58 | (110 << 8) | (165 << 16))

                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Colors") as k1:
                    winreg.SetValueEx(k1, "Background", 0, winreg.REG_SZ, rgb_str)

                if state:
                    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as k2:
                        winreg.SetValueEx(k2, "Wallpaper", 0, winreg.REG_SZ, "")
                    ctypes.windll.user32.SystemParametersInfoW(
                        SPI_SETDESKWALLPAPER,
                        0,
                        "",
                        SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
                    )

                # Apply background RGB color immediately to the active session
                elements = (ctypes.c_int * 1)(COLOR_DESKTOP)
                colors = (ctypes.c_uint * 1)(color_ref)
                ctypes.windll.user32.SetSysColors(1, elements, colors)
                return

            if tweak.get("is_special") == "context_menu":
                if state:
                    with winreg.CreateKey(tweak["hive"], tweak["path"]) as key:
                        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
                else:
                    self._delete_context_menu_keys(tweak["hive"], tweak["path"], tweak.get("parent_path"))
                return

            with winreg.CreateKey(tweak["hive"], tweak["path"]) as key:
                winreg.SetValueEx(key, tweak["value"], 0, tweak["type"], target_val)

        except PermissionError:
            # Setting var triggers trace_add -> redraws switch back to previous state
            var.set(not state)
            messagebox.showerror(
                "Permission Denied",
                f"Modifying '{tweak['name']}' requires Administrator privileges.\n\n"
                "Click the 'Elevate to Admin' badge in the sidebar.",
                parent=self,
            )
        except Exception as e:
            var.set(not state)
            messagebox.showerror("Registry Error", f"Failed to apply tweak:\n{e}", parent=self)

    @staticmethod
    def _delete_context_menu_keys(hive, inproc_path: str, parent_path: str | None):
        for subkey in (inproc_path, parent_path):
            if subkey:
                try:
                    winreg.DeleteKey(hive, subkey)
                except OSError:
                    pass

    def restart_explorer(self):
        """Restarts Windows Explorer cleanly in a background thread without freezing the GUI."""
        def _worker():
            try:
                subprocess.run(
                    ["taskkill", "/f", "/im", "explorer.exe"],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                )
                time.sleep(0.4)
                subprocess.Popen(["explorer.exe"])
            except Exception as e:
                self.after(
                    0,
                    lambda err=str(e): messagebox.showerror(
                        "Explorer Restart Failed", f"Could not restart explorer.exe:\n{err}", parent=self
                    ),
                )

        threading.Thread(target=_worker, daemon=True).start()


# Compatibility alias for main.py dynamic routing
PrivacyTweaksTab = TweaksModule