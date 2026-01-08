# ui_manager.py
import ctypes
import threading
import subprocess

class Win11UXManager:
    @staticmethod
    def send_notification(title, message):
        """Sends a native Windows 11 Toast Notification via PowerShell"""
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);
        $xml = $template.GetXml();
        $text = $template.GetElementsByTagName("text");
        $text[0].AppendChild($template.CreateTextNode("{title}")) > $null;
        $text[1].AppendChild($template.CreateTextNode("{message}")) > $null;
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template);
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Wibe Suite Utility");
        $notifier.Show($toast);
        """
        threading.Thread(target=lambda: subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW), daemon=True).start()

    @staticmethod
    def flash_taskbar(window_handle):
        """Flashes the taskbar icon to demand attention"""
        FLASHW_TRAY = 0x00000002
        FLASHW_TIMERNOFG = 0x0000000C
        
        class FLASHWINFO(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint),
                        ('hwnd', ctypes.c_void_p),
                        ('dwFlags', ctypes.c_uint),
                        ('uCount', ctypes.c_uint),
                        ('dwTimeout', ctypes.c_uint)]
        
        info = FLASHWINFO(
            cbSize=ctypes.sizeof(FLASHWINFO),
            hwnd=window_handle,
            dwFlags=FLASHW_TRAY | FLASHW_TIMERNOFG,
            uCount=3,
            dwTimeout=0
        )
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))