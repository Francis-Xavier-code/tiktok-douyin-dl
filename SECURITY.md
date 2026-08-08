# Security Policy

## Supported Versions

Only the **latest release** is eligible for security fixes. Please always
upgrade to the newest version from the
[Releases page](https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases).

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅                 |
| older   | ❌ (please upgrade) |

## Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.** Instead,
report privately through GitHub's built-in mechanism:

1. Open the repository **Security** tab → **Report a vulnerability**
   (private vulnerability reporting, visible only to the maintainers).
2. If that option is unavailable, email-style disclosure is not configured —
   open a regular issue **without** reproducing the exploit in public, and
   prefix the title with `[SECURITY]`. The maintainers will convert it to a
   private advisory.

Please include as much of the following as possible:

- The affected component/platform (CLI, Windows GUI, macOS/iOS app, Android,
  WebUI, or shared core).
- Steps to reproduce (with the smallest possible sample).
- Impact assessment (what an attacker could achieve).
- Suggested fix, if you have one.

### What we do

- **Acknowledge** receipt within **48 hours**.
- **Investigate** and triage within **1 week**.
- **Fix and release** as fast as the severity allows; a fix is shipped with the
  next release (or a hotfix release for critical issues).
- **Credit** reporters (unless you prefer to stay anonymous).

## Security notes for users

- All parsing/downloading happens **locally** on your device. The apps only
  fetch remote content you explicitly ask for (share text/link, update
  checks, changelog).
- Update checks are **fail-open**: if the update server is unreachable, the
  app keeps working and simply does not nag.
- The bundled Playwright headless browser (`ms-playwright/`) runs locally and
  never receives your private data.

## Scope

In scope: the Python core (`python/`), Windows GUI (`apps/windows/`), macOS/iOS
apps (`apps/`), Android app (`apps/android/`), WebUI (`apps/web/`), and shared
Swift library (`apple/`).

Out of scope: the target platforms themselves (Douyin/TikTok anti-abuse
mechanisms) and any third-party service the tool merely interacts with.
