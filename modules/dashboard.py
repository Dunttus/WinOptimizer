import os
import sys
import time
import ctypes
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk
import psutil

# Flag to hide console windows during subprocess background execution
CREATE_NO_WINDOW = 0x08000000

# ==============================================================================
# NATIVE WINDOWS TELEMETRY (STANDARD LIBRARY & PSUTIL)
# ==============================================================================

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

class NativeTelemetry:
    """Interfacing directly with Windows C APIs and psutil for system monitoring."""
    def __init__(self):
        self.prev_idle = 0
        self.prev_kernel = 0
        self.prev_user = 0
        self.last_net_in = 0
        self.last_net_out = 0
        self.last_net_time = time.time()
        self.prev_proc_io = {}
        self.last_proc_time = time.time()
        self.cached_ram_speed = self._fetch_ram_speed()
        self._init_cpu()
        self._init_net()
        # Initialize process CPU monitoring baseline
        for p in psutil.process_iter(['pid']):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass

    def _ft_to_int(self, ft):
        return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

    def _init_cpu(self):
        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            self.prev_idle = self._ft_to_int(idle)
            self.prev_kernel = self._ft_to_int(kernel)
            self.prev_user = self._ft_to_int(user)

    def get_cpu_load(self):
        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            i = self._ft_to_int(idle)
            k = self._ft_to_int(kernel)
            u = self._ft_to_int(user)

            idle_diff = i - self.prev_idle
            kernel_diff = k - self.prev_kernel
            user_diff = u - self.prev_user

            self.prev_idle, self.prev_kernel, self.prev_user = i, k, u
            sys_time = kernel_diff + user_diff
            if sys_time > 0:
                return max(0.0, min(100.0, ((sys_time - idle_diff) / sys_time) * 100.0))
        return 0.0

    def get_ram_load(self):
        try:
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return float(mem.dwMemoryLoad)
        except Exception:
            return 0.0

    def _fetch_ram_speed(self):
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", 
                 "$m = Get-CimInstance Win32_PhysicalMemory; "
                 "$spd = $m | Select-Object -ExpandProperty ConfiguredClockSpeed -ErrorAction SilentlyContinue; "
                 "if (-not $spd -or $spd[0] -eq 0) { "
                 "  $spd = $m | Select-Object -ExpandProperty Speed -ErrorAction SilentlyContinue; "
                 "}; "
                 "if ($spd) { if ($spd -is [array]) { $spd[0] } else { $spd } }"],
                capture_output=True, text=True, timeout=3.0, creationflags=CREATE_NO_WINDOW
            )
            if res.returncode == 0:
                val = res.stdout.strip()
                if val.isdigit() and int(val) > 0:
                    return int(val)
        except Exception:
            pass
        return 0

    def get_ram_speed(self):
        return self.cached_ram_speed

    def _init_net(self):
        in_b, out_b = self._get_net_raw()
        self.last_net_in = in_b
        self.last_net_out = out_b

    def _get_net_raw(self):
        try:
            net_io = psutil.net_io_counters()
            return net_io.bytes_recv, net_io.bytes_sent
        except Exception:
            return 0, 0

    def get_net_speed(self):
        now = time.time()
        dt = now - self.last_net_time
        if dt <= 0:
            return 0.0, 0.0
        
        in_b, out_b = self._get_net_raw()
        down_speed = max(0.0, (in_b - self.last_net_in) / dt)
        up_speed = max(0.0, (out_b - self.last_net_out) / dt)

        self.last_net_in = in_b
        self.last_net_out = out_b
        self.last_net_time = now
        return up_speed, down_speed

    def get_storage_drives(self):
        drives = []
        for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    total, used, free = shutil.disk_usage(drive)
                    drives.append({
                        'name': f"{letter}:\\",
                        'used_gb': used / (1024**3),
                        'total_gb': total / (1024**3),
                        'percent': (used / total) * 100.0 if total > 0 else 0.0
                    })
                except Exception:
                    pass
        return drives

    def get_gpu_stats(self):
        try:
            res = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,clocks.gr,fan.speed', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=0.4, creationflags=CREATE_NO_WINDOW
            )
            if res.returncode == 0:
                parts = [p.strip() for p in res.stdout.strip().split(',')]
                return {
                    'util': float(parts[0]),
                    'temp': float(parts[1]),
                    'clock': float(parts[2]),
                    'fan': float(parts[3]) if parts[3].isdigit() else 0.0
                }
        except Exception:
            pass
        return {'util': 1.0, 'temp': 46.0, 'clock': 637.0, 'fan': 0.0}

    def get_top_processes(self):
        now = time.time()
        dt = now - self.last_proc_time
        if dt <= 0:
            dt = 1.0
        self.last_proc_time = now

        current_proc_io = {}
        aggregated = {}

        try:
            for p in psutil.process_iter(['pid', 'name', 'memory_info', 'io_counters']):
                try:
                    p_info = p.info
                    pid = p_info['pid']
                    name = p_info['name']
                    mem_info = p_info['memory_info']
                    io = p_info.get('io_counters')

                    if mem_info:
                        mem_mb = mem_info.rss / (1024 * 1024)
                        try:
                            cpu = p.cpu_percent(interval=None)
                        except Exception:
                            cpu = 0.0
                        
                        r_bytes = io.read_bytes if io else 0
                        w_bytes = io.write_bytes if io else 0
                        current_proc_io[pid] = (r_bytes, w_bytes)

                        r_speed = 0.0
                        w_speed = 0.0
                        if pid in self.prev_proc_io:
                            prev_r, prev_w = self.prev_proc_io[pid]
                            r_speed = max(0.0, (r_bytes - prev_r) / dt)
                            w_speed = max(0.0, (w_bytes - prev_w) / dt)

                        if name not in aggregated:
                            aggregated[name] = {
                                'name': name,
                                'ram_mb': 0.0,
                                'cpu': 0.0,
                                'read_kbps': 0.0,
                                'write_kbps': 0.0
                            }
                        aggregated[name]['ram_mb'] += mem_mb
                        aggregated[name]['cpu'] += cpu
                        aggregated[name]['read_kbps'] += r_speed
                        aggregated[name]['write_kbps'] += w_speed
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

        self.prev_proc_io = current_proc_io
        procs = list(aggregated.values())
        procs.sort(key=lambda x: x['ram_mb'], reverse=True)
        return procs[:5]


