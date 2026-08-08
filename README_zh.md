<p align="center">
  <img src="assets/app.ico" alt="MediaDownloader 图标" width="128" height="128">
</p>

<h1 align="center">TikTok &amp; 抖音无水印下载器</h1>

<!-- 语言切换：置顶显眼，新手一眼可见 -->
<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🌐_English-点我阅读英文-blue?style=for-the-badge" alt="English"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v2.0.0-blue?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/python-3.9+-yellow?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/swift-5.9+-orange?style=flat-square&logo=swift&logoColor=white" alt="Swift">
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial-blue?style=flat-square" alt="License">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20iOS%20%7C%20Android%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

一款跨平台的高效工具套件，用于下载 TikTok 和抖音无水印视频及图文作品。项目提供 **现代化 Windows 桌面客户端**、**原生 SwiftUI iOS App**、**Android 客户端**、适合 NAS 的 **实验性 Docker WebUI**，以及 **Linux/macOS 独立命令行工具**。

打包后的桌面程序已包含所需运行环境与浏览器组件；iOS 客户端可在设备本地解析支持的分享页面并下载媒体，不依赖 Python 服务或 Docker WebUI。

📝 **[更新日志](CHANGELOG.md)** —— 各版本完整变更记录。

---

---

## 🖼️ 界面预览

### 🖥️ Windows 图形界面

| 主界面 | 更新检查 |
|:---:|:---:|
| ![Windows 图形界面](assets/windows-gui.png) | ![更新检查](assets/windows-gui-autoupdate-checkNewVison.png) |

### 🍎 macOS App

| 主界面 | 菜单栏 · 等待分享链接 | 菜单栏 · 识别链接 |
|:---:|:---:|:---:|
| ![macOS 主界面](assets/macos-gui.png) | ![菜单栏等待](assets/macos-menubar-preview.png) | ![菜单栏就绪](assets/macos-menubar-ready-preview.png) |

### 📱 iOS App

| 选择视频 | 预览下载 | 查看已下载视频 |
|:---:|:---:|:---:|
| ![iOS 选择视频](assets/ios-gui-select-video.png) | ![iOS 预览下载](assets/ios-gui-preview-download.png) | ![iOS 查看已下载视频](assets/ios-look-downloaded-video.png) |
| 设置 | 免责声明 | 使用下载器 |
|:---:|:---:|:---:|
| ![iOS 设置](assets/ios-gui-setting.png) | ![iOS 免责声明](assets/ios-login-免责声明.png) | ![iOS 使用下载器](assets/ios-gui-useDownload.png) |

### 🐧 Linux 命令行

| 终端 |
|:---:|
| ![Linux CLI](assets/linux-cli.png) |

### 🤖 Android

| 主界面 | 设置 |
|:---:|:---:|
| ![Android 主界面](assets/android-gui-index.png) | ![Android 设置](assets/android-setting-gui.png) |

### 🐳 WebUI（实验性）· 即将上线

<!-- 预留：截图就绪后放到 assets/webui-preview.png，替换下方占位行即可 -->
| 预览 |
|:---:|
| _即将上线，敬请期待。_ |

## ✨ 功能亮点

* 🎨 **现代化 UI 设计**：全新引入 Windows 11 Fluent 风格的暗黑模式极简界面，并**新增了跨语言无缝切换 (中/英)**。
* 📱 **原生 iOS App**：直接在设备上解析支持的抖音/TikTok 分享链接，下载无水印视频和图文作品，并通过原生 SwiftUI 界面管理本地文件。
* ☁️ **可选的 iOS 多位置保存**：默认保留 App 本地文件；按需将支持的媒体额外保存到系统相册，并镜像到用户选择的 iCloud Drive 文件夹。
* 📁 **自动构建专属档案库**：下载内容不再杂乱无章！智能提取视频作者名，自动为你建立“作者专属文件夹”归档图文和视频。
* 📦 **规范化安装包**：提供标准的 Windows `Setup.exe`，包含自动安装、桌面快捷方式生成以及“不留痕迹”的暴力卸载。
* 🛡️ **终极风控伪装 (Stealth Mode)**：底层引入了最强防检测注入代码，隐匿 WebDriver 痕迹，最大程度防止下载时被官方风控。

## 📥 下载与安装

### 💻 Windows / 🍎 macOS / 📱 iOS 用户 (图形界面推荐)

前往[发布页面](https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases)下载最新安装包：

- **Windows**：`MediaDownloader-Windows-x64-Setup-<ver>.exe`
- **macOS**：`MediaDownloader-macOS-<ver>.dmg`（ad-hoc 签名；如首次打开被 Gatekeeper 拦截，请前往 系统设置 → 隐私与安全性 → 仍要打开）
- **iOS**：`MediaDownloader-iOS-<ver>-unsigned.ipa`（需使用自己的 Apple ID 重新签名）

