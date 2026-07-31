#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

"$PYTHON_BIN" -m pip install -e "$REPO_ROOT/python" pyinstaller

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
