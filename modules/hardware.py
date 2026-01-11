import customtkinter as ctk
import subprocess
import json
import threading
import os
from tkinter import messagebox
from utils import add_info_section

class HardwareModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Hardware Health", 
                         "Monitor silicon thermals, RAM configuration, storage reliability, and battery health.")

        # --- Loading Overlay ---
        self.loading_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.loading_frame.pack(expand=True)
        
        self.loading_lbl = ctk.CTkLabel(self.loading_frame, text="Gathering Deep Hardware Metrics...", 
                                        font=("Arial", 14, "italic"), text_color="gray")
        self.loading_lbl.pack(pady=10)
        
        self.prog = ctk.CTkProgressBar(self.loading_frame, orientation="horizontal", width=240, mode="indeterminate")
        self.prog.pack()

        # --- Content Container ---
        self.scroll_frame = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        
        self.ui_initialized = False

    def start_load(self, force=False):
        """Triggers the background data fetch."""
        if force or not self.scroll_frame.winfo_ismapped():
            self.prog.start()
            
            if not self.ui_initialized:
                self.scroll_frame.pack_forget()
                self.loading_frame.pack(expand=True)
            
            threading.Thread(target=self._fetch_data_thread, daemon=True).start()

    def _fetch_data_thread(self):
        """Gathers all metrics in a background thread."""
        try:
            disks = self._get_disk_data()
            silicon = self._get_silicon_data()
            self.frame.after(0, lambda: self._render_ui(disks, silicon))
        except Exception as e:
            print(f"Hardware Logic Error: {e}")
            self.frame.after(0, self._render_error)

    def _render_ui(self, disks, silicon):
        self.prog.stop()
        self.loading_frame.pack_forget()

        if not self.ui_initialized:
            self.footer_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
            self.footer_frame.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
            
            self.refresh_btn = ctk.CTkButton(self.footer_frame, text="Refresh Hardware Data", 
                                        font=("Arial", 12, "bold"),
                                        command=lambda: self.start_load(force=True),
                                        height=35, fg_color="#1f538d")
            self.refresh_btn.pack(side="right")

            self.scroll_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)
            self.ui_initialized = True

        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Build Sections
        self._build_battery_ui() 
        self._build_silicon_ui(silicon)
        self._build_disk_ui(disks)

    def _render_error(self):
        self.prog.stop()
        self.loading_lbl.configure(text="Error: Could not retrieve hardware info.", text_color="#FF5252")

    # ==========================================
    # BATTERY REPORT LOGIC
    # ==========================================
    def run_battery_report(self, btn_widget):
        def _target():
            try:
                user_home = os.path.expanduser("~")
                report_path = os.path.join(user_home, "battery-report.html")
                self.frame.after(0, lambda: btn_widget.configure(text="Generating...", state="disabled"))
                
                subprocess.run(f'powercfg /batteryreport /output "{report_path}"', shell=True, check=True)
                
                self.frame.after(0, lambda: btn_widget.configure(text="Generate Windows Battery Report", state="normal"))
                
                if os.path.exists(report_path):
                    if messagebox.askyesno("Report Ready", "Battery Report generated successfully.\nOpen it now in your browser?"):
                        subprocess.Popen(f'explorer "{report_path}"', shell=True)
            except Exception as e:
                self.frame.after(0, lambda: btn_widget.configure(text="Error Generating", state="normal"))
                messagebox.showerror("Error", f"Could not generate battery report: {e}")

        threading.Thread(target=_target, daemon=True).start()

    # ==========================================
    # DATA FETCHING
    # ==========================================
    def _get_disk_data(self):
        try:
            ps_cmd = (
                "Get-PhysicalDisk -ErrorAction SilentlyContinue | ForEach-Object { "
                "  $disk = $_; "
                "  try { $stats = $disk | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue } catch { $stats = $null }; "
                "  [PSCustomObject]@{ "
                "    Name = $disk.FriendlyName; Health = $disk.HealthStatus; Type = $disk.MediaType; "
                "    Temp = if ($stats -and $stats.Temperature -ne $null) { $stats.Temperature } else { $null }; "
                "    Wear = if ($stats -and $stats.Wear -ne $null) { $stats.Wear } else { $null }; "
                "    ReadErrors = if ($stats -and $stats.ReadErrorsTotal -ne $null) { $stats.ReadErrorsTotal } else { 0 }; "
                "    WriteErrors = if ($stats -and $stats.WriteErrorsTotal -ne $null) { $stats.WriteErrorsTotal } else { 0 } "
                "  } "
                "} | ConvertTo-Json"
            )
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            raw = subprocess.check_output(["powershell", "-Command", ps_cmd], text=True, startupinfo=startupinfo).strip()
            if not raw: return []
            data = json.loads(raw)
            return data if isinstance(data, list) else [data]
        except: return []

    def _get_silicon_data(self):
        res = {}
        try:
            ram = "Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator, Speed, Capacity, Manufacturer | ConvertTo-Json"
            temp = "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object CurrentTemperature | ConvertTo-Json"
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            res['ram'] = json.loads(subprocess.check_output(["powershell", "-Command", ram], text=True, startupinfo=startupinfo).strip() or "[]")
            res['temp'] = json.loads(subprocess.check_output(["powershell", "-Command", temp], text=True, startupinfo=startupinfo).strip() or "[]")
        except: pass
        return res

    # ==========================================
    # UI BUILDING
    # ==========================================
    def _build_battery_ui(self):
        section = self.create_section_frame("Battery Health & Reports")
        
        # UPDATED TEXT HERE
        info_text = (
            "Generates a detailed HTML report containing usage history,\n"
            "capacity trends, and estimated battery life statistics."
        )
        ctk.CTkLabel(section, text=info_text, text_color="gray", justify="center").pack(pady=(10, 5))

        report_btn = ctk.CTkButton(section, text="Generate Windows Battery Report", 
                                   command=lambda: self.run_battery_report(report_btn))
        report_btn.pack(pady=15)

    def _build_silicon_ui(self, data):
        section = self.create_section_frame("Silicon & Memory")
        t_list = data.get('temp', [])
        t_list = t_list if isinstance(t_list, list) else [t_list]
        cpu_temp = "N/A"
        if t_list and t_list[0] and t_list[0].get("CurrentTemperature"):
            cpu_temp = f"{round((t_list[0]['CurrentTemperature'] / 10) - 273.15, 1)}°C"
        
        t_row = ctk.CTkFrame(section, fg_color="#2b2b2b", corner_radius=8)
        t_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(t_row, text=f"CPU Temperature: {cpu_temp}", font=("Arial", 12, "bold"), 
                     text_color="#00E676" if cpu_temp != "N/A" else "gray").pack(pady=10)

        ram_list = data.get('ram', [])
        ram_list = ram_list if isinstance(ram_list, list) else [ram_list]
        for stick in ram_list:
            r_row = ctk.CTkFrame(section, fg_color="#2b2b2b", corner_radius=6)
            r_row.pack(fill="x", pady=2, padx=15)
            cap_gb = round(int(stick.get("Capacity", 0)) / (1024**3))
            ctk.CTkLabel(r_row, text=f"Slot: {stick.get('DeviceLocator', 'Unknown')} ({stick.get('Manufacturer', 'Generic')})", font=("Arial", 11)).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(r_row, text=f"{cap_gb}GB @ {stick.get('Speed')}MHz", text_color="#3B8ED0").pack(side="right", padx=10)

    def _build_disk_ui(self, disks):
        section = self.create_section_frame("Storage Reliability")
        if not disks:
            ctk.CTkLabel(section, text="No disk data found.", text_color="gray").pack(pady=10)
            return

        for drive in disks:
            row = ctk.CTkFrame(section, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", pady=8, padx=15)
            header = ctk.CTkFrame(row, fg_color="transparent")
            header.pack(fill="x", padx=10, pady=(5, 0))
            status = str(drive.get("Health", "Unknown"))
            ctk.CTkLabel(header, text=f"{drive.get('Name')} ({drive.get('Type')})", font=("Arial", 12, "bold")).pack(side="left")
            ctk.CTkLabel(header, text=status.upper(), text_color="#00E676" if status == "Healthy" else "#FF5252").pack(side="right")
            
            stats_f = ctk.CTkFrame(row, fg_color="transparent")
            stats_f.pack(fill="x", padx=10, pady=10)
            
            temp = drive.get("Temp")
            self.add_mini_stat(stats_f, "Temp", f"{temp}°C" if temp else "N/A")
            wear = drive.get("Wear")
            self.add_mini_stat(stats_f, "Life", f"{100 - int(wear)}%" if wear is not None else "N/A")
            self.add_mini_stat(stats_f, "R/W Errors", f"{drive.get('ReadErrors',0)}/{drive.get('WriteErrors',0)}")

    def add_mini_stat(self, parent, label, value):
        f = ctk.CTkFrame(parent, fg_color="#333333", corner_radius=4)
        f.pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkLabel(f, text=label, font=("Arial", 10), text_color="gray").pack()
        ctk.CTkLabel(f, text=str(value), font=("Arial", 11, "bold")).pack()

    def create_section_frame(self, title):
        f = ctk.CTkFrame(self.scroll_frame, fg_color="#1e1e1e", corner_radius=10)
        f.pack(fill="x", pady=10)
        ctk.CTkLabel(f, text=title.upper(), font=("Arial", 11, "bold"), text_color="#3B8ED0").pack(pady=10)
        return f