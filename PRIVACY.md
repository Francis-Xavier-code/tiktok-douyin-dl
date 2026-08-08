# Privacy Policy / 隐私说明

**English summary** · This tool is fully **local-first**. It does not collect,
store, or transmit any personal information, and it has no telemetry, no
analytics, and no accounts. Everything you download stays on your device in
the folder you choose. The only network requests are the ones you trigger:
the download itself, update checks, and fetching the shared changelog.

**中文摘要** · 本工具完全**本地优先**：不收集、不存储、不上传任何个人信息，
无遥测、无统计、无账号体系。所有下载内容仅保存在你指定的本地目录。
唯一的网络请求都是你主动触发的：下载行为本身、更新检查、拉取共享更新日志。

---

## 1. What we collect / 我们收集什么

**Nothing. 什么都不收集。**

- No accounts, no registration, no email, no device fingerprinting.
- No analytics SDKs, no crash reporters that phone home, no telemetry.
- We never see your share text, links, or downloaded media — they are
  processed **locally on your device** only.

## 2. Network requests / 网络请求

The app only makes network requests when you (or the update check) trigger them:

| Request | Purpose | Data sent |
| --- | --- | --- |
| Downloading a video/photo post | Fetch the media you explicitly asked for | The share text / link you pasted (to the target platform only) |
| Update check | Compare installed version vs. latest release | Nothing personal (version number + user-agent) |
| Changelog fetch | Show per-platform update notes | Nothing personal |
| Version/download policy | Fail-open / fail-closed rules | Nothing personal |

Update checks are **fail-open** (CLI/macOS/iOS/Android): if the server is unreachable
the app keeps working. The download policy is **fail-closed** by default:
unreachable policy server = downloads blocked, which is the safe default
(Android additionally verifies the policy with an Ed25519 signature).

## 3. Data storage / 数据存储

- Downloads are saved **only to the folder you choose** (`output_directory` or
  the app's local documents folder).
- Config is minimal and local: e.g. language preference in
  `~/.local/share/tiktok-douyin-dl/config.json` (CLI) or the app's sandbox.
- No data is ever uploaded to the project's servers — there are none.

## 4. Third-party services / 第三方服务

- Media is fetched directly from the target platform (Douyin / TikTok) using
  your pasted share text or link.
- The bundled Playwright headless browser (`ms-playwright/`) runs **locally**
  as a sidecar; it does not proxy your traffic through the project.

## 5. Your rights / 你的权利

- Everything is local, so "deleting your data" = deleting the local files.
- You can uninstall completely at any time (see
  [`install.sh`](install.sh) / [`uninstall.ps1`](uninstall.ps1)).

## 6. Disclaimer / 免责声明

This tool is for **personal study and technical testing only**. Commercial
use, illegal scraping, and abuse are prohibited. You are responsible for
complying with the target platforms' terms and with local laws. See
[`Disclaimer.txt`](Disclaimer.txt) for the full legal notice.

---

*Last updated: 2026-08-08 · 更新日期：2026-08-08*
