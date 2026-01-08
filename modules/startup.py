import customtkinter as ctk
import winreg
from tkinter import messagebox
from utils import add_info_section, is_admin

class StartupModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Startup Manager", "Remove applications that start automatically with Windows.")
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame, label_text="Registry Startup Items")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkButton(self.frame, text="Refresh List", command=self.load_startup_items).pack(pady=10)
        
        self.load_startup_items()

    def load_startup_items(self):
        # Clear existing entries
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        # Define Registry locations to scan
        # (Root Key, Path, Display Context)
        locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Current User"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "System Wide (64-bit)"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "System Wide (32-bit)")
        ]
        
        items_found = False
        
        for hkey, path, context in locations:
            try:
                # Open the key with Read permissions
                with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            # EnumValue returns (name, value, type)
                            name, value, _ = winreg.EnumValue(key, i)
                            self.add_row(name, value, path, hkey, context)
                            items_found = True
                            i += 1
                        except OSError:
                            # No more values in this key
                            break
            except PermissionError:
                print(f"Permission denied reading: {path}")
            except FileNotFoundError:
                pass # Key doesn't exist, skip it
                
        if not items_found:
             ctk.CTkLabel(self.scroll_frame, text="No startup items found in Registry.", text_color="gray").pack(pady=20)

    def add_row(self, name, path_val, reg_path, hkey_root, context):
        row = ctk.CTkFrame(self.scroll_frame)
        row.pack(fill="x", pady=2)
        
        # Info Section
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # App Name
        ctk.CTkLabel(info, text=name, font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        
        # App Command/Path
        sub_text = f"[{context}]  {path_val}"
        ctk.CTkLabel(info, text=sub_text, font=ctk.CTkFont(size=10), text_color="gray", wraplength=500).pack(anchor="w")
        
        # Remove Button
        ctk.CTkButton(row, text="Remove", width=80, height=28, fg_color="#c42b1c", hover_color="#8a1c11",
                      command=lambda: self.delete_entry(name, reg_path, hkey_root)).pack(side="right", padx=10)

    def delete_entry(self, name, reg_path, hkey_root):
        # Admin check
        if hkey_root == winreg.HKEY_LOCAL_MACHINE and not is_admin():
            messagebox.showerror("Permission Error", "Administrator privileges are required to remove System Wide items.\nPlease restart the app as Admin.")
            return

        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to stop '{name}' from starting with Windows?\n\nThis will delete the registry entry."):
            try:
                # Open key with Write permissions (KEY_SET_VALUE)
                with winreg.OpenKey(hkey_root, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, name)
                
                # Refresh list
                self.load_startup_items()
                messagebox.showinfo("Success", f"Removed '{name}' from startup.")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not remove item: {e}")