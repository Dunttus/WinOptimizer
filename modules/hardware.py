import customtkinter as ctk
import subprocess
import json
from utils import add_info_section

class HardwareModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Hardware Health", 
                         "Deep-dive monitoring for battery wear and storage reliability metrics.")

        self.scroll_frame = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # --- Refresh Button ---
        self.refresh_btn = ctk.CTkButton(self.frame, text="Refresh Hardware Data", command=self.refresh_data)
        self.refresh_btn.pack(pady=10)

        self.refresh_data()

    def refresh_data(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        self.render_battery_section()
        self.render_disk_section()
        self.render_silicon_section() # <--- NEW SECTION

    def render_silicon_section(self):
        section_f = self.create_section_frame("🧠 Silicon, Memory & Thermals")
        
        try:
            # 1. Query RAM Speed & Manufacturer
            ram_cmd = "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, Speed, Capacity | ConvertTo-Json"
            ram_raw = subprocess.check_output(["powershell", "-Command", ram_cmd], text=True).strip()
            
            # 2. Query GPU Details
            gpu_cmd = "Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, VideoProcessor | ConvertTo-Json"
            gpu_raw = subprocess.check_output(["powershell", "-Command", gpu_cmd], text=True).strip()

            # 3. Query CPU Temperature (Thermal Zone)
            # Temp is stored in decikelvins. Formula: (Value / 10) - 273.15
            temp_cmd = "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object CurrentTemperature | ConvertTo-Json"
            temp_raw = subprocess.check_output(["powershell", "-Command", temp_cmd], text=True).strip()

            # 4. Query Fan Speeds
            fan_cmd = "Get-CimInstance Win32_Fan | Select-Object DesiredSpeed, Status | ConvertTo-Json"
            fan_raw = subprocess.check_output(["powershell", "-Command", fan_cmd], text=True).strip()

            # --- Render Thermals & Fans (TOP PRIORITY) ---
            t_row = ctk.CTkFrame(section_f, fg_color="#2b2b2b", corner_radius=8)
            t_row.pack(fill="x", pady=5, padx=15)
            
            # Temperature Logic
            cpu_temp_str = "N/A"
            if temp_raw:
                t_data = json.loads(temp_raw)
                t_list = t_data if isinstance(t_data, list) else [t_data]
                raw_temp = t_list[0].get("CurrentTemperature", 0)
                if raw_temp > 0:
                    celsius = (raw_temp / 10) - 273.15
                    cpu_temp_str = f"{round(celsius, 1)}°C"
            
            temp_color = "#FFA726" if cpu_temp_str != "N/A" and float(cpu_temp_str.replace("°C","")) > 75 else "#00E676"
            ctk.CTkLabel(t_row, text=f"CPU Temp: {cpu_temp_str}", font=("Arial", 12, "bold"), text_color=temp_color).pack(side="left", padx=15, pady=10)

            # Fan Logic
            fan_count = 0
            if fan_raw:
                f_data = json.loads(fan_raw)
                f_list = f_data if isinstance(f_data, list) else [f_data]
                fan_count = len(f_list)
            ctk.CTkLabel(t_row, text=f"Fans Detected: {fan_count}", text_color="gray").pack(side="right", padx=15)

            # --- Render RAM ---
            if ram_raw:
                ram_data = json.loads(ram_raw)
                ram_list = ram_data if isinstance(ram_data, list) else [ram_data]
                speed = ram_list[0].get("Speed", "N/A")
                make = ram_list[0].get("Manufacturer", "Unknown")
                
                row = ctk.CTkFrame(section_f, fg_color="#2b2b2b", corner_radius=8)
                row.pack(fill="x", pady=5, padx=15)
                ctk.CTkLabel(row, text=f"RAM: {make}", font=("Arial", 11, "bold")).pack(side="left", padx=15, pady=8)
                ctk.CTkLabel(row, text=f"{speed} MHz", text_color="#3B8ED0").pack(side="right", padx=15)

            # --- Render GPU ---
            if gpu_raw:
                gpu_data = json.loads(gpu_raw)
                gpu_list = gpu_data if isinstance(gpu_data, list) else [gpu_data]
                for gpu in gpu_list:
                    name = gpu.get("Name", "Unknown GPU")
                    row = ctk.CTkFrame(section_f, fg_color="#2b2b2b", corner_radius=8)
                    row.pack(fill="x", pady=5, padx=15)
                    ctk.CTkLabel(row, text=f"GPU: {name}", font=("Arial", 11)).pack(side="left", padx=15, pady=8)

        except Exception as e:
            ctk.CTkLabel(section_f, text="Thermal/Silicon sensors not exposed by BIOS.", text_color="gray").pack(pady=10)
            print(f"Silicon Debug: {e}")

    def render_battery_section(self):
        section_f = self.create_section_frame("🔋 Battery Health")
        try:
            cmd = "Get-CimInstance -ClassName Win32_Battery | Select-Object DesignCapacity, FullChargeCapacity, CycleCount | ConvertTo-Json"
            raw = subprocess.check_output(["powershell", "-Command", cmd], text=True).strip()
            
            if not raw: raise Exception()
                
            data = json.loads(raw)
            design = data.get("DesignCapacity", 0)
            full = data.get("FullChargeCapacity", 0)
            cycles = data.get("CycleCount", "N/A")
            
            if design > 0:
                health_pct = round((full / design) * 100, 1)
                
                ctk.CTkLabel(section_f, text=f"Overall Health: {health_pct}%", font=("Arial", 16, "bold")).pack(pady=5)
                
                prog = ctk.CTkProgressBar(section_f, height=15, progress_color="#00E676" if health_pct > 80 else "#FFA726")
                prog.set(health_pct / 100)
                prog.pack(fill="x", padx=40, pady=10)

                detail_txt = f"Design: {design} mWh | Current Max: {full} mWh | Cycles: {cycles}"
                ctk.CTkLabel(section_f, text=detail_txt, text_color="gray").pack(pady=5)
            else:
                ctk.CTkLabel(section_f, text="Battery detected but reporting 0 capacity.", text_color="gray").pack(pady=20)

        except Exception:
            ctk.CTkLabel(section_f, text="No Battery Detected (Desktop PC)", text_color="gray").pack(pady=20)

    def render_disk_section(self):
        section_f = self.create_section_frame("💽 Detailed Storage Reliability")
        
        try:
            # PowerShell Query with strict error handling
            ps_cmd = (
                "Get-PhysicalDisk -ErrorAction SilentlyContinue | ForEach-Object { "
                "  $disk = $_; "
                "  try { $stats = $disk | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue } catch { $stats = $null }; "
                "  [PSCustomObject]@{ "
                "    Name = $disk.FriendlyName; "
                "    Health = $disk.HealthStatus; "
                "    Type = $disk.MediaType; "
                "    Temp = if ($stats -and $stats.Temperature -ne $null) { $stats.Temperature } else { $null }; "
                "    Wear = if ($stats -and $stats.Wear -ne $null) { $stats.Wear } else { $null }; "
                "    ReadErrors = if ($stats -and $stats.ReadErrorsTotal -ne $null) { $stats.ReadErrorsTotal } else { 0 }; "
                "    WriteErrors = if ($stats -and $stats.WriteErrorsTotal -ne $null) { $stats.WriteErrorsTotal } else { 0 } "
                "  } "
                "} | ConvertTo-Json"
            )
            
            raw = subprocess.check_output(["powershell", "-Command", ps_cmd], text=True).strip()
            
            if not raw:
                ctk.CTkLabel(section_f, text="No physical disks detected.", text_color="gray").pack(pady=20)
                return

            data = json.loads(raw)
            drives = data if isinstance(data, list) else [data]

            for drive in drives:
                name = drive.get("Name", "Unknown Drive")
                status = str(drive.get("Health", "Unknown"))
                m_type = drive.get("Type", "Drive")
                
                # --- NUL-SAFE DATA EXTRACTION ---
                # This ensures we never pass None to int()
                temp = drive.get("Temp")
                wear = drive.get("Wear")
                
                r_err_val = drive.get("ReadErrors")
                r_err = int(r_err_val) if r_err_val is not None else 0
                
                w_err_val = drive.get("WriteErrors")
                w_err = int(w_err_val) if w_err_val is not None else 0

                # --- UI RENDERING ---
                row = ctk.CTkFrame(section_f, fg_color="#2b2b2b", corner_radius=8)
                row.pack(fill="x", pady=8, padx=15)

                header = ctk.CTkFrame(row, fg_color="transparent")
                header.pack(fill="x", padx=10, pady=(5, 0))
                
                status_color = "#00E676" if status == "Healthy" else "#FF5252"
                ctk.CTkLabel(header, text=f"{name} ({m_type})", font=("Arial", 13, "bold"), anchor="w").pack(side="left")
                ctk.CTkLabel(header, text=status.upper(), text_color=status_color, font=("Arial", 11, "bold")).pack(side="right")

                stats_inner = ctk.CTkFrame(row, fg_color="transparent")
                stats_inner.pack(fill="x", padx=10, pady=10)
                
                # Temp display
                temp_str = f"{temp}°C" if (temp is not None and 0 < temp < 110) else "N/A"
                self.add_mini_stat(stats_inner, "Temp", temp_str, 0)
                
                # Wear display
                wear_str = f"{100 - int(wear)}%" if (wear is not None and 0 <= int(wear) <= 100) else "N/A"
                self.add_mini_stat(stats_inner, "Life", wear_str, 1)
                
                # Errors display
                err_str = f"{r_err} / {w_err}"
                err_color = "#FF5252" if (r_err + w_err) > 0 else "gray"
                self.add_mini_stat(stats_inner, "R/W Errors", err_str, 2, val_color=err_color)

        except Exception as e:
            ctk.CTkLabel(section_f, text="Hardware reporting error. Check Console.", text_color="#FF5252").pack(pady=20)
            print(f"DEBUG - Disk Health Error: {e}")

    def add_mini_stat(self, parent, label, value, col, val_color="white"):
        f = ctk.CTkFrame(parent, fg_color="#333333", corner_radius=4)
        f.pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkLabel(f, text=label, font=("Arial", 10), text_color="gray").pack()
        ctk.CTkLabel(f, text=str(value), font=("Arial", 11, "bold"), text_color=val_color).pack()

    def create_section_frame(self, title):
        f = ctk.CTkFrame(self.scroll_frame, fg_color="#1e1e1e", corner_radius=10)
        f.pack(fill="x", pady=10)
        ctk.CTkLabel(f, text=title, font=("Arial", 14, "bold"), text_color="#3B8ED0").pack(pady=10)
        return f