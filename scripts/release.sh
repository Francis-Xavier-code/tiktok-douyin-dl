#!/usr/bin/env bash
# =============================================================================
# release.sh — 本地发布触发器（不再本地构建任何二进制）
#
# 所有平台的产物（Windows / Linux / macOS DMG / iOS IPA）现在都由 GitHub
# Actions 在推送 v* 标签时远程构建，见 .github/workflows/release.yml。
# 本脚本只做三件事：
#   1. 从 Python 包读取版本号，校验 tag 未存在；
#   2. 刷新 version-policy.json / download-policy.json 的 updated_at 并提交；
#   3. 打 tag + push，触发 CI 完成全部构建与 Release 上传。
#
# 用法：
#   ./scripts/release.sh            # 正常发布（CI 构建所有平台）
#   SKIP_POLICY_BUMP=1 ./scripts/release.sh   # 不刷新策略 updated_at
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
VERSION="$("$PYTHON_BIN" -c 'import media_downloader; print(media_downloader.__version__)' 2>/dev/null || "$PYTHON_BIN" -c 'import sys; sys.path.insert(0, "'"$REPO_ROOT/python/src"'"); import media_downloader; print(media_downloader.__version__)')"
TAG="v$VERSION"
REPO="Francis-Xavier-code/tiktok-douyin-dl"

echo "==> Release version: $VERSION (tag $TAG)"

# ---------------------------------------------------------------------------
# 0. 前置检查：gh 可用、tag 未存在
# ---------------------------------------------------------------------------
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) 是必须的。" >&2
  exit 1
fi

if git -C "$REPO_ROOT" rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "::error:: tag $TAG 已存在。请先 bump 版本号（python/src/media_downloader/__init__.py）。" >&2
  exit 1
fi

if ! git -C "$REPO_ROOT" diff --quiet --exit-code; then
  echo "::error:: 工作区有未提交改动，请先 commit 再发布。" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. 刷新策略文件 updated_at（release.sh 本地负责，CI 不再动这两个文件）
# ---------------------------------------------------------------------------
bump_policy() {
  local file="$1" name="$2"
  [[ -f "$file" ]] || { echo "==> 跳过 $name（未找到）"; return; }
  if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    "$PYTHON_BIN" - "$file" <<'PY'
import json, sys, datetime
path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"==> Bumped {path} updated_at")
except Exception as e:
    print(f"==> WARNING: 无法更新 {path}: {e}", file=sys.stderr)
PY
    git -C "$REPO_ROOT" add "$file"
    if ! git -C "$REPO_ROOT" diff --cached --quiet -- "$file"; then
      git -C "$REPO_ROOT" commit -m "release: bump $name updated_at for $VERSION"
      echo "==> Committed $name update"
    fi
  else
    echo "==> WARNING: 未找到 $PYTHON_BIN；跳过 $name bump" >&2
  fi
}

if [[ "${SKIP_POLICY_BUMP:-0}" != "1" ]]; then
  bump_policy "$REPO_ROOT/version-policy.json" "version-policy.json"
  bump_policy "$REPO_ROOT/download-policy.json" "download-policy.json"
else
  echo "==> SKIP_POLICY_BUMP=1: 跳过策略 updated_at 刷新"
fi

# ---------------------------------------------------------------------------
# 2. 推送 main（策略更新），然后打 tag 触发 CI 构建
# ---------------------------------------------------------------------------
echo "==> Pushing branch to origin"
git -C "$REPO_ROOT" push origin HEAD

echo "==> Creating tag $TAG"
git -C "$REPO_ROOT" tag "$TAG"
git -C "$REPO_ROOT" push origin "$TAG"

echo ""
echo "==> 已触发远程构建：.github/workflows/release.yml"
echo "    CI 会自动产出 Windows / Linux / macOS DMG / iOS IPA 并上传到 Release $TAG。"
echo "    可在 https://github.com/$REPO/actions 查看进度。"
echo "    完成后请确认 Release 资产齐全，并检查 Casks/tiktok-douyin-dl.rb 的 sha256 已被 CI 更新。"
