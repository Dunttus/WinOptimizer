# 🚀 Windows 11 Optimize - Wibe Suite

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**A modern, all-in-one system utility suite for Windows built with Python & CustomTkinter.**

WinOptimize 11 streamlines Windows maintenance by combining a powerful **Package Manager GUI**, **System Debloater**, and **Repair Tools** into a single, professional dark-mode interface.

---

## 🖥️ Feature Tabs Overview

### 1️⃣ Overview
<details open>
<summary><b>Dashboard</b></summary>
<br>
The central command center for your system.
<ul>
  <li><b>Live Monitoring:</b> Real-time circular gauges for <b>CPU</b>, <b>RAM</b>, and <b>Disk</b> usage.</li>
  <li><b>System Specs:</b> Instant view of Hostname, OS Build, GPU, and Uptime.</li>
  <li><b>Status:</b> Quick health check status at a glance.</li>
</ul>
</details>

### 2️⃣ Software Management
<details>
<summary><b>Package Manager</b> (WinGet GUI)</summary>
<br>
A fully-featured GUI for the Microsoft Winget CLI.
<ul>
  <li><b>Store Search:</b> Search and download apps from the public Microsoft repository.</li>
  <li><b>Smart Progress:</b> Clean, non-intrusive download progress updates (every 5%).</li>
  <li><b>Batch Updates:</b> "Update Winget Apps" button sequentially updates all your software (skipping self-updating processes).</li>
  <li><b>Precision Grid:</b> Professional UI identifying App IDs, Versions, and Install Sources.</li>
</ul>
</details>

<details>
<summary><b>Bloat Uninstaller</b></summary>
<br>
Remove pre-installed junk safely.
<ul>
  <li><b>Whitelist Protection:</b> Only targets known bloatware (Xbox, Weather, News, Solitaire, etc.).</li>
  <li><b>Safety First:</b> Prevents accidental removal of critical system components.</li>
</ul>
</details>

### 3️⃣ System Optimization
<details>
<summary><b>Privacy & Tweaks</b></summary>
<br>
Customize Windows behavior with simple toggles.
<ul>
  <li><b>Privacy:</b> Disable Telemetry and Bing Search results in Start Menu.</li>
  <li><b>UI Tweaks:</b> Restore "Classic" Context Menu (Win 11) and disable Lock Screen ads.</li>
</ul>
</details>

<details>
<summary><b>System Cleaner</b></summary>
<br>
Free up disk space by removing temporary junk.
<ul>
  <li><b>Deep Scan:</b> Cleans User Temp, System Temp, Prefetch, and Windows Update Cache.</li>
  <li><b>Smart Skip:</b> Automatically detects and skips locked files to prevent crashes.</li>
</ul>
</details>

<details>
<summary><b>File Scanner</b></summary>
<br>
Analyze your drive for clutter.
<ul>
  <li><b>Large Files:</b> Instantly find files larger than 100MB.</li>
  <li><b>Duplicate Finder:</b> Scans for duplicate files to recover wasted space.</li>
</ul>
</details>

<details>
<summary><b>Startup Manager</b></summary>
<br>
Improve Windows boot times.
<ul>
  <li><b>Registry Scan:</b> Detects startup entries in `HKCU` and `HKLM` hives.</li>
  <li><b>Delete Entries:</b> Remove persistent programs that slow down your login.</li>
</ul>
</details>

<details>
<summary><b>Service Manager</b></summary>
<br>
Optimize background services.
<ul>
  <li><b>Debloat Mode:</b> Disable Telemetry, DiagTrack, and SysMain (Superfetch).</li>
  <li><b>Protection:</b> Prevents disabling critical core services (Network, Audio, Defender).</li>
</ul>
</details>

<details>
<summary><b>Process Priority</b></summary>
<br>
Allocate resources to active apps.
<ul>
  <li><b>Boost Mode:</b> Force specific active applications (Games, IDEs) to "High Priority".</li>
  <li><b>Power Plan:</b> Toggle "Ultimate Performance" power plans directly.</li>
</ul>
</details>

### 4️⃣ Diagnostics & Repair
<details>
<summary><b>Network Tools</b></summary>
<br>
Fix connectivity issues instantly.
<ul>
  <li><b>One-Click Fixes:</b> Flush DNS, Renew IP, and Reset Winsock.</li>
  <li><b>Diagnostics:</b> Run Latency Pings and generate detailed HTML WLAN Reports.</li>
</ul>
</details>

<details>
<summary><b>Windows Repair</b></summary>
<br>
Fix corrupted Windows system files.
<ul>
  <li><b>SFC Scannow:</b> Runs the System File Checker to repair integrity violations.</li>
  <li><b>DISM Restore:</b> Uses the Deployment Image Servicing and Management tool to fix the system image.</li>
  <li><b>CHKDSK:</b> Schedules a Disk Check for the next system restart.</li>
</ul>
</details>

---

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Dunttus/WinOptimizer.git
    ```
    ```bash
    cd WinOptimize-Wibe-Suite
    ```

2.  **Install dependencies:**
    ```bash
    pip install customtkinter psutil pillow darkdetect
    ```

3.  **Run as Administrator:**
    * Right-click your terminal or IDE and select **"Run as Administrator"**.
    * Execute the main script:
    ```bash
    python main.py
    ```

---

## ⚠️ Safety Disclaimer

> [!WARNING]
> **This tool modifies Windows Registry keys and System Files.**

* **Administrator Rights:** Required for most features.
* **License Notice:** The Package Manager installs apps from public repositories. You must own a valid license for any paid software installed.
* **Liability:** Always create a **System Restore Point** before performing deep cleaning or mass uninstallations.

---

## 🤝 Credits

### 🧠 Project Team
* **Project Creator:** Dunttus
* **AI Assistance:** Partly Wibe Coded with Gemini

### 📚 Open Source Libraries
Powered by these amazing projects:
* **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern UI framework
* **[psutil](https://github.com/giampaolo/psutil)** - System & process monitoring
* **[Pillow](https://github.com/python-pillow/Pillow)** - Image processing
* **[DarkDetect](https://github.com/albertosottile/darkdetect)** - System theme integration

---

## 📄 License

This project is licensed under the **GPL-3.0 License**.