import winreg
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

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


class ToggleSwitch(tk.Canvas):
    """Modern custom sliding switch widget built natively in standard Tkinter."""
    def __init__(self, parent, variable, command=None, width=46, height=24, bg_color="#1c1c1c"):
        super().__init__(parent, width=width, height=height, bg=bg_color, highlightthickness=0, cursor="hand2")
        self.variable = variable
        self.command = command
        self.width = width
        self.height = height
        
        self.bind("<Button-1>", self.on_click)
        self.draw()

    def draw(self):
        self.delete("all")
        val = self.variable.get()
        
        # Track colors (Active blue vs dark grey)
        track_bg = "#3B8ED0" if val else "#333333"
        thumb_fill = "#FFFFFF"
        
        r = self.height / 2
        # Draw pill-shaped background track
        self.create_oval(0, 0, self.height, self.height, fill=track_bg, outline=track_bg)
        self.create_oval(self.width - self.height, 0, self.width, self.height, fill=track_bg, outline=track_bg)
        self.create_rectangle(r, 0, self.width - r, self.height, fill=track_bg, outline=track_bg)
        
        # Draw sliding circular thumb
        pad = 3
        thumb_d = self.height - (pad * 2)
        if val:
            x0 = self.width - thumb_d - pad
            x1 = self.width - pad
        else:
            x0 = pad
            x1 = thumb_d + pad
        y0 = pad
        y1 = self.height - pad
        
        self.create_oval(x0, y0, x1, y1, fill=thumb_fill, outline=thumb_fill)

    def on_click(self, event):
        current = self.variable.get()
        self.variable.set(not current)
        self.draw()
        if self.command:
            self.command()


