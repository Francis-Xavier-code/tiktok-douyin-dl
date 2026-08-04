# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/compare/v1.8.0...HEAD
[1.8.0]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/tag/v1.8.0
[1.7.0]: https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/tag/v1.7.0
