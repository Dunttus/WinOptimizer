import customtkinter as ctk
import psutil
import threading
import time
import platform
import datetime
import winreg
import socket
import subprocess
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
        self.session_proc_usage = {} # Stores accumulated usage per session (PID based)

        # --- Section 1: System Info Grid (2 Rows) ---
        self.info_frame = ctk.CTkFrame(self.frame)
        self.info_frame.pack(fill="x", pady=(0, 20))
        self.info_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Fetch static data
        uname = platform.uname()
        cpu_name = self.get_processor_name()
        gpu_name = self.get_gpu_name()
        local_ip = self.get_local_ip()
        boot_time_str = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M")

        # Row 1
        self.create_info_card(self.info_frame, 0, 0, "Windows Version", f"{uname.system} {uname.release}")
        self.create_info_card(self.info_frame, 0, 1, "PC Name", uname.node)
        self.create_info_card(self.info_frame, 0, 2, "Processor", cpu_name)
        self.create_info_card(self.info_frame, 0, 3, "GPU Model", gpu_name)

        # Row 2
        self.uptime_label = self.create_info_card(self.info_frame, 1, 0, "System Uptime", "Calculating...")
        self.create_info_card(self.info_frame, 1, 1, "Local IP Address", local_ip)
        self.create_info_card(self.info_frame, 1, 2, "Last Boot Time", boot_time_str)
        self.proc_label = self.create_info_card(self.info_frame, 1, 3, "Active Processes", "...")

        # --- Section 2: Resource Gauges ---
        self.stats_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.stats_frame.pack(fill="both", expand=True)
        self.stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.cpu_dial = self.create_gauge(self.stats_frame, 0, 0, "CPU Usage", COLOR_LIGHT_BLUE)
        self.ram_dial = self.create_gauge(self.stats_frame, 0, 1, "RAM Usage", COLOR_GREEN)
        self.disk_dial = self.create_gauge(self.stats_frame, 0, 2, "Disk Usage", COLOR_RED)

        # --- Section 3: Network Monitor & Graph ---
        self.net_frame = ctk.CTkFrame(self.frame)
        self.net_frame.pack(fill="x", pady=20)
        
        # Header & Text Stats
        net_header = ctk.CTkFrame(self.net_frame, fg_color="transparent")
        net_header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(net_header, text="Network Activity (1 min history)", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        
        stats_box = ctk.CTkFrame(net_header, fg_color="transparent")
        stats_box.pack(side="right")
        
        self.lbl_download = ctk.CTkLabel(stats_box, text="↓ 0 KB/s", font=ctk.CTkFont(weight="bold"), text_color="#00E676")
        self.lbl_download.pack(side="left", padx=10)
        
        self.lbl_upload = ctk.CTkLabel(stats_box, text="↑ 0 KB/s", font=ctk.CTkFont(weight="bold"), text_color="#2979FF")
        self.lbl_upload.pack(side="left", padx=10)

        # Canvas for Graphing
        self.canvas_height = 100
        self.canvas = ctk.CTkCanvas(self.net_frame, height=self.canvas_height, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="x", padx=10, pady=(0, 10))

        # --- Section 4: Top Processes ---
        self.top_proc_frame = ctk.CTkFrame(self.frame)
        self.top_proc_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(self.top_proc_frame, text="Top Bandwidth Consumers (Combined Session Total)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=5)
        
        # Container for the list items
        self.proc_list_container = ctk.CTkFrame(self.top_proc_frame, fg_color="transparent")
        self.proc_list_container.pack(fill="x", padx=10, pady=5)
        
        # Start
        self.start_monitoring()

    # --- Lifecycle ---
    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()

    def stop_monitoring(self):
        self.running = False

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

    # --- Info Fetchers ---
    def get_local_ip(self):
        try: return socket.gethostbyname(socket.gethostname())
        except: return "Unknown"

    def get_gpu_name(self):
        try:
            cmd = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(cmd, startupinfo=startupinfo, shell=True).decode().strip()
            lines = [line.strip() for line in output.split('\n') if line.strip()]
            if not lines: return "Unknown GPU"
            for name in lines:
                lower = name.lower()
                if any(x in lower for x in ["nvidia", "amd", "radeon", "rtx", "gtx"]): return name
            return lines[0]
        except: return "Integrated / Unknown"

    def get_processor_name(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
            key.Close()
            clean_name = name.replace("Intel(R)", "").replace("AMD", "").replace("(TM)", "").replace("(R)", "").replace("CPU", "").strip()
            if "@" in clean_name: clean_name = clean_name.split("@")[0].strip()
            if "Core" in clean_name:
                import re
                match = re.search(r'-(\d{2,})', clean_name)
                if match:
                    gen = match.group(1)[:2]
                    suffix = "th"
                    if gen.isdigit() and 10 <= int(gen) <= 20: suffix = "th"
                    gen_str = f"{gen}{suffix} Gen"
                    if gen_str.lower() in clean_name.lower(): return clean_name
                    return f"{gen_str}, {clean_name}"
            return clean_name
        except: return platform.processor()

    def format_bytes(self, size):
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.1f} {power_labels[n]}"

    def get_uptime(self):
        try:
            boot = datetime.datetime.fromtimestamp(psutil.boot_time())
            delta = datetime.datetime.now() - boot
            days, rem = divmod(int(delta.total_seconds()), 86400)
            hours, rem = divmod(rem, 3600)
            mins, _ = divmod(rem, 60)
            if days > 0: return f"{days}d {hours}h {mins}m"
            return f"{hours}h {mins}m"
        except: return "Unknown"

    # --- Monitoring Logic ---
    def monitor_loop(self):
        while self.running:
            try:
                # 1. System Stats
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                proc_count = len(psutil.pids())
                
                # 2. Network Total
                net_io = psutil.net_io_counters()
                bytes_sent = net_io.bytes_sent - self.last_net_io.bytes_sent
                bytes_recv = net_io.bytes_recv - self.last_net_io.bytes_recv
                self.last_net_io = net_io
                
                # 3. Top IO Processes (Accumulated & Grouped)
                top_procs = self.get_top_accumulated_processes()

                # Update UI
                self.frame.after(0, lambda: self.update_ui(cpu, ram, disk, bytes_sent, bytes_recv, proc_count, top_procs))
                time.sleep(1)
            except Exception as e:
                print(f"Monitor Error: {e}")
                break

    def get_top_accumulated_processes(self):
        """Accumulate usage for each process, then GROUP by Name."""
        current_proc_io = {}

        # 1. Update internal tracking per PID
        for p in psutil.process_iter(['pid', 'name', 'io_counters']):
            try:
                io = p.info['io_counters']
                if io:
                    current_bytes = io.read_bytes + io.write_bytes
                    pid = p.info['pid']
                    name = p.info['name']
                    current_proc_io[pid] = current_bytes
                    
                    if pid in self.prev_proc_io:
                        delta = current_bytes - self.prev_proc_io[pid]
                        if delta > 0:
                            if pid not in self.session_proc_usage:
                                self.session_proc_usage[pid] = {'name': name, 'total': 0}
                            self.session_proc_usage[pid]['total'] += delta
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        self.prev_proc_io = current_proc_io
        
        # 2. Group by Name (Combine "chrome.exe" totals)
        grouped_usage = {}
        for data in self.session_proc_usage.values():
            proc_name = data['name']
            if proc_name not in grouped_usage:
                grouped_usage[proc_name] = 0
            grouped_usage[proc_name] += data['total']

        # 3. Convert to list and sort
        sorted_list = [{'name': k, 'total': v} for k, v in grouped_usage.items()]
        sorted_list.sort(key=lambda x: x['total'], reverse=True)
        
        return sorted_list[:5]

    def update_ui(self, cpu, ram, disk, up_speed, down_speed, proc_count, top_procs):
        try:
            if not self.frame.winfo_exists():
                self.running = False
                return

            # Gauges
            self.cpu_dial.progress_bar.set(cpu / 100)
            self.cpu_dial.value_label.configure(text=f"{cpu}%")
            self.ram_dial.progress_bar.set(ram / 100)
            self.ram_dial.value_label.configure(text=f"{ram}%")
            self.disk_dial.progress_bar.set(disk / 100)
            self.disk_dial.value_label.configure(text=f"{disk}%")
            
            # Text
            self.lbl_download.configure(text=f"↓ {self.format_bytes(down_speed)}B/s")
            self.lbl_upload.configure(text=f"↑ {self.format_bytes(up_speed)}B/s")
            self.uptime_label.configure(text=self.get_uptime())
            self.proc_label.configure(text=str(proc_count))

            # Graph
            self.down_history.append(down_speed)
            self.down_history.pop(0)
            self.up_history.append(up_speed)
            self.up_history.pop(0)
            self.draw_graph()

            # Update Top Processes List
            for widget in self.proc_list_container.winfo_children():
                widget.destroy()

            # Header
            hdr = ctk.CTkFrame(self.proc_list_container, fg_color="transparent", height=20)
            hdr.pack(fill="x")
            ctk.CTkLabel(hdr, text="Process Name", font=ctk.CTkFont(size=11, weight="bold"), width=200, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Session Total", font=ctk.CTkFont(size=11, weight="bold"), width=100, anchor="e").pack(side="right")

            # Rows
            if not top_procs:
                ctk.CTkLabel(self.proc_list_container, text="No active usage detected yet...", text_color="gray").pack()
            else:
                for p in top_procs:
                    row = ctk.CTkFrame(self.proc_list_container, fg_color="transparent", height=20)
                    row.pack(fill="x", pady=2)
                    ctk.CTkLabel(row, text=p['name'], font=ctk.CTkFont(size=11), width=200, anchor="w").pack(side="left")
                    ctk.CTkLabel(row, text=self.format_bytes(p['total']) + "B", font=ctk.CTkFont(size=11), width=100, anchor="e", text_color="#00E676").pack(side="right")

        except Exception:
            pass

    def draw_graph(self):
        try:
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

            if len(points_down) > 4: self.canvas.create_line(points_down, fill="#00E676", width=2, smooth=True)
            if len(points_up) > 4: self.canvas.create_line(points_up, fill="#2979FF", width=2, smooth=True)
        except: pass