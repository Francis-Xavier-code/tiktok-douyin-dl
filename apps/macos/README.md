# MediaDownloader for macOS

The macOS app targets macOS 14 or later and shares its parsing and download implementation with the iOS app through `apple/MediaDownloaderCore`.

## Local build

From the repository root:

```bash
./scripts/build-apple.sh macos
```

The unsigned release disk image is written to:

```text
dist/apple/macos/MediaDownloader-macOS-1.7.0-unsigned.dmg
```

The DMG contains `MediaDownloader.app` and an `Applications` shortcut. The menu bar icon opens a compact quick-download panel that watches the clipboard while it is visible, identifies Douyin and TikTok links, and starts a download with one click. The panel also keeps the current download status, main window, download folder, refresh, and quit actions close at hand.

For a signed distribution build, open `apps/macos/MediaDownloader.xcodeproj`, select your development team, then use **Product > Archive**. Distribution outside your own Mac also requires the appropriate Developer ID signing and notarization.
