import customtkinter as ctk
import psutil
import threading
import time
import platform
import datetime
import winreg
import socket
import subprocess
import os
import re
from tkinter import messagebox
from config import COLOR_GREEN, COLOR_LIGHT_BLUE, COLOR_RED

class DashboardModule:
    def __init__(self, parent):
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        
        self.running = False
        self.monitor_thread = None
        self.last_net_io = psutil.net_io_counters()
        
        # History for Graphing
        self.history_len = 60
        self.down_history = [0] * self.history_len
        self.up_history = [0] * self.history_len

        # Tracking Process IO (PID -> Bytes)
        self.prev_proc_io = {} 
        self.session_proc_usage = {} 

        # --- SAFETY FIRST: REGISTRY BACKUP ---
        self.safety_frame = ctk.CTkFrame(self.frame, fg_color="#2b2b2b", border_width=1, border_color="#3d3d3d")
        self.safety_frame.pack(fill="x", padx=10, pady=(0, 20))

        ctk.CTkLabel(self.safety_frame, text="SYSTEM SAFETY: REGISTRY BACKUP", 
                     font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(pady=(10, 5))
        
        warning_text = (
            "This utility modifies Windows Registry keys. We strongly recommend creating a backup before applying changes.\n"
            "(The Registry is a hierarchical database storing crucial settings for the OS, hardware, and applications.)"
        )
        ctk.CTkLabel(self.safety_frame, text=warning_text, 
                     font=("Arial", 11), text_color="gray70", justify="center").pack(pady=(0, 5))

        self.backup_btn = ctk.CTkButton(self.safety_frame, text="Backup Registry Now", 
                                        command=self.run_backup, fg_color="#1f538d", height=35)
        self.backup_btn.pack(pady=15)

        # --- Section 1: System Info Grid ---
        self.info_frame = ctk.CTkFrame(self.frame)
        self.info_frame.pack(fill="x", pady=(0, 20))
        self.info_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        uname = platform.uname()
        
        # Boot Time
        boot_timestamp = psutil.boot_time()
        boot_time_dt = datetime.datetime.fromtimestamp(boot_timestamp)
        boot_time_str = boot_time_dt.strftime("%Y-%m-%d %H:%M")

        # UPDATED: Use detailed version fetcher
        self.create_info_card(self.info_frame, 0, 0, "Windows Version", self.get_windows_version())
        self.create_info_card(self.info_frame, 0, 1, "PC Name", uname.node)
        self.create_info_card(self.info_frame, 0, 2, "Processor", self.get_clean_cpu_name()) 
        self.create_info_card(self.info_frame, 0, 3, "GPU Model", self.get_gpu_name())

        self.uptime_label = self.create_info_card(self.info_frame, 1, 0, "System Uptime (reboot)", "Calculating...")
        self.create_info_card(self.info_frame, 1, 1, "Local IP Address", self.get_local_ip())
        self.create_info_card(self.info_frame, 1, 2, "Last Boot Time (reboot)", boot_time_str)
        self.proc_label = self.create_info_card(self.info_frame, 1, 3, "Active Processes", "...")

        # --- Section 2: Resource Gauges ---
        self.stats_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.stats_frame.pack(fill="both", expand=True)
        self.stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.cpu_dial = self.create_gauge(self.stats_frame, 0, 0, "CPU Usage", COLOR_LIGHT_BLUE)
        self.ram_dial = self.create_gauge(self.stats_frame, 0, 1, "RAM Usage", COLOR_GREEN)
        self.disk_dial = self.create_gauge(self.stats_frame, 0, 2, "Disk Usage", COLOR_RED)

        # --- Section 3: Network Monitor ---
        self.net_frame = ctk.CTkFrame(self.frame)
        self.net_frame.pack(fill="x", pady=20)
        
        net_header = ctk.CTkFrame(self.net_frame, fg_color="transparent")
        net_header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(net_header, text="Network Activity (Live)", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        stats_box = ctk.CTkFrame(net_header, fg_color="transparent")
        stats_box.pack(side="right")
        self.lbl_download = ctk.CTkLabel(stats_box, text="↓ 0 KB/s", font=ctk.CTkFont(weight="bold"), text_color="#00E676")
        self.lbl_download.pack(side="left", padx=10)
        self.lbl_upload = ctk.CTkLabel(stats_box, text="↑ 0 KB/s", font=ctk.CTkFont(weight="bold"), text_color="#2979FF")
        self.lbl_upload.pack(side="left", padx=10)

        self.canvas_height = 100
        self.canvas = ctk.CTkCanvas(self.net_frame, height=self.canvas_height, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="x", padx=10, pady=(0, 10))

        # --- Section 4: Process Activity ---
        self.top_proc_frame = ctk.CTkFrame(self.frame)
        self.top_proc_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(self.top_proc_frame, text="Active Apps (Data Used This Session)", 
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=5)
        
        self.proc_list_container = ctk.CTkFrame(self.top_proc_frame, fg_color="transparent")
        self.proc_list_container.pack(fill="x", padx=10, pady=5)
        
        self.start_monitoring()

    # --- NEW: Real Windows Version Fetcher ---
    def get_windows_version(self):
        try:
            # Access Registry for the real branding and build number
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            
            # ProductName often says "Windows 10" even on 11, so we check Build Number
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            current_build, _ = winreg.QueryValueEx(key, "CurrentBuild")
            
            # Try to get "DisplayVersion" (e.g. 22H2, 23H2)
            try:
                display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            except:
                display_version, _ = winreg.QueryValueEx(key, "ReleaseId") # Fallback for older builds
            
            winreg.CloseKey(key)

            # Fix Windows 11 detection (Build 22000+)
            if int(current_build) >= 22000 and "Windows 10" in product_name:
                product_name = product_name.replace("Windows 10", "Windows 11")
            
            # Format: "Windows 11 Pro 23H2 (Build 22631)"
            return f"{product_name} {display_version} (Build {current_build})"
        except:
            # Fallback if registry access fails
            uname = platform.uname()
            return f"{uname.system} {uname.release} ({uname.version})"

    # --- CPU Parsing ---
    def get_clean_cpu_name(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            raw_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
        except:
            raw_name = platform.processor()

        clean = raw_name.replace("(R)", "").replace("(TM)", "").replace("CPU", "").replace("Processor", "").split("@")[0].strip()
        make = "Unknown"
        if "Intel" in clean: make = "Intel"
        elif "AMD" in clean: make = "AMD"
        
        final_str = clean 
        if make == "Intel":
            match = re.search(r'(Core\s+)?(i\d|Ultra\s\d)-(\d{3,5}\w?)', clean, re.IGNORECASE)
            if match:
                family = match.group(2) 
                model_num = match.group(3) 
                gen_digits = model_num[:2] if len(model_num) >= 4 and model_num[:2].isdigit() and int(model_num[:2]) > 9 else model_num[0]
                final_str = f"Intel Gen {gen_digits}, Core {family}-{model_num}"
        elif make == "AMD":
            clean = clean.replace("AMD", "").strip()
            final_str = f"AMD {clean}"

        return final_str

    # --- Backup Logic ---
    def run_backup(self):
        def _thread_task():
            try:
                self.backup_btn.configure(state="disabled", text="Backing up...")
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                backup_dir = os.path.join(os.path.expanduser("~"), "Documents", "WinOptimize_Backups")
                if not os.path.exists(backup_dir): os.makedirs(backup_dir)
                
                file_path = os.path.join(backup_dir, f"FullBackup_{timestamp}.reg")
                subprocess.run(f'reg export HKLM "{file_path}" /y', shell=True, check=True)
                
                self.frame.after(0, lambda: messagebox.showinfo("Backup Success", f"Registry backup created:\n{file_path}"))
            except Exception as e:
                self.frame.after(0, lambda: messagebox.showerror("Backup Error", f"Failed: {e}"))
            finally:
                self.frame.after(0, lambda: self.backup_btn.configure(state="normal", text="Backup Registry Now"))
        threading.Thread(target=_thread_task, daemon=True).start()

    # --- Monitoring Loop ---
    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()

    def monitor_loop(self):
        while self.running:
            try:
                # 1. System Stats
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                uptime_sec = time.time() - psutil.boot_time()
                days = int(uptime_sec // 86400)
                hours = int((uptime_sec % 86400) // 3600)
                mins = int((uptime_sec % 3600) // 60)
                
                if days > 0:
                    uptime_str = f"{days}d {hours}h {mins}m"
                else:
                    uptime_str = f"{hours}h {mins}m"
                
                proc_count = len(psutil.pids())

                # 2. Network Speed
                net_io = psutil.net_io_counters()
                bytes_sent = net_io.bytes_sent - self.last_net_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self.last_net_io.bytes_recv
                self.last_net_io = net_io

                self.down_history.pop(0)
                self.down_history.append(bytes_recv)
                self.up_history.pop(0)
                self.up_history.append(bytes_sent)

                # 3. Process Usage Logic
                curr_proc_io = {}
                for p in psutil.process_iter(['pid', 'name', 'io_counters']):
                    try:
                        io = p.info['io_counters']
                        if io:
                            total = io.read_bytes + io.write_bytes
                            curr_proc_io[p.info['pid']] = {'name': p.info['name'], 'total': total}
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Accumulate Usage per PID
                for pid, info in curr_proc_io.items():
                    total = info['total']
                    prev = self.prev_proc_io.get(pid, total)
                    diff = total - prev
                    self.prev_proc_io[pid] = total
                    
                    if diff > 0:
                        if pid not in self.session_proc_usage:
                            self.session_proc_usage[pid] = {'name': info['name'], 'usage': 0}
                        self.session_proc_usage[pid]['usage'] += diff

                # Aggregate by Process Name
                aggregated_usage = {}
                for pid, data in self.session_proc_usage.items():
                    name = data['name']
                    usage = data['usage']
                    if name in aggregated_usage:
                        aggregated_usage[name] += usage
                    else:
                        aggregated_usage[name] = usage

                # Sort by Usage
                top_procs = [{'name': name, 'usage': usage} for name, usage in aggregated_usage.items()]
                top_procs = sorted(top_procs, key=lambda x: x['usage'], reverse=True)[:5]

                # Update UI
                if self.running:
                    self.frame.after(0, lambda: self.update_ui(cpu, ram, disk, uptime_str, proc_count, bytes_sent, bytes_recv, top_procs))
                
                time.sleep(1)
            except Exception as e:
                print(f"Monitor Error: {e}")
                time.sleep(1)

    def update_ui(self, cpu, ram, disk, uptime, procs, tx, rx, top_procs):
        try:
            self.cpu_dial.progress_bar.set(cpu / 100)
            self.cpu_dial.value_label.configure(text=f"{cpu}%")
            self.ram_dial.progress_bar.set(ram / 100)
            self.ram_dial.value_label.configure(text=f"{ram}%")
            self.disk_dial.progress_bar.set(disk / 100)
            self.disk_dial.value_label.configure(text=f"{disk}%")

            self.uptime_label.configure(text=uptime)
            self.proc_label.configure(text=str(procs))
            self.lbl_download.configure(text=f"↓ {self.format_bytes(rx)}/s")
            self.lbl_upload.configure(text=f"↑ {self.format_bytes(tx)}/s")

            self.draw_graph()
            self.update_proc_list(top_procs)

        except Exception:
            pass

    def update_proc_list(self, top_procs):
        try:
            for widget in self.proc_list_container.winfo_children():
                widget.destroy()
            
            if not top_procs:
                ctk.CTkLabel(self.proc_list_container, text="Calculating session usage...", text_color="gray").pack()
            else:
                for p in top_procs:
                    row = ctk.CTkFrame(self.proc_list_container, fg_color="transparent", height=20)
                    row.pack(fill="x", pady=2)
                    
                    name_lbl = ctk.CTkLabel(row, text=p['name'], font=ctk.CTkFont(size=12), width=200, anchor="w")
                    name_lbl.pack(side="left", padx=5)
                    
                    data_str = self.format_bytes(p['usage'])
                    stat_lbl = ctk.CTkLabel(row, text=data_str, font=ctk.CTkFont(size=12, weight="bold"), 
                                            text_color="#00E676", width=120, anchor="e")
                    stat_lbl.pack(side="right", padx=5)
        except Exception:
            pass

    # --- Helpers ---
    def create_info_card(self, parent, row, col, title, value):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack()
        lbl = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=12), wraplength=180)
        lbl.pack()
        return lbl

    def create_gauge(self, parent, row, col, title, color):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(15, 5))
        progress = ctk.CTkProgressBar(frame, orientation="horizontal", height=15, progress_color=color)
        progress.set(0)
        progress.pack(pady=10, padx=20, fill="x")
        label = ctk.CTkLabel(frame, text="0%", font=ctk.CTkFont(size=20, weight="bold"), text_color=color)
        label.pack(pady=(0, 15))
        frame.progress_bar = progress
        frame.value_label = label
        return frame

    def format_bytes(self, size):
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels.get(n, '')}B"

    def draw_graph(self):
        if not self.canvas.winfo_exists(): return
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas_height
        
        max_val = max(max(self.down_history), max(self.up_history), 1024)
        step_x = w / (self.history_len - 1)
        
        def get_y(val): return h - (val / max_val * (h - 10)) - 5 

        points_down = []
        points_up = []
        
        for i, val in enumerate(self.down_history): points_down.extend([i * step_x, get_y(val)])
        for i, val in enumerate(self.up_history): points_up.extend([i * step_x, get_y(val)])

        if len(points_down) > 2:
            self.canvas.create_line(points_down, fill="#00E676", width=2, smooth=True)
        if len(points_up) > 2:
            self.canvas.create_line(points_up, fill="#2979FF", width=2, smooth=True)

    def get_local_ip(self):
        try: return socket.gethostbyname(socket.gethostname())
        except: return "Unknown"

    def get_gpu_name(self):
        try:
            cmd = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(cmd, startupinfo=startupinfo, shell=True).decode().strip()
            return output.split('\n')[0].strip() if output else "Unknown GPU"
        except: return "Unknown GPU"