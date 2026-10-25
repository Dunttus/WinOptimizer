# The ultimate open-source PC optimization and maintenance toolkit for Windows 10/11

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**A modern, all-in-one system utility suite for Windows built with Python & native Tkinter.**

Modern, lightweight, all-in-one system utility and PC optimization suite for Windows 10 and 11, built using **Python** and native **Tkinter**. 

Streamline your system maintenance by combining a powerful **WinGet GUI Package Manager**, a safe **Windows Bloatware Uninstaller**, real-time **Hardware Telemetry Diagnostics**, and advanced **Performance Tweaks** into a single, professional interface—no heavy frameworks or bloated background services required.

---

## 🖥️ Feature Tabs Overview

<details>
<summary><b>1. Dashboard</b></summary>
<br>
<ul>
  <li><b>Resource Gauges:</b> Real-time circular resource dials for CPU, GPU, RAM speed/load, and Storage.</li>
  <li><b>Network Monitor:</b> Live upload and download speed indicators.</li>
  <li><b>Top Processes:</b> Aggregated real-time process monitoring for CPU, RAM, and Disk I/O.</li>
</ul>
</details>

<details>
<summary><b>2. Package Manager</b></summary>
<br>
<ul>
  <li><b>WinGet GUI:</b> Search, install, uninstall, and batch-update software directly from Microsoft's official repository, or batch-install preset apps from <code>config.py</code>.</li>
</ul>
</details>

<details>
<summary><b>3. Bloat Uninstaller</b></summary>
<br>
<ul>
  <li><b>App Removal:</b> Scan for and batch-remove pre-installed Windows bloatware and Office components using a configurable safe whitelist (<code>SAFE_TO_REMOVE_APPS</code>).</li>
</ul>
</details>

<details>
<summary><b>4. Privacy & Tweaks</b></summary>
<br>
<ul>
  <li><b>Registry Toggles:</b> One-click sliding switches to enhance privacy, disable telemetry/Copilot/Bing search, restore the classic Windows 11 context menu, and configure system UI preferences.</li>
</ul>
</details>

<details>
<summary><b>5. System Cleaner</b></summary>
<br>
<ul>
  <li><b>Maintenance:</b> Deep cleaning tools with category selection and safe file extension filtering (<code>SAFE_JUNK_EXTENSIONS</code>) for temporary files, system cache, prefetch, and junk data.</li>
</ul>
</details>

<details>
<summary><b>6. File Scanner</b></summary>
<br>
<ul>
  <li><b>Disk Analysis:</b> Analyze storage usage, find duplicate files with extension filters, and identify large files (>100 MB) taking up space.</li>
</ul>
</details>

<details>
<summary><b>7. Startup Manager</b></summary>
<br>
<ul>
  <li><b>Boot Optimization:</b> View and remove applications that launch automatically at boot across Registry <code>Run</code> keys and Windows Startup folders to improve startup speed.</li>
</ul>
</details>

<details>
<summary><b>8. Service Manager</b></summary>
<br>
<ul>
  <li><b>Background Services:</b> Manage and safely disable unnecessary Windows background services using the verified <code>DISABLABLE_SERVICES</code> whitelist to free up resources.</li>
</ul>
</details>

<details>
<summary><b>9. Process Priority</b></summary>
<br>
<ul>
  <li><b>CPU Allocation:</b> Real-time management of process CPU priorities to optimize active foreground applications, with automatic lockout protection for critical Windows system processes (<code>CRITICAL_PROCESS_NAMES</code>).</li>
</ul>
</details>

<details>
<summary><b>10. Network Tools</b></summary>
<br>
<ul>
  <li><b>Diagnostics:</b> Utilities for connectivity testing, DNS flushing, IP renewal, Winsock resets, and WLAN report generation.</li>
</ul>
</details>

<details>
<summary><b>11. Windows Repair</b></summary>
<br>
<ul>
  <li><b>System Repair:</b> Automated execution of built-in Windows troubleshooting commands (SFC scans, DISM health checks/repairs, and Check Disk scheduling) to fix corrupted system files.</li>
</ul>
</details>

<details>
<summary><b>12. Power Settings</b></summary>
<br>
<ul>
  <li><b>Power Management:</b> Switch active power plans, configure screen-off and sleep timeouts for battery and AC power, and generate HTML battery health reports.</li>
</ul>
</details>

---

## ⚙️ Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Dunttus/WinOptimizer.git](https://github.com/Dunttus/WinOptimizer.git)
   cd WinOptimizer
   ```

2. **Install dependencies:**
   ```bash
   winget install Python.Python.3.14
   ```
   ```bash
   pip install psutil
   ```

3. **Run as Administrator:**
   * Launch the main script (automatically prompts for Windows UAC **Administrator** elevation on startup):
   ```bash
   python.exe main.py
   ```

---

## ⚠️ Safety Disclaimer

> [!WARNING]
> **This tool modifies Windows Registry keys and Hardware Settings.**
- **Administrator Rights:** Required for most features.
- **License Notice:** The Package Manager installs apps from public repositories. You must own a valid license for any paid software installed.
- **Liability:** Always create a **System Restore Point** before performing deep cleaning or mass uninstallations.

---

## 🤝 Credits

### 🧠 Project Team
- **Project Creator:** Dunttus
- **AI Assistance:** Partly vibe coded with Gemini 4 Argon

### 📚 Open Source Libraries
- **[psutil](https://github.com/giampaolo/psutil)** - System monitoring

---

## 📄 License

This project is licensed under the **GPL-3.0 License**.