class TweaksModule(tk.Frame):
    """Native Tkinter Privacy & Tweaks Module."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")

        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="Privacy & Tweaks", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Customize Windows behavior. Toggle switches to Enable/Disable features instantly.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Restart Explorer Button Frame (Bottom) ---
        btn_frame = tk.Frame(self, bg="#1c1c1c")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=15)
        
        tk.Label(
            btn_frame, text="Note: Some changes require restarting File Explorer to take effect.", 
            fg="gray", bg="#1c1c1c", font=("Segoe UI", 9)
        ).pack(side="left")

        tk.Button(
            btn_frame, text="Restart Explorer", width=14, height=1,
            bg="#D32F2F", fg="white", font=("Segoe UI", 9, "bold"),
            activebackground="#B71C1C", activeforeground="white", bd=0, cursor="hand2",
            command=self.restart_explorer
        ).pack(side="right")

        # --- Settings Container ---
        self.scroll_frame = ScrollableFrame(self, bg_color="#1c1c1c")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Defined Tweaks ---
        self.tweaks = [
            {
                "name": "Taskbar Alignment (Left)",
                "desc": "Move Start Menu to the Left (Windows 10 Style). Default is Center.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "TaskbarAl",
                "type": winreg.REG_DWORD,
                "on_val": 0, 
                "off_val": 1 
            },
            {
                "name": "Restore Classic Context Menu",
                "desc": "Brings back the old right-click menu on Windows 11. (Requires Restart)",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32",
                "value": "", 
                "type": winreg.REG_SZ,
                "on_val": "",     
                "off_val": None, 
                "is_special": "context_menu"
            },
            {
                "name": "Show File Extensions",
                "desc": "Always show .exe, .txt, .png extensions in File Explorer.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "HideFileExt",
                "type": winreg.REG_DWORD,
                "on_val": 0, 
                "off_val": 1
            },
            {
                "name": "Open Explorer to 'This PC'",
                "desc": "Make File Explorer open 'This PC' instead of 'Home/Quick Access'.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "LaunchTo",
                "type": winreg.REG_DWORD,
                "on_val": 1, 
                "off_val": 2 
            },
            {
                "name": "Disable Advertising ID",
                "desc": "Prevents apps from using your ID for cross-app targeted experiences.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                "value": "Enabled",
                "type": winreg.REG_DWORD,
                "on_val": 0, 
                "off_val": 1
            },
            {
                "name": "Disable Bing in Start Menu",
                "desc": "Removes web search results from your Start Menu search bar.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Search",
                "value": "BingSearchEnabled",
                "type": winreg.REG_DWORD,
                "on_val": 0, 
                "off_val": 1 
            },
            {
                "name": "Disable Windows Copilot",
                "desc": "Removes the AI Copilot button and sidebar. (Win 11)",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Policies\Microsoft\Windows\WindowsCopilot",
                "value": "TurnOffWindowsCopilot",
                "type": winreg.REG_DWORD,
                "on_val": 1, 
                "off_val": 0
            },
            {
                "name": "Disable Lock Screen Ads",
                "desc": "Stops Windows from showing 'fun facts' and tips on the lock screen.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
                "value": "RotatingLockScreenEnabled",
                "type": winreg.REG_DWORD,
                "on_val": 0, 
                "off_val": 1 
            },
            {
                "name": "Disable 'Shake to Minimize'",
                "desc": "Stops windows from minimizing when you shake the active window.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "DisallowShaking",
                "type": winreg.REG_DWORD,
                "on_val": 1, 
                "off_val": 0 
            },
            {
                "name": "Disable Telemetry (Basic)",
                "desc": "Reduces data sent to Microsoft. (May require Admin)",
                "hive": winreg.HKEY_LOCAL_MACHINE,
                "path": r"Software\Policies\Microsoft\Windows\DataCollection",
                "value": "AllowTelemetry",
                "type": winreg.REG_DWORD,
                "on_val": 0, 
                "off_val": 1 
            }
        ]

        self.switches = []
        self.render_tweaks()

    def render_tweaks(self):
        parent = self.scroll_frame.inner_frame
        for tweak in self.tweaks:
            row = tk.Frame(parent, bg="#1c1c1c")
            row.pack(fill="x", pady=8, padx=5)

            # Labels Container
            text_frame = tk.Frame(row, bg="#1c1c1c")
            text_frame.pack(side="left", padx=5, fill="x", expand=True)
            
            tk.Label(text_frame, text=tweak["name"], font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#1c1c1c", anchor="w").pack(anchor="w")
            tk.Label(text_frame, text=tweak["desc"], font=("Segoe UI", 9), fg="#888888", bg="#1c1c1c", anchor="w").pack(anchor="w")

            # Custom Sliding Toggle Switch
            switch_var = tk.BooleanVar(value=self.check_tweak_state(tweak))
            switch = ToggleSwitch(
                row, variable=switch_var,
                command=lambda t=tweak, v=switch_var: self.toggle_tweak(t, v),
                bg_color="#1c1c1c"
            )
            switch.pack(side="right", padx=15)
            self.switches.append((switch, switch_var))

    def check_tweak_state(self, tweak):
        try:
            key = winreg.OpenKey(tweak["hive"], tweak["path"], 0, winreg.KEY_READ)
            
            if tweak.get("is_special") == "context_menu":
                winreg.CloseKey(key)
                return True 
                
            val, _ = winreg.QueryValueEx(key, tweak["value"])
            winreg.CloseKey(key)
            return val == tweak["on_val"]
            
        except FileNotFoundError:
            if tweak.get("is_special") == "context_menu": return False 
            if tweak["name"] == "Disable Windows Copilot": return False
            return False
        except Exception:
            return False

    def toggle_tweak(self, tweak, var):
        state = var.get()
        target_val = tweak["on_val"] if state else tweak["off_val"]
        
        try:
            if tweak.get("is_special") == "context_menu":
                if state:
                    key = winreg.CreateKey(tweak["hive"], tweak["path"])
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
                    winreg.CloseKey(key)
                else:
                    self.delete_key_recursive(tweak["hive"], tweak["path"])
                return

            key = winreg.CreateKey(tweak["hive"], tweak["path"])
            winreg.SetValueEx(key, tweak["value"], 0, tweak["type"], target_val)
            winreg.CloseKey(key)
            
        except PermissionError:
            var.set(not state) 
            messagebox.showerror("Permission Denied", "Run as Administrator.")
        except Exception as e:
            var.set(not state)
            print(f"Error: {e}")

    def delete_key_recursive(self, hive, subkey):
        try:
            winreg.DeleteKey(hive, subkey)
        except Exception:
            pass

    def restart_explorer(self):
        subprocess.run("taskkill /f /im explorer.exe & start explorer.exe", shell=True, creationflags=0x08000000)

# Compatibility alias for main.py dynamic routing
PrivacyTweaksTab = TweaksModule