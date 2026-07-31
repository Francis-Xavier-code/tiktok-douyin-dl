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

The DMG contains `MediaDownloader.app` and an `Applications` shortcut. The app also exposes a menu bar item for opening the main window, downloading the URL currently on the clipboard, opening the download folder, and quitting.

For a signed distribution build, open `apps/macos/MediaDownloader.xcodeproj`, select your development team, then use **Product > Archive**. Distribution outside your own Mac also requires the appropriate Developer ID signing and notarization.
