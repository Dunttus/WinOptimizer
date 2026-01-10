import customtkinter as ctk
import psutil
import threading
from tkinter import messagebox
from utils import add_info_section, is_admin

class ProcessesModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "Process Priority Manager", "Boost the CPU priority of active applications (e.g., Games, IDEs).")

        # --- WARNING LABEL ---
        warning_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        warning_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Professional & Accurate Warning Text
        warning_text = (
            "⚠️ PROCESS PRIORITY GUIDELINES:\n\n"
            "• Scope of Use: Modify priority only for the active foreground application (e.g., Video Games, Rendering Software). Never alter Windows system processes.\n"
            "• Stability Risk: Setting CPU-intensive applications to 'High' priority can cause 'Thread Starvation' for system drivers. This may result in input latency (mouse/keyboard lag), audio dropouts, or total system freezes.\n"
            "• Restrictions: Applications utilizing kernel-level anti-cheat (e.g., Vanguard, Easy Anti-Cheat) generally enforce process isolation and will reject priority modification requests."
        )
        
        ctk.CTkLabel(warning_frame, 
                     text=warning_text, 
                     text_color="#FF5555", 
                     font=ctk.CTkFont(size=12, weight="bold"),
                     wraplength=800,
                     justify="left").pack(anchor="w")

        # --- Search & Controls ---
        ctrl_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=20, pady=10)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(ctrl_frame, placeholder_text="Search process name (e.g. chrome)...", 
                                         textvariable=self.search_var, width=300)
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.refresh_list())

        ctk.CTkButton(ctrl_frame, text="Search / Refresh", command=self.refresh_list).pack(side="left")
        
        self.status_lbl = ctk.CTkLabel(ctrl_frame, text="", text_color="gray")
        self.status_lbl.pack(side="left", padx=15)

        # --- Headers ---
        header = ctk.CTkFrame(self.frame, fg_color="gray30", height=35)
        header.pack(fill="x", padx=20, pady=(10,0))
        
        header.grid_columnconfigure(0, weight=1) # Name
        header.grid_columnconfigure(1, weight=0) # PID
        header.grid_columnconfigure(2, weight=0) # Priority
        header.grid_columnconfigure(3, weight=0) # Actions
        
        ctk.CTkLabel(header, text="Process Name", font=ctk.CTkFont(weight="bold"), anchor="w").grid(row=0, column=0, padx=10, sticky="w")
        ctk.CTkLabel(header, text="PID", font=ctk.CTkFont(weight="bold"), width=60).grid(row=0, column=1, padx=5)
        ctk.CTkLabel(header, text="Current Priority", font=ctk.CTkFont(weight="bold"), width=120).grid(row=0, column=2, padx=5)
        ctk.CTkLabel(header, text="Actions", font=ctk.CTkFont(weight="bold"), width=150).grid(row=0, column=3, padx=10)

        # --- List Area ---
        self.proc_list = ctk.CTkScrollableFrame(self.frame)
        self.proc_list.pack(fill="both", expand=True, padx=20, pady=5)

        # Initial Load
        self.refresh_list()

    def refresh_list(self):
        # Clear existing rows
        for widget in self.proc_list.winfo_children():
            widget.destroy()

        search_text = self.search_var.get().lower()
        self.status_lbl.configure(text="Loading...")
        
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

        self.frame.after(0, lambda: [self._render_rows(procs), self.status_lbl.configure(text=status_msg)])

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
            row = ctk.CTkFrame(self.proc_list)
            row.pack(fill="x", pady=2)
            row.grid_columnconfigure(0, weight=1)
            
            # Name
            ctk.CTkLabel(row, text=p['name'], anchor="w").grid(row=0, column=0, padx=10, sticky="ew")
            
            # PID
            ctk.CTkLabel(row, text=str(p['pid']), width=60, text_color="gray").grid(row=0, column=1, padx=5)
            
            # Priority
            curr_nice = p.get('nice', 0)
            prio_name = prio_map.get(curr_nice, "Unknown")
            
            prio_color = "#00FF00" if curr_nice == psutil.HIGH_PRIORITY_CLASS else "gray90"
            ctk.CTkLabel(row, text=prio_name, width=120, text_color=prio_color).grid(row=0, column=2, padx=5)

            # Actions
            btn_frame = ctk.CTkFrame(row, fg_color="transparent")
            btn_frame.grid(row=0, column=3, padx=10)

            ctk.CTkButton(btn_frame, text="High", width=60, fg_color=("#3B8ED0", "#1F6AA5"), 
                          command=lambda pid=p['pid'], n=p['name']: self.set_prio(pid, n, psutil.HIGH_PRIORITY_CLASS)).pack(side="left", padx=2)
            
            ctk.CTkButton(btn_frame, text="Normal", width=60, fg_color="gray", 
                          command=lambda pid=p['pid'], n=p['name']: self.set_prio(pid, n, psutil.NORMAL_PRIORITY_CLASS)).pack(side="left", padx=2)

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