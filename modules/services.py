import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from config import DISABLABLE_SERVICES

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


class ServicesModule(tk.Frame):
    """Native Tkinter Service Manager Module utilizing config.py."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")

        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="Service Manager", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Disable unnecessary background services to free up RAM and CPU.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- Warning Frame ---
        warning_frame = tk.Frame(self, bg="#1c1c1c")
        warning_frame.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(
            warning_frame, 
            text="⚠️ Note: Services listed below are safe to disable for most users, pulled directly from config definitions.", 
            fg="gray", bg="#1c1c1c", font=("Segoe UI", 9)
        ).pack(anchor="w")

        # --- Services List Container ---
        list_container = tk.Frame(self, bg="#1c1c1c", bd=1, relief="solid")
        list_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        tk.Label(
            list_container, text=" Debloat Services (Config Whitelist) ", fg="#888888", 
            bg="#1c1c1c", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=10, pady=(8, 0))

        self.scroll = VerticalScrollFrame(list_container, bg_color="#1c1c1c")
        self.scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Dictionary mapping service names to user-friendly descriptions
        service_descriptions = {
            "DiagTrack": ("Connected User Exp (Telemetry)", "Tracks usage data and sends it to Microsoft."),
            "SysMain": ("SysMain (Superfetch)", "Preloads apps to RAM. Can cause high disk usage on HDDs."),
            "PcaSvc": ("Program Compatibility Assistant", "Manages compatibility assistance for user applications."),
            "Fax": ("Fax Service", "Legacy service for sending and receiving faxes."),
            "MapsBroker": ("Downloaded Maps Manager", "Updates offline map data in the background."),
            "RetailDemo": ("Retail Demo Service", "Controls store-display demo modes"),
            "TabletInputService": ("Touch Keyboard Service", "On-screen keyboard/handwriting (disable if not using touch).")
        }

        # Populate rows dynamically using DISABLABLE_SERVICES from config.py
        for service_name in sorted(DISABLABLE_SERVICES):
            title, desc = service_descriptions.get(service_name, (service_name, "Whitelisted safe service from configuration."))
            self.create_row(title, service_name, desc)

    def create_row(self, title, service_name, desc):
        parent = self.scroll.inner_frame
        
        row = tk.Frame(parent, bg="#2a2a2a", bd=1, relief="solid")
        row.pack(fill="x", pady=4, padx=5)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0)
        
        # Text Info
        info = tk.Frame(row, bg="#2a2a2a")
        info.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)
        
        tk.Label(
            info, text=title, font=("Segoe UI", 10, "bold"), 
            fg="#ffffff", bg="#2a2a2a", anchor="w"
        ).pack(anchor="w", fill="x")
        
        tk.Label(
            info, text=f"Service ID: {service_name} — {desc}", font=("Segoe UI", 9), 
            fg="#888888", bg="#2a2a2a", anchor="w", wraplength=550
        ).pack(anchor="w", fill="x", pady=(2, 0))

        # Action Button Frame
        btn_frame = tk.Frame(row, bg="#2a2a2a")
        btn_frame.grid(row=0, column=1, sticky="e", padx=12, pady=8)

        btn = tk.Button(
            btn_frame, text="Disable", width=12, bg="#3B8ED0", fg="white", 
            font=("Segoe UI", 8, "bold"), activebackground="#1F6AA5", 
            activeforeground="white", bd=0, cursor="hand2", padx=5, pady=4
        )
        btn.configure(command=lambda b=btn, s=service_name: self.disable_service(s, b))
        btn.pack()

    def disable_service(self, service_name, button):
        """Disables service and updates button with specific status."""
        
        button.configure(text="Processing...", state="disabled", bg="#4d4d4d", fg="#aaaaaa")
        
        def _target():
            try:
                subprocess.run(f"net stop {service_name} /y", shell=True, capture_output=True, creationflags=0x08000000)

                cmd = f"sc config {service_name} start= disabled"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000)

                if result.returncode == 0:
                    new_text = "Disabled ✓"
                    new_color = "#4d4d4d" 
                else:
                    err = result.stderr.strip()
                    if "Access is denied" in err:
                        new_text = "Access Denied" 
                    elif "OpenService FAILED 1060" in err:
                        new_text = "Not Installed" 
                    elif "OpenService FAILED 5" in err:
                        new_text = "System Locked" 
                    elif "OpenService FAILED" in err:
                        new_text = "Protected"     
                    else:
                        new_text = "Failed"

                    new_color = "#4d4d4d" 

                self.after(0, lambda: button.configure(text=new_text, bg=new_color, fg="#aaaaaa", state="disabled"))

            except Exception as e:
                print(f"Service Error: {e}")
                self.after(0, lambda: button.configure(text="Script Error", bg="#4d4d4d", fg="#aaaaaa", state="disabled"))

        threading.Thread(target=_target, daemon=True).start()

# Compatibility alias for main.py dynamic routing
ServiceManagerTab = ServicesModule