### 🤖 Android 用户

在[发布页面](https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases)下载 `douyin-download-Android-<ver>.apk` 并安装到手机（需允许「安装未知来源应用」）。

### 🐧 Linux / 🍎 macOS 用户 (CLI 命令行)

在终端运行以下命令，即可自动拉取最新 CLI（Linux x86_64 / macOS Apple 芯片 arm64）并软链接至 `~/.local/bin`：

```bash
curl -fsSL "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/install.sh?v=$(date +%s)" | bash
```

### 🪟 Windows 用户 (CLI 命令行)

在 PowerShell 中运行以下命令，即可安装 Windows CLI（将 `%LOCALAPPDATA%\MediaDownloader` 加入用户 PATH，无需管理员权限）：

```powershell
irm https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/install.ps1 | iex
```

卸载：

```powershell
irm https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/uninstall.ps1 | iex
```

## 🤖 给 AI 的一句话指令

复制下面这句话，把 `<链接>` 换成你要下载的抖音 / TikTok 分享链接或作品链接，直接发给任意 AI 助手即可——AI 会自己读取技能文件并按其中的方法帮你下载。**无需安装，不用敲命令。**

```text
请先阅读技能文件 https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/skills/media-downloader/SKILL.md ，然后按其中的方法帮我下载这个作品：<链接>
```

想搜索而不是粘贴链接：`请先阅读技能文件 https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/skills/media-downloader/SKILL.md ，搜索符合“<关键词>”的公开抖音或 TikTok 视频，告诉我选中的结果，然后下载。`

OpenClaw / AgentSkills 环境可改为安装：`openclaw skills install skills-sh:Francis-Xavier-code/tiktok-douyin-dl/media-downloader`，之后直接用 `$media-downloader`。

对于不支持自动发现 Skill 的代理，可直接说：`读取 skills/media-downloader/SKILL.md，并使用其完整脚本下载这个搜索结果或分享链接：<URL>`。

---

## 🚀 使用方法

### Windows 图形界面
双击桌面生成的 **MediaDownloader** 图标，在文本框内直接粘贴你在抖音/TikTok复制的“分享文本”或纯链接，选择对应平台，点击“开始下载”即可。

### iOS App

在下载页面粘贴抖音/TikTok 分享文本或链接并开始任务。下载完成后默认只保存在 App 的本地文件目录；如需相册或 iCloud Drive 副本，可前往设置页面手动开启。

### 命令行静默调用 (适用于 Linux 或 Windows CMD)
```bash
media-downloader "分享文本或链接" [保存目录]
```

CLI 会根据链接域名自动识别抖音或 TikTok；带 `modal_id` 的抖音搜索结果链接会自动转换为直接作品链接，不再要求必须提供手机分享文案。只有需要手动覆盖时才使用 `--platform douyin` 或 `--platform tiktok`。

## 项目结构

各平台应用位于 `apps/`，可安装的 Python 包位于 `python/`，Apple 共享 Swift 代码位于 `apple/`，自主 AI 代理 Skill 位于 `skills/`，构建入口位于 `scripts/`。详细说明见 [`docs/architecture.md`](docs/architecture.md)。

执行 `./scripts/build-apple.sh all` 可按 `2.0.0` 版本同时构建 iOS 与 macOS 无签名产物；将 `all` 改为 `ios` 或 `macos` 可单独构建。

## ⚖️ 免责声明
本软件仅限用于个人学习研究、学术交流及网页技术备份测试，严禁用于任何商业用途、非法抓取或网络攻击。因使用本软件导致的一切版权纠纷或账号风控后果，均由使用者自行承担全部责任。

## ⭐ Star History

如果本项目对你有帮助，请点个 ⭐ 支持我们。若下方的第三方 star-history 图表加载失败（该服务对小仓库不稳定），上面的实时徽章计数始终可以正常显示：

<p align="center">
  <img src="https://img.shields.io/github/stars/Francis-Xavier-code/tiktok-douyin-dl?style=for-the-badge&logo=github&color=gold" alt="GitHub Stars">
  <img src="https://img.shields.io/github/forks/Francis-Xavier-code/tiktok-douyin-dl?style=for-the-badge&logo=github" alt="GitHub Forks">
  <img src="https://img.shields.io/github/watchers/Francis-Xavier-code/tiktok-douyin-dl?style=for-the-badge&logo=github" alt="GitHub Watchers">
</p>

<a href="https://www.star-history.com/?repos=Francis-Xavier-code%2Ftiktok-douyin-dl&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Francis-Xavier-code/tiktok-douyin-dl&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Francis-Xavier-code/tiktok-douyin-dl&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Francis-Xavier-code/tiktok-douyin-dl&type=date&legend=top-left" />
 </picture>
</a>
