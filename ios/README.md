# MediaDownloader for iOS

MediaDownloader.xcodeproj is a native SwiftUI client for iOS 17 and later.

## What it does

- Extracts URLs from copied share text.
- Parses supported Douyin and TikTok share pages inside a private WKWebView.
- Resolves no-watermark playback URLs without requiring the Python service or Docker WebUI.
- Saves downloaded videos and images to **Files > On My iPhone/iPad > MediaDownloader**.
- Lists, previews, shares, and deletes local downloads.

## Build

1. Open MediaDownloader.xcodeproj in Xcode 16 or later on macOS.
2. Select an iOS 17+ simulator or device.
3. In **Signing & Capabilities**, select your development team and use a bundle identifier that belongs to that team.
4. Select an iPhone or iPad target and run the app.

The target supports both iPhone and iPad (targeted device families 1 and 2). The artifact produced by the existing GitHub Actions workflow is a Simulator build and cannot be installed on a physical iPhone or iPad.

## Installable distribution

All physical-device builds must be signed. An unsigned IPA uploaded to GitHub cannot be installed normally by tapping it on an iPhone.

### TestFlight (recommended for testers)

1. Join the Apple Developer Program and create an app record in App Store Connect.
2. Set the Xcode target's Team and registered bundle identifier.
3. Add a production app icon, increment the build number, then select **Any iOS Device (arm64)**.
4. Choose **Product > Archive**.
5. In Organizer, choose **Distribute App > App Store Connect > Upload**.
6. Add the processed build to a TestFlight external-testing group and share its public invitation link after approval.

### Ad Hoc IPA (small fixed tester group)

Register each tester device's UDID in the developer account, then archive and export with **Distribute App > Ad Hoc**. The exported IPA only installs on the devices included in its provisioning profile.

### Open-source self-build

Users can clone the repository, open the project in Xcode, select their own signing team, and install directly on their own device. This avoids distributing your signing certificate.

Before attempting App Store or external TestFlight distribution, review the target platforms' terms and Apple's rules for downloading third-party audio/video. Apple may request proof that the app is authorized to download content from those services.

## Open-source self-sign releases

The project's default public iOS artifact is an unsigned device IPA. It contains an arm64 iPhone/iPad build but no developer certificate. Each user signs it locally with their own Apple ID before installation.

### Build on the remote Mac

After copying the current ios directory to **/Users/cbzw025/Desktop/ios**, run:

    cd /Users/cbzw025/Desktop/ios
    IOS_VERSION=1.0.0 IOS_BUILD_NUMBER=1 bash scripts/build-unsigned-ipa.sh

The output is:

    /Users/cbzw025/Desktop/ios/dist/MediaDownloader-iOS-1.0.0-unsigned.ipa

To copy it back from Windows PowerShell:

    scp cbzw025@REMOTE_MAC_IP:/Users/cbzw025/Desktop/ios/dist/MediaDownloader-iOS-1.0.0-unsigned.ipa C:\Users\YOUR_NAME\Downloads\

Replace **REMOTE_MAC_IP** and **YOUR_NAME** with the actual values. Add **-P PORT** after **scp** if the remote Mac uses a non-default SSH port.

### Publish an iOS release

GitHub Actions also produces the unsigned device IPA. Push an iOS-specific tag to create a GitHub Release automatically:

    git tag ios-v1.0.0
    git push origin ios-v1.0.0

The in-app updater only considers stable tags beginning with **ios-v**, so desktop releases do not appear as iOS updates.

### Install on a personal iPhone

Use a local self-signing tool such as Sideloadly or AltStore on the computer connected to the iPhone. Import the unsigned IPA, sign it with your own Apple ID, install it, then enable **Settings > Privacy & Security > Developer Mode** if iOS requests it. A free personal signing identity may require periodic re-signing.
