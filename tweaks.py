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

        # --- Backup Section (Top) ---
        self.setup_backup_ui()

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
        
        ctk.CTkLabel(btn_frame, text="Note: Some changes require restarting File Explorer to take effect.", 
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(side="left")
        
        ctk.CTkButton(btn_frame, text="Restart Explorer", command=self.restart_explorer, 
                      fg_color="#F57C00", hover_color="#E65100", width=150).pack(side="right")

    # --- BACKUP SYSTEM ---
    def setup_backup_ui(self):
        backup_frame = ctk.CTkFrame(self.frame, fg_color="#262626", corner_radius=6, border_width=1, border_color="#404040")
        backup_frame.pack(fill="x", padx=20, pady=(0, 10))

        # Icon/Title
        ctk.CTkLabel(backup_frame, text="🛡️ Safety First", 
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#00E676", anchor="w").pack(side="left", padx=15, pady=10)
        
        # Info
        ctk.CTkLabel(backup_frame, text="Create a backup before applying changes.", 
                     font=ctk.CTkFont(size=12), text_color="#B0B0B0", anchor="w").pack(side="left", padx=5)

        # Button
        ctk.CTkButton(backup_frame, text="Backup Registry", command=self.backup_registry, 
                      fg_color="#1F6AA5", width=120, height=28).pack(side="right", padx=15, pady=8)

    def backup_registry(self):
        try:
            # Generate filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            filename = f"WinOptimize_Backup_{timestamp}.reg"
            filepath = os.path.join(desktop, filename)

            # Use Windows native reg export command
            # Exporting HKCU and HKLM\Software usually covers 99% of Tweaks
            cmd = f'reg export HKEY_CURRENT_USER "{filepath}" /y'
            
            subprocess.run(cmd, shell=True, check=True)
            messagebox.showinfo("Backup Success", f"Registry Backup saved to Desktop:\n\n{filename}")
            
        except subprocess.CalledProcessError:
            messagebox.showerror("Backup Failed", "Could not export Registry key. Ensure you have Admin rights.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # --- RENDERER ---
    def render_tweaks(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        for tweak in self.tweaks:
            row = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", corner_radius=6)
            row.pack(fill="x", pady=5)
            
            # Text Info
            info_f = ctk.CTkFrame(row, fg_color="transparent")
            info_f.pack(side="left", padx=15, pady=10, fill="x", expand=True)
            
            ctk.CTkLabel(info_f, text=tweak["name"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(info_f, text=tweak["desc"], font=ctk.CTkFont(size=11), text_color="#aaaaaa", anchor="w").pack(fill="x")

            # Switch
            switch_var = ctk.BooleanVar()
            switch = ctk.CTkSwitch(row, text="", variable=switch_var, width=50,
                                   command=lambda t=tweak, v=switch_var: self.toggle_tweak(t, v))
            switch.pack(side="right", padx=20)
            
            # Set Initial State
            is_active = self.check_registry(tweak)
            switch_var.set(is_active)
            
            self.switches.append(switch)

    # --- LOGIC ---
    def check_registry(self, tweak):
        try:
            key = winreg.OpenKey(tweak["hive"], tweak["path"], 0, winreg.KEY_READ)
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
        try: winreg.DeleteKey(hive, subkey)
        except: pass 

    def restart_explorer(self):
        subprocess.run("taskkill /f /im explorer.exe & start explorer.exe", shell=True)