import subprocess
import threading
import tkinter as tk
from tkinter import ttk

# Used to hide console windows during background commands
CREATE_NO_WINDOW = 0x08000000

class ScrollableFrame:
    """Custom standard Tkinter scrollable frame using Composition to hide it from main.py's auto-loader."""
    def __init__(self, container, bg_color):
        self.frame = tk.Frame(container, bg=bg_color)
        
        self.canvas = tk.Canvas(self.frame, bg=bg_color, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas, bg=bg_color)
        
        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mousewheel scrolling (Windows standard)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if self.inner_frame.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
    def clear(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

    def pack(self, *args, **kwargs):
        self.frame.pack(*args, **kwargs)
        
    def pack_forget(self):
        self.frame.pack_forget()


class WingetModule(tk.Frame):
    """Native Tkinter Winget Package Manager."""
    def __init__(self, parent):
        super().__init__(parent, bg="#1c1c1c")
        
        # --- Info Section ---
        info_frame = tk.Frame(self, bg="#1c1c1c")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(info_frame, text="WinGet Package Manager", fg="#ffffff", bg="#1c1c1c", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Manage software. Toggle between searching the Store and managing Installed Apps.", fg="#888888", bg="#1c1c1c", font=("Segoe UI", 10)).pack(anchor="w")

        # --- View Switcher (Tabs) ---
        self.switch_frame = tk.Frame(self, bg="#1c1c1c")
        self.switch_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.btn_store = tk.Button(self.switch_frame, text="Store Search", font=("Segoe UI", 10, "bold"), width=20, bd=0, cursor="hand2", command=lambda: self.toggle_view("Store Search"))
        self.btn_store.pack(side="left", padx=(0, 5))

        self.btn_installed = tk.Button(self.switch_frame, text="My Installed Apps", font=("Segoe UI", 10, "bold"), width=20, bd=0, cursor="hand2", command=lambda: self.toggle_view("My Installed Apps"))
        self.btn_installed.pack(side="left")

        # --- Container Frames ---
        self.store_container = tk.Frame(self, bg="#1c1c1c")
        self.installed_container = tk.Frame(self, bg="#1c1c1c")

        # --- Shared Console (Bottom) ---
        console_frame = tk.Frame(self, bg="#1c1c1c")
        console_frame.pack(side="bottom", fill="x", padx=20, pady=15)
        
        self.console = tk.Text(console_frame, height=8, font=("Consolas", 10), bg="#0B0B0E", fg="#00FF00", bd=1, relief="flat", insertbackground="white")
        self.console.pack(fill="x")
        self.console.insert("1.0", "Ready.\n")
        self.console.configure(state="disabled")

        # --- Data Caches ---
        self.installed_cache = [] 
        self.is_loading_installed = False
        
        # --- Build UIs ---
        self.setup_store_ui()
        self.setup_installed_ui()

        # Start with Store View
        self.toggle_view("Store Search")

    def toggle_view(self, value):
        active_bg, active_fg = "#383838", "#ffffff"
        inactive_bg, inactive_fg = "#262626", "#888888"

        if value == "Store Search":
            self.btn_store.config(bg=active_bg, fg=active_fg)
            self.btn_installed.config(bg=inactive_bg, fg=inactive_fg)
            self.installed_container.pack_forget()
            self.store_container.pack(fill="both", expand=True, padx=20, pady=5)
        else:
            self.btn_store.config(bg=inactive_bg, fg=inactive_fg)
            self.btn_installed.config(bg=active_bg, fg=active_fg)
            self.store_container.pack_forget()
            self.installed_container.pack(fill="both", expand=True, padx=20, pady=5)
            if not self.installed_cache and not self.is_loading_installed:
                self.refresh_installed()

    # =========================================================
    # UI BUILDERS
    # =========================================================

    def setup_store_ui(self):
        disclaimer_frame = tk.Frame(self.store_container, bg="#262626", bd=1, relief="solid")
        disclaimer_frame.pack(fill="x", pady=(0, 15))

        tk.Label(disclaimer_frame, text="⚠️ Repository & License Notice", fg="#FFA726", bg="#262626", font=("Segoe UI", 10, "bold"), anchor="w").pack(padx=15, pady=(8, 0), anchor="w", fill="x")
        notice_text = "Packages are retrieved entirely from the public Microsoft Winget repository. Installing software via this tool does not grant commercial licenses."
        tk.Label(disclaimer_frame, text=notice_text, fg="#B0B0B0", bg="#262626", font=("Segoe UI", 9), anchor="w", justify="left").pack(padx=15, pady=(2, 8), anchor="w", fill="x")

        search_area = tk.Frame(self.store_container, bg="#1c1c1c")
        search_area.pack(fill="x", pady=0)
        
        self.store_search_var = tk.StringVar()
        entry = tk.Entry(search_area, textvariable=self.store_search_var, width=50, bg="#111111", fg="#ffffff", insertbackground="white", font=("Segoe UI", 10), bd=1, relief="solid")
        entry.pack(side="left", padx=(0, 10), ipady=5)
        entry.insert(0, "Search public repository...")
        entry.bind("<FocusIn>", lambda e: entry.delete(0, 'end') if entry.get() == "Search public repository..." else None)
        entry.bind("<Return>", lambda e: self.run_store_search())
        
        tk.Button(search_area, text="Search Store", command=self.run_store_search, bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", padx=15, pady=4).pack(side="left")

        self.create_header_frame(self.store_container, ["Name", "Id", "Version", "Match"])
        
        self.store_results = ScrollableFrame(self.store_container, bg_color="#1c1c1c")
        self.store_results.pack(fill="both", expand=True)
        self.configure_grid(self.store_results.inner_frame)

    def setup_installed_ui(self):
        tool_area = tk.Frame(self.installed_container, bg="#1c1c1c")
        tool_area.pack(fill="x", pady=(0, 10))
        
        self.local_filter_var = tk.StringVar()
        entry = tk.Entry(tool_area, textvariable=self.local_filter_var, width=40, bg="#111111", fg="#ffffff", insertbackground="white", font=("Segoe UI", 10), bd=1, relief="solid")
        entry.pack(side="left", padx=(0, 10), ipady=5)
        entry.insert(0, "Filter local apps...")
        entry.bind("<FocusIn>", lambda e: entry.delete(0, 'end') if entry.get() == "Filter local apps..." else None)
        entry.bind("<Return>", lambda e: self.filter_local_apps())

        tk.Button(tool_area, text="Search Installed", command=self.filter_local_apps, bg="#3B8ED0", fg="white", font=("Segoe UI", 9, "bold"), bd=0, cursor="hand2", padx=15, pady=4).pack(side="left", padx=5)
        tk.Button(tool_area, text="Update Winget Apps", command=self.update_all_apps, bg="#F57C00", fg="white", font=("Segoe UI", 9, "bold"), activebackground="#E65100", activeforeground="white", bd=0, cursor="hand2", padx=15, pady=4).pack(side="right")

        self.create_header_frame(self.installed_container, ["Name", "Id", "Version", "Available"])

        self.installed_results = ScrollableFrame(self.installed_container, bg_color="#1c1c1c")
        self.installed_results.pack(fill="both", expand=True)
        self.configure_grid(self.installed_results.inner_frame)

    # =========================================================
    # HELPERS
    # =========================================================

    def create_header_frame(self, parent, labels):
        frame = tk.Frame(parent, bg="#1a1a1a", height=35)
        frame.pack(fill="x", pady=(10, 0))
        self.configure_grid(frame)
        
        for i, h in enumerate(labels):
            tk.Label(frame, text=h, font=("Segoe UI", 10, "bold"), fg="#888888", bg="#1a1a1a", anchor="w").grid(row=0, column=i, padx=10, pady=5, sticky="ew")
        
        tk.Label(frame, text="Action", font=("Segoe UI", 10, "bold"), fg="#888888", bg="#1a1a1a", anchor="e").grid(row=0, column=5, padx=15, pady=5, sticky="ew")
        return frame

    def configure_grid(self, frame):
        frame.grid_columnconfigure(0, minsize=200, weight=1)
        frame.grid_columnconfigure(1, minsize=200, weight=1)
        frame.grid_columnconfigure(2, minsize=100, weight=0)
        frame.grid_columnconfigure(3, minsize=100, weight=0)
        frame.grid_columnconfigure(4, minsize=20, weight=0)
        frame.grid_columnconfigure(5, minsize=90, weight=0)

    def log(self, text):
        clean_text = text.strip()
        if clean_text in ["|", "/", "-", "\\"]: return
        if "MB /" in clean_text: return
        
        if "â–" in clean_text or "█" in clean_text:
            try:
                percent_str = clean_text.split()[-1]
                if "%" in percent_str:
                    val = int(percent_str.replace("%", ""))
                    if val % 5 == 0 or val == 100:
                        self._raw_log(f"Download Progress: {val}%")
            except:
                pass
            return 
            
        self._raw_log(text)

    def _raw_log(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", f"> {text}\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def truncate_text(self, text, max_len):
        if not text: return "-"
        if len(text) > max_len:
            return text[:max_len-3] + "..."
        return text

    # =========================================================
    # PARSING
    # =========================================================

    def parse_winget_table(self, output):
        lines = output.splitlines()
        if not lines: return []
        
        h_idx = -1
        for i, line in enumerate(lines):
            if "Name" in line and "Id" in line:
                h_idx = i
                break
        if h_idx == -1: return []
        
        h_line = lines[h_idx]
        p_id = h_line.find("Id")
        p_ver = h_line.find("Version")
        p_match = h_line.find("Match") if "Match" in h_line else h_line.find("Available")
        p_src = h_line.find("Source")
        
        slices = [0]
        if p_id > 0: slices.append(p_id)
        if p_ver > 0: slices.append(p_ver)
        if p_match > 0: slices.append(p_match)
        if p_src > 0: slices.append(p_src)
        slices.append(len(h_line) + 100)
        
        results = []
        for line in lines[h_idx + 2:]:
            if not line.strip() or "---" in line: continue
            row_data = []
            for i in range(len(slices)-1):
                val = line[slices[i]:slices[i+1]].strip()
                row_data.append(val if val else "-")
            while len(row_data) < 5: row_data.append("-")
            results.append(row_data[:4]) 
            
        return results

    # =========================================================
    # LOGIC
    # =========================================================

    def run_store_search(self):
        query = self.store_search_var.get().strip()
        if not query or query == "Search public repository...": return
        self.fetch_data(f'winget search "{query}" --source winget', "Install", self.store_results)

    def refresh_installed(self):
        self.log("Scanning installed apps... (This may take a moment)")
        self.is_loading_installed = True
        
        self.installed_results.clear()
        tk.Label(self.installed_results.inner_frame, text="Scanning installed applications...", fg="gray", bg="#1c1c1c", font=("Segoe UI", 10)).pack(pady=20)
        
        def _fetch():
            try:
                # Added encoding='utf-8', errors='ignore' to prevent charmap decode crashes
                raw = subprocess.check_output("winget list", shell=True, text=True, encoding='utf-8', errors='ignore', creationflags=CREATE_NO_WINDOW)
                self.installed_cache = self.parse_winget_table(raw)
                self.after(0, self.finish_loading_installed)
            except Exception as e:
                self.log(f"Failed to fetch installed apps: {e}")
                self.installed_cache = []
                self.after(0, self.finish_loading_installed)
        threading.Thread(target=_fetch, daemon=True).start()

    def finish_loading_installed(self):
        self.is_loading_installed = False
        self.log(f"Scan complete. Found {len(self.installed_cache)} apps.")
        filter_val = self.local_filter_var.get()
        if not filter_val or filter_val == "Filter local apps...":
            self.render_rows(self.installed_cache, "Uninstall", self.installed_results)
        else:
            self.filter_local_apps()

    def filter_local_apps(self):
        if self.is_loading_installed: return
        query = self.local_filter_var.get().lower()
        
        if not query or query == "filter local apps...":
            self.render_rows(self.installed_cache, "Uninstall", self.installed_results)
            return
            
        if not self.installed_cache:
            self.installed_results.clear()
            tk.Label(self.installed_results.inner_frame, text="List is empty. Try reloading tabs.", fg="gray", bg="#1c1c1c").pack(pady=20)
            return
            
        filtered = [app for app in self.installed_cache if query in app[0].lower() or query in app[1].lower()]
        self.installed_results.clear()
        
        if not filtered:
             tk.Label(self.installed_results.inner_frame, text=f"No apps match '{query}'", fg="gray", bg="#1c1c1c").pack(pady=20)
        else:
            self.render_rows(filtered, "Uninstall", self.installed_results)

    def update_all_apps(self):
        self.log("Checking for Winget-managed updates...")
        def _batch_process():
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                raw = subprocess.check_output("winget upgrade --include-unknown", startupinfo=si, shell=True, text=True, encoding='utf-8', errors='ignore')
                upgrades = self.parse_winget_table(raw)
                
                to_update = []
                for u in upgrades:
                    if len(u) > 1 and "Microsoft.AppInstaller" in u[1]:
                        self.log(f"Skipping {u[0]} (Cannot update itself while running)")
                    else:
                        to_update.append(u)

                if not to_update:
                    self.log("No Winget-managed updates found.")
                    return

                self.log(f"Found {len(to_update)} package(s) to update.")
                for app in to_update:
                    name = app[0]
                    app_id = app[1]
                    self.log(f"----------------------------------------")
                    self.log(f"Upgrading: {name} ({app_id})")
                    cmd = [
                        "winget", "upgrade", "--id", app_id, 
                        "--silent", "--accept-package-agreements", "--accept-source-agreements", "--include-unknown"
                    ]
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                            text=True, encoding='utf-8', errors='ignore', shell=True, creationflags=CREATE_NO_WINDOW)
                    for line in proc.stdout:
                        if line.strip(): self.log(line.strip())
                    proc.wait()
                
                self.log("----------------------------------------")
                self.log("Batch update completed.")
                self.after(1000, self.refresh_installed)
            except Exception as e:
                self.log(f"Batch Update Error: {e}")
        threading.Thread(target=_batch_process, daemon=True).start()

    def fetch_data(self, cmd, action, scroll_frame):
        self.log("Searching Repository...")
        scroll_frame.clear()
        tk.Label(scroll_frame.inner_frame, text="Searching...", fg="gray", bg="#1c1c1c", font=("Segoe UI", 10)).pack(pady=20)
        
        def _run():
            try:
                # Added encoding='utf-8', errors='ignore' here as well
                raw = subprocess.check_output(cmd, shell=True, text=True, encoding='utf-8', errors='ignore', stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW)
                data = self.parse_winget_table(raw)
                self.after(0, lambda: self.render_rows(data, action, scroll_frame))
            except Exception as e:
                self.log(f"Search Error: {e}")
                self.after(0, lambda: self.show_error(scroll_frame, "No results found."))
        threading.Thread(target=_run, daemon=True).start()

    def show_error(self, scroll_frame, msg):
        scroll_frame.clear()
        tk.Label(scroll_frame.inner_frame, text=msg, fg="gray", bg="#1c1c1c", font=("Segoe UI", 10)).pack(pady=20)

    def render_rows(self, apps, action, scroll_frame):
        scroll_frame.clear()
        parent = scroll_frame.inner_frame
        
        if not apps:
            tk.Label(parent, text="No results found.", fg="gray", bg="#1c1c1c", font=("Segoe UI", 10)).pack(pady=20)
            return

        limit = 100 if action == "Uninstall" else 50
        for idx, app in enumerate(apps[:limit]):
            bg = "#222222" if idx % 2 == 0 else "#1c1c1c"
            row_f = tk.Frame(parent, bg=bg)
            row_f.pack(fill="x", pady=0)
            self.configure_grid(row_f)

            tk.Label(row_f, text=self.truncate_text(app[0], 40), font=("Segoe UI", 9), fg="#ffffff", bg=bg, anchor="w").grid(row=0, column=0, padx=10, pady=8, sticky="ew")
            tk.Label(row_f, text=self.truncate_text(app[1], 40), font=("Segoe UI", 9), fg="#a0a0a0", bg=bg, anchor="w").grid(row=0, column=1, padx=10, pady=8, sticky="ew")
            tk.Label(row_f, text=self.truncate_text(app[2], 12), font=("Segoe UI", 9), fg="#ffffff", bg=bg, anchor="w").grid(row=0, column=2, padx=10, pady=8, sticky="ew")
            tk.Label(row_f, text=self.truncate_text(app[3], 15), font=("Segoe UI", 9), fg="#a0a0a0", bg=bg, anchor="w").grid(row=0, column=3, padx=10, pady=8, sticky="ew")

            btn_bg, btn_act = ("#c42b1c", "#A32014") if action == "Uninstall" else ("#3B8ED0", "#2873AD")
            app_id = app[1]
            cmd_action = "uninstall" if action == "Uninstall" else "install"
            
            btn = tk.Button(row_f, text=action, width=10, bg=btn_bg, fg="white", font=("Segoe UI", 9, "bold"), activebackground=btn_act, activeforeground="white", bd=0, cursor="hand2")
            btn.configure(command=lambda i=app_id, a=cmd_action: self.execute_action([a, "--id", i]))
            btn.grid(row=0, column=5, padx=15, pady=6, sticky="e")

    def execute_action(self, args):
        def _run():
            cmd_list = ["winget"] + args + ["--accept-source-agreements"]
            if "install" in args or "upgrade" in args:
                cmd_list.append("--accept-package-agreements")
                cmd_list.append("--silent")
            
            self.log(f"Running: {' '.join(cmd_list)}")
            proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore', shell=True, creationflags=CREATE_NO_WINDOW)
            for line in proc.stdout:
                if line.strip(): self.log(line.strip())
            proc.wait()
            self.log("Done.")
            if "uninstall" in args or "upgrade" in args:
                 self.after(1000, self.refresh_installed)
        threading.Thread(target=_run, daemon=True).start()