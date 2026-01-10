import customtkinter as ctk
import subprocess
import threading
from utils import add_info_section

class WingetModule:
    def __init__(self, parent):
        self.frame = ctk.CTkFrame(parent)
        add_info_section(self.frame, "WinGet Package Manager", 
                         "Manage software. Toggle between searching the Store and managing Installed Apps.")

        # --- View Switcher (Tabs) ---
        self.switch_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.switch_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.view_selector = ctk.CTkSegmentedButton(self.switch_frame, 
                                                    values=["Store Search", "My Installed Apps"],
                                                    command=self.toggle_view,
                                                    width=300)
        self.view_selector.set("Store Search")
        self.view_selector.pack()

        # --- Container Frames ---
        self.store_container = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.installed_container = ctk.CTkFrame(self.frame, fg_color="transparent")

        # --- Shared Console (Bottom) ---
        self.console = ctk.CTkTextbox(self.frame, height=200, font=("Consolas", 11), fg_color="black", text_color="#00FF00")
        self.console.pack(side="bottom", fill="x", padx=20, pady=10)
        self.console.insert("0.0", "Ready.\n")
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
        if value == "Store Search":
            self.installed_container.pack_forget()
            self.store_container.pack(fill="both", expand=True, padx=20, pady=5)
        else:
            self.store_container.pack_forget()
            self.installed_container.pack(fill="both", expand=True, padx=20, pady=5)
            if not self.installed_cache and not self.is_loading_installed:
                self.refresh_installed()

    # =========================================================
    # UI BUILDERS
    # =========================================================

    def setup_store_ui(self):
        # --- DISCLAIMER BANNER ---
        disclaimer_frame = ctk.CTkFrame(self.store_container, fg_color="#262626", corner_radius=6, border_width=1, border_color="#404040")
        disclaimer_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(disclaimer_frame, text="⚠️ Repository & License Notice", 
                     font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFA726", anchor="w").pack(padx=15, pady=(8, 0), anchor="w")
        
        notice_text = (
            "Packages are retrieved entirely from the public Microsoft Winget repository. "
            "Installing software via this tool does not grant commercial licenses."
        )
        ctk.CTkLabel(disclaimer_frame, text=notice_text, 
                     font=ctk.CTkFont(size=11), text_color="#B0B0B0", anchor="w", justify="left").pack(padx=15, pady=(2, 8), anchor="w")

        # --- Search Bar ---
        search_area = ctk.CTkFrame(self.store_container, fg_color="transparent")
        search_area.pack(fill="x", pady=0)
        
        self.store_search_var = ctk.StringVar()
        entry = ctk.CTkEntry(search_area, placeholder_text="Search public repository...", 
                             textvariable=self.store_search_var, width=400)
        entry.pack(side="left", padx=(0, 10))
        entry.bind("<Return>", lambda e: self.run_store_search())
        
        ctk.CTkButton(search_area, text="Search Store", command=self.run_store_search, width=120).pack(side="left")

        # --- Headers ---
        self.store_headers = self.create_header_frame(self.store_container, ["Name", "Id", "Version", "Match"])
        
        # --- Results ---
        self.store_results = ctk.CTkScrollableFrame(self.store_container, fg_color="transparent", corner_radius=0)
        self.store_results.pack(fill="both", expand=True)
        self.configure_grid(self.store_results)

    def setup_installed_ui(self):
        # 1. Filter Bar
        tool_area = ctk.CTkFrame(self.installed_container, fg_color="transparent")
        tool_area.pack(fill="x", pady=10)
        
        self.local_filter_var = ctk.StringVar()
        entry = ctk.CTkEntry(tool_area, placeholder_text="Filter local apps...", 
                             textvariable=self.local_filter_var, width=300)
        entry.pack(side="left", padx=(0, 10))
        entry.bind("<Return>", lambda e: self.filter_local_apps())

        ctk.CTkButton(tool_area, text="Search Installed", command=self.filter_local_apps, 
                      fg_color="#3B8ED0", width=120).pack(side="left", padx=5)
        
        ctk.CTkButton(tool_area, text="Update Winget Apps", command=self.update_all_apps, 
                      fg_color="#F57C00", hover_color="#E65100", width=140).pack(side="right")

        # 2. Table Headers
        self.installed_headers = self.create_header_frame(self.installed_container, ["Name", "Id", "Version", "Available"])

        # 3. Results List
        self.installed_results = ctk.CTkScrollableFrame(self.installed_container, fg_color="transparent", corner_radius=0)
        self.installed_results.pack(fill="both", expand=True)
        self.configure_grid(self.installed_results)

    # =========================================================
    # HELPERS
    # =========================================================

    def create_header_frame(self, parent, labels):
        frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", height=35, corner_radius=0)
        frame.pack(fill="x", pady=(10, 0))
        self.configure_grid(frame)
        
        for i, h in enumerate(labels):
            ctk.CTkLabel(frame, text=h, font=ctk.CTkFont(size=12, weight="bold"), 
                         text_color="#888888", anchor="w").grid(row=0, column=i, padx=10, sticky="ew")
        
        ctk.CTkLabel(frame, text="Action", font=ctk.CTkFont(size=12, weight="bold"), 
                         text_color="#888888", anchor="e").grid(row=0, column=5, padx=15, sticky="ew")
        return frame

    def configure_grid(self, frame):
        frame.grid_columnconfigure(0, minsize=200, weight=0) # Name
        frame.grid_columnconfigure(1, minsize=200, weight=0) # Id
        frame.grid_columnconfigure(2, minsize=100, weight=0) # Version
        frame.grid_columnconfigure(3, minsize=100, weight=0) # Match/Available
        frame.grid_columnconfigure(4, weight=1)              # Spacer
        frame.grid_columnconfigure(5, minsize=90, weight=0)  # Action

    def log(self, text):
        clean_text = text.strip()
        
        # 1. Spinner spam (Ignore)
        if clean_text in ["|", "/", "-", "\\"]: return
        
        # 2. Download size spam (e.g. 10MB / 100MB) -> Ignore to prevent flooding
        if "MB /" in clean_text: return
        
        # 3. SMART PROGRESS PARSER
        # Detects the "blocky" progress bar and converts it to a clean "Progress: XX%" line
        if "â–" in clean_text or "█" in clean_text:
            try:
                # Extract the last part which is usually the percentage (e.g. "24%")
                percent_str = clean_text.split()[-1]
                if "%" in percent_str:
                    val = int(percent_str.replace("%", ""))
                    
                    # UPDATED: Print every 5% (0, 5, 10, ... 100)
                    if val % 5 == 0 or val == 100:
                        self._raw_log(f"Download Progress: {val}%")
            except:
                pass
            return # Block the raw messy line
            
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
            
            # Remove Source column data
            results.append(row_data[:4]) 
            
        return results

    # =========================================================
    # LOGIC
    # =========================================================

    def run_store_search(self):
        query = self.store_search_var.get().strip()
        if not query: return
        self.fetch_data(f'winget search "{query}" --source winget', "Install", self.store_results)

    def refresh_installed(self):
        self.log("Scanning installed apps... (This may take a moment)")
        self.is_loading_installed = True
        
        for w in self.installed_results.winfo_children(): w.destroy()
        ctk.CTkLabel(self.installed_results, text="Scanning installed applications...", text_color="gray").pack(pady=20)
        
        def _fetch():
            try:
                raw = subprocess.check_output("winget list", shell=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                self.installed_cache = self.parse_winget_table(raw)
                self.frame.after(0, self.finish_loading_installed)
            except Exception as e:
                self.log(f"Failed to fetch installed apps: {e}")
                self.installed_cache = []
                self.frame.after(0, self.finish_loading_installed)
        threading.Thread(target=_fetch, daemon=True).start()

    def finish_loading_installed(self):
        self.is_loading_installed = False
        self.log(f"Scan complete. Found {len(self.installed_cache)} apps.")
        if not self.local_filter_var.get():
            self.render_rows(self.installed_cache, "Uninstall", self.installed_results)
        else:
            self.filter_local_apps()

    def filter_local_apps(self):
        if self.is_loading_installed: return
        query = self.local_filter_var.get().lower()
        if not query:
            self.render_rows(self.installed_cache, "Uninstall", self.installed_results)
            return
        if not self.installed_cache:
            for w in self.installed_results.winfo_children(): w.destroy()
            ctk.CTkLabel(self.installed_results, text="List is empty. Try reloading tabs.", text_color="gray").pack(pady=20)
            return
        filtered = [app for app in self.installed_cache if query in app[0].lower() or query in app[1].lower()]
        for w in self.installed_results.winfo_children(): w.destroy()
        if not filtered:
             ctk.CTkLabel(self.installed_results, text=f"No apps match '{query}'", text_color="gray").pack(pady=20)
        else:
            self.render_rows(filtered, "Uninstall", self.installed_results)

    def update_all_apps(self):
        self.log("Checking for Winget-managed updates...")
        def _batch_process():
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                raw = subprocess.check_output("winget upgrade --include-unknown", startupinfo=si, shell=True, text=True)
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
                                            text=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    for line in proc.stdout:
                        if line.strip(): self.log(line.strip())
                    proc.wait()
                
                self.log("----------------------------------------")
                self.log("Batch update completed.")
                self.frame.after(1000, self.refresh_installed)
            except Exception as e:
                self.log(f"Batch Update Error: {e}")
        threading.Thread(target=_batch_process, daemon=True).start()

    def fetch_data(self, cmd, action, parent_frame):
        self.log("Searching Repository...")
        for w in parent_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(parent_frame, text="Searching...", text_color="gray").pack(pady=20)
        
        def _run():
            try:
                raw = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                data = self.parse_winget_table(raw)
                self.frame.after(0, lambda: self.render_rows(data, action, parent_frame))
            except Exception as e:
                self.log(f"Search Error: {e}")
                self.frame.after(0, lambda: self.show_error(parent_frame, "No results found."))
        threading.Thread(target=_run, daemon=True).start()

    def show_error(self, frame, msg):
        for w in frame.winfo_children(): w.destroy()
        ctk.CTkLabel(frame, text=msg, text_color="gray").pack(pady=20)

    def render_rows(self, apps, action, parent_frame):
        for w in parent_frame.winfo_children(): w.destroy()
        if not apps:
            ctk.CTkLabel(parent_frame, text="No results found.").pack(pady=20)
            return

        limit = 100 if action == "Uninstall" else 50
        for idx, app in enumerate(apps[:limit]):
            bg = "#222222" if idx % 2 == 0 else "transparent"
            row_f = ctk.CTkFrame(parent_frame, fg_color=bg, corner_radius=0, height=40)
            row_f.pack(fill="x", pady=0)
            self.configure_grid(row_f)

            # Name (Col 0)
            txt = self.truncate_text(app[0], 30)
            ctk.CTkLabel(row_f, text=txt, font=ctk.CTkFont(size=11), anchor="w", text_color="white").grid(row=0, column=0, padx=10, pady=8, sticky="ew")
            # Id (Col 1)
            txt = self.truncate_text(app[1], 30)
            ctk.CTkLabel(row_f, text=txt, font=ctk.CTkFont(size=11), anchor="w", text_color="gray70").grid(row=0, column=1, padx=10, pady=8, sticky="ew")
            # Version (Col 2)
            txt = self.truncate_text(app[2], 12)
            ctk.CTkLabel(row_f, text=txt, font=ctk.CTkFont(size=11), anchor="w", text_color="white").grid(row=0, column=2, padx=10, pady=8, sticky="ew")
            # Match (Col 3)
            txt = self.truncate_text(app[3], 15)
            ctk.CTkLabel(row_f, text=txt, font=ctk.CTkFont(size=11), anchor="w", text_color="gray70").grid(row=0, column=3, padx=10, pady=8, sticky="ew")

            # Action Button (Col 5)
            btn_color = "#c42b1c" if action == "Uninstall" else ["#3B8ED0", "#1F6AA5"]
            btn = ctk.CTkButton(row_f, text=action, width=80, height=26, fg_color=btn_color, 
                                font=ctk.CTkFont(size=11, weight="bold"))
            app_id = app[1]
            cmd_action = "uninstall" if action == "Uninstall" else "install"
            btn.configure(command=lambda i=app_id, a=cmd_action: self.execute_action([a, "--id", i]))
            btn.grid(row=0, column=5, padx=15, pady=8, sticky="e")

    def execute_action(self, args):
        def _run():
            cmd_list = ["winget"] + args + ["--accept-source-agreements"]
            if "install" in args or "upgrade" in args:
                cmd_list.append("--accept-package-agreements")
                cmd_list.append("--silent")
            
            self.log(f"Running: {' '.join(cmd_list)}")
            proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                    text=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            for line in proc.stdout:
                if line.strip(): self.log(line.strip())
            proc.wait()
            self.log("Done.")
            if "uninstall" in args or "upgrade" in args:
                 self.frame.after(1000, self.refresh_installed)
        threading.Thread(target=_run, daemon=True).start()