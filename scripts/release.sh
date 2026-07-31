#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
VERSION="$(PYTHONPATH="$REPO_ROOT/python/src" "$PYTHON_BIN" -c 'import media_downloader; print(media_downloader.__version__)')"
TAG="v$VERSION"

"$SCRIPT_DIR/build-linux.sh"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required to publish $TAG." >&2
  exit 1
fi

git -C "$REPO_ROOT" tag "$TAG"
git -C "$REPO_ROOT" push origin "$TAG"
gh release create "$TAG" \
  "$REPO_ROOT/dist/douyin-dl" \
  "$REPO_ROOT/dist/tiktok-dl" \
  --repo "Francis-Xavier-code/tiktok-douyin-dl" \
  --generate-notes \
  --title "$TAG"
