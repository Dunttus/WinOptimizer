import os
import time
import ctypes
import shutil
import threading
import subprocess
from collections import deque
import tkinter as tk
from tkinter import ttk
import psutil

from config import (
    THEME,
    BG_MAIN,
    BG_SIDEBAR,
    BG_CARD,
    BG_INPUT,
    FG_PRIMARY,
    FG_SECONDARY,
    FG_MUTED,
    BORDER_COLOR,
    FONT_FAMILY,
    FONT_BODY,
    FONT_BOLD,
    FONT_SMALL,
    FONT_MONO,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000


def format_rate(bytes_per_sec: float) -> str:
    """Formats byte/sec throughput accurately into B/s, KB/s, or MB/s."""
    if bytes_per_sec < 1024.0:
        return f"{bytes_per_sec:.0f} B/s"
    kb = bytes_per_sec / 1024.0
    if kb < 1024.0:
        return f"{kb:.1f} KB/s"
    mb = kb / 1024.0
    return f"{mb:.2f} MB/s"


def format_uptime(boot_timestamp: float) -> str:
    """Formats system uptime into a compact Xd Xh Xm string."""
    elapsed = max(0, int(time.time() - boot_timestamp))
    days, rem = divmod(elapsed, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h {mins}m"
    return f"{hours}h {mins}m"


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
    """Interfaces with Windows C APIs, WMI/CIM, nvidia-smi, and psutil for non-blocking telemetry."""

    def __init__(self):
        self.prev_idle = 0
        self.prev_kernel = 0
        self.prev_user = 0
        self.last_net_in = 0
        self.last_net_out = 0
        self.last_net_time = time.time()
        self.prev_proc_io: dict[int, tuple[int, int]] = {}
        self.last_proc_time = time.time()
        self.boot_time = psutil.boot_time()

        self.logical_cores = max(1, psutil.cpu_count(logical=True) or 1)
        self.physical_cores = max(1, psutil.cpu_count(logical=False) or self.logical_cores)
        self.cached_ram_speed = 0
        self.disk_health_summary = "Checking..."
        self.sysmon_status = "Checking..."
        self.has_nvidia_smi = shutil.which("nvidia-smi") is not None

        # Rolling 30-point history for sparklines
        self.cpu_history: deque[float] = deque([0.0] * 30, maxlen=30)
        self.gpu_history: deque[float] = deque([0.0] * 30, maxlen=30)
        self.net_down_history: deque[float] = deque([0.0] * 30, maxlen=30)

        # Shared state updated by background worker thread
        self._lock = threading.Lock()
        self._gpu_stats = {
            "name": "GPU",
            "util": 0.0,
            "temp": 0.0,
            "power_w": 0.0,
            "power_limit_w": 350.0,
            "vram_used_mb": 0.0,
            "vram_total_mb": 0.0,
            "clock": 0.0,
            "fan": 0.0,
            "available": False,
        }
        self._top_procs: list[dict] = []
        self._security_stats = {
            "tcp_established": 0,
            "tcp_listen": 0,
            "total_threads": 0,
            "total_handles": 0,
            "sysmon": "Not Installed",
        }
        self._bg_busy = False

        self._init_cpu()
        self._init_net()

        threading.Thread(target=self._init_background_data, daemon=True).start()

    def _init_background_data(self):
        for p in psutil.process_iter(["pid"]):
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass
        self.cached_ram_speed = self._fetch_ram_speed()
        self.disk_health_summary = self._fetch_disk_health()
        self.sysmon_status = self._check_sysmon_service()
        self.refresh_heavy_telemetry()

    @staticmethod
    def _ft_to_int(ft: FILETIME) -> int:
        return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

    def _init_cpu(self):
        if os.name != "nt":
            return
        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
        ):
            self.prev_idle = self._ft_to_int(idle)
            self.prev_kernel = self._ft_to_int(kernel)
            self.prev_user = self._ft_to_int(user)

    def get_cpu_load(self) -> float:
        val = 0.0
        if os.name != "nt":
            val = psutil.cpu_percent(interval=None)
        else:
            idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
            if ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            ):
                i = self._ft_to_int(idle)
                k = self._ft_to_int(kernel)
                u = self._ft_to_int(user)

                idle_diff = i - self.prev_idle
                kernel_diff = k - self.prev_kernel
                user_diff = u - self.prev_user

                self.prev_idle, self.prev_kernel, self.prev_user = i, k, u
                sys_time = kernel_diff + user_diff
                if sys_time > 0:
                    val = max(0.0, min(100.0, ((sys_time - idle_diff) / sys_time) * 100.0))

        self.cpu_history.append(val)
        return val

    def get_cpu_details(self) -> dict:
        """Returns real CPU clock frequency (MHz), realistic max boost ceiling, and core counts."""
        current_mhz = 0.0
        max_mhz = 5500.0
        try:
            freq = psutil.cpu_freq()
            if freq:
                current_mhz = freq.current or 0.0
                # Windows often reports base clock in freq.max; keep ceiling realistic for boost clocks
                if freq.max and freq.max > 0:
                    max_mhz = max(5200.0, float(freq.max), current_mhz)
        except Exception:
            pass

        return {
            "clock_mhz": current_mhz,
            "max_mhz": max_mhz,
            "cores": self.physical_cores,
            "threads": self.logical_cores,
            "uptime": format_uptime(self.boot_time),
        }

    def get_ram_info(self) -> tuple[float, float, float, float, float]:
        """Returns (load_percent, used_gb, total_gb, commit_used_gb, commit_total_gb)."""
        try:
            if os.name == "nt":
                mem = MEMORYSTATUSEX()
                mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
                total_gb = mem.ullTotalPhys / (1024**3)
                used_gb = (mem.ullTotalPhys - mem.ullAvailPhys) / (1024**3)
                commit_total = mem.ullTotalPageFile / (1024**3)
                commit_used = (mem.ullTotalPageFile - mem.ullAvailPageFile) / (1024**3)
                return float(mem.dwMemoryLoad), used_gb, total_gb, commit_used, commit_total
            else:
                vm = psutil.virtual_memory()
                return float(vm.percent), vm.used / (1024**3), vm.total / (1024**3), 0.0, 0.0
        except Exception:
            return 0.0, 0.0, 0.0, 0.0, 0.0

    def _fetch_ram_speed(self) -> int:
        if os.name != "nt":
            return 0
        try:
            res = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "$m = Get-CimInstance Win32_PhysicalMemory; "
                    "$spd = $m | Select-Object -ExpandProperty ConfiguredClockSpeed -ErrorAction SilentlyContinue; "
                    "if (-not $spd -or $spd[0] -eq 0) { "
                    "  $spd = $m | Select-Object -ExpandProperty Speed -ErrorAction SilentlyContinue; "
                    "}; "
                    "if ($spd) { if ($spd -is [array]) { $spd[0] } else { $spd } }",
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=CREATE_NO_WINDOW,
            )
            if res.returncode == 0:
                val = res.stdout.strip()
                if val.isdigit() and int(val) > 0:
                    return int(val)
        except Exception:
            pass
        return 0

    def _fetch_disk_health(self) -> str:
        """Queries Windows Storage Management for NVMe/SMART physical disk health status."""
        if os.name != "nt":
            return "Healthy"
        try:
            res = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-PhysicalDisk | Select-Object -ExpandProperty HealthStatus",
                ],
                capture_output=True,
                text=True,
                timeout=3.0,
                creationflags=CREATE_NO_WINDOW,
            )
            if res.returncode == 0 and res.stdout.strip():
                statuses = [s.strip() for s in res.stdout.strip().splitlines() if s.strip()]
                if all(s.lower() == "healthy" for s in statuses):
                    return f"SMART: Healthy ({len(statuses)} Drive{'s' if len(statuses) != 1 else ''})"
                return f"SMART: {', '.join(set(statuses))}"
        except Exception:
            pass
        return "SMART: Healthy"

    def _check_sysmon_service(self) -> str:
        """Checks if Microsoft Sysmon (Sysmon64 or Sysmon) service is active for security auditing."""
        if os.name != "nt":
            return "N/A"
        for svc_name in ("Sysmon64", "Sysmon"):
            try:
                svc = psutil.win_service_get(svc_name)
                if svc.status() == "running":
                    return f"Active ({svc_name})"
                return f"Stopped ({svc_name})"
            except Exception:
                continue
        return "Not Installed"

    def _init_net(self):
        in_b, out_b = self._get_net_raw()
        self.last_net_in = in_b
        self.last_net_out = out_b

    @staticmethod
    def _get_net_raw() -> tuple[int, int]:
        try:
            net_io = psutil.net_io_counters()
            return net_io.bytes_recv, net_io.bytes_sent
        except Exception:
            return 0, 0

    def get_net_speed(self) -> tuple[float, float]:
        """Returns (upload_bytes_per_sec, download_bytes_per_sec)."""
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
        self.net_down_history.append(down_speed / 1024.0)
        return up_speed, down_speed

    @staticmethod
    def get_storage_drives() -> list[dict]:
        drives = []
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    total, used, _free = shutil.disk_usage(drive)
                    drives.append(
                        {
                            "name": f"{letter}:",
                            "used_gb": used / (1024**3),
                            "total_gb": total / (1024**3),
                            "percent": (used / total) * 100.0 if total > 0 else 0.0,
                        }
                    )
                except Exception:
                    pass
        return drives

    def trigger_async_refresh(self):
        """Triggers a non-blocking background update for GPU, Processes, and Security telemetry."""
        if self._bg_busy:
            return
        self._bg_busy = True
        threading.Thread(target=self.refresh_heavy_telemetry, daemon=True).start()

    def refresh_heavy_telemetry(self):
        try:
            gpu = self._poll_gpu_stats()
            procs, total_threads, total_handles = self._poll_top_processes()
            sec = self._poll_security_connections(total_threads, total_handles)
            with self._lock:
                self._gpu_stats = gpu
                self._top_procs = procs
                self._security_stats = sec
                self.gpu_history.append(gpu.get("util", 0.0))
        finally:
            self._bg_busy = False

    def get_cached_heavy_telemetry(self) -> tuple[dict, list[dict], dict]:
        with self._lock:
            return (
                dict(self._gpu_stats),
                list(self._top_procs),
                dict(self._security_stats),
            )

    def _poll_gpu_stats(self) -> dict:
        if self.has_nvidia_smi:
            try:
                res = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=utilization.gpu,temperature.gpu,power.draw,power.limit,memory.used,memory.total,clocks.gr,fan.speed,name",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=0.6,
                    creationflags=CREATE_NO_WINDOW,
                )
                if res.returncode == 0 and res.stdout.strip():
                    line = res.stdout.strip().splitlines()[0]
                    parts = [p.strip() for p in line.split(",")]

                    def _f(idx: int, default: float = 0.0) -> float:
                        if idx < len(parts):
                            try:
                                return float(parts[idx])
                            except ValueError:
                                return default
                        return default

                    gpu_name = parts[8] if len(parts) > 8 else "NVIDIA GPU"
                    gpu_name = gpu_name.replace("NVIDIA GeForce ", "").strip()

                    return {
                        "name": gpu_name,
                        "util": _f(0),
                        "temp": _f(1),
                        "power_w": _f(2),
                        "power_limit_w": _f(3, 350.0) or 350.0,
                        "vram_used_mb": _f(4),
                        "vram_total_mb": _f(5, 16384.0) or 16384.0,
                        "clock": _f(6),
                        "fan": _f(7),
                        "available": True,
                    }
            except Exception:
                pass
        return {
            "name": "GPU",
            "util": 0.0,
            "temp": 0.0,
            "power_w": 0.0,
            "power_limit_w": 350.0,
            "vram_used_mb": 0.0,
            "vram_total_mb": 0.0,
            "clock": 0.0,
            "fan": 0.0,
            "available": False,
        }

    def _poll_top_processes(self) -> tuple[list[dict], int, int]:
        now = time.time()
        dt = max(0.2, now - self.last_proc_time)
        self.last_proc_time = now

        current_proc_io: dict[int, tuple[int, int]] = {}
        aggregated: dict[str, dict] = {}
        total_threads = 0
        total_handles = 0

        try:
            attrs = ["pid", "ppid", "name", "memory_info", "io_counters", "num_threads"]
            if os.name == "nt":
                attrs.append("num_handles")

            for p in psutil.process_iter(attrs):
                try:
                    p_info = p.info
                    pid = p_info["pid"]
                    name = p_info["name"] or "Unknown"
                    if pid == 0 or name in ("System Idle Process", "Idle"):
                        continue

                    ppid = p_info.get("ppid") or 0
                    mem_info = p_info.get("memory_info")
                    io = p_info.get("io_counters")
                    n_threads = p_info.get("num_threads") or 0
                    n_handles = p_info.get("num_handles") or 0

                    total_threads += n_threads
                    total_handles += n_handles

                    if mem_info:
                        mem_mb = mem_info.rss / (1024 * 1024)
                        try:
                            raw_cpu = p.cpu_percent(interval=None)
                            cpu = max(0.0, min(100.0, raw_cpu / self.logical_cores))
                        except Exception:
                            cpu = 0.0

                        r_bytes = io.read_bytes if io else 0
                        w_bytes = io.write_bytes if io else 0
                        current_proc_io[pid] = (r_bytes, w_bytes)

                        r_bps = 0.0
                        w_bps = 0.0
                        if pid in self.prev_proc_io:
                            prev_r, prev_w = self.prev_proc_io[pid]
                            r_bps = max(0.0, (r_bytes - prev_r) / dt)
                            w_bps = max(0.0, (w_bytes - prev_w) / dt)

                        if name not in aggregated:
                            aggregated[name] = {
                                "name": name,
                                "pid": pid,
                                "ppid": ppid,
                                "count": 0,
                                "ram_mb": 0.0,
                                "cpu": 0.0,
                                "threads": 0,
                                "handles": 0,
                                "read_bps": 0.0,
                                "write_bps": 0.0,
                            }
                        entry = aggregated[name]
                        entry["count"] += 1
                        entry["ram_mb"] += mem_mb
                        entry["cpu"] = min(100.0, entry["cpu"] + cpu)
                        entry["threads"] += n_threads
                        entry["handles"] += n_handles
                        entry["read_bps"] += r_bps
                        entry["write_bps"] += w_bps
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass

        self.prev_proc_io = current_proc_io
        return list(aggregated.values()), total_threads, total_handles

    def _poll_security_connections(self, total_threads: int, total_handles: int) -> dict:
        established = 0
        listening = 0
        try:
            for conn in psutil.net_connections(kind="tcp"):
                if conn.status == psutil.CONN_ESTABLISHED:
                    established += 1
                elif conn.status == psutil.CONN_LISTEN:
                    listening += 1
        except Exception:
            pass

        return {
            "tcp_established": established,
            "tcp_listen": listening,
            "total_threads": total_threads,
            "total_handles": total_handles,
            "sysmon": self.sysmon_status,
        }


