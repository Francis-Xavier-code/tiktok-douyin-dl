# Repository architecture

- `apps/` contains platform-specific application shells and packaging files.
- `python/` contains the installable Python core, platform adapters, CLI, and tests.
- `apple/` contains Swift sources shared by the iOS and macOS Xcode projects.
- `scripts/` contains reproducible local and release builds.
- `assets/` contains repository-wide icons and screenshots.

The Windows GUI and WebUI add `python/src` to `sys.path` when run from a checkout. Packaged and installed builds use the `media-downloader` Python distribution.
