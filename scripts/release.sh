#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
VERSION="$(PYTHONPATH="$REPO_ROOT/python/src" "$PYTHON_BIN" -c 'import media_downloader; print(media_downloader.__version__)')"
TAG="v$VERSION"
REPO="Francis-Xavier-code/tiktok-douyin-dl"

# ---------------------------------------------------------------------------
# 1. Linux CLI binaries (set SKIP_LINUX=1 to publish only the macOS DMG)
# ---------------------------------------------------------------------------
if [[ "${SKIP_LINUX:-0}" == "1" ]]; then
  echo "==> SKIP_LINUX=1: skipping Linux CLI build"
else
  echo "==> Building Linux CLI ($VERSION)"
  "$SCRIPT_DIR/build-linux.sh"
fi

# ---------------------------------------------------------------------------
# 2. macOS DMG
#    Signed + notarized automatically when APPLE_* env vars are set, e.g.:
#      export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)"
#      export APPLE_ID="you@example.com"
#      export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
#      export APPLE_TEAM_ID="TEAMID"
# ---------------------------------------------------------------------------
echo "==> Building macOS app ($VERSION)"
DMG_PATH="$(APPLE_VERSION="$VERSION" "$SCRIPT_DIR/build-apple.sh" macos | tail -1)"
if [[ -z "$DMG_PATH" || ! -f "$DMG_PATH" ]]; then
  echo "macOS build failed: no DMG produced" >&2
  exit 1
fi
echo "==> macOS DMG: $DMG_PATH"

# ---------------------------------------------------------------------------
# 3. Regenerate the Homebrew cask
#    - ad-hoc / unsigned DMG: cask removes Gatekeeper quarantine via postflight
#      (custom-tap only; official homebrew-cask requires Apple signing)
#    - Developer ID signed DMG: standard cask, ready for official submission
# ---------------------------------------------------------------------------
CASK_FILE="$REPO_ROOT/Casks/tiktok-douyin-dl.rb"
DMG_NAME="$(basename "$DMG_PATH")"
mkdir -p "$(dirname "$CASK_FILE")"
SHA256="$(shasum -a 256 "$DMG_PATH" | awk '{print $1}')"

if [[ "$DMG_NAME" == *"-unsigned.dmg" ]]; then
  echo "==> DMG is ad-hoc signed (no Apple Developer ID). Generating custom-tap cask (with quarantine bypass)"
  cat > "$CASK_FILE" <<EOF
cask "tiktok-douyin-dl" do
  version "$VERSION"
  sha256 "$SHA256"

  url "https://github.com/$REPO/releases/download/v#{version}/MediaDownloader-macOS-#{version}-unsigned.dmg"
  name "MediaDownloader"
  desc "TikTok & Douyin no-watermark downloader for macOS"
  homepage "https://github.com/$REPO"

  livecheck do
    url :url
    strategy :github_latest
  end

  postflight do
    system_command "xattr",
                   args: ["-dr", "com.apple.quarantine", "#{appdir}/MediaDownloader.app"]
  end

  app "MediaDownloader.app"

  caveats do
    <<~EOS
      This build is ad-hoc signed and NOT notarized by Apple.
      Distributed through the custom tap only (official homebrew-cask
      requires Apple Developer ID signing). The Gatekeeper quarantine
      attribute is removed automatically after install, so the app
      opens without approval prompts.
    EOS
  end

  zap trash: [
    "~/Documents/MediaDownloader",
  ]
end
EOF
  echo "    (official homebrew-cask will reject unsigned apps; use your own tap)"
else
  echo "==> DMG is Developer ID signed + notarized. Generating standard cask"
  cat > "$CASK_FILE" <<EOF
cask "tiktok-douyin-dl" do
  version "$VERSION"
  sha256 "$SHA256"

  url "https://github.com/$REPO/releases/download/v#{version}/MediaDownloader-macOS-#{version}.dmg"
  name "MediaDownloader"
  desc "TikTok & Douyin no-watermark downloader for macOS"
  homepage "https://github.com/$REPO"

  livecheck do
    url :url
    strategy :github_latest
  end

  app "MediaDownloader.app"

  zap trash: [
    "~/Documents/MediaDownloader",
  ]
end
EOF
fi
echo "==> Updated $CASK_FILE (sha256 $SHA256)"

git -C "$REPO_ROOT" add "$CASK_FILE"
if ! git -C "$REPO_ROOT" diff --cached --quiet -- "$CASK_FILE"; then
  git -C "$REPO_ROOT" commit -m "release: update Homebrew cask for $VERSION"
  echo "==> Committed cask update"
fi

# ---------------------------------------------------------------------------
# 4b. Refresh version-policy.json (bump updated_at) and ship it as a release asset.
#     Lets maintainers retire old clients without re-shipping every binary.
#     See docs/version-policy.md.
# ---------------------------------------------------------------------------
POLICY_FILE="$REPO_ROOT/version-policy.json"
if [[ -f "$POLICY_FILE" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$POLICY_FILE" <<'PY'
import json, sys, datetime
path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("==> Bumped version-policy.json updated_at")
except Exception as e:
    print(f"==> WARNING: could not update version-policy.json: {e}", file=sys.stderr)
PY
    git -C "$REPO_ROOT" add "$POLICY_FILE"
    if ! git -C "$REPO_ROOT" diff --cached --quiet -- "$POLICY_FILE"; then
      git -C "$REPO_ROOT" commit -m "release: bump version-policy.json updated_at for $VERSION"
      echo "==> Committed version-policy.json update"
    fi
  else
    echo "==> WARNING: python3 not found; skipping version-policy.json bump" >&2
  fi
else
  echo "==> WARNING: version-policy.json not found; skipping" >&2
fi

# ---------------------------------------------------------------------------
# 4. Publish the GitHub release
#    - existing tag/release are updated in place (assets added with --clobber)
#    - the tag push also triggers the CI workflow which adds Windows/Linux assets
# ---------------------------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required to publish $TAG." >&2
  exit 1
fi

echo "==> Pushing branch (cask update) to origin"
git -C "$REPO_ROOT" push origin HEAD

if git -C "$REPO_ROOT" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "==> Tag $TAG already exists; skipping tag creation"
else
  git -C "$REPO_ROOT" tag "$TAG"
fi
git -C "$REPO_ROOT" push origin "$TAG"

ASSETS=("$DMG_PATH" "$POLICY_FILE")
if [[ "${SKIP_LINUX:-0}" != "1" ]]; then
  ASSETS+=("$REPO_ROOT/dist/douyin-dl" "$REPO_ROOT/dist/tiktok-dl")
fi
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  gh release upload "$TAG" "${ASSETS[@]}" --clobber --repo "$REPO"
else
  gh release create "$TAG" "${ASSETS[@]}" \
    --repo "$REPO" \
    --generate-notes \
    --title "$TAG"
fi
echo "==> Published $TAG"