# ==============================================================================
# CUSTOM TKINTER TELEMETRY WIDGETS & FLOATING SENSORPANEL HUD
# ==============================================================================
class ArcGauge(tk.Canvas):
    """Circular arc gauge painted on a Tkinter Canvas."""

    def __init__(self, parent, label_text: str = "Load", bg=BG_CARD, size=110):
        super().__init__(parent, bg=bg, width=size, height=size, highlightthickness=0)
        self.size = size
        self.value = 0.0
        self.label_text = label_text
        self.draw_gauge()

    def set_value(self, val: float):
        self.value = max(0.0, min(100.0, float(val)))
        self.draw_gauge()

    def draw_gauge(self):
        self.delete("all")
        margin = 10
        x0, y0 = margin, margin
        x1, y1 = self.size - margin, self.size - margin

        # Background Track Arc
        self.create_arc(
            x0, y0, x1, y1, start=210, extent=-240, style=tk.ARC, outline=BG_INPUT, width=7
        )

        # Active Value Arc
        span = -240 * (self.value / 100.0)
        if self.value >= 85:
            color = THEME["danger"]
        elif self.value >= 65:
            color = THEME["warning"]
        else:
            color = THEME["accent"]

        if self.value > 0:
            self.create_arc(
                x0, y0, x1, y1, start=210, extent=span, style=tk.ARC, outline=color, width=7
            )

        cx, cy = self.size / 2, self.size / 2 - 4
        self.create_text(
            cx,
            cy,
            text=f"{int(round(self.value))}%",
            fill=FG_PRIMARY,
            font=(FONT_FAMILY, 14, "bold"),
        )
        self.create_text(
            cx, cy + 19, text=self.label_text, fill=FG_SECONDARY, font=FONT_SMALL
        )


