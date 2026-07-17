<p align="center">
  <img src="app.ico" alt="MediaDownloader 图标" width="128" height="128">
</p>

<h1 align="center">🚀 TikTok &amp; 抖音无水印下载器</h1>
<p align="center"><strong>Windows · iOS · Docker · Linux</strong></p>

<p align="center">
    <a href="https://linux.do" alt="LINUX DO">
        <img
            src="https://img.shields.io/badge/LINUX-DO-FFB003.svg?logo=data:image/svg%2bxml;base64,DQo8c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiPjxwYXRoIGQ9Ik00Ni44Mi0uMDU1aDYuMjVxMjMuOTY5IDIuMDYyIDM4IDIxLjQyNmM1LjI1OCA3LjY3NiA4LjIxNSAxNi4xNTYgOC44NzUgMjUuNDV2Ni4yNXEtMi4wNjQgMjMuOTY4LTIxLjQzIDM4LTExLjUxMiA3Ljg4NS0yNS40NDUgOC44NzRoLTYuMjVxLTIzLjk3LTIuMDY0LTM4LjAwNC0yMS40M1EuOTcxIDY3LjA1Ni0uMDU0IDUzLjE4di02LjQ3M0MxLjM2MiAzMC43ODEgOC41MDMgMTguMTQ4IDIxLjM3IDguODE3IDI5LjA0NyAzLjU2MiAzNy41MjcuNjA0IDQ2LjgyMS0uMDU2IiBzdHlsZT0ic3Ryb2tlOm5vbmU7ZmlsbC1ydWxlOmV2ZW5vZGQ7ZmlsbDojZWNlY2VjO2ZpbGwtb3BhY2l0eToxIi8+PHBhdGggZD0iTTQ3LjI2NiAyLjk1N3EyMi41My0uNjUgMzcuNzc3IDE1LjczOGE0OS43IDQ5LjcgMCAwIDEgNi44NjcgMTAuMTU3cS00MS45NjQuMjIyLTgzLjkzIDAgOS43NS0xOC42MTYgMzAuMDI0LTI0LjM4N2E2MSA2MSAwIDAgMSA5LjI2Mi0xLjUwOCIgc3R5bGU9InN0cm9rZTpub25lO2ZpbGwtcnVsZTpldmVub2RkO2ZpbGw6IzE5MTkxOTtmaWxsLW9wYWNpdHk6MSIvPjxwYXRoIGQ9Ik03Ljk4IDcwLjkyNmMyNy45NzctLjAzNSA1NS45NTQgMCA4My45My4xMTNRODMuNDI2IDg3LjQ3MyA2Ni4xMyA5NC4wODZxLTE4LjgxIDYuNTQ0LTM2LjgzMi0xLjg5OC0xNC4yMDMtNy4wOS0yMS4zMTctMjEuMjYyIiBzdHlsZT0ic3Ryb2tlOm5vbmU7ZmlsbC1ydWxlOmV2ZW5vZGQ7ZmlsbDojZjlhZjAwO2ZpbGwtb3BhY2l0eToxIi8+PC9zdmc+" /></a>
</p>

<p align="center">
  <a href="https://github.com/Xynrin/tiktok-douyin-dl/releases/tag/v1.6.4"><img src="https://img.shields.io/badge/release-v1.6.4-brightgreen?logo=github&amp;style=flat-square" alt="桌面版 v1.6.4"></a>
  <a href="https://github.com/Xynrin/tiktok-douyin-dl/releases/tag/ios-v1.0.2"><img src="https://img.shields.io/badge/iOS-v1.0.2-007AFF?logo=apple&amp;style=flat-square" alt="iOS v1.0.2"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Xynrin/tiktok-douyin-dl?color=blue&amp;style=flat-square" alt="License"></a>
</p>

一款跨平台的高效工具套件，用于下载 TikTok 和抖音无水印视频及图文作品。项目提供 **现代化 Windows 桌面客户端**、**原生 SwiftUI iOS App**、适合 NAS 的 **实验性 Docker WebUI**，以及 **Linux 独立命令行工具**。

打包后的桌面程序已包含所需运行环境与浏览器组件；iOS 客户端可在设备本地解析支持的分享页面并下载媒体，不依赖 Python 服务或 Docker WebUI。

---

🌐 **[English](README.md)** | **[简体中文]**

---

## 🖼️ 界面预览

<table width="100%">
  <tr>
    <th align="center" width="33%">新建下载</th>
    <th align="center" width="33%">本地文件管理</th>
    <th align="center" width="33%">照片与 iCloud 设置</th>
  </tr>
  <tr>
    <td align="center"><img src="ios/image/ios-new-download.png" alt="iOS 新建下载" width="280"></td>
    <td align="center"><img src="ios/image/ios-local-files.png" alt="iOS 本地文件管理" width="280"></td>
    <td align="center"><img src="ios/image/ios-settings.png" alt="iOS 照片与 iCloud 设置" width="280"></td>
  </tr>
</table>

<table width="100%">
  <tr>
    <th align="center">Windows 图形界面</th>
  </tr>
  <tr>
    <td align="center"><img src="image/windows-gui.png" alt="Windows 图形界面" width="900"></td>
  </tr>
</table>

## ✨ 功能亮点

