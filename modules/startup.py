import winreg
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox

def is_admin():
    """Checks if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


class StartupModule(tk.Frame):
    """Native Tkinter Startup Manager Module."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")

        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="Startup Manager", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Remove applications that start automatically with Windows.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Bottom Refresh Bar ---
        btn_frame = tk.Frame(self, bg="#1c1c1c")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=15)

        tk.Button(
            btn_frame, text="Refresh List", command=self.load_startup_items, 
            bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), 
            bd=0, cursor="hand2", padx=15, pady=6
        ).pack(side="left")

        # --- Startup Items Container ---
        list_container = tk.Frame(self, bg="#1c1c1c", bd=1, relief="solid")
        list_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(
            list_container, text=" Registry Startup Items ", fg="#888888", 
            bg="#1c1c1c", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=10, pady=(8, 0))

        self.scroll = VerticalScrollFrame(list_container, bg_color="#1c1c1c")
        self.scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.load_startup_items()

    def load_startup_items(self):
        self.scroll.clear()
            
        locations = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Current User"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "System Wide (64-bit)"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "System Wide (32-bit)")
        ]
        
        items_found = False
        
        for hkey, path, context in locations:
            try:
                with winreg.OpenKey(hkey, path, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            self.add_row(name, value, path, hkey, context)
                            items_found = True
                            i += 1
                        except OSError:
                            break
            except PermissionError:
                print(f"Permission denied reading: {path}")
            except FileNotFoundError:
                pass 
                
        if not items_found:
            tk.Label(
                self.scroll.inner_frame, text="No startup items found in Registry.", 
                fg="gray", bg="#1c1c1c", font=("Segoe UI", 10)
            ).pack(pady=20)

    def add_row(self, name, path_val, reg_path, hkey_root, context):
        parent = self.scroll.inner_frame
        
        row = tk.Frame(parent, bg="#2a2a2a", bd=1, relief="solid")
        row.pack(fill="x", pady=4, padx=5)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0)
        
        # Info Section
        info = tk.Frame(row, bg="#2a2a2a")
        info.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)
        
        tk.Label(
            info, text=name, font=("Segoe UI", 10, "bold"), 
            fg="#ffffff", bg="#2a2a2a", anchor="w"
        ).pack(anchor="w", fill="x")
        
        sub_text = f"[{context}]   {path_val}"
        tk.Label(
            info, text=sub_text, font=("Segoe UI", 9), 
            fg="#aaaaaa", bg="#2a2a2a", anchor="w", wraplength=550
        ).pack(anchor="w", fill="x", pady=(2, 0))
        
        # Remove Button
        btn_frame = tk.Frame(row, bg="#2a2a2a")
        btn_frame.grid(row=0, column=1, sticky="e", padx=12, pady=8)

        tk.Button(
            btn_frame, text="Remove", width=12, bg="#c42b1c", fg="white", 
            font=("Segoe UI", 8, "bold"), activebackground="#A32014", 
            activeforeground="white", bd=0, cursor="hand2", padx=5, pady=4,
            command=lambda: self.delete_entry(name, reg_path, hkey_root)
        ).pack()

    def delete_entry(self, name, reg_path, hkey_root):
        if hkey_root == winreg.HKEY_LOCAL_MACHINE and not is_admin():
            messagebox.showerror("Permission Error", "Administrator privileges are required to remove System Wide items.\nPlease restart the app as Admin.")
            return

        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to stop '{name}' from starting with Windows?\n\nThis will delete the registry entry."):
            try:
                with winreg.OpenKey(hkey_root, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, name)
                
                self.load_startup_items()
                messagebox.showinfo("Success", f"Removed '{name}' from startup.")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not remove item: {e}")


class VerticalScrollFrame(tk.Frame):
    """Custom standard Tkinter scrollable container."""
    def __init__(self, container, bg_color="#1c1c1c"):
        super().__init__(container, bg=bg_color)
        
        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas, bg=bg_color)
        
        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mousewheel binding on hover
        self.bind("<Enter>", self._bind_mouse)
        self.bind("<Leave>", self._unbind_mouse)
        self.canvas.bind("<Enter>", self._bind_mouse)
        self.canvas.bind("<Leave>", self._unbind_mouse)
        self.inner_frame.bind("<Enter>", self._bind_mouse)
        self.inner_frame.bind("<Leave>", self._unbind_mouse)

    def _bind_mouse(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mouse(self, event):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _on_mousewheel(self, event):
        try:
            if self.winfo_exists():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
            
    def clear(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

# Compatibility alias for main.py dynamic routing
StartupManagerTab = StartupModule