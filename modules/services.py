import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    THEME,
    BG_MAIN,
    BG_CARD,
    BG_INPUT,
    FG_PRIMARY,
    FG_SECONDARY,
    FG_MUTED,
    BORDER_COLOR,
    FONT_BODY,
    FONT_BOLD,
    FONT_SMALL,
    DISABLABLE_SERVICES,
    create_header,
    create_button,
)

CREATE_NO_WINDOW = 0x08000000

# User-friendly descriptions for common Windows background services
SERVICE_METADATA = {
    "DiagTrack": (
        "Connected User Experiences and Telemetry",
        "Tracks diagnostic and usage telemetry sent to Microsoft.",
    ),
    "SysMain": (
        "SysMain (Superfetch)",
        "Preloads frequent apps into RAM. Can cause 100% disk usage on mechanical HDDs.",
    ),
    "PcaSvc": (
        "Program Compatibility Assistant Service",
        "Monitors and detects compatibility issues for installed user applications.",
    ),
    "Fax": (
        "Fax Service",
        "Legacy fax transmission and reception service.",
    ),
    "MapsBroker": (
        "Downloaded Maps Manager",
        "Periodically syncs and updates offline maps in the background.",
    ),
    "RetailDemo": (
        "Retail Demo Service",
        "Used exclusively by retail stores for display demo modes.",
    ),
    "TabletInputService": (
        "Touch Keyboard and Handwriting Panel Service",
        "Manages touch keyboard input (safe to disable on desktop PCs).",
    ),
}


class ServicesModule(tk.Frame):
    """Windows Service Manager Module for disabling unnecessary background services."""

    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)
        self.service_buttons: dict[str, tk.Button] = {}

        self.init_ui()

    def init_ui(self):
        # --- Standard Header ---
        create_header(
            self,
            title="Windows Service Manager",
            subtitle="Safely stop and disable unnecessary background services to free up RAM and CPU resources.",
        )

        # --- Notice Card ---
        notice_card = tk.Frame(
            self,
            bg=BG_CARD,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
            padx=16,
            pady=10,
        )
        notice_card.pack(fill=tk.X, padx=24, pady=(0, 12))

        tk.Label(
            notice_card,
            text="ℹ️ Whitelisted Safe-to-Disable Services",
            fg=THEME["info"],
            bg=BG_CARD,
            font=FONT_BOLD,
        ).pack(anchor="w", pady=(0, 2))

        tk.Label(
            notice_card,
            text="The services listed below are sourced directly from your verified safety whitelist definitions (config.py). Disabling them prevents background telemetry and idle resource drain.",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=FONT_SMALL,
            justify="left",
            anchor="w",
        ).pack(fill=tk.X)

        # --- Services Table Frame ---
        table_container = tk.Frame(
            self,
            bg=BG_INPUT,
            highlightbackground=BORDER_COLOR,
            highlightthickness=1,
        )
        table_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        scrollbar = ttk.Scrollbar(table_container, orient="vertical")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Name", "ID", "Description", "Action")
        self.tree = ttk.Treeview(
            table_container,
            columns=columns,
            show="headings",
            height=8,
            selectmode="browse",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.tree.yview)

        headers = [
            ("Name", "Service Display Name", 240, "w"),
            ("ID", "Service ID", 150, "w"),
            ("Description", "Description", 390, "w"),
            ("Action", "Action", 120, "center"),
        ]
        for col, text, width, anchor in headers:
            self.tree.heading(col, text=text, anchor=anchor)
            self.tree.column(col, width=width, anchor=anchor)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Populate rows
        for svc_name in sorted(DISABLABLE_SERVICES):
            display_title, desc = SERVICE_METADATA.get(
                svc_name, (svc_name, "Whitelisted safe service from configuration.")
            )
            self.tree.insert(
                "",
                tk.END,
                values=(display_title, svc_name, desc, "Disable"),
                tags=(svc_name,),
            )

        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item_id = self.tree.identify_row(event.y)
            # Column #4 is Action
            if column == "#4" and item_id:
                values = self.tree.item(item_id, "values")
                if len(values) >= 2:
                    svc_id = values[1]
                    self.disable_service(svc_id, item_id)

    def disable_service(self, service_name: str, item_id: str):
        values = self.tree.item(item_id, "values")
        if values and values[3] in ("Disabled ✓", "Processing..."):
            return

        # Update table row status to Processing
        self.tree.item(item_id, values=(values[0], values[1], values[2], "Processing..."))

        def _worker():
            try:
                # 1. Stop service
                subprocess.run(
                    ["net", "stop", service_name, "/y"],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                )

                # 2. Configure start type to disabled
                result = subprocess.run(
                    ["sc", "config", service_name, "start=", "disabled"],
                    capture_output=True,
                    text=True,
                    creationflags=CREATE_NO_WINDOW,
                )

                if result.returncode == 0:
                    status_text = "Disabled ✓"
                else:
                    err = result.stderr.strip()
                    if "Access is denied" in err:
                        status_text = "Access Denied"
                    elif "1060" in err:
                        status_text = "Not Installed"
                    else:
                        status_text = "Failed"

                self.after(
                    0,
                    lambda st=status_text: self.tree.item(
                        item_id, values=(values[0], values[1], values[2], st)
                    ),
                )
            except Exception as e:
                print(f"Service Error ({service_name}): {e}")
                self.after(
                    0,
                    lambda: self.tree.item(
                        item_id, values=(values[0], values[1], values[2], "Error")
                    ),
                )

        threading.Thread(target=_worker, daemon=True).start()


# Compatibility alias for main.py dynamic routing
ServiceManagerTab = ServicesModule