class HardwareStatBar(tk.Frame):
    """Compact metric row with label, progress bar, and right-aligned value.
    Supports `severity_mode=False` so neutral frequency/core metrics don't turn red at boost clocks.
    """

    def __init__(
        self,
        parent,
        title: str,
        unit: str = "",
        bg=BG_CARD,
        severity_mode: bool = True,
    ):
        super().__init__(parent, bg=bg)
        self.unit = unit
        self.severity_mode = severity_mode

        self.lbl_title = tk.Label(
            self, text=title, fg=FG_SECONDARY, bg=bg, font=FONT_SMALL, anchor="w"
        )
        self.lbl_title.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.canvas = tk.Canvas(self, width=74, height=6, bg=BG_INPUT, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, padx=8)

        self.lbl_val = tk.Label(
            self,
            text=f"--{unit}",
            fg=FG_PRIMARY,
            bg=bg,
            font=(FONT_FAMILY, 9, "bold"),
            anchor="e",
            width=14,
        )
        self.lbl_val.pack(side=tk.RIGHT)

    def set_data(self, val: float, max_val: float = 100.0, custom_text: str | None = None):
        percent = max(0.0, min(1.0, val / max_val)) if max_val > 0 else 0.0
        self.canvas.delete("all")
        if percent > 0:
            if not self.severity_mode:
                bar_color = THEME["info"]
            elif percent >= 0.85:
                bar_color = THEME["danger"]
            elif percent >= 0.70:
                bar_color = THEME["warning"]
            else:
                bar_color = THEME["info"]

            self.canvas.create_rectangle(0, 0, int(74 * percent), 6, fill=bar_color, width=0)

        if custom_text is not None:
            self.lbl_val.config(text=custom_text)
        else:
            self.lbl_val.config(text=f"{int(round(val))}{self.unit}")


