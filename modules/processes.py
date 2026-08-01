import ctypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import psutil

def is_admin():
    """Checks if the script is running with administrative privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


class ProcessesModule(tk.Frame):
    """Native Tkinter Process Priority Manager Module."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")

        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="Process Priority Manager", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Boost the CPU priority of active applications (e.g., Games, IDEs).", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- WARNING LABEL ---
        warning_frame = tk.Frame(self, bg="#262121", bd=1, relief="solid")
        warning_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        warning_text = (
            "⚠️ PROCESS PRIORITY GUIDELINES:\n\n"
            "• Scope of Use: Modify priority only for the active foreground application (e.g., Video Games, Rendering Software). Never alter Windows system processes.\n"
            "• Stability Risk: Setting CPU-intensive applications to 'High' priority can cause 'Thread Starvation' for system drivers. This may result in input latency (mouse/keyboard lag), audio dropouts, or total system freezes.\n"
            "• Restrictions: Applications utilizing kernel-level anti-cheat (e.g., Vanguard, Easy Anti-Cheat) generally enforce process isolation and will reject priority modification requests."
        )
        
        tk.Label(
            warning_frame, 
            text=warning_text, 
            fg="#FF5555", 
            bg="#262121",
            font=("Segoe UI", 9, "bold"),
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=12, pady=10)

        # --- Search & Controls ---
        ctrl_frame = tk.Frame(self, bg="#1c1c1c")
        ctrl_frame.pack(fill="x", padx=20, pady=10)

        self.search_entry = tk.Entry(ctrl_frame, bg="#111111", fg="#ffffff", insertbackground="white", font=("Segoe UI", 10), bd=1, relief="solid", width=35)
        self.search_entry.pack(side="left", padx=(0, 10), ipady=5)
        self.search_entry.insert(0, "Search process name...")
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.delete(0, 'end') if self.search_entry.get() == "Search process name..." else None)
        self.search_entry.bind("<Return>", lambda e: self.refresh_list())

        tk.Button(
            ctrl_frame, text="Search / Refresh", command=self.refresh_list, 
            bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), 
            bd=0, cursor="hand2", padx=12, pady=5
        ).pack(side="left")
        
        self.status_lbl = tk.Label(ctrl_frame, text="", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 9))
        self.status_lbl.pack(side="left", padx=15)

        # --- Headers ---
        header = tk.Frame(self, bg="#2a2a2a", bd=1, relief="solid")
        header.pack(fill="x", padx=20, pady=(10, 0))
        
        header.grid_columnconfigure(0, weight=1) # Name
        header.grid_columnconfigure(1, weight=0) # PID
        header.grid_columnconfigure(2, weight=0) # Priority
        header.grid_columnconfigure(3, weight=0) # Actions
        
        tk.Label(header, text="Process Name", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#2a2a2a", anchor="w").grid(row=0, column=0, padx=10, pady=6, sticky="w")
        tk.Label(header, text="PID", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#2a2a2a", width=10).grid(row=0, column=1, padx=5, pady=6)
        tk.Label(header, text="Current Priority", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#2a2a2a", width=15).grid(row=0, column=2, padx=5, pady=6)
        tk.Label(header, text="Actions", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#2a2a2a", width=18).grid(row=0, column=3, padx=10, pady=6)

        # --- List Area Container ---
        list_container = tk.Frame(self, bg="#1c1c1c", bd=1, relief="solid")
        list_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self.proc_list = VerticalScrollFrame(list_container, bg_color="#1c1c1c")
        self.proc_list.pack(fill="both", expand=True, padx=2, pady=2)

        # Initial Load
        self.refresh_list()

    def refresh_list(self):
        self.proc_list.clear()

        search_text = self.search_entry.get().strip()
        if search_text == "Search process name...":
            search_text = ""
        search_text = search_text.lower()

        self.status_lbl.config(text="Loading...")
        
        threading.Thread(target=self._fetch_and_display, args=(search_text,), daemon=True).start()

    def _fetch_and_display(self, search_text):
        procs = []
        try:
            for p in psutil.process_iter(['pid', 'name', 'nice']):
                try:
                    p_info = p.info
                    name = p_info['name']
                    
                    if search_text and search_text not in name.lower():
                        continue
                    
                    procs.append(p_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"Error fetching processes: {e}")

        procs.sort(key=lambda x: x['name'].lower())
        
        max_display = 100
        total_found = len(procs)
        
        if not search_text and total_found > max_display:
            procs = procs[:max_display]
            status_msg = f"Showing top {max_display} processes (Search to find specific ones)"
        else:
            status_msg = f"Found {total_found} processes"

        self.after(0, lambda: [self._render_rows(procs), self.status_lbl.config(text=status_msg)])

    def _render_rows(self, procs):
        prio_map = {
            psutil.IDLE_PRIORITY_CLASS: "Low",
            psutil.BELOW_NORMAL_PRIORITY_CLASS: "Below Normal",
            psutil.NORMAL_PRIORITY_CLASS: "Normal",
            psutil.ABOVE_NORMAL_PRIORITY_CLASS: "Above Normal",
            psutil.HIGH_PRIORITY_CLASS: "High",
            psutil.REALTIME_PRIORITY_CLASS: "Realtime"
        }

        for p in procs:
            row = tk.Frame(self.proc_list.inner_frame, bg="#2a2a2a", bd=1, relief="solid")
            row.pack(fill="x", pady=2, padx=5)
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=0)
            row.grid_columnconfigure(2, weight=0)
            row.grid_columnconfigure(3, weight=0)

            # Name
            name_lbl = tk.Label(row, text=p['name'], font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#2a2a2a", anchor="w")
            name_lbl.grid(row=0, column=0, padx=10, pady=6, sticky="ew")

            # PID
            pid_lbl = tk.Label(row, text=str(p['pid']), font=("Segoe UI", 9), fg="#aaaaaa", bg="#2a2a2a", width=10)
            pid_lbl.grid(row=0, column=1, padx=5, pady=6)

            # Priority
            curr_nice = p.get('nice', 0)
            prio_name = prio_map.get(curr_nice, "Unknown")
            prio_color = "#00FF00" if curr_nice == psutil.HIGH_PRIORITY_CLASS else "#dddddd"
            
            prio_lbl = tk.Label(row, text=prio_name, font=("Segoe UI", 9, "bold"), fg=prio_color, bg="#2a2a2a", width=15)
            prio_lbl.grid(row=0, column=2, padx=5, pady=6)

            # Actions
            btn_frame = tk.Frame(row, bg="#2a2a2a")
            btn_frame.grid(row=0, column=3, padx=10, pady=6)

            btn_high = tk.Button(
                btn_frame, text="High", width=8, bg="#3B8ED0", fg="white", 
                font=("Segoe UI", 8, "bold"), activebackground="#1F6AA5", activeforeground="white", 
                bd=0, cursor="hand2", padx=4, pady=2,
                command=lambda pid=p['pid'], n=p['name']: self.set_prio(pid, n, psutil.HIGH_PRIORITY_CLASS)
            )
            btn_high.pack(side="left", padx=2)

            btn_norm = tk.Button(
                btn_frame, text="Normal", width=8, bg="#444444", fg="white", 
                font=("Segoe UI", 8, "bold"), activebackground="#555555", activeforeground="white", 
                bd=0, cursor="hand2", padx=4, pady=2,
                command=lambda pid=p['pid'], n=p['name']: self.set_prio(pid, n, psutil.NORMAL_PRIORITY_CLASS)
            )
            btn_norm.pack(side="left", padx=2)

    def set_prio(self, pid, name, prio_class):
        if not is_admin():
            messagebox.showwarning("Admin Required", "Changing process priority requires Administrator privileges.\nPlease restart the app as Administrator.")
            return

        try:
            p = psutil.Process(pid)
            p.nice(prio_class)
            
            prio_name = "High" if prio_class == psutil.HIGH_PRIORITY_CLASS else "Normal"
            messagebox.showinfo("Success", f"Set '{name}' (PID: {pid}) to {prio_name} Priority.")
            self.refresh_list()
            
        except psutil.AccessDenied:
            messagebox.showerror("Error", f"Access Denied.\n\nCould not change priority for '{name}'.\n\nPossible reasons:\n1. It is a protected system process.\n2. An Anti-Cheat system is blocking access (e.g., Vanguard, EAC).")
        except psutil.NoSuchProcess:
            messagebox.showerror("Error", f"Process '{name}' is no longer running.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set priority: {e}")


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
        self.window_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.window_id, width=e.width))
        
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


# Compatibility aliases for main.py dynamic routing
ProcessPriorityTab = ProcessesModule