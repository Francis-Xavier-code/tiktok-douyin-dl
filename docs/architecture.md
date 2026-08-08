# Repository architecture

- `apps/` contains platform-specific application shells and packaging files.
- `python/` contains the installable Python core, platform adapters, CLI, and tests.
- `apple/` contains Swift sources shared by the iOS and macOS Xcode projects.
- `scripts/` contains reproducible local and release builds.
- `assets/` contains repository-wide icons and screenshots.

The Windows GUI and WebUI add `python/src` to `sys.path` when run from a checkout. Packaged and installed builds use the `media-downloader` Python distribution.

The Android app (`apps/android/`, Kotlin) is an **independent implementation** — it does not use the Python core or the Swift library; it has its own parsers, downloader, policy verification (Ed25519) and update checks, and versions its own line (`version.json` → `android.*`).
