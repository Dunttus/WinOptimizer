# 🚀 Windows 11 Optimize - Wibe Suite

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows_10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**A modern, all-in-one system utility suite for Windows built with Python & CustomTkinter.**

WinOptimize 11 streamlines Windows maintenance by combining a powerful **Package Manager GUI**, **System Debloater**, and **Deep Hardware Diagnostics** into a single, professional interface.

---

## 🖥️ Feature Tabs Overview

### 1. Overview
<details open>
<summary><b>Dashboard & Hardware Health</b></summary>
<br>
The central command center for system monitoring and physical health.
<ul>
  <li><b>Dashboard:</b> Real-time circular gauges for CPU, RAM, and Disk usage with live system specs.</li>
  <li><b>Hardware Health:</b> A dedicated diagnostic suite with <b>asynchronous loading</b> to prevent UI freezing.
    <ul>
      <li><b>Battery Health:</b> Estimated health percentage, cycle counts, and a one-click <b>Official Windows Battery Report</b> generator that prompts to open immediately upon completion.</li>
      <li><b>Silicon & Memory:</b> Live CPU temperatures (using °C) and detailed <b>RAM Slot Mapping</b> showing Manufacturer, Speed, and Capacity per slot.</li>
      <li><b>Storage Reliability:</b> Deep S.M.A.R.T. data including drive temperature, <b>Life Remaining %</b>, and physical Read/Write error tracking.</li>
    </ul>
  </li>
</ul>
</details>



### 2. Software Management
<details>
<summary><b>Package Manager & Bloat Uninstaller</b></summary>
<br>
Efficiently manage your applications.
<ul>
  <li><b>WinGet GUI:</b> Search, install, and batch-update software from the Microsoft repository.</li>
  <li><b>Bloat Uninstaller:</b> Whitelist-protected removal of pre-installed Windows junk.</li>
</ul>
</details>

### 3. System Optimization
<details>
<summary><b>Privacy & Tweaks</b></summary>
<br>
Customize Windows behavior with simple toggles.
<ul>
  <li><b>Privacy:</b> Disable Telemetry, Advertising ID, and Bing Search.</li>
  <li><b>Performance:</b> One-click high-priority process boosting and deep system cleaning tools for temp files.</li>
</ul>
</details>

---

## 🎨 UI & Performance Highlights

* **Boxed Navigation Sidebar:** A modern, scrollable sidebar that groups tools into logical categories (Overview, Software, Optimization, Repair) using distinct visual frames.
* **Asynchronous Logic:** Heavy PowerShell and WMI hardware queries run in background threads, ensuring the app remains fully responsive while gathering data.
* **Persistent Action Footer:** The Hardware Health tab features a "Refresh" button docked to the bottom corner, allowing for instant data updates without losing your scroll position.
* **Zero-Emoji Backend:** Clean internal code structure to ensure maximum compatibility across different Python environments.

---

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Dunttus/WinOptimizer.git](https://github.com/Dunttus/WinOptimizer.git)
    cd WinOptimizer
    ```

2.  **Install dependencies:**
    ```bash
    pip install customtkinter psutil pillow
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
> **This tool modifies Windows Registry keys and Hardware Settings.**

Accuracy of hardware diagnostics (S.M.A.R.T. and Thermal zones) depends on manufacturer driver support. Always use the **Registry Backup** feature before applying deep system tweaks.

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