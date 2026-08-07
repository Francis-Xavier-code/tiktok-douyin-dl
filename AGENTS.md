# AGENTS.md

## What this is

Cross-platform TikTok/Douyin no-watermark downloader. Four clients share one Python core:
- **Python CLI** (`python/`) — the installable `media-downloader` package, also used by Windows GUI and WebUI
- **iOS app** (`apps/ios/`) — native SwiftUI, uses shared Swift library from `apple/`
- **macOS app** (`apps/macos/`) — native SwiftUI, same shared Swift library
- **Windows GUI** (`apps/windows/`) — Python + tkinter (sv-ttk), wraps the Python core

## Repo layout

```
python/                  # Python package (source of truth for version + logic)
  src/media_downloader/  # Package source
    __init__.py          # __version__ (synced from version.json)
    cli.py               # Entry points: main(), douyin_main(), tiktok_main()
    core/                # Models, downloader dispatch, policies, network
    platforms/           # douyin.py, tiktok.py — platform-specific parsers + downloaders
    browser/             # Playwright wrapper with stealth
    i18n/                # Internationalization catalogs
  tests/                 # Pytest unit tests (no network, no browser)
  pyproject.toml         # Package metadata, deps, pytest config
  uv.lock                # Lockfile (uv package manager)
apple/                   # Shared Swift library (MediaDownloaderCore) for iOS + macOS
  Package.swift          # SPM package, platforms: iOS 17+, macOS 14+
  Sources/MediaDownloaderCore/  # ShareTextParser, Models, NativeMediaScraper, MediaDownloadService
apps/
  ios/                   # Xcode project, SwiftUI app
  macos/                 # Xcode project, SwiftUI app
  android/               # Android app (Kotlin, Gradle; Douyin downloader, versioned 0.1.x independently)
  windows/               # Python GUI (gui/) + Inno Setup installer (installer/)
  web/                   # Gradio WebUI (single file webui.py)
scripts/                 # Build entry points (see Build section)
Casks/                   # Homebrew cask (tiktok-douyin-dl.rb) — sha256 updated by CI
skills/                  # AgentSkills-compatible media-downloader skill
docs/                    # Architecture, release notes, policy docs
version-policy.json      # Client-side version nag/block rules (fail-open)
download-policy.json     # Client-side download enable/disable (fail-closed)
changelog.json           # Machine-readable per-platform changelog (generated from CHANGELOG.md)
version.json             # SINGLE source of truth for all version numbers (scripts/sync-versions.py)
```

## Platforms

Clients: Windows GUI, macOS/iOS native apps, Android (Kotlin), CLI (Windows/Linux/macOS), WebUI.
The shared policy/changelog platform keys are: `cli`, `windows`, `macos`, `ios`, `android` (plus `all` for changelog).
Android versions (0.1.x) are independent of the `media_downloader.__version__` line.

## Commands

### Python development

```bash
# Setup (from repo root)
cd python && uv sync                    # Install deps into .venv
uv run playwright install chromium      # Required for browser-based downloads

# Run tests
cd python && uv run pytest              # All tests
cd python && uv run pytest tests/test_cli.py           # Single file
cd python && uv run pytest tests/test_cli.py::test_detect_platform  # Single test
cd python && uv run pytest -k "version_policy"          # By keyword

# Run CLI from source
cd python && uv run media-downloader "share text or link"
cd python && uv run python -m media_downloader.cli "share text or link"
```

### Build scripts (run from repo root)

```bash
./scripts/build-apple.sh all            # Build unsigned iOS IPA + macOS DMG
./scripts/build-apple.sh ios            # iOS only
./scripts/build-apple.sh macos          # macOS only
./scripts/build-linux.sh                # Linux CLI (PyInstaller one-file)
./scripts/build-macos-cli.sh            # macOS CLI for host arch (arm64/x86_64, PyInstaller one-file + zip)
./scripts/build-windows.ps1             # Windows (PowerShell, needs Inno Setup)
./scripts/update-changelog-json.py      # Regenerate changelog.json from CHANGELOG.md (run at release)
./scripts/sync-versions.py               # Propagate version.json to all hard-coded version constants
./scripts/sync-versions.py --policies    # Also mirror policy min_version fields
./scripts/release.sh                    # Bump policy timestamps, tag, push → CI builds all
```

Apple build env vars: `APPLE_VERSION`, `APPLE_BUILD_NUMBER`, `APPLE_OUTPUT_DIR`, `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`.

### Release flow

`./scripts/release.sh` does NOT build locally. It:
1. Reads version from `media_downloader.__version__`
2. Verifies the tag doesn't exist and working tree is clean
3. Bumps `updated_at` in `version-policy.json` and `download-policy.json`
4. Pushes branch + tag → `.github/workflows/release.yml` builds all platforms on GitHub runners