* 🎨 **现代化 UI 设计**：全新引入 Windows 11 Fluent 风格的暗黑模式极简界面，并**新增了跨语言无缝切换 (中/英)**。
* 📱 **原生 iOS App**：直接在设备上解析支持的抖音/TikTok 分享链接，下载无水印视频和图文作品，并通过原生 SwiftUI 界面管理本地文件。
* ☁️ **可选的 iOS 多位置保存**：默认保留 App 本地文件；按需将支持的媒体额外保存到系统相册，并镜像到用户选择的 iCloud Drive 文件夹。
* 🧪 **实验性 Docker WebUI**：提供适用于飞牛 OS (fnos) 等 NAS 环境的参考部署方式，但当前 Docker 方案尚未由维护者完成充分测试。
* 📁 **自动构建专属档案库**：下载内容不再杂乱无章！智能提取视频作者名，自动为你建立“作者专属文件夹”归档图文和视频。
* 🔄 **静默智能热更新**：启动时自动比对 GitHub 版本，支持一键无感覆盖更新。
* 📦 **规范化安装包**：提供标准的 Windows `Setup.exe`，包含自动安装、桌面快捷方式生成以及“不留痕迹”的暴力卸载。
* 🛡️ **终极风控伪装 (Stealth Mode)**：底层引入了最强防检测注入代码，隐匿 WebDriver 痕迹，最大程度防止下载时被官方风控。

## 📥 下载与安装

### 💻 Windows 用户 (图形界面推荐)
1. 打开 [v1.6.4 桌面版发布页](https://github.com/Xynrin/tiktok-douyin-dl/releases/tag/v1.6.4)（iOS 版本使用独立的 `ios-v*` 标签）。
2. 下载 `MediaDownloader_Setup.exe`，双击安装即可（内置中文向导与免责声明）。
3. *语言切换：* 安装后在主界面点击“🌐 Language / 语言”即可一键重启切换。
4. *可选：* 如果你偏好命令行，也可以在同页面直接下载 `douyin-dl.exe` 或 `tiktok-dl.exe`。

### 📱 iOS 客户端

原生 SwiftUI 客户端位于 [`ios/MediaDownloader.xcodeproj`](ios/MediaDownloader.xcodeproj)，最低支持 iOS 17，现已支持：

- 直接在设备上解析支持的抖音和 TikTok 分享链接。
- 下载无水印视频和多图作品。
- 在 **文件 > 我的 iPhone/iPad > MediaDownloader** 中预览、分享和删除本地文件。
- 按需将支持的媒体额外保存到系统相册，并镜像到选定的 iCloud Drive 文件夹。
- 检测使用 `ios-v*` 标签发布的稳定 GitHub Release。

可下载当前的 [`ios-v1.0.2` 未签名 IPA](https://github.com/Xynrin/tiktok-douyin-dl/releases/tag/ios-v1.0.2)，再使用 Xcode、AltStore、Sideloadly 或其他兼容工具，通过自己的 Apple ID 完成签名安装。App 内更新功能只负责发现新版本并打开下载页面；受 iOS 自签机制限制，不能在后台静默替换自身。构建、签名和安装方法见 [`ios/README.md`](ios/README.md)。

### 🧪 NAS 用户（实验性 Docker WebUI）

> **尚未测试：** 当前 Docker 部署尚未由维护者完成端到端验证。以下 Compose 文件仅供参考，请在使用前自行检查配置，并欢迎反馈兼容性问题。

如需在飞牛 OS 等 NAS 上尝试，可新建自定义应用，并根据自己的目录和网络环境调整以下 Docker Compose 配置：
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
      - /vol1/downloads:/downloads   # 左侧替换为你NAS的真实下载路径
```
部署后可尝试在浏览器访问 `http://NAS的IP:7860`。在 Docker 方案完成充分测试前，不保证所有环境均可正常运行。

### 🐧 Linux 用户 (CLI 命令行)
在终端运行以下命令，即可自动拉取最新二进制包并软链接至 `~/.local/bin`：

```bash
curl -fsSL "https://raw.githubusercontent.com/Xynrin/tiktok-douyin-dl/main/install.sh?v=$(date +%s)" | bash
```
---

## 🚀 使用方法

### Windows 图形界面
双击桌面生成的 **MediaDownloader** 图标，在文本框内直接粘贴你在抖音/TikTok复制的“分享文本”或纯链接，选择对应平台，点击“开始下载”即可。

### iOS App

在下载页面粘贴抖音/TikTok 分享文本或链接并开始任务。下载完成后默认只保存在 App 的本地文件目录；如需相册或 iCloud Drive 副本，可前往设置页面手动开启。

### 命令行静默调用 (适用于 Linux 或 Windows CMD)
```bash
douyin-dl "分享文本或链接" [保存目录]
tiktok-dl "分享文本或链接" [保存目录]
```

## ⚖️ 免责声明
本软件仅限用于个人学习研究、学术交流及网页技术备份测试，严禁用于任何商业用途、非法抓取或网络攻击。因使用本软件导致的一切版权纠纷或账号风控后果，均由使用者自行承担全部责任。

## Star History

<a href="https://www.star-history.com/?repos=Xynrin%2Ftiktok-douyin-dl&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Xynrin/tiktok-douyin-dl&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Xynrin/tiktok-douyin-dl&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Xynrin/tiktok-douyin-dl&type=date&legend=top-left" />
 </picture>
</a>
