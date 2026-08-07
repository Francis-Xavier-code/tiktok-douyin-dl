# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **[CLI]** 内置无头浏览器：Windows / Linux / macOS CLI 产物现在随包附带 Playwright headless Chromium（`ms-playwright/` 侧车目录，仅 headless shell，~200MB），首次运行不再需要联网下载浏览器；没有侧车时回退到原有自动下载。Windows GUI 安装包同步改用 `--only-shell`，安装包体积大幅缩小。
- **[CLI]** macOS CLI 打包：新增 `scripts/build-macos-cli.sh`（PyInstaller 单文件），按 Apple 芯片（arm64）与 Intel（x86_64）双架构产出 `MediaDownloader-macOS-{arch}-CLI-{version}.zip`；CI 每次 Release 自动构建上传。`install.sh` 一键安装脚本现同时支持 Linux 与 macOS，并在 macOS 上自动解除 quarantine 属性。
- **[全平台]** 更新日志自动识别显示：新增机器可读的 `changelog.json`（由 `scripts/update-changelog-json.py` 从 CHANGELOG.md 自动生成，`release.sh` 发版时自动刷新）。CLI / Windows GUI / macOS / iOS 检查更新时自动拉取该文件（raw 镜像，国内可达），并按端过滤只显示本端相关的更新内容。
- **[Windows]** GUI 自动识别平台：粘贴/输入链接后自动识别抖音或 TikTok 并切换平台下拉框（可手动覆盖）；同时包含两种平台的链接会报错提示分开下载。
- **[Windows]** 修复更新弹窗：改用共享 changelog.json 替代被限流/被墙的 GitHub API，更新日志不再截断 300 字。
- **[iOS]** 修复更新检测：改为读取共享 changelog.json 获取最新版本与更新日志（原来查找不存在的 `ios-v*` 标签，永远检测不到更新）。
- **[macOS]** 更新时显示本端更新日志。
- **[CLI]** 更新提示显示本端更新日志；Agent skill 支持 macOS 安装，并修复安装时下载不存在的裸二进制资产的错误。
- **[全平台]** 版本号统一管理：新增 `version.json` 作为所有端版本号的唯一事实来源（`main` / `android.versionName+versionCode` / `apple.buildNumber`），`scripts/sync-versions.py` 一键同步到全部硬编码位置（Python 包、pyproject、updater、Windows GUI、install.sh、Homebrew cask、两个 Xcode project、Swift fallback、Android gradle），`release.sh` 发版前自动同步。
- **[Android]** 预留为全平台基础设施的一等公民：`changelog.json` 新增 `android` 平台桶（`[Android]` 标签）、`version-policy.json` / `download-policy.json` 新增 `android` 平台条目，Release CI 自动构建并上传 `douyin-download-Android-{version}.apk`（debug 签名，版本号独立于主版本线）。

## [1.8.2] - 2026-08-06

### Added

- **[全平台]** 版本号显示：CLI 启动时显示版本号并支持 `--version` / `-V` 参数；Windows 标题栏显示版本号；macOS 主窗口和菜单栏显示版本号。
- **[CLI]** 免责声明同意弹窗：交互模式首次运行显示完整免责声明，支持「下次不再提示」并持久化到 `~/.config/tiktok-douyin-dl/config.json`。
- **[iOS]** 免责声明同意弹窗：首次启动全屏弹窗，支持「下次不再提示」并持久化到 UserDefaults。
- **[macOS]** 免责声明同意弹窗：首次启动 sheet 弹窗，支持「下次不再提示」并持久化到 UserDefaults。
- **[iOS]** 静默自动更新：版本被硬阻挡时自动检查 GitHub releases 并提供下载链接。

### Fixed

- **[macOS]** AppUpdateService.swift 类型错误：`dropFirst("v")` 改为 `dropFirst(1)`，修复 Swift 编译失败。

### Changed

- **[全平台]** 版本策略升级：`version-policy.json` 设置所有平台 `min_version: 1.8.2`，`hard_block: true`。1.8.1 及以下版本启动时将被强制拦截。

## [1.8.1] - 2026-08-06

### Added

- **[macOS]** 静默自动更新：版本被硬阻挡时自动检查 GitHub releases、下载 DMG 并打开 Finder 安装界面。
- **[CLI]** (Linux) 静默自动更新：frozen 二进制在 silent 模式下自动下载新版本并替换自身。

### Fixed

- **[Windows]** 下载策略支持 per-platform 覆盖：`download-policy.json` 中 `download.platforms.windows` 的设置现在能正确生效，而非被忽略。
- **[Windows]** 下载拦截提示国际化：错误提示改用 i18n 翻译，切换英文后不再显示中文。
- **[Windows]** 版本号格式统一：`CURRENT_VERSION` 去掉 `v` 前缀，与 `download-policy.json` 的 `min_version` 格式一致。

### Changed

- **[全平台]** 版本策略升级：`version-policy.json` 设置所有平台 `min_version: 1.8.1`，`hard_block: true`。1.8.0 及以下版本启动时将被强制拦截，提示升级。

## [1.8.0] - 2026-08-04

### Added

- **远程版本策略（停用旧版本）正式发布**：由 GitHub 托管的 `version-policy.json`，维护者可以在**不重新编译/重新发布各端安装包**的前提下，远程控制哪些旧版本被提示升级或拒绝运行。各端启动时拉取该文件（失败则放行，绝不影响正常使用），与自身版本号比对：
  - **软提示（默认）**：低于 `min_version` 时弹窗/横幅提醒升级，但旧版本仍可使用。
  - **硬阻挡**：对应平台 `hard_block: true` 时，低于 `min_version` 直接拒绝运行，仅显示升级提示与下载链接。
  - 覆盖端：CLI / macOS / Linux（Python 核心 `core/version_policy.py`）、Windows GUI（`auto_updater.enforce_version_policy`）、iOS 与 macOS 菜单栏（各自的 `VersionPolicyService`）。
  - `scripts/release.sh` 会在发布时自动刷新 `updated_at` 并把策略文件作为 Release 产物上传。详见 `docs/version-policy.md`。
  - 注意：本项目是无后端的纯客户端，已发布且不含本机制的旧版本无法被远程杀掉——本机制仅对未来包含版本检查的新构建生效。
- 全平台版本号统一为 `1.8.0`。

## [1.7.0] - 2026-07-17

### Added

- 重构为 Windows、Web、iOS、macOS、Python 核心分离的跨平台项目结构。
- 新增原生 macOS App、菜单栏快捷下载及 DMG 安装包。
- iOS 与 macOS 统一使用 Swift 媒体解析和下载核心。
- Windows 与 Linux 改由 GitHub Actions 自动构建并加入同一个 Release。
- 新增兼容 OpenClaw/AgentSkills 的 `media-downloader` Skill，可让自主 AI 代理搜索、选择并下载公开作品。
- Linux/Windows CLI 新增抖音搜索结果 URL 规范化，支持 `modal_id` 和抖音精选作品链接，不再强制要求手机分享短链。
- 全平台版本号统一为 `1.7.0`。

[Unreleased]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/compare/v1.8.2...HEAD
[1.8.2]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/tag/v1.8.2
[1.8.1]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/tag/v1.8.1
[1.8.0]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/tag/v1.8.0
[1.7.0]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/tag/v1.7.0
