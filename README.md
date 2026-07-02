![ico](app.ico)

# 🚀 TikTok & Douyin Downloader (Windows GUI & Linux CLI)

<p align="center">
    <a href="https://linux.do" alt="LINUX DO">
        <img
            src="https://img.shields.io/badge/LINUX-DO-FFB003.svg?logo=data:image/svg%2bxml;base64,DQo8c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiPjxwYXRoIGQ9Ik00Ni44Mi0uMDU1aDYuMjVxMjMuOTY5IDIuMDYyIDM4IDIxLjQyNmM1LjI1OCA3LjY3NiA4LjIxNSAxNi4xNTYgOC44NzUgMjUuNDV2Ni4yNXEtMi4wNjQgMjMuOTY4LTIxLjQzIDM4LTExLjUxMiA3Ljg4NS0yNS40NDUgOC44NzRoLTYuMjVxLTIzLjk3LTIuMDY0LTM4LjAwNC0yMS40M1EuOTcxIDY3LjA1Ni0uMDU0IDUzLjE4di02LjQ3M0MxLjM2MiAzMC43ODEgOC41MDMgMTguMTQ4IDIxLjM3IDguODE3IDI5LjA0NyAzLjU2MiAzNy41MjcuNjA0IDQ2LjgyMS0uMDU2IiBzdHlsZT0ic3Ryb2tlOm5vbmU7ZmlsbC1ydWxlOmV2ZW5vZGQ7ZmlsbDojZWNlY2VjO2ZpbGwtb3BhY2l0eToxIi8+PHBhdGggZD0iTTQ3LjI2NiAyLjk1N3EyMi41My0uNjUgMzcuNzc3IDE1LjczOGE0OS43IDQ5LjcgMCAwIDEgNi44NjcgMTAuMTU3cS00MS45NjQuMjIyLTgzLjkzIDAgOS43NS0xOC42MTYgMzAuMDI0LTI0LjM4N2E2MSA2MSAwIDAgMSA5LjI2Mi0xLjUwOCIgc3R5bGU9InN0cm9rZTpub25lO2ZpbGwtcnVsZTpldmVub2RkO2ZpbGw6IzE5MTkxOTtmaWxsLW9wYWNpdHk6MSIvPjxwYXRoIGQ9Ik03Ljk4IDcwLjkyNmMyNy45NzctLjAzNSA1NS45NTQgMCA4My45My4xMTNRODMuNDI2IDg3LjQ3MyA2Ni4xMyA5NC4wODZxLTE4LjgxIDYuNTQ0LTM2LjgzMi0xLjg5OC0xNC4yMDMtNy4wOS0yMS4zMTctMjEuMjYyIiBzdHlsZT0ic3Ryb2tlOm5vbmU7ZmlsbC1ydWxlOmV2ZW5vZGQ7ZmlsbDojZjlhZjAwO2ZpbGwtb3BhY2l0eToxIi8+PC9zdmc+" /></a>
</p>

[![Release](https://img.shields.io/github/v/release/Xynrin/tiktok-douyin-dl?color=brightgreen&logo=github&style=flat-square)](https://github.com/Xynrin/tiktok-douyin-dl/releases)
[![License](https://img.shields.io/github/license/Xynrin/tiktok-douyin-dl?color=blue&style=flat-square)](LICENSE)



A powerful cross-platform tool suite for downloading TikTok and Douyin videos/photos without watermarks. 
Available as a **Modern Windows GUI app** with one-click installation, and an **Independent Linux CLI tool**. **Zero environment dependencies** (built-in Python, Playwright, and drivers).

---

🌐 **[English]** | **[简体中文](README_zh.md)**

---

## ✨ v1.4+ New Features
* 🎨 **Modern UI Design**: Windows 11 Fluent Design (Dark Mode) with a minimalist interface and **seamless language switching (EN/ZH)**.
* 🌐 **NAS & Docker WebUI**: Deploy a web interface on NAS systems like FeiNiu OS (fnos) via Docker, enabling downloads from any device on the network without a client.
* 📁 **Smart Archive Management**: Automatically extracts the creator's username and groups downloaded videos and images into dedicated author folders.
* 🔄 **Silent Auto-Update**: Checks GitHub for updates on startup and performs seamless one-click background updates.
* 📦 **Standardized Installer**: Provides a standard Windows `Setup.exe` with desktop shortcuts and a robust uninstaller that leaves no trace.
* 🛡️ **Stealth Mode (Anti-Fingerprint)**: Uses advanced WebDriver evasion techniques to bypass platform bot detection and avoid IP bans.

## 📥 Download & Install

### 💻 Windows Users (GUI Recommended)
1. Go to the [Releases Page](https://github.com/Xynrin/tiktok-douyin-dl/releases/latest).
2. Download `MediaDownloader_Setup.exe` and install it.
3. *Language Switch:* Click the "🌐 Language / 语言" button in the app to switch languages and restart instantly.
4. *Optional:* Download the standalone `douyin-dl.exe` or `tiktok-dl.exe` if you prefer the CLI.

### 🐳 NAS Users (FeiNiu OS / Docker WebUI)
If you have a NAS device, create a Custom App (Docker Compose) and paste the following configuration:
```yaml
version: '3.8'
services:
  mediadownloader:
    build: https://github.com/Xynrin/tiktok-douyin-dl.git#main
    container_name: mediadownloader-webui
    restart: unless-stopped
    ports:
      - "7860:7860"
    volumes:
      - /vol1/downloads:/downloads   # Change the left side to your NAS download path
```
Deploy it and access `http://<NAS_IP>:7860` in your browser!

### 🐧 Linux Users (CLI)
Run the following command in your terminal to automatically install the latest Linux binaries to `~/.local/bin`:

```bash
curl -fsSL "https://raw.githubusercontent.com/Xynrin/tiktok-douyin-dl/main/install.sh?v=$(date +%s)" | bash
```

> **Note:** The install script looks for Linux binaries in the latest release. Make sure the Linux binaries (`douyin-dl` / `tiktok-dl`) are uploaded to the latest release.

---

## 🚀 Usage

### Windows GUI
Simply open **MediaDownloader** from your desktop, paste the share text/links, choose the platform (Douyin/TikTok), and click "Start Download".

### CLI Usage (Linux & Windows CMD)
```bash
douyin-dl "Share text or link" [output_directory]
tiktok-dl "Share text or link" [output_directory]
```

## ⚖️ Disclaimer
By downloading or using this software, you agree that it is strictly for educational, academic, and web-testing purposes. Commercial use or illegal scraping is strictly prohibited. You are solely responsible for any copyright or legal disputes arising from its use.
