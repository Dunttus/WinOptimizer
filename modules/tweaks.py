import customtkinter as ctk
import winreg
import subprocess
import os
import datetime
from tkinter import messagebox
from utils import add_info_section

class TweaksModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Privacy & Tweaks", 
                         "Customize Windows behavior. Toggle switches to Enable/Disable features instantly.")

        # --- Backup Section Removed (Moved to Dashboard) ---

        # --- Settings Container ---
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Defined Tweaks ---
        # Each tweak has: Name, Description, Hive, Key Path, Value Name, Value Type, On_Val, Off_Val
        self.tweaks = [
            # --- UI & VISUALS ---
            {
                "name": "Taskbar Alignment (Left)",
                "desc": "Move Start Menu to the Left (Windows 10 Style). Default is Center.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "TaskbarAl",
                "type": winreg.REG_DWORD,
                "on_val": 0, # 0 = Left
                "off_val": 1 # 1 = Center
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
                "on_val": 0, # 0 = Show
                "off_val": 1
            },
            {
                "name": "Open Explorer to 'This PC'",
                "desc": "Make File Explorer open 'This PC' instead of 'Home/Quick Access'.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                "value": "LaunchTo",
                "type": winreg.REG_DWORD,
                "on_val": 1, # 1 = This PC
                "off_val": 2 # 2 = Quick Access
            },

            # --- PRIVACY & ADS ---
            {
                "name": "Disable Advertising ID",
                "desc": "Prevents apps from using your ID for cross-app targeted experiences.",
                "hive": winreg.HKEY_CURRENT_USER,
                "path": r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                "value": "Enabled",
                "type": winreg.REG_DWORD,
                "on_val": 0, # 0 = Disabled
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
                "on_val": 1, # 1 = Turn OFF Copilot
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

            # --- ANNOYANCES ---
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

        # Restart Explorer Button (Bottom)
        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(btn_frame, text="Note: Some changes require restarting File Explorer to take effect.", text_color="gray", font=("Arial", 10)).pack(side="left")

        restart_btn = ctk.CTkButton(btn_frame, text="Restart Explorer", width=120, height=30,
                                    fg_color="#D32F2F", hover_color="#B71C1C",
                                    command=self.restart_explorer)
        restart_btn.pack(side="right")

    def render_tweaks(self):
        for tweak in self.tweaks:
            row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row.pack(fill="x", pady=8)

            # Labels
            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", padx=5)
            
            ctk.CTkLabel(text_frame, text=tweak["name"], font=("Arial", 13, "bold")).pack(anchor="w")
            ctk.CTkLabel(text_frame, text=tweak["desc"], font=("Arial", 11), text_color="gray").pack(anchor="w")

            # Switch
            switch_var = ctk.BooleanVar(value=self.check_tweak_state(tweak))
            switch = ctk.CTkSwitch(row, text="", variable=switch_var, onvalue=True, offvalue=False,
                                   command=lambda t=tweak, v=switch_var: self.toggle_tweak(t, v))
            switch.pack(side="right", padx=10)
            self.switches.append(switch)

    def check_tweak_state(self, tweak):
        try:
            key = winreg.OpenKey(tweak["hive"], tweak["path"], 0, winreg.KEY_READ)
            
            # Special handling for Context Menu hack (it relies on key existence, not value)
            if tweak.get("is_special") == "context_menu":
                winreg.CloseKey(key)
                return True # Key exists = Hack Enabled (Classic Menu)
                
            val, _ = winreg.QueryValueEx(key, tweak["value"])
            winreg.CloseKey(key)
            return val == tweak["on_val"]
            
        except FileNotFoundError:
            # If key doesn't exist...
            if tweak.get("is_special") == "context_menu": return False # Key missing = Default Win11 Menu
            
            # For Copilot, if key missing, it's ON (default behavior), so our switch (Disable) is False
            if tweak["name"] == "Disable Windows Copilot": return False
            
            return False
        except Exception:
            return False

    def toggle_tweak(self, tweak, var):
        state = var.get()
        target_val = tweak["on_val"] if state else tweak["off_val"]
        
        try:
            # Special logic for Context Menu
            if tweak.get("is_special") == "context_menu":
                if state:
                    # Create the key to enable classic menu
                    key = winreg.CreateKey(tweak["hive"], tweak["path"])
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
                    winreg.CloseKey(key)
                else:
                    # Delete the key to restore Win11 menu
                    self.delete_key_recursive(tweak["hive"], tweak["path"])
                return

            # Normal logic
            key = winreg.CreateKey(tweak["hive"], tweak["path"])
            winreg.SetValueEx(key, tweak["value"], 0, tweak["type"], target_val)
            winreg.CloseKey(key)
            
        except PermissionError:
            var.set(not state) # Revert switch
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
        subprocess.run("taskkill /f /im explorer.exe & start explorer.exe", shell=True)