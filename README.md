# 🚀 Windows 11 Optimize - Wibe Suite

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**A modern, all-in-one system utility suite for Windows built with Python & CustomTkinter.**

WinOptimize 11 streamlines Windows maintenance by combining a powerful **Package Manager GUI**, **System Debloater**, and **Deep Hardware Diagnostics** into a single, professional interface.

---

## 🖥️ Feature Tabs Overview

### 1. OVERVIEW
<details open>
<summary><b>System Status & Health</b></summary>
<br>
<ul>
  <li><b>Dashboard:</b>
    <ul>
      <li><b>Resource Gauges:</b> Real-time circular dials for CPU, RAM, and Disk usage.</li>
      <li><b>Network Monitor:</b> Live graph and speed indicators for upload/download activity.</li>
      <li><b>Active Apps:</b> Tracks top bandwidth-consuming applications by session usage.</li>
      <li><b>System Info:</b> Displays detailed Windows build, accurate CPU model, and uptime.</li>
      <li><b>Registry Backup:</b> One-click safety tool to backup the `HKLM` hive.</li>
    </ul>
  </li>
  <li><b>Hardware Health:</b>
    <ul>
      <li><b>Battery:</b> Health %, cycle count, and official Windows Battery Report generation.</li>
      <li><b>Silicon:</b> Live CPU temperatures and RAM slot mapping.</li>
      <li><b>Storage:</b> S.M.A.R.T. data, drive temps, and life remaining percentages.</li>
    </ul>
  </li>
</ul>
</details>

### 2. SOFTWARE MANAGEMENT
<details>
<summary><b>Apps & Packages</b></summary>
<br>
<ul>
  <li><b>Package Manager:</b> A full GUI for <b>WinGet</b>. Search, install, and batch-update software from Microsoft's official repository.</li>
  <li><b>Bloat Uninstaller:</b> Scan for and remove pre-installed Windows junk apps using a safe whitelist system.</li>
</ul>
</details>

### 3. SYSTEM OPTIMIZATION
<details>
<summary><b>Performance & Maintenance</b></summary>
<br>
<ul>
  <li><b>Privacy & Tweaks:</b> One-click registry toggles (e.g., Disable Telemetry, Remove Bing Search, Classic Context Menu).</li>
  <li><b>System Cleaner:</b> deep cleaning tools for temporary files, cache, and system junk.</li>
  <li><b>File Scanner:</b> Analyze disk usage and identify large files taking up space.</li>
  <li><b>Startup Manager:</b> View and disable applications that launch automatically at boot to improve startup speed.</li>
  <li><b>Service Manager:</b> Manage Windows background services to free up resources.</li>
  <li><b>Process Priority:</b> Real-time management of process CPU priorities to boost foreground apps.</li>
</ul>
</details>

### 4. DIAGNOSTICS & REPAIR
<details>
<summary><b>Troubleshooting</b></summary>
<br>
<ul>
  <li><b>Network Tools:</b> Utilities for connectivity testing, DNS flushing, and IP configuration.</li>
  <li><b>Windows Repair:</b> Automated execution of Windows troubleshooting commands (DISM Check/Scan/Restore and SFC Scannow) to fix corrupted system files.</li>
</ul>
</details>

---

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Dunttus/WinOptimizer.git
    cd WinOptimizer
    ```
    ```bash
    cd WinOptimizer
    ```

2.  **Install dependencies:**
    ```bash
    winget install Python.Python.3.14
    ```
    ```bash
    pip install customtkinter psutil pillow
    ```

3.  **Run as Administrator:**
    * Right-click your terminal or IDE and select **"Run as Administrator"**.
    * Execute the main script:
    ```bash
    python.exe main.py
    ```

---

## ⚠️ Safety Disclaimer

> [!WARNING]
> **This tool modifies Windows Registry keys and Hardware Settings.**
* **Administrator Rights:** Required for most features.
* **License Notice:** The Package Manager installs apps from public repositories. You must own a valid license for any paid software installed.
* **Liability:** Always create a **System Restore Point** before performing deep cleaning or mass uninstallations.

---

## 🤝 Credits

### 🧠 Project Team
* **Project Creator:** Dunttus
* **AI Assistance:** Partly vibe coded with Gemini

### 📚 Open Source Libraries
* **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern UI framework
* **[psutil](https://github.com/giampaolo/psutil)** - System monitoring
* **[Pillow](https://github.com/python-pillow/Pillow)** - Image processing

---

## 📄 License


This project is licensed under the **GPL-3.0 License**.