#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

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

# Ship the browser next to the binary; the frozen CLI detects it via
# media_downloader.core.launch.bundled_browser_path().
cp -r "$BROWSER_SRC" "$REPO_ROOT/dist/ms-playwright"
echo "Bundled browser at $REPO_ROOT/dist/ms-playwright"