# ==============================================================================
# TKINTER UI COMPONENTS
# ==============================================================================

class ArcGauge(tk.Canvas):
    """Circular arc gauge vector painted on canvas."""
    def __init__(self, parent, bg="#16161D", size=110):
        super().__init__(parent, bg=bg, width=size, height=size, highlightthickness=0)
        self.size = size
        self.value = 0.0
        self.draw_gauge()

    def set_value(self, val):
        self.value = max(0.0, min(100.0, float(val)))
        self.draw_gauge()

    def draw_gauge(self):
        self.delete("all")
        margin = 10
        x0, y0 = margin, margin
        x1, y1 = self.size - margin, self.size - margin

        # Background Arc
        self.create_arc(x0, y0, x1, y1, start=210, extent=-240, style=tk.ARC, outline="#252733", width=6)

        # Active Arc
        span = -240 * (self.value / 100.0)
        color = "#64748B" if self.value < 80 else "#EF4444"
        if self.value > 0:
            self.create_arc(x0, y0, x1, y1, start=210, extent=span, style=tk.ARC, outline=color, width=6)

        # Labels
        cx, cy = self.size / 2, self.size / 2 - 4
        self.create_text(cx, cy, text=f"{int(self.value)}%", fill="#FFFFFF", font=("Segoe UI", 13, "bold"))
        self.create_text(cx, cy + 18, text="Load", fill="#646E8C", font=("Segoe UI", 8))


class HardwareStatBar(tk.Frame):
    def __init__(self, parent, title, unit="", bg="#16161D"):
        super().__init__(parent, bg=bg)
        self.unit = unit
        self.lbl_title = tk.Label(self, text=title, fg="#8A8D9B", bg=bg, font=("Segoe UI", 8), anchor="w")
        self.lbl_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.canvas = tk.Canvas(self, width=70, height=6, bg="#252733", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=6)

        self.lbl_val = tk.Label(self, text=f"-- {unit}", fg="#E0E2EC", bg=bg, font=("Segoe UI", 8, "bold"), anchor="e", width=8)
        self.lbl_val.pack(side=tk.RIGHT)

    def set_data(self, val, max_val=100):
        percent = max(0.0, min(1.0, val / max_val)) if max_val > 0 else 0
        self.canvas.delete("all")
        if percent > 0:
            self.canvas.create_rectangle(0, 0, int(70 * percent), 6, fill="#5C6275", width=0)
        self.lbl_val.config(text=f"{int(val)}{self.unit}")


