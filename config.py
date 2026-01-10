import os  # Added missing import

# Service Configurations
ALLOWED_SERVICES = {
    "SysMain", "DiagTrack", "WSearch", "XblAuthManager", "XblGameSave",
    "XboxNetApiSvc", "Themes", "wuauserv", "fdPHost", "NcbService", "PcaSvc"
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

# --- App Uninstaller Whitelist ---
# Only apps containing these strings will be displayed in the Uninstaller
SAFE_APP_WHITELIST = [
    "Microsoft.BingNews",
    "Microsoft.BingWeather",
    "Microsoft.WindowsFeedbackHub",
    "Microsoft.GetHelp",
    "Microsoft.Getstarted",
    "Microsoft.Messaging",
    "Microsoft.MicrosoftSolitaireCollection",
    "Microsoft.People",
    "Microsoft.SkypeApp",
    "Microsoft.YourPhone",
    "Microsoft.ZuneVideo",
    "Microsoft.ZuneMusic",
    "Microsoft.WindowsAlarms",
    "Microsoft.WindowsMaps",
    "Microsoft.WindowsCamera",
    "Microsoft.WindowsSoundRecorder",
    "Microsoft.Office.OneNote",
    "Microsoft.XboxApp",
    "Microsoft.XboxGameOverlay",
    "Microsoft.XboxGamingOverlay",
    "Microsoft.XboxIdentityProvider",
    "Microsoft.XboxSpeechToTextOverlay",
    "Microsoft.GamingApp",
    "Microsoft.PowerAutomateDesktop",
    "Microsoft.Todos",
    "Microsoft.BingSearch",
]

# UI Colors
COLOR_RED = "#c42b1c"
COLOR_BLUE = "#1f6aa5"
COLOR_GREEN = "#00FF00"
COLOR_LIGHT_BLUE = "#1E90FF"