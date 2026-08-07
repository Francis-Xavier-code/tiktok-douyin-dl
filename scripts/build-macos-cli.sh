#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Build the macOS CLI (PyInstaller one-file) for the CURRENT host architecture.
#
# Usage:
#   ./scripts/build-macos-cli.sh
#
# Outputs:
#   dist/media-downloader                                    (one-file binary)
#   dist/MediaDownloader-macOS-{arm64,x86_64}-CLI-<version>.zip
#
# Notes:
#   * PyInstaller cannot cross-compile: run this on an Apple Silicon Mac to
#     produce arm64 binaries and on an Intel Mac for x86_64 binaries. CI builds
#     both via the matrix in .github/workflows/release.yml (macos-14 = arm64,
#     macos-13 = x86_64).
#   * The binary is ad-hoc codesigned. Apple Silicon requires every binary to
#     carry at least an ad-hoc signature, and a downloaded copy may be killed
#     by Gatekeeper until the quarantine attribute is removed:
#         xattr -d com.apple.quarantine media-downloader
#   * The Playwright headless Chromium is downloaded during the build and
#     shipped as a sidecar `ms-playwright/` inside the zip, so end users never
#     download a browser on first run. Without the sidecar the frozen CLI
#     falls back to auto-installing into ~/.cache/ms-playwright.
# -----------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "build-macos-cli.sh must run on macOS (PyInstaller cannot cross-compile)." >&2
  exit 1
fi

ARCH="$(uname -m)"   # arm64 or x86_64

"$PYTHON_BIN" -m pip install -e "$REPO_ROOT/python" pyinstaller

# Download the Playwright Chromium browser (kept as a sidecar next to the
# binary, NOT embedded in the one-file executable): shipping it avoids the
# first-run download, and a sidecar keeps startup fast — embedding would force
# PyInstaller to extract ~160MB of Chromium to a temp dir on every invocation.
BROWSER_SRC="$REPO_ROOT/build/ms-playwright"
mkdir -p "$BROWSER_SRC"
# --only-shell: the downloader always launches headless, so the full Chromium
# (~1GB on macOS) is unnecessary — the headless shell (~200MB) is enough and
# keeps the release archive reasonable.
PLAYWRIGHT_BROWSERS_PATH="$BROWSER_SRC" "$PYTHON_BIN" -m playwright install --only-shell chromium

VERSION="$("$PYTHON_BIN" -c 'import media_downloader; print(media_downloader.__version__)')"
echo "Building macOS CLI $VERSION for $ARCH ..."

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --onefile \
  --name media-downloader \
  --paths "$REPO_ROOT/python/src" \
  --hidden-import media_downloader.platforms.douyin \
  --hidden-import media_downloader.platforms.tiktok \
  --hidden-import media_downloader.i18n.catalogs \
  --collect-all playwright \
  --collect-all playwright_stealth \
  --collect-all PIL \
  --distpath "$REPO_ROOT/dist" \
  --workpath "$REPO_ROOT/build/media-downloader" \
  --specpath "$REPO_ROOT/build" \
  --clean \
  "$REPO_ROOT/python/src/media_downloader/cli.py"

BINARY="$REPO_ROOT/dist/media-downloader"
if [[ ! -f "$BINARY" ]]; then
  echo "media-downloader binary was not produced at $BINARY" >&2
  exit 1
fi

# Ad-hoc codesign: mandatory on Apple Silicon, keeps Gatekeeper happy-ish.
echo "Ad-hoc codesigning $BINARY ..."
codesign --force --sign - "$BINARY"
codesign --verify --deep --strict "$BINARY" || {
  echo "warning: codesign verification failed; the binary may be blocked by macOS." >&2
}

# Ship the browser next to the binary; the frozen CLI detects it via
# media_downloader.core.launch.bundled_browser_path().
cp -r "$BROWSER_SRC" "$REPO_ROOT/dist/ms-playwright"

ZIP_NAME="MediaDownloader-macOS-${ARCH}-CLI-${VERSION}.zip"
ZIP_PATH="$REPO_ROOT/dist/$ZIP_NAME"
(
  cd "$REPO_ROOT/dist"
  rm -f "$ZIP_NAME"
  zip -q -r "$ZIP_NAME" media-downloader ms-playwright
)
echo "Packaged: $ZIP_PATH"
echo "$ZIP_PATH"