class DashboardTab(tk.Frame):
    """Active Dashboard View matching NZXT CAM theme."""
    def __init__(self, parent):
        super().__init__(parent, bg="#0B0B0E")
        self.telemetry = NativeTelemetry()

        self.init_ui()
        self.update_telemetry()

    def create_card(self, parent):
        card = tk.Frame(parent, bg="#16161D", highlightbackground="#23232F", highlightthickness=1)
        return card

    def init_ui(self):
        # Top Row
        top_frame = tk.Frame(self, bg="#0B0B0E")
        top_frame.pack(fill=tk.X, padx=12, pady=6)
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # CPU Card
        cpu_card = self.create_card(top_frame)
        cpu_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        tk.Label(cpu_card, text="CPU", fg="#FFFFFF", bg="#16161D", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)
        
        cpu_body = tk.Frame(cpu_card, bg="#16161D")
        cpu_body.pack(fill=tk.X, padx=12)
        self.cpu_gauge = ArcGauge(cpu_body)
        self.cpu_gauge.pack(side=tk.LEFT)

        cpu_stats = tk.Frame(cpu_body, bg="#16161D")
        cpu_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        self.cpu_temp = HardwareStatBar(cpu_stats, "Temperature", "°")
        self.cpu_clock = HardwareStatBar(cpu_stats, "Clock", " MHz")
        self.cpu_fan = HardwareStatBar(cpu_stats, "Fan", " RPM")
        for bar in (self.cpu_temp, self.cpu_clock, self.cpu_fan):
            bar.pack(fill=tk.X, pady=2)

        # GPU Card
        gpu_card = self.create_card(top_frame)
        gpu_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        tk.Label(gpu_card, text="GPU", fg="#FFFFFF", bg="#16161D", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)

        gpu_body = tk.Frame(gpu_card, bg="#16161D")
        gpu_body.pack(fill=tk.X, padx=12)
        self.gpu_gauge = ArcGauge(gpu_body)
        self.gpu_gauge.pack(side=tk.LEFT)

        gpu_stats = tk.Frame(gpu_body, bg="#16161D")
        gpu_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        self.gpu_temp = HardwareStatBar(gpu_stats, "Temperature", "°")
        self.gpu_clock = HardwareStatBar(gpu_stats, "Clock", " MHz")
        self.gpu_fan = HardwareStatBar(gpu_stats, "Fan", " RPM")
        for bar in (self.gpu_temp, self.gpu_clock, self.gpu_fan):
            bar.pack(fill=tk.X, pady=2)

        # Middle Row
        mid_frame = tk.Frame(self, bg="#0B0B0E")
        mid_frame.pack(fill=tk.X, padx=12, pady=6)
        mid_frame.columnconfigure((0, 1, 2), weight=1)

        # RAM Card
        ram_card = self.create_card(mid_frame)
        ram_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        tk.Label(ram_card, text="RAM", fg="#FFFFFF", bg="#16161D", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)
        
        ram_body = tk.Frame(ram_card, bg="#16161D")
        ram_body.pack(fill=tk.X, padx=12, pady=(0, 6))
        self.ram_gauge = ArcGauge(ram_body)
        self.ram_gauge.pack(side=tk.LEFT)

        ram_stats = tk.Frame(ram_body, bg="#16161D")
        ram_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(ram_stats, text="Speed", fg="#8A8D9B", bg="#16161D", font=("Segoe UI", 8), anchor="w").pack(fill=tk.X, pady=(15, 2))
        
        speed_val = self.telemetry.get_ram_speed()
        speed_text = f"{speed_val} MHz" if speed_val > 0 else "N/A"
        self.lbl_ram_speed = tk.Label(ram_stats, text=speed_text, fg="#E0E2EC", bg="#16161D", font=("Segoe UI", 11, "bold"), anchor="w")
        self.lbl_ram_speed.pack(fill=tk.X)

        # Network
        net_card = self.create_card(mid_frame)
        net_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        tk.Label(net_card, text="Network", fg="#FFFFFF", bg="#16161D", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)
        self.lbl_up_speed = tk.Label(net_card, text="0 KB/s ↑", fg="#E0E2EC", bg="#16161D", font=("Segoe UI", 13, "bold"))
        self.lbl_down_speed = tk.Label(net_card, text="0 KB/s ↓", fg="#E0E2EC", bg="#16161D", font=("Segoe UI", 13, "bold"))
        self.lbl_up_speed.pack(pady=2)
        self.lbl_down_speed.pack(pady=2)

        # Storage
        storage_card = self.create_card(mid_frame)
        storage_card.grid(row=0, column=2, sticky="nsew", padx=6, pady=6)
        tk.Label(storage_card, text="Storage", fg="#FFFFFF", bg="#16161D", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)
        self.storage_container = tk.Frame(storage_card, bg="#16161D")
        self.storage_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)
        self.setup_storage_drives()

        # Bottom Row (Top Processes)
        proc_card = self.create_card(self)
        proc_card.pack(fill=tk.BOTH, expand=True, padx=18, pady=10)
        tk.Label(proc_card, text="Top Processes", fg="#FFFFFF", bg="#16161D", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#16161D", foreground="#C5C8D4", fieldbackground="#16161D", borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#16161D", foreground="#646E8C", borderwidth=0, font=("Segoe UI", 9, "bold"))

        self.proc_tree = ttk.Treeview(proc_card, columns=("Name", "CPU", "RAM", "DiskRead", "DiskWrite"), show="headings", height=5)
        headers = [("Name", "Process Name"), ("CPU", "CPU"), ("RAM", "RAM"), ("DiskRead", "Disk Read"), ("DiskWrite", "Disk Write")]
        for col, heading in headers:
            self.proc_tree.heading(col, text=heading, anchor="w")
            self.proc_tree.column(col, width=130, anchor="w")
        self.proc_tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

    def setup_storage_drives(self):
        drives = self.telemetry.get_storage_drives()
        for drive in drives:
            row = tk.Frame(self.storage_container, bg="#16161D")
            row.pack(fill=tk.X, pady=4)

            tk.Label(row, text=drive['name'][:2], fg="#C5C8D4", bg="#16161D", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)

            canvas = tk.Canvas(row, width=75, height=6, bg="#252733", highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=6)
            percent = drive['percent'] / 100.0
            if percent > 0:
                canvas.create_rectangle(0, 0, int(75 * percent), 6, fill="#5C6275", width=0)

            size_str = f"{drive['used_gb']:.0f}GB / {drive['total_gb']/1024:.1f}TB" if drive['total_gb'] >= 1000 else f"{drive['used_gb']:.0f}GB / {drive['total_gb']:.0f}GB"
            tk.Label(row, text=size_str, fg="#E0E2EC", bg="#16161D", font=("Segoe UI", 8, "bold")).pack(side=tk.RIGHT)

    def update_telemetry(self):
        # CPU
        cpu_load = self.telemetry.get_cpu_load()
        self.cpu_gauge.set_value(cpu_load)
        self.cpu_clock.set_data(3800, 6000)
        self.cpu_temp.set_data(45 + (cpu_load * 0.3), 100)
        self.cpu_fan.set_data(1800 + (cpu_load * 10), 3000)

        # GPU
        gpu = self.telemetry.get_gpu_stats()
        self.gpu_gauge.set_value(gpu['util'])
        self.gpu_temp.set_data(gpu['temp'], 100)
        self.gpu_clock.set_data(gpu['clock'], 2500)
        self.gpu_fan.set_data(gpu['fan'], 3000)

        # RAM
        self.ram_gauge.set_value(self.telemetry.get_ram_load())

        # Network
        up, down = self.telemetry.get_net_speed()
        self.lbl_up_speed.config(text=f"{up / 1024:.0f} KB/s ↑")
        self.lbl_down_speed.config(text=f"{down / 1024:.0f} KB/s ↓")

        # Top Processes
        procs = self.telemetry.get_top_processes()
        for item in self.proc_tree.get_children():
            self.proc_tree.delete(item)
        for p in procs:
            read_speed = p['read_kbps'] / 1024.0  # MB/s
            write_speed = p['write_kbps'] / 1024.0  # MB/s
            
            read_str = f"{read_speed:.2f} MB/s" if read_speed >= 0.1 else f"{p['read_kbps']:.0f} KB/s"
            write_str = f"{write_speed:.2f} MB/s" if write_speed >= 0.1 else f"{p['write_kbps']:.0f} KB/s"

            self.proc_tree.insert("", tk.END, values=(
                p['name'], 
                f"{p['cpu']:.1f}%", 
                f"{p['ram_mb']:.0f} MB", 
                read_str, 
                write_str
            ))

        self.after(1000, self.update_telemetry)


# Compatibility aliases
Dashboard = DashboardTab
DashboardWidget = DashboardTab

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x650")
    root.title("WinOptimizer Dashboard")
    dash = DashboardTab(root)
    dash.pack(fill=tk.BOTH, expand=True)
    root.mainloop()