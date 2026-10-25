import os
import tempfile
import tkinter as tk
from tkinter import ttk

# ==============================================================================
# UI THEME & DESIGN TOKENS (Wibe Suite Dark Theme)
# ==============================================================================
THEME = {
    # Backgrounds
    "bg_main": "#18181b",        # Primary content area background
    "bg_sidebar": "#121215",     # Sidebar background
    "bg_card": "#222227",        # Elevated cards / panels
    "bg_card_hover": "#2a2a30",  # Card hover / secondary surface
    "bg_input": "#141417",       # Text entries, logs, treeviews, consoles
    "bg_active": "#2e2e36",      # Active navigation button background
    
    # Borders & Dividers
    "border": "#2e2e36",         # Subtle card/section border
    "border_focus": "#3b82f6",   # Active input border
    
    # Typography Colors
    "fg_primary": "#f4f4f6",     # Main headings and primary text
    "fg_secondary": "#a1a1aa",   # Subtitles, labels, descriptions
    "fg_muted": "#63636e",       # Disabled / placeholder text
    
    # Accents & Semantic Colors
    "accent": "#2563eb",         # Primary action blue
    "accent_hover": "#1d4ed8",   # Primary action hover
    "info": "#38bdf8",           # Light blue informational highlight
    "success": "#10b981",        # Emerald green (safe / active / done)
    "success_hover": "#059669",
    "warning": "#f59e0b",        # Amber warning
    "warning_hover": "#d97706",
    "danger": "#ef4444",         # Red destructive / critical action
    "danger_hover": "#dc2626",
}

# Flat exports for convenient imports inside modules
BG_MAIN = THEME["bg_main"]
BG_SIDEBAR = THEME["bg_sidebar"]
BG_CARD = THEME["bg_card"]
BG_CARD_HOVER = THEME["bg_card_hover"]
BG_INPUT = THEME["bg_input"]
BORDER_COLOR = THEME["border"]

FG_PRIMARY = THEME["fg_primary"]
FG_SECONDARY = THEME["fg_secondary"]
FG_MUTED = THEME["fg_muted"]

# Backward-compatible color constants (used by existing modules)
COLOR_RED = THEME["danger"]
COLOR_BLUE = THEME["accent"]
COLOR_GREEN = THEME["success"]
COLOR_LIGHT_BLUE = THEME["info"]
COLOR_WARNING = THEME["warning"]

# Standard Typography
FONT_FAMILY = "Segoe UI"
FONT_MONO_FAMILY = "Consolas"

FONT_TITLE = (FONT_FAMILY, 16, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 10)
FONT_SECTION = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_SMALL = (FONT_FAMILY, 9)
FONT_MONO = (FONT_MONO_FAMILY, 10)


def apply_global_ttk_style(root: tk.Misc):
    """Applies a consistent dark theme to all standard ttk widgets across modules."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # General Frame & Label defaults
    style.configure("TFrame", background=BG_MAIN)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("TLabel", background=BG_MAIN, foreground=FG_PRIMARY, font=FONT_BODY)

    # Treeview (Tables used in Processes, Services, Startup, Scanner, etc.)
    style.configure(
        "Treeview",
        background=BG_INPUT,
        foreground=FG_PRIMARY,
        fieldbackground=BG_INPUT,
        borderwidth=0,
        rowheight=28,
        font=FONT_BODY,
    )
    style.configure(
        "Treeview.Heading",
        background=BG_CARD,
        foreground=FG_PRIMARY,
        relief="flat",
        font=FONT_BOLD,
        padding=(8, 6),
    )
    style.map(
        "Treeview",
        background=[("selected", THEME["accent"])],
        foreground=[("selected", "#ffffff")],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", BG_CARD_HOVER)],
    )

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=BG_CARD,
        troughcolor=BG_INPUT,
        bordercolor=BG_INPUT,
        arrowcolor=FG_SECONDARY,
        relief="flat",
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", THEME["bg_active"])],
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=BG_CARD,
        troughcolor=BG_INPUT,
        bordercolor=BG_INPUT,
        arrowcolor=FG_SECONDARY,
        relief="flat",
    )

    # Progressbar
    style.configure(
        "TProgressbar",
        troughcolor=BG_INPUT,
        background=THEME["accent"],
        bordercolor=BG_INPUT,
        lightcolor=THEME["accent"],
        darkcolor=THEME["accent"],
        thickness=10,
    )
    style.configure(
        "Success.Horizontal.TProgressbar",
        troughcolor=BG_INPUT,
        background=THEME["success"],
        thickness=10,
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=BG_INPUT,
        background=BG_CARD,
        foreground=FG_PRIMARY,
        arrowcolor=FG_PRIMARY,
        bordercolor=BORDER_COLOR,
        lightcolor=BG_CARD,
        darkcolor=BG_CARD,
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", BG_INPUT)],
        selectbackground=[("readonly", THEME["accent"])],
        selectforeground=[("readonly", "#ffffff")],
    )

    # Notebook (Tabs)
    style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=BG_CARD,
        foreground=FG_SECONDARY,
        padding=(14, 7),
        font=FONT_BOLD,
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", THEME["accent"]), ("active", BG_CARD_HOVER)],
        foreground=[("selected", "#ffffff"), ("active", FG_PRIMARY)],
    )


# ==============================================================================
# REUSABLE UI HELPER BUILDERS (Optional helpers for the 12 modules)
# ==============================================================================
def create_header(parent, title: str, subtitle: str = "") -> tk.Frame:
    """Creates a standardized top header block for any module tab."""
    header = tk.Frame(parent, bg=BG_MAIN)
    header.pack(fill=tk.X, padx=24, pady=(20, 12))

    tk.Label(
        header, text=title, fg=FG_PRIMARY, bg=BG_MAIN, font=FONT_TITLE
    ).pack(anchor="w")

    if subtitle:
        tk.Label(
            header, text=subtitle, fg=FG_SECONDARY, bg=BG_MAIN, font=FONT_SUBTITLE
        ).pack(anchor="w", pady=(2, 0))

    return header


def create_button(parent, text: str, command=None, variant: str = "primary", **kwargs) -> tk.Button:
    """Creates a styled flat button with hover effects.
    Variants: 'primary', 'success', 'danger', 'warning', 'secondary'
    """
    palette = {
        "primary": (THEME["accent"], THEME["accent_hover"], "#ffffff"),
        "success": (THEME["success"], THEME["success_hover"], "#ffffff"),
        "danger": (THEME["danger"], THEME["danger_hover"], "#ffffff"),
        "warning": (THEME["warning"], THEME["warning_hover"], "#121215"),
        "secondary": (BG_CARD_HOVER, THEME["bg_active"], FG_PRIMARY),
    }
    bg_col, hover_col, fg_col = palette.get(variant, palette["primary"])

    defaults = {
        "bg": bg_col,
        "fg": fg_col,
        "activebackground": hover_col,
        "activeforeground": fg_col,
        "font": FONT_BOLD,
        "bd": 0,
        "relief": "flat",
        "padx": 14,
        "pady": 7,
        "cursor": "hand2",
    }
    defaults.update(kwargs)

    btn = tk.Button(parent, text=text, command=command, **defaults)
    btn.bind("<Enter>", lambda _e: btn.cget("state") != "disabled" and btn.config(bg=hover_col))
    btn.bind("<Leave>", lambda _e: btn.cget("state") != "disabled" and btn.config(bg=bg_col))
    return btn


# ==============================================================================
# TOOLKIT DATA & SAFETY LISTS
# ==============================================================================
# WinGet Preset Apps for Batch Installation
PRESET_APPS = [
    "Discord.Discord",
    "Git.Git",
    "VideoLAN.VLC",
    "Valve.Steam",
    "Microsoft.PowerToys",
    "Obsidian.Obsidian",
    "DominikReichl.KeePass",
    "Mozilla.Firefox",
    "Google.Chrome",
    "ExpressVPN.ExpressVPN",
    "Logitech.GHUB",
    "Brave.Brave",
]

# Service Configurations
DISABLABLE_SERVICES = {
    "SysMain", "DiagTrack", "PcaSvc",
    "Fax", "MapsBroker", "RetailDemo", "TabletInputService",
}

CRITICAL_SERVICES = {
    "WinDefend", "RpcSs", "EventLog", "SamSs",
    "LSASS", "TrustedInstaller", "BITS", "Dhcp",
}

# Process & File Safety
CRITICAL_PROCESS_NAMES = {
    "System", "System Idle Process", "Registry", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "winlogon.exe", "smss.exe",
}

SAFE_TEMP_EXTENSIONS = {".tmp", ".log", ".pf", ".dmp", ".old", ".etl", ".evtx"}

# Cleaner Configuration
SAFE_JUNK_EXTENSIONS = {
    ".tmp", ".temp", ".log", ".bak", ".old", ".dmp", ".chk", ".pf", ".error",
}

# (Removed Windows Update Cache to prevent update corruption / error 0x80070002)
CLEANER_PATHS = [
    ("User Temp", os.environ.get("TEMP") or tempfile.gettempdir()),
    ("System Temp", r"C:\Windows\Temp"),
    ("Prefetch", r"C:\Windows\Prefetch"),
    ("Crash Dumps", r"C:\Windows\Minidump"),
    ("Error Reports", r"C:\ProgramData\Microsoft\Windows\WER"),
]

# Safe Apps Whitelist for Bloat Uninstaller (Office Hub removed to protect Office 365 licensing portal)
SAFE_TO_REMOVE_APPS = [
    # Microsoft Office / 365 Components (Excluding OfficeHub)
    "Microsoft.Office.Word",
    "Microsoft.Office.Excel",
    "Microsoft.Office.PowerPoint",
    "Microsoft.Office.Outlook",
    "Microsoft.Office.OneNote",

    # News, Weather & Feed
    "Microsoft.BingNews",
    "Microsoft.BingWeather",
    "Microsoft.BingSearch",

    # Feedback & Help
    "Microsoft.WindowsFeedbackHub",
    "Microsoft.GetHelp",
    "Microsoft.Getstarted",

    # Communication & Utilities
    "Microsoft.Messaging",
    "Microsoft.SkypeApp",
    "Microsoft.YourPhone",
    "Microsoft.People",
    "Microsoft.WindowsAlarms",
    "Microsoft.WindowsMaps",
    "Microsoft.WindowsCamera",
    "Microsoft.WindowsSoundRecorder",
    "Microsoft.Todos",
    "Microsoft.PowerAutomateDesktop",
    "Microsoft.Clipchamp",
    "Microsoft.Teams",

    # Media & Gaming
    "Microsoft.MicrosoftSolitaireCollection",
    "Microsoft.ZuneVideo",
    "Microsoft.ZuneMusic",
    "Microsoft.XboxApp",
    "Microsoft.XboxGameOverlay",
    "Microsoft.XboxGamingOverlay",
    "Microsoft.XboxIdentityProvider",
    "Microsoft.XboxSpeechToTextOverlay",
    "Microsoft.GamingApp",
]