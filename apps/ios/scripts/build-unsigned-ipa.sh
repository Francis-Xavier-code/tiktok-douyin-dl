#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT="$IOS_DIR/MediaDownloader.xcodeproj"
OUTPUT_DIR="${1:-$IOS_DIR/dist}"
DERIVED_DATA="$OUTPUT_DIR/DerivedData"
VERSION="${IOS_VERSION:-2.0.1}"
BUILD_NUMBER="${IOS_BUILD_NUMBER:-1}"

if ! xcodebuild -version >/dev/null 2>&1 && [[ -d /Applications/Xcode.app/Contents/Developer ]]; then
  export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
fi

mkdir -p "$OUTPUT_DIR"

xcodebuild \
  -project "$PROJECT" \
  -scheme MediaDownloader \
  -configuration Release \
  -sdk iphoneos \
  -destination "generic/platform=iOS" \
  -derivedDataPath "$DERIVED_DATA" \
  MARKETING_VERSION="$VERSION" \
  CURRENT_PROJECT_VERSION="$BUILD_NUMBER" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY="" \
  clean build

APP_PATH="$DERIVED_DATA/Build/Products/Release-iphoneos/MediaDownloader.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "MediaDownloader.app was not produced at $APP_PATH" >&2
  exit 1
fi

STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGING_DIR"' EXIT
mkdir -p "$STAGING_DIR/Payload"
ditto "$APP_PATH" "$STAGING_DIR/Payload/MediaDownloader.app"

IPA_PATH="$OUTPUT_DIR/MediaDownloader-iOS-${VERSION}-unsigned.ipa"
(
  cd "$STAGING_DIR"
  /usr/bin/zip -qry "$IPA_PATH" Payload
)

echo "$IPA_PATH"
