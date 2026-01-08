import customtkinter as ctk
import psutil
import tkinter as tk
from collections import deque, Counter
from utils import add_info_section, create_history_chart, create_meter, create_dynamic_chart, draw_line_chart
from config import COLOR_GREEN, COLOR_LIGHT_BLUE

class DashboardModule:
    def __init__(self, parent):
        self.frame = ctk.CTkScrollableFrame(parent, label_text="System Dashboard")
        
        # --- System Monitor ---
        add_info_section(self.frame, "System Monitor", "Real-time CPU, RAM, and Disk usage history.")
        
        self.cpu_history = deque([0]*40, maxlen=40)
        self.ram_history = deque([0]*40, maxlen=40)
        
        self.cpu_chart_frame, self.cpu_chart_canvas, self.cpu_val_lbl = create_history_chart(self.frame, "CPU Usage")
        self.ram_chart_frame, self.ram_chart_canvas, self.ram_val_lbl = create_history_chart(self.frame, "RAM Usage")
        self.disk_progress, self.disk_value_label = create_meter(self.frame, "Disk Usage (C:)")

        # --- Traffic Monitor ---
        add_info_section(self.frame, "Traffic Monitor", "Real-time network usage & active process connections.")
        
        self.net_down_history = deque([0]*60, maxlen=60)
        self.net_up_history = deque([0]*60, maxlen=60)
        self.last_net_io = psutil.net_io_counters()
        self.traffic_update_tick = 0
        
        # Traffic Stats Text
        self.traffic_stats_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.traffic_stats_frame.pack(fill="x", padx=20, pady=5)
        
        self.lbl_down_current = ctk.CTkLabel(self.traffic_stats_frame, text="↓ 0 KB/s", font=ctk.CTkFont(size=20, weight="bold"), text_color=COLOR_GREEN)
        self.lbl_down_current.pack(side="left", expand=True)
        
        self.lbl_up_current = ctk.CTkLabel(self.traffic_stats_frame, text="↑ 0 KB/s", font=ctk.CTkFont(size=20, weight="bold"), text_color=COLOR_LIGHT_BLUE)
        self.lbl_up_current.pack(side="left", expand=True)

        # Traffic Charts
        self.chart_down_frame, self.chart_down_canvas, self.chart_down_max_lbl = create_dynamic_chart(self.frame, "Download History")
        self.chart_up_frame, self.chart_up_canvas, self.chart_up_max_lbl = create_dynamic_chart(self.frame, "Upload History")

        # Process List Container
        self.traffic_proc_frame = ctk.CTkFrame(self.frame, fg_color="gray20")
        self.traffic_proc_frame.pack(fill="x", padx=20, pady=10)
        
        # Header for the list
        header_row = ctk.CTkFrame(self.traffic_proc_frame, fg_color="gray30", height=30)
        header_row.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header_row, text="Process Name", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(header_row, text="Open Connections", font=ctk.CTkFont(size=11)).pack(side="right", padx=10)

        # The Scrollable List for Processes
        self.traffic_list = ctk.CTkScrollableFrame(self.traffic_proc_frame, label_text="Active Network Processes", height=200)
        self.traffic_list.pack(fill="x", padx=5, pady=(0,5))
        
        self.is_active = False

    def start_monitoring(self):
        self.is_active = True
        self.update_stats()

    def stop_monitoring(self):
        self.is_active = False

    def update_stats(self):
        if not self.is_active: return
        
        # 1. Update CPU/RAM
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            self.cpu_history.append(cpu)
            self.ram_history.append(mem)
            self.cpu_val_lbl.configure(text=f"{cpu}%")
            self.ram_val_lbl.configure(text=f"{mem}%")
            draw_line_chart(self.cpu_chart_canvas, self.cpu_history, COLOR_LIGHT_BLUE)
            draw_line_chart(self.ram_chart_canvas, self.ram_history, "#e100ff")
            
            # Disk check (every 5 ticks)
            if self.traffic_update_tick % 5 == 0:
                d = psutil.disk_usage("C:\\")
                self.disk_progress.set(d.percent / 100)
                self.disk_value_label.configure(text=f"{d.percent}%")
        except: pass

        # 2. Update Network Traffic
        try:
            current_net_io = psutil.net_io_counters()
            # Calculate bytes per second (assuming ~1000ms update rate)
            bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
            bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
            self.last_net_io = current_net_io
            
            self.net_down_history.append(bytes_recv)
            self.net_up_history.append(bytes_sent)
            
            self.lbl_down_current.configure(text=f"↓ {self._fmt_speed(bytes_recv)}")
            self.lbl_up_current.configure(text=f"↑ {self._fmt_speed(bytes_sent)}")
            
            self._draw_traffic_chart(self.chart_down_canvas, self.net_down_history, COLOR_GREEN, self.chart_down_max_lbl)
            self._draw_traffic_chart(self.chart_up_canvas, self.net_up_history, COLOR_LIGHT_BLUE, self.chart_up_max_lbl)
            
            # 3. Update Process List (Every 3 seconds to save CPU)
            self.traffic_update_tick += 1
            if self.traffic_update_tick >= 3:
                self.update_traffic_process_list()
                self.traffic_update_tick = 0
                
        except Exception as e: 
            print(f"Stats Error: {e}")
            
        # Schedule next update
        if self.is_active:
            self.frame.after(1000, self.update_stats)

    def update_traffic_process_list(self):
        """Scans for processes with open network connections and updates the UI."""
        try:
            # Clear current list
            for widget in self.traffic_list.winfo_children():
                widget.destroy()

            # Get all network connections
            connections = psutil.net_connections(kind='inet')
            
            # Count connections by PID
            pid_counts = Counter(c.pid for c in connections)
            
            # Get Top 15 processes
            top_pids = pid_counts.most_common(15)
            
            for pid, count in top_pids:
                try:
                    p = psutil.Process(pid)
                    name = p.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

                # Create Row
                row = ctk.CTkFrame(self.traffic_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                # Process Name & PID
                ctk.CTkLabel(row, text=f"{name} (PID: {pid})", anchor="w").pack(side="left", padx=10)
                
                # Connection Count Badge
                count_lbl = ctk.CTkLabel(row, text=f"{count} conns", 
                                       fg_color="gray30", corner_radius=6, width=80)
                count_lbl.pack(side="right", padx=10)

        except Exception as e:
            print(f"Process List Error: {e}")

    def _fmt_speed(self, bytes_sec):
        if bytes_sec < 1024: return f"{bytes_sec} B/s"
        elif bytes_sec < 1024**2: return f"{bytes_sec/1024:.1f} KB/s"
        else: return f"{bytes_sec/1024**2:.1f} MB/s"

    def _draw_traffic_chart(self, canvas, data, color, max_lbl):
        try:
            canvas.update()
            w = canvas.winfo_width()
            h = int(canvas['height'])
            
            # Avoid division by zero
            current_max = max(data)
            max_val = current_max if current_max > 0 else 1
            
            max_lbl.configure(text=f"Max: {self._fmt_speed(max_val)}")
            
            canvas.delete("all")
            if len(data) < 2: return
            
            step_x = w / (len(data) - 1)
            points = []
            for i, val in enumerate(data):
                x = i * step_x
                y = h - ((val / max_val) * h)
                points.append(x)
                points.append(y)
            
            # Use smooth=True for a nicer curve
            canvas.create_line(points, fill=color, width=2, smooth=True)
        except: pass