## Version management

Version is defined in exactly one place: `version.json` at the repo root.

```json
{ "main": "2.0.0", "android": {"versionName": "2.0.0", "versionCode": 4}, "apple": {"buildNumber": 1} }
```

- `main` — shared by CLI / Windows GUI / macOS / iOS (matches `media_downloader.__version__`)
- `android.*` — the Android app versions its own line (0.1.x, independent of main)
- `apple.buildNumber` — `APPLE_BUILD_NUMBER` / `CURRENT_PROJECT_VERSION`

**Bump flow**: edit `version.json` → run `python3 scripts/sync-versions.py` → commit.
`scripts/sync-versions.py` propagates to every hard-coded location:
`python/src/media_downloader/__init__.py` (`__version__`), `python/pyproject.toml`,
`python/src/media_downloader/core/updater.py` (`VERSION`), `apps/windows/gui/auto_updater.py`
(`CURRENT_VERSION`), `install.sh` (`RELEASE_TAG`), `Casks/tiktok-douyin-dl.rb`,
both Xcode `project.pbxproj` (`MARKETING_VERSION`), the Swift Bundle fallbacks, and
`apps/android/app/build.gradle.kts` (`versionName`/`versionCode`).
`scripts/build-apple.sh` and `scripts/build-windows.ps1` read `version.json` directly.
Run `sync-versions.py --policies` to also mirror policy `min_version` fields
(`version-policy.json` platforms + `download-policy.json` platforms.android).
`scripts/release.sh` auto-syncs versions before tagging.

## Key architecture notes

- **Platform detection** is URL-based in `cli.py:detect_platform()`. Host matching: `*.douyin.com` → Douyin, `*.tiktok.com` → TikTok. Mixed links in one text is an error.
- **Dispatch flow**: `cli.main()` → `detect_platform()` → `downloader.download()` → `platforms.{douyin,tiktok}.download_urls()`
- **Douyin search-result URLs** with `modal_id` are auto-converted to direct `/video/` URLs by `douyin.normalize_douyin_url()`.
- **Policy evaluation**: `download-policy.json` is fail-closed (unreachable = block downloads). `version-policy.json` is fail-open (unreachable = allow, no nag). Both support per-platform overrides.
- **Playwright + stealth** is required for actual downloads (bypasses WebDriver fingerprint detection). Tests do NOT exercise the browser — they only test parsers and policy logic.
- **CLI archives bundle the browser**: build scripts install the Playwright headless shell (`--only-shell`) into `dist/ms-playwright` as a sidecar next to the binary; the frozen CLI finds it via `core/launch.py:bundled_browser_path()` and falls back to runtime auto-install when absent.
- **Shared changelog**: `changelog.json` at repo root is a machine-readable, per-platform changelog generated from `CHANGELOG.md` by `scripts/update-changelog-json.py` (single source of truth). Entry bullets are tagged `**[全平台]**` / `**[CLI]**` / `**[Windows]**` / `**[macOS]**` / `**[iOS]**` / `**[Android]**`. Every client (CLI updater, Windows `auto_updater.py`, macOS/iOS `AppUpdateService.swift`) fetches it via raw-file mirrors and filters entries for its own platform; `scripts/release.sh` regenerates it on release.
- **Windows GUI** and **WebUI** add `python/src` to `sys.path` when run from a checkout. Packaged builds use the installed `media-downloader` distribution.
- **Apple targets** require iOS 17+ / macOS 14+. The Swift `MediaDownloaderCore` library is shared via SPM local package.

## Testing

- All tests are pure unit tests — no network, no browser, no external services.
- Tests use `monkeypatch` to mock `http_get_bytes` for policy tests.
- Parser fixtures go in `python/tests/fixtures/` — must be sanitized (no cookies or private data).
- Pytest config in `pyproject.toml`: `pythonpath = ["src"]`, `testpaths = ["tests"]`.

## Gotchas

- The `.gitignore` blocks `*.json` globally but explicitly allows `version-policy.json` and `download-policy.json`. If you add a new JSON file to the repo root, you need a `!` exception in `.gitignore`.
- The `.gitignore` blocks `*.html` globally. Debug pages (`debug_page.html`) are excluded.
- `scripts/release.sh` requires a clean working tree and `gh` CLI installed.
- The Homebrew cask only works with the custom tap `Francis-Xavier-code/tap` (ad-hoc signed, not notarized).
- CI auto-commits cask sha256 updates back to `main` during release (`git push origin HEAD:main`).
