# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.8.2] - 2026-08-06

### Added

- **全平台版本号显示**：CLI 启动时显示版本号并支持 `--version` / `-V` 参数；Windows 标题栏显示版本号；macOS 主窗口和菜单栏显示版本号。
- **CLI 免责声明同意弹窗**：交互模式首次运行显示完整免责声明，支持「下次不再提示」并持久化到 `~/.config/tiktok-douyin-dl/config.json`。
- **iOS 免责声明同意弹窗**：首次启动全屏弹窗，支持「下次不再提示」并持久化到 UserDefaults。
- **macOS 免责声明同意弹窗**：首次启动 sheet 弹窗，支持「下次不再提示」并持久化到 UserDefaults。
- **iOS 静默自动更新**：版本被硬阻挡时自动检查 GitHub releases 并提供下载链接。

### Fixed

- **macOS AppUpdateService.swift 类型错误**：`dropFirst("v")` 改为 `dropFirst(1)`，修复 Swift 编译失败。

### Changed

- **全平台版本策略升级**：`version-policy.json` 设置所有平台 `min_version: 1.8.2`，`hard_block: true`。1.8.1 及以下版本启动时将被强制拦截。

## [1.8.1] - 2026-08-06

### Added

- **macOS 静默自动更新**：版本被硬阻挡时自动检查 GitHub releases、下载 DMG 并打开 Finder 安装界面。
- **CLI (Linux) 静默自动更新**：frozen 二进制在 silent 模式下自动下载新版本并替换自身。

### Fixed

- **Windows GUI 下载策略支持 per-platform 覆盖**：`download-policy.json` 中 `download.platforms.windows` 的设置现在能正确生效，而非被忽略。
- **Windows GUI 下载拦截提示国际化**：错误提示改用 i18n 翻译，切换英文后不再显示中文。
- **Windows GUI 版本号格式统一**：`CURRENT_VERSION` 去掉 `v` 前缀，与 `download-policy.json` 的 `min_version` 格式一致。

### Changed

- **全平台版本策略升级**：`version-policy.json` 设置所有平台 `min_version: 1.8.1`，`hard_block: true`。1.8.0 及以下版本启动时将被强制拦截，提示升级。

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
