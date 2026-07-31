<p align="center">
  <img src="assets/app.ico" alt="MediaDownloader 图标" width="128" height="128">
</p>

<h1 align="center">🚀 TikTok &amp; 抖音无水印下载器</h1>
<p align="center"><strong>Windows · iOS · Mac · Linux</strong></p>


一款跨平台的高效工具套件，用于下载 TikTok 和抖音无水印视频及图文作品。项目提供 **现代化 Windows 桌面客户端**、**原生 SwiftUI iOS App**、适合 NAS 的 **实验性 Docker WebUI**，以及 **Linux 独立命令行工具**。

打包后的桌面程序已包含所需运行环境与浏览器组件；iOS 客户端可在设备本地解析支持的分享页面并下载媒体，不依赖 Python 服务或 Docker WebUI。

---

🌐 **[English](README.md)** | **[简体中文]**

---

## 🖼️ 界面预览

<table width="100%">
  <tr>
    <th align="center">原生 macOS App</th>
  </tr>
  <tr>
    <td align="center"><img src="assets/macos-preview.png" alt="MediaDownloader macOS 运行预览" width="900"></td>
  </tr>
</table>

<table width="100%">
  <tr>
    <th align="center" width="33%">新建下载</th>
    <th align="center" width="33%">本地文件管理</th>
    <th align="center" width="33%">照片与 iCloud 设置</th>
  </tr>
  <tr>
    <td align="center"><img src="apps/ios/image/ios-new-download.png" alt="iOS 新建下载" width="280"></td>
    <td align="center"><img src="apps/ios/image/ios-local-files.png" alt="iOS 本地文件管理" width="280"></td>
    <td align="center"><img src="apps/ios/image/ios-settings.png" alt="iOS 照片与 iCloud 设置" width="280"></td>
  </tr>
</table>

<table width="100%">
  <tr>
    <th align="center">Windows 图形界面</th>
  </tr>
  <tr>
    <td align="center"><img src="assets/windows-gui.png" alt="Windows 图形界面" width="900"></td>
  </tr>
</table>

## ✨ 功能亮点

* 🎨 **现代化 UI 设计**：全新引入 Windows 11 Fluent 风格的暗黑模式极简界面，并**新增了跨语言无缝切换 (中/英)**。
* 📱 **原生 iOS App**：直接在设备上解析支持的抖音/TikTok 分享链接，下载无水印视频和图文作品，并通过原生 SwiftUI 界面管理本地文件。
* ☁️ **可选的 iOS 多位置保存**：默认保留 App 本地文件；按需将支持的媒体额外保存到系统相册，并镜像到用户选择的 iCloud Drive 文件夹。
* 📁 **自动构建专属档案库**：下载内容不再杂乱无章！智能提取视频作者名，自动为你建立“作者专属文件夹”归档图文和视频。
* 📦 **规范化安装包**：提供标准的 Windows `Setup.exe`，包含自动安装、桌面快捷方式生成以及“不留痕迹”的暴力卸载。
* 🛡️ **终极风控伪装 (Stealth Mode)**：底层引入了最强防检测注入代码，隐匿 WebDriver 痕迹，最大程度防止下载时被官方风控。

## 📥 下载与安装

### 💻 Windows/Mac/ios 用户 (图形界面推荐)
前往[发布页面](https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases)下载最新的安装包



### 🐧 Linux 用户 (CLI 命令行)
在终端运行以下命令，即可自动拉取最新二进制包并软链接至 `~/.local/bin`：

```bash
curl -fsSL "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/install.sh?v=$(date +%s)" | bash
```
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

CLI 会根据链接域名自动识别抖音或 TikTok；只有需要手动覆盖时才使用 `--platform douyin` 或 `--platform tiktok`。

## 项目结构

各平台应用位于 `apps/`，可安装的 Python 包位于 `python/`，Apple 共享 Swift 代码位于 `apple/`，构建入口位于 `scripts/`。详细说明见 [`docs/architecture.md`](docs/architecture.md)。

执行 `./scripts/build-apple.sh all` 可按 `1.7.0` 版本同时构建 iOS 与 macOS 无签名产物；将 `all` 改为 `ios` 或 `macos` 可单独构建。

## ⚖️ 免责声明
本软件仅限用于个人学习研究、学术交流及网页技术备份测试，严禁用于任何商业用途、非法抓取或网络攻击。因使用本软件导致的一切版权纠纷或账号风控后果，均由使用者自行承担全部责任。

## Star History

<a href="https://www.star-history.com/?repos=Francis-Xavier-code%2Ftiktok-douyin-dl&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Francis-Xavier-code/tiktok-douyin-dl&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Francis-Xavier-code/tiktok-douyin-dl&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Francis-Xavier-code/tiktok-douyin-dl&type=date&legend=top-left" />
 </picture>
</a>
