# MediaDownloader for iOS

`MediaDownloader.xcodeproj` is a native SwiftUI client for iOS 17 and later.

## What it does

- Extracts URLs from copied share text.
- Saves direct video, image, and audio URLs to `Files > On My iPhone/iPad > MediaDownloader`.
- Opens this repository's Docker WebUI inside the app for share links that need the existing Python + Playwright parser.

TikTok and Douyin share-page parsing cannot run directly in an iOS app because the repository's parser requires Python and Playwright. Deploy the repository's existing Docker WebUI, then set its LAN URL under **Settings > Docker WebUI** in the app (for example `http://192.168.1.20:7860`).

## Build

1. Open `MediaDownloader.xcodeproj` in Xcode 16 or later on macOS.
2. Select an iOS 17+ simulator or device.
3. Set a signing team and a unique bundle identifier before running on a physical device.

For a real device accessing a plain-HTTP LAN WebUI, iOS App Transport Security may block the connection. Prefer HTTPS through a reverse proxy before distribution.