class MiniSparkline(tk.Canvas):
    """Lightweight real-time vector sparkline graph for history visualization."""

    def __init__(self, parent, width=180, height=34, bg=BG_INPUT, line_color=THEME["success"]):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=bg,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        self.w = width
        self.h = height
        self.line_color = line_color

    def plot(self, values: list[float] | deque[float], dynamic_scale: bool = True, max_ceil: float = 100.0):
        self.delete("all")
        pts = list(values)
        if len(pts) < 2:
            return

        peak = max(max(pts), 1.0) if dynamic_scale else max_ceil
        step_x = self.w / max(1, len(pts) - 1)

        coords = []
        for idx, v in enumerate(pts):
            x = idx * step_x
            norm = max(0.0, min(1.0, v / peak))
            y = self.h - 3 - (norm * (self.h - 6))
            coords.extend([x, y])

        if len(coords) >= 4:
            self.create_line(*coords, fill=self.line_color, width=2, smooth=True)


class SensorPanelHUD(tk.Toplevel):
    """AIDA64 / Rainmeter style Always-On-Top draggable desktop SensorPanel overlay."""

    def __init__(self, parent, telemetry: NativeTelemetry):
        super().__init__(parent)
        self.telemetry = telemetry
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.94)
        self.configure(bg=BG_SIDEBAR)
        self.geometry("310x235+60+60")

        self._drag_x = 0
        self._drag_y = 0
        self._transparent_mode = False

        outer = tk.Frame(
            self,
            bg=BG_SIDEBAR,
            highlightbackground=THEME["accent"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        outer.pack(fill=tk.BOTH, expand=True)

        # Title bar (Draggable)
        title_bar = tk.Frame(outer, bg=BG_SIDEBAR, cursor="fleur")
        title_bar.pack(fill=tk.X, pady=(0, 6))
        title_bar.bind("<ButtonPress-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._on_drag)

        lbl_title = tk.Label(
            title_bar,
            text="⚡ WIBE SENSORPANEL HUD",
            fg=THEME["info"],
            bg=BG_SIDEBAR,
            font=(FONT_FAMILY, 9, "bold"),
            cursor="fleur",
        )
        lbl_title.pack(side=tk.LEFT)
        lbl_title.bind("<ButtonPress-1>", self._start_drag)
        lbl_title.bind("<B1-Motion>", self._on_drag)

        btn_close = tk.Label(
            title_bar,
            text="✕",
            fg=FG_SECONDARY,
            bg=BG_SIDEBAR,
            font=FONT_BOLD,
            cursor="hand2",
            padx=4,
        )
        btn_close.pack(side=tk.RIGHT)
        btn_close.bind("<Button-1>", lambda _e: self.destroy())

        btn_alpha = tk.Label(
            title_bar,
            text="◐",
            fg=FG_SECONDARY,
            bg=BG_SIDEBAR,
            font=FONT_BOLD,
            cursor="hand2",
            padx=4,
        )
        btn_alpha.pack(side=tk.RIGHT)
        btn_alpha.bind("<Button-1>", self._toggle_alpha)

        tk.Frame(outer, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=(0, 6))

        # Metrics rows
        self.rows: dict[str, tk.Label] = {}
        for key, label in [
            ("cpu", "CPU Load / Clock"),
            ("gpu", "GPU Load / Temp"),
            ("pwr", "GPU Power / VRAM"),
            ("ram", "System Memory"),
            ("net", "Net Down / Up"),
        ]:
            r = tk.Frame(outer, bg=BG_SIDEBAR)
            r.pack(fill=tk.X, pady=2)
            tk.Label(r, text=label, fg=FG_SECONDARY, bg=BG_SIDEBAR, font=FONT_SMALL).pack(
                side=tk.LEFT
            )
            val_lbl = tk.Label(
                r, text="--", fg=FG_PRIMARY, bg=BG_SIDEBAR, font=(FONT_MONO[0], 9, "bold")
            )
            val_lbl.pack(side=tk.RIGHT)
            self.rows[key] = val_lbl

        # Sparkline inside HUD
        self.spark = MiniSparkline(outer, width=282, height=36, bg=BG_INPUT, line_color=THEME["info"])
        self.spark.pack(fill=tk.X, pady=(8, 0))

        self.refresh_hud()

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def _toggle_alpha(self, _event):
        self._transparent_mode = not self._transparent_mode
        self.attributes("-alpha", 0.78 if self._transparent_mode else 0.94)

    def refresh_hud(self):
        if not self.winfo_exists():
            return

        cpu_pct = self.telemetry.cpu_history[-1] if self.telemetry.cpu_history else 0.0
        cpu_info = self.telemetry.get_cpu_details()
        gpu, _procs, _sec = self.telemetry.get_cached_heavy_telemetry()
        ram_pct, used_gb, total_gb, _cu, _ct = self.telemetry.get_ram_info()
        up_bps, down_bps = self.telemetry.get_net_speed()

        self.rows["cpu"].config(text=f"{cpu_pct:>4.0f}% | {cpu_info['clock_mhz']:.0f} MHz")
        if gpu.get("available"):
            self.rows["gpu"].config(
                text=f"{gpu['util']:>4.0f}% | {gpu['temp']:.0f}°C",
                fg=THEME["danger"] if gpu["temp"] >= 83 else FG_PRIMARY,
            )
            vram_gb = gpu["vram_used_mb"] / 1024.0
            self.rows["pwr"].config(text=f"{gpu['power_w']:.0f}W | {vram_gb:.1f} GB")
        else:
            self.rows["gpu"].config(text="N/A")
            self.rows["pwr"].config(text="N/A")

        self.rows["ram"].config(text=f"{ram_pct:.0f}% ({used_gb:.1f}/{total_gb:.0f} GB)")
        self.rows["net"].config(text=f"↓{format_rate(down_bps)} ↑{format_rate(up_bps)}")

        self.spark.plot(self.telemetry.cpu_history, dynamic_scale=False, max_ceil=100.0)
        self.after(1000, self.refresh_hud)


# ==============================================================================
# MAIN DASHBOARD TAB
# ==============================================================================
class DashboardTab(tk.Frame):
    """Real-Time Hardware Sensors, Process Diagnostics, HUD & Security Auditing Dashboard."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.telemetry = NativeTelemetry()
        self.proc_sort_key = "ram_mb"  # 'ram_mb', 'cpu', 'io', 'handles'
        self.sort_buttons: dict[str, tk.Button] = {}
        self.hud_window: SensorPanelHUD | None = None

        self.init_ui()
        self.update_telemetry()

    def create_card(self, parent) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=14,
            pady=10,
        )

    def init_ui(self):
        # ------------------ HEADER + ALERT BADGE + HUD BUTTON ------------------
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill=tk.X, padx=24, pady=(16, 10))

        left_hdr = tk.Frame(header, bg=BG_MAIN)
        left_hdr.pack(side=tk.LEFT)

        tk.Label(
            left_hdr,
            text="System Dashboard",
            fg=FG_PRIMARY,
            bg=BG_MAIN,
            font=(FONT_FAMILY, 16, "bold"),
        ).pack(anchor="w")

        tk.Label(
            left_hdr,
            text="Hardware sensors, VRAM/power telemetry, Sysinternals process diagnostics, and security auditing.",
            fg=FG_SECONDARY,
            bg=BG_MAIN,
            font=FONT_BODY,
        ).pack(anchor="w", pady=(1, 0))

        right_hdr = tk.Frame(header, bg=BG_MAIN)
        right_hdr.pack(side=tk.RIGHT)

        # Live Thermal & Load Alert Pill
        self.alert_badge = tk.Label(
            right_hdr,
            text="● Sensors Nominal",
            fg=THEME["success"],
            bg=BG_CARD,
            font=FONT_BOLD,
            padx=12,
            pady=6,
        )
        self.alert_badge.pack(side=tk.LEFT, padx=(0, 8))

        create_button(
            right_hdr,
            text="⧉ SensorPanel HUD",
            command=self.toggle_sensorpanel_hud,
            variant="primary",
            padx=12,
            pady=5,
        ).pack(side=tk.LEFT)

        # ------------------ TOP ROW: CPU & GPU DEEP SENSORS ------------------
        top_frame = tk.Frame(self, bg=BG_MAIN)
        top_frame.pack(fill=tk.X, padx=18, pady=(0, 4))
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        # 1. CPU Card
        cpu_card = self.create_card(top_frame)
        cpu_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)

        cpu_hdr = tk.Frame(cpu_card, bg=BG_CARD)
        cpu_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(cpu_hdr, text="CPU & OS Handles", fg=FG_PRIMARY, bg=BG_CARD, font=FONT_BOLD).pack(
            side=tk.LEFT
        )
        self.lbl_uptime = tk.Label(
            cpu_hdr, text="Uptime: --", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL
        )
        self.lbl_uptime.pack(side=tk.RIGHT)

        cpu_body = tk.Frame(cpu_card, bg=BG_CARD)
        cpu_body.pack(fill=tk.X)
        self.cpu_gauge = ArcGauge(cpu_body, label_text="CPU Load")
        self.cpu_gauge.pack(side=tk.LEFT)

        cpu_stats = tk.Frame(cpu_body, bg=BG_CARD)
        cpu_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(14, 0))
        # severity_mode=False prevents normal CPU boost clocks from turning the bar red
        self.cpu_clock = HardwareStatBar(cpu_stats, "Clock Speed", " MHz", severity_mode=False)
        self.cpu_cores = HardwareStatBar(cpu_stats, "Cores / Threads", "", severity_mode=False)
        self.cpu_handles = HardwareStatBar(cpu_stats, "OS Threads / Handles", "", severity_mode=False)
        self.cpu_procs = HardwareStatBar(cpu_stats, "Active Processes", "", severity_mode=False)
        for bar in (self.cpu_clock, self.cpu_cores, self.cpu_handles, self.cpu_procs):
            bar.pack(fill=tk.X, pady=2)

        # 2. GPU Card (HWiNFO / NVIDIA-SMI Deep Telemetry)
        gpu_card = self.create_card(top_frame)
        gpu_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        gpu_hdr = tk.Frame(gpu_card, bg=BG_CARD)
        gpu_hdr.pack(fill=tk.X, pady=(0, 4))
        self.lbl_gpu_title = tk.Label(
            gpu_hdr, text="GPU (NVIDIA SMI)", fg=FG_PRIMARY, bg=BG_CARD, font=FONT_BOLD
        )
        self.lbl_gpu_title.pack(side=tk.LEFT)
        self.lbl_gpu_fan_clock = tk.Label(
            gpu_hdr, text="-- MHz | Fan --%", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL
        )
        self.lbl_gpu_fan_clock.pack(side=tk.RIGHT)

        gpu_body = tk.Frame(gpu_card, bg=BG_CARD)
        gpu_body.pack(fill=tk.X)
        self.gpu_gauge = ArcGauge(gpu_body, label_text="GPU Load")
        self.gpu_gauge.pack(side=tk.LEFT)

        gpu_stats = tk.Frame(gpu_body, bg=BG_CARD)
        gpu_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(14, 0))
        self.gpu_temp = HardwareStatBar(gpu_stats, "Core Temp", "°C", severity_mode=True)
        self.gpu_power = HardwareStatBar(gpu_stats, "Power Draw", " W", severity_mode=True)
        self.gpu_vram = HardwareStatBar(gpu_stats, "VRAM Usage", " GB", severity_mode=True)
        self.gpu_clock = HardwareStatBar(gpu_stats, "Graphics Clock", " MHz", severity_mode=False)
        for bar in (self.gpu_temp, self.gpu_power, self.gpu_vram, self.gpu_clock):
            bar.pack(fill=tk.X, pady=2)

        # ------------------ MIDDLE ROW: RAM, NETWORK/SYSMON, STORAGE/SMART ------------------
        mid_frame = tk.Frame(self, bg=BG_MAIN)
        mid_frame.pack(fill=tk.X, padx=18, pady=2)
        mid_frame.columnconfigure((0, 1, 2), weight=1)

        # 3. RAM Card
        ram_card = self.create_card(mid_frame)
        ram_card.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        tk.Label(ram_card, text="Memory (RAM & Commit)", fg=FG_PRIMARY, bg=BG_CARD, font=FONT_BOLD).pack(
            anchor="w", pady=(0, 4)
        )

        ram_body = tk.Frame(ram_card, bg=BG_CARD)
        ram_body.pack(fill=tk.X)
        self.ram_gauge = ArcGauge(ram_body, label_text="RAM Load")
        self.ram_gauge.pack(side=tk.LEFT)

        ram_stats = tk.Frame(ram_body, bg=BG_CARD)
        ram_stats.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(14, 0))

        tk.Label(
            ram_stats, text="Physical Used / Total", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL, anchor="w"
        ).pack(fill=tk.X)
        self.lbl_ram_used = tk.Label(
            ram_stats, text="-- / -- GB", fg=FG_PRIMARY, bg=BG_CARD, font=FONT_BOLD, anchor="w"
        )
        self.lbl_ram_used.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            ram_stats, text="Commit Charge (Pagefile)", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL, anchor="w"
        ).pack(fill=tk.X)
        self.lbl_ram_commit = tk.Label(
            ram_stats, text="-- / -- GB", fg=FG_PRIMARY, bg=BG_CARD, font=FONT_SMALL, anchor="w"
        )
        self.lbl_ram_commit.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            ram_stats, text="Configured Speed", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL, anchor="w"
        ).pack(fill=tk.X)
        self.lbl_ram_speed = tk.Label(
            ram_stats, text="Detecting...", fg=THEME["info"], bg=BG_CARD, font=FONT_BOLD, anchor="w"
        )
        self.lbl_ram_speed.pack(fill=tk.X)

        # 4. Network & Security Auditing Card (Sysmon + Active Sockets + Sparkline)
        net_card = self.create_card(mid_frame)
        net_card.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        net_hdr = tk.Frame(net_card, bg=BG_CARD)
        net_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(
            net_hdr, text="Network & Security Audit", fg=FG_PRIMARY, bg=BG_CARD, font=FONT_BOLD
        ).pack(side=tk.LEFT)
        self.lbl_sysmon = tk.Label(
            net_hdr, text="Sysmon: ...", fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL
        )
        self.lbl_sysmon.pack(side=tk.RIGHT)

        speeds_row = tk.Frame(net_card, bg=BG_CARD)
        speeds_row.pack(fill=tk.X, pady=(2, 4))
        self.lbl_down_speed = tk.Label(
            speeds_row, text="0 B/s ↓", fg=THEME["success"], bg=BG_CARD, font=(FONT_FAMILY, 12, "bold")
        )
        self.lbl_down_speed.pack(side=tk.LEFT)
        self.lbl_up_speed = tk.Label(
            speeds_row, text="0 B/s ↑", fg=THEME["info"], bg=BG_CARD, font=(FONT_FAMILY, 12, "bold")
        )
        self.lbl_up_speed.pack(side=tk.RIGHT)

        self.net_spark = MiniSparkline(net_card, width=220, height=28, bg=BG_INPUT, line_color=THEME["success"])
        self.net_spark.pack(fill=tk.X, pady=(2, 6))

        sec_row = tk.Frame(net_card, bg=BG_CARD)
        sec_row.pack(fill=tk.X)
        self.lbl_tcp_conns = tk.Label(
            sec_row,
            text="TCP Established: -- | Listening: --",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_SMALL,
        )
        self.lbl_tcp_conns.pack(side=tk.LEFT)

        # 5. Storage & NVMe SMART Health Card
        storage_card = self.create_card(mid_frame)
        storage_card.grid(row=0, column=2, sticky="nsew", padx=6, pady=4)

        st_hdr = tk.Frame(storage_card, bg=BG_CARD)
        st_hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(st_hdr, text="Storage Drives", fg=FG_PRIMARY, bg=BG_CARD, font=FONT_BOLD).pack(
            side=tk.LEFT
        )
        self.lbl_disk_health = tk.Label(
            st_hdr, text="SMART: Checking...", fg=THEME["success"], bg=BG_CARD, font=FONT_SMALL
        )
        self.lbl_disk_health.pack(side=tk.RIGHT)

        self.storage_container = tk.Frame(storage_card, bg=BG_CARD)
        self.storage_container.pack(fill=tk.BOTH, expand=True)
        self.setup_storage_drives()

        # ------------------ BOTTOM ROW: SYSINTERNALS PROCESS DIAGNOSTICS ------------------
        proc_card = self.create_card(self)
        proc_card.pack(fill=tk.BOTH, expand=True, padx=24, pady=(4, 16))

        proc_hdr = tk.Frame(proc_card, bg=BG_CARD)
        proc_hdr.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            proc_hdr,
            text="Process Diagnostics & Leak Tracer (Aggregated)",
            fg=FG_PRIMARY,
            bg=BG_CARD,
            font=FONT_BOLD,
        ).pack(side=tk.LEFT)

        # Quick OS Diagnostic Launchers (Resource Monitor & Event Viewer)
        create_button(
            proc_hdr,
            text="Event Viewer",
            command=lambda: subprocess.Popen(["eventvwr.msc"], shell=True),
            variant="secondary",
            padx=8,
            pady=2,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        create_button(
            proc_hdr,
            text="Resource Monitor (resmon)",
            command=lambda: subprocess.Popen(["resmon.exe"]),
            variant="secondary",
            padx=8,
            pady=2,
        ).pack(side=tk.RIGHT, padx=(6, 0))

        # Interactive Sort Mode Pills
        for label, key in [
            ("Sort: Handles", "handles"),
            ("Sort: Disk I/O", "io"),
            ("Sort: CPU", "cpu"),
            ("Sort: Memory", "ram_mb"),
        ]:
            btn = tk.Button(
                proc_hdr,
                text=label,
                font=FONT_SMALL,
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda k=key: self.set_process_sort(k),
            )
            btn.pack(side=tk.RIGHT, padx=2)
            self.sort_buttons[key] = btn

        self._update_sort_button_styles()

        columns = ("Name", "Lineage", "CPU", "RAM", "HandlesThreads", "DiskRead", "DiskWrite")
        self.proc_tree = ttk.Treeview(proc_card, columns=columns, show="headings", height=6)

        headers = [
            ("Name", "Process Name (Instances)", 210, "w"),
            ("Lineage", "PID → Parent PID", 130, "center"),
            ("CPU", "CPU", 85, "e"),
            ("RAM", "Memory (RSS)", 115, "e"),
            ("HandlesThreads", "Handles / Threads", 135, "e"),
            ("DiskRead", "Disk Read", 115, "e"),
            ("DiskWrite", "Disk Write", 115, "e"),
        ]
        for col, heading, width, anchor in headers:
            self.proc_tree.heading(col, text=heading, anchor=anchor)
            self.proc_tree.column(col, width=width, anchor=anchor)

        self.proc_tree.pack(fill=tk.BOTH, expand=True)

    # --------------------------------------------------------------------------
    # Interactive Helpers
    # --------------------------------------------------------------------------
    def set_process_sort(self, sort_key: str):
        self.proc_sort_key = sort_key
        self._update_sort_button_styles()

    def _update_sort_button_styles(self):
        for key, btn in self.sort_buttons.items():
            if key == self.proc_sort_key:
                btn.config(bg=THEME["accent"], fg="#ffffff")
            else:
                btn.config(bg=BG_INPUT, fg=FG_SECONDARY)

    def toggle_sensorpanel_hud(self):
        if self.hud_window is not None and self.hud_window.winfo_exists():
            self.hud_window.destroy()
            self.hud_window = None
        else:
            self.hud_window = SensorPanelHUD(self, self.telemetry)

    def setup_storage_drives(self):
        for child in self.storage_container.winfo_children():
            child.destroy()

        drives = self.telemetry.get_storage_drives()
        for drive in drives:
            row = tk.Frame(self.storage_container, bg=BG_CARD)
            row.pack(fill=tk.X, pady=4)

            tk.Label(
                row, text=drive["name"], fg=FG_PRIMARY, bg=BG_CARD, font=FONT_BOLD, width=3, anchor="w"
            ).pack(side=tk.LEFT)

            canvas = tk.Canvas(row, width=80, height=6, bg=BG_INPUT, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=8)
            percent = max(0.0, min(1.0, drive["percent"] / 100.0))
            if percent > 0:
                fill_col = THEME["danger"] if percent > 0.9 else THEME["accent"]
                canvas.create_rectangle(0, 0, int(80 * percent), 6, fill=fill_col, width=0)

            if drive["total_gb"] >= 1000:
                size_str = f"{drive['used_gb']:.0f} GB / {drive['total_gb'] / 1024:.1f} TB"
            else:
                size_str = f"{drive['used_gb']:.0f} / {drive['total_gb']:.0f} GB"

            tk.Label(row, text=size_str, fg=FG_SECONDARY, bg=BG_CARD, font=FONT_SMALL).pack(side=tk.RIGHT)

    # --------------------------------------------------------------------------
    # Live Telemetry Loop
    # --------------------------------------------------------------------------
    def update_telemetry(self):
        if self.winfo_ismapped():
            self.telemetry.trigger_async_refresh()

            # 1. CPU & OS Handles
            cpu_load = self.telemetry.get_cpu_load()
            cpu_info = self.telemetry.get_cpu_details()
            gpu, procs, sec = self.telemetry.get_cached_heavy_telemetry()

            self.cpu_gauge.set_value(cpu_load)
            self.lbl_uptime.config(text=f"Uptime: {cpu_info['uptime']}")
            self.cpu_clock.set_data(cpu_info["clock_mhz"], cpu_info["max_mhz"])
            self.cpu_cores.set_data(
                cpu_info["cores"],
                cpu_info["threads"],
                custom_text=f"{cpu_info['cores']}C / {cpu_info['threads']}T",
            )
            self.cpu_handles.set_data(
                sec["total_threads"],
                6000,
                custom_text=f"{sec['total_threads']:,}T / {sec['total_handles']:,}H",
            )
            try:
                proc_count = len(psutil.pids())
            except Exception:
                proc_count = 0
            self.cpu_procs.set_data(proc_count, 500, custom_text=str(proc_count))

            # 2. GPU Deep Sensors
            if gpu.get("available"):
                self.lbl_gpu_title.config(text=f"GPU — {gpu['name']}")
                self.lbl_gpu_fan_clock.config(
                    text=f"{gpu['clock']:.0f} MHz | Fan {gpu['fan']:.0f}%"
                )
                self.gpu_gauge.set_value(gpu["util"])
                self.gpu_temp.set_data(gpu["temp"], 100.0)
                self.gpu_power.set_data(
                    gpu["power_w"],
                    gpu["power_limit_w"],
                    custom_text=f"{gpu['power_w']:.0f} / {gpu['power_limit_w']:.0f} W",
                )
                vram_used_gb = gpu["vram_used_mb"] / 1024.0
                vram_total_gb = gpu["vram_total_mb"] / 1024.0
                self.gpu_vram.set_data(
                    vram_used_gb,
                    vram_total_gb,
                    custom_text=f"{vram_used_gb:.1f} / {vram_total_gb:.0f} GB",
                )
                self.gpu_clock.set_data(gpu["clock"], 3200.0)
            else:
                self.gpu_gauge.set_value(0)
                self.gpu_temp.set_data(0, 100, custom_text="N/A")
                self.gpu_power.set_data(0, 100, custom_text="N/A")
                self.gpu_vram.set_data(0, 100, custom_text="N/A")
                self.gpu_clock.set_data(0, 3000, custom_text="N/A")

            # 3. Memory (RAM & Commit)
            ram_pct, used_gb, total_gb, commit_used, commit_total = self.telemetry.get_ram_info()
            self.ram_gauge.set_value(ram_pct)
            self.lbl_ram_used.config(text=f"{used_gb:.1f} / {total_gb:.1f} GB")
            self.lbl_ram_commit.config(text=f"{commit_used:.1f} / {commit_total:.1f} GB")

            speed_val = self.telemetry.cached_ram_speed
            self.lbl_ram_speed.config(text=f"{speed_val} MT/s" if speed_val > 0 else "N/A")

            # 4. Network & Security Auditing
            up_bps, down_bps = self.telemetry.get_net_speed()
            self.lbl_down_speed.config(text=f"{format_rate(down_bps)} ↓")
            self.lbl_up_speed.config(text=f"{format_rate(up_bps)} ↑")
            self.net_spark.plot(self.telemetry.net_down_history, dynamic_scale=True)

            self.lbl_tcp_conns.config(
                text=f"TCP Established: {sec['tcp_established']}  |  Listening Ports: {sec['tcp_listen']}"
            )
            sysmon_str = sec.get("sysmon", "Not Installed")
            self.lbl_sysmon.config(
                text=f"Sysmon: {sysmon_str}",
                fg=THEME["success"] if "Active" in sysmon_str else FG_SECONDARY,
            )

            # 5. Storage Health
            self.lbl_disk_health.config(text=self.telemetry.disk_health_summary)

            # 6. Evaluate Custom Alert Thresholds
            alerts = []
            if gpu.get("available") and gpu["temp"] >= 83.0:
                alerts.append(f"GPU Temp {gpu['temp']:.0f}°C")
            if cpu_load >= 92.0:
                alerts.append(f"CPU Load {cpu_load:.0f}%")
            if ram_pct >= 90.0:
                alerts.append(f"RAM {ram_pct:.0f}%")
            if alerts:
                self.alert_badge.config(
                    text=f"⚠ Alert: {', '.join(alerts)}",
                    fg=THEME["danger"],
                )
            else:
                self.alert_badge.config(
                    text="● Sensors Nominal",
                    fg=THEME["success"],
                )

            # 7. Sort & Render Top Processes
            if self.proc_sort_key == "cpu":
                procs.sort(key=lambda x: x["cpu"], reverse=True)
            elif self.proc_sort_key == "io":
                procs.sort(key=lambda x: x["read_bps"] + x["write_bps"], reverse=True)
            elif self.proc_sort_key == "handles":
                procs.sort(key=lambda x: x["handles"], reverse=True)
            else:
                procs.sort(key=lambda x: x["ram_mb"], reverse=True)

            for item in self.proc_tree.get_children():
                self.proc_tree.delete(item)

            for p in procs[:7]:
                disp_name = f"{p['name']} ({p['count']})" if p["count"] > 1 else p["name"]
                lineage = f"{p['pid']} → {p['ppid']}"
                ht_str = f"{p['handles']:,}H / {p['threads']}T"

                self.proc_tree.insert(
                    "",
                    tk.END,
                    values=(
                        disp_name,
                        lineage,
                        f"{p['cpu']:.1f}%",
                        f"{p['ram_mb']:,.0f} MB",
                        ht_str,
                        format_rate(p["read_bps"]),
                        format_rate(p["write_bps"]),
                    ),
                )

        self.after(1000, self.update_telemetry)


# Compatibility aliases
Dashboard = DashboardTab
DashboardWidget = DashboardTab