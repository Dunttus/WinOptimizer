import os  # Added missing import

# Service Configurations
DISABLABLE_SERVICES = {
    "SysMain", "DiagTrack", "PcaSvc", 
    "Fax", "MapsBroker", "RetailDemo", "TabletInputService"
}

CRITICAL_SERVICES = {
    "WinDefend", "RpcSs", "EventLog", "SamSs", "LSASS", "TrustedInstaller", "BITS", "Dhcp"
}

# Process & File Safety
CRITICAL_PROCESS_NAMES = {
    'System', 'System Idle Process', 'Registry', 'csrss.exe', 'wininit.exe',
    'services.exe', 'lsass.exe', 'winlogon.exe', 'smss.exe'
}

SAFE_TEMP_EXTENSIONS = {'.tmp', '.log', '.pf', '.dmp', '.old', '.etl', '.evtx'}

# Cleaner Configuration
SAFE_JUNK_EXTENSIONS = {
    '.tmp', '.temp', '.log', '.bak', '.old', '.dmp', '.chk', '.pf', '.error'
}

CLEANER_PATHS = [
    ("User Temp", os.environ.get('TEMP')),
    ("System Temp", r"C:\Windows\Temp"),
    ("Prefetch", r"C:\Windows\Prefetch"),
    ("Windows Update Cache", r"C:\Windows\SoftwareDistribution\Download"),
    ("Crash Dumps", r"C:\Windows\Minidump"),
    ("Error Reports", r"C:\ProgramData\Microsoft\Windows\WER"),
]

# Safe Apps Whitelist for Bloat Uninstaller (Includes Office 365 / M365 components & Bloatware)
SAFE_TO_REMOVE_APPS = [
    # Microsoft Office / 365 Components
    "Microsoft.MicrosoftOfficeHub",
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

# UI Colors
COLOR_RED = "#c42b1c"
COLOR_BLUE = "#1f6aa5"
COLOR_GREEN = "#00FF00"
COLOR_LIGHT_BLUE = "#1E90FF"