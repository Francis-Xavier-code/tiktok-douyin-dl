#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET="${1:-all}"
VERSION="${APPLE_VERSION:-1.7.0}"
BUILD_NUMBER="${APPLE_BUILD_NUMBER:-1}"
OUTPUT_ROOT="${APPLE_OUTPUT_DIR:-$REPO_ROOT/dist/apple}"

if ! xcodebuild -version >/dev/null 2>&1; then
  if [[ -d /Applications/Xcode.app/Contents/Developer ]]; then
    export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
  else
    echo "Xcode.app is required to build the Apple applications." >&2
    exit 1
  fi
fi

build_ios() {
  local output_dir="$OUTPUT_ROOT/ios"
  echo "Building iOS $VERSION (build $BUILD_NUMBER)..."
  IOS_VERSION="$VERSION" \
  IOS_BUILD_NUMBER="$BUILD_NUMBER" \
    bash "$REPO_ROOT/apps/ios/scripts/build-unsigned-ipa.sh" "$output_dir"
}

build_macos() {
  local output_dir="$OUTPUT_ROOT/macos"
  local derived_data="$output_dir/DerivedData"
  local project="$REPO_ROOT/apps/macos/MediaDownloader.xcodeproj"
  local app_path="$derived_data/Build/Products/Release/MediaDownloader.app"
  local dmg_path="$output_dir/MediaDownloader-macOS-${VERSION}-unsigned.dmg"

  echo "Building macOS $VERSION (build $BUILD_NUMBER)..."
  mkdir -p "$output_dir"
  xcodebuild \
    -project "$project" \
    -scheme MediaDownloader \
    -configuration Release \
    -sdk macosx \
    -destination "generic/platform=macOS" \
    -derivedDataPath "$derived_data" \
    MARKETING_VERSION="$VERSION" \
    CURRENT_PROJECT_VERSION="$BUILD_NUMBER" \
    CODE_SIGNING_ALLOWED=NO \
    clean build

  if [[ ! -d "$app_path" ]]; then
    echo "MediaDownloader.app was not produced at $app_path" >&2
    exit 1
  fi

  (
    local packaging_dir staging_dir mount_dir rw_dmg volume_icon
    packaging_dir="$(mktemp -d)"
    staging_dir="$packaging_dir/staging"
    mount_dir="$packaging_dir/mount"
    rw_dmg="$packaging_dir/MediaDownloader-rw.dmg"
    volume_icon="$app_path/Contents/Resources/AppIcon.icns"
    mkdir -p "$staging_dir" "$mount_dir"
    trap 'hdiutil detach "$mount_dir" >/dev/null 2>&1 || true; rm -rf "$packaging_dir"' EXIT
    ditto "$app_path" "$staging_dir/MediaDownloader.app"
    ln -s /Applications "$staging_dir/Applications"

    if [[ -f "$volume_icon" ]]; then
      ditto "$volume_icon" "$staging_dir/.VolumeIcon.icns"
    fi

    hdiutil create \
      -volname "MediaDownloader $VERSION" \
      -srcfolder "$staging_dir" \
      -ov \
      -format UDRW \
      "$rw_dmg"

    hdiutil attach \
      -readwrite \
      -nobrowse \
      -mountpoint "$mount_dir" \
      "$rw_dmg" >/dev/null

    if [[ -f "$mount_dir/.VolumeIcon.icns" ]]; then
      xcrun SetFile -a V "$mount_dir/.VolumeIcon.icns"
      xcrun SetFile -a C "$mount_dir"
    fi

    hdiutil detach "$mount_dir" >/dev/null
    hdiutil convert \
      "$rw_dmg" \
      -format UDZO \
      -ov \
      -o "$dmg_path"
  )
  echo "$dmg_path"
}

case "$TARGET" in
  ios)
    build_ios
    ;;
  macos)
    build_macos
    ;;
  all)
    build_ios
    build_macos
    ;;
  *)
    echo "Usage: $0 [ios|macos|all]" >&2
    exit 2
    ;;
esac
