#!/usr/bin/env bash
# =============================================================================
# release.sh — 本地发布触发器（不再本地构建任何二进制）
#
# 所有平台的产物（Windows / Linux / macOS DMG / iOS IPA）现在都由 GitHub
# Actions 在推送 v* 标签时远程构建，见 .github/workflows/release.yml。
# 本脚本做四件事：
#   1. 从 version.json 读取版本号，校验 tag 未存在；
#   2. 把版本常量同步到所有端（scripts/sync-versions.py），刷新两个 policy 的
#      updated_at，重新生成 changelog.json，并提交；
#   3. 打 tag + push，触发 CI 完成全部构建与 Release 上传。
#
# 发新版流程：改 version.json（main / android / apple.buildNumber）→
# 可选 python3 scripts/sync-versions.py --policies 同步策略 min_version →
# 运行本脚本。
#
# 用法：
#   ./scripts/release.sh            # 正常发布（CI 构建所有平台）
#   SKIP_POLICY_BUMP=1 ./scripts/release.sh   # 不刷新策略 updated_at
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"

# 读取版本号：version.json 是唯一事实来源；兼容旧习惯回退到 __init__.py。
# 注意：命令替换内的 python 可能失败，必须加 `|| true` 豁免 set -e，
# 否则第一次读取失败会直接终止脚本，走不到下面的 fallback / 错误提示。
VERSION="$($PYTHON_BIN -c 'import json,sys;print(json.load(open(sys.argv[1]))["main"])' "$REPO_ROOT/version.json" 2>/dev/null)" || true
if [[ -z "$VERSION" ]]; then
  VERSION="$($PYTHON_BIN -c 'import media_downloader, sys; print(media_downloader.__version__)' 2>/dev/null)" || true
fi
if [[ -z "$VERSION" ]]; then
  VERSION="$($PYTHON_BIN -c 'import sys; sys.path.insert(0, "'"$REPO_ROOT/python/src"'"); import media_downloader; print(media_downloader.__version__)' 2>/dev/null)" || true
fi
if [[ -z "$VERSION" ]]; then
  echo "::error:: 无法读取版本号。请确认 version.json 存在（或本机可 import media_downloader）。" >&2
  exit 1
fi
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
  echo "::error:: tag $TAG 已存在。请先 bump 版本号（version.json）。" >&2
  exit 1
fi

if ! git -C "$REPO_ROOT" diff --quiet --exit-code; then
  echo "::error:: 工作区有未提交改动，请先 commit 再发布。" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. 同步所有端版本常量（version.json → 各处硬编码位置），并刷新策略文件
#    updated_at + 重新生成 changelog.json。这些改动会作为 release commit 提交。
# ---------------------------------------------------------------------------
echo "==> Syncing version constants from version.json (main $VERSION)"
"$PYTHON_BIN" "$REPO_ROOT/scripts/sync-versions.py"
git -C "$REPO_ROOT" add -A "$REPO_ROOT/python" "$REPO_ROOT/apps" "$REPO_ROOT/scripts" "$REPO_ROOT/Casks" "$REPO_ROOT/install.sh"
if ! git -C "$REPO_ROOT" diff --cached --quiet; then
  git -C "$REPO_ROOT" commit -m "release: sync version constants to $VERSION"
  echo "==> Committed version constant sync"
fi

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
# 1.5 重新生成 changelog.json（各端共用的机器可读更新日志；单一事实来源为 CHANGELOG.md）
# ---------------------------------------------------------------------------
if [[ "${SKIP_POLICY_BUMP:-0}" != "1" ]]; then
  if "$PYTHON_BIN" "$REPO_ROOT/scripts/update-changelog-json.py"; then
    git -C "$REPO_ROOT" add "$REPO_ROOT/changelog.json"
    if ! git -C "$REPO_ROOT" diff --cached --quiet -- "$REPO_ROOT/changelog.json"; then
      git -C "$REPO_ROOT" commit -m "release: regenerate changelog.json for $VERSION"
      echo "==> Committed changelog.json update"
    fi
  else
    echo "==> WARNING: changelog.json 生成失败；请手动运行 scripts/update-changelog-json.py" >&2
  fi
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
echo "    CI 会自动产出 Windows / Linux / macOS CLI / macOS DMG / iOS IPA / Android APK 并上传到 Release ${TAG:-v$VERSION}。"
echo "    可在 https://github.com/$REPO/actions 查看进度。"
echo "    完成后请确认 Release 资产齐全，并检查 Casks/tiktok-douyin-dl.rb 的 sha256 已被 CI 更新。"
