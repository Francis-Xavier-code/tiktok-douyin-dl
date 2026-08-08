#!/bin/bash
# -----------------------------------------------------------------------------
# TikTok & Douyin Downloader - Linux / macOS One-Click Installer
# -----------------------------------------------------------------------------

set -e

# GitHub Repository Configuration
GITHUB_USER="Francis-Xavier-code"
GITHUB_REPO="tiktok-douyin-dl"
RELEASE_TAG="v2.0.0"

INSTALL_DIR="$HOME/.local/share/tiktok-douyin-dl"
BIN_DIR="$HOME/.local/bin"

# Terminal Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}   🚀 TikTok & Douyin Downloader Installer        ${NC}"
echo -e "${BLUE}==================================================${NC}"

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 1. Choose Language
echo -e "\n${YELLOW}🌐 选择语言 / Choose Language：${NC}"
echo "1. 简体中文 (Chinese)"
echo "2. English"
read -p "请输入选项序号 / Enter option number [1-2] (Default: 1): " LANG_OPT < /dev/tty
if [ "$LANG_OPT" = "2" ]; then
    USER_LANG="en"
    echo -e "✓ Language set to English."
else
    USER_LANG="zh"
    echo -e "✓ 语言设置为：简体中文。"
fi

# Write language configuration
echo "{\"lang\": \"$USER_LANG\"}" > "$INSTALL_DIR/config.json"

# 2. Install binaries (local or remote)
install_binary() {
    local name=$1
    local local_file="dist/$name"
    local version="${RELEASE_TAG#v}"
    local os_type archive_name
    if [[ "$(uname -s)" == "Darwin" ]]; then
        # macOS CLI is packaged per-architecture: arm64 (Apple Silicon) or x86_64 (Intel)
        os_type="macos"
        local arch
        arch="$(uname -m)"
        archive_name="MediaDownloader-macOS-${arch}-CLI-${version}.zip"
    else
        os_type="linux"
        archive_name="MediaDownloader-Linux-x86_64-${version}.tar.gz"
    fi
    local raw_url="https://github.com/$GITHUB_USER/$GITHUB_REPO/releases/download/$RELEASE_TAG/$archive_name"

    # Mirror URLs: direct GitHub first, then domestic accelerators.
    local -a MIRROR_URLS=(
        "$raw_url"
        "https://gh-proxy.com/$raw_url"
        "https://ghproxy.net/$raw_url"
    )

    if [ -f "$local_file" ]; then
        if [ "$USER_LANG" = "zh" ]; then
            echo -e "📦 检测到本地已编译好的二进制文件，正在安装 $name ..."
        else
            echo -e "📦 Local pre-compiled binary found, installing $name ..."
        fi
        cp "$local_file" "$INSTALL_DIR/"
        # Also ship a locally-built browser sidecar when present.
        if [ -d "dist/ms-playwright" ]; then
            cp -r "dist/ms-playwright" "$INSTALL_DIR/"
        fi
    else
        if [ "$GITHUB_USER" = "YOUR_GITHUB_USERNAME" ] || [ "$GITHUB_REPO" = "YOUR_GITHUB_REPO" ]; then
            echo -e "${RED}❌ Error: GITHUB_USER / GITHUB_REPO not configured in install.sh.${NC}"
            exit 1
        fi

        local tmp_archive
        tmp_archive="$(mktemp)"
        local download_ok=false

        for url in "${MIRROR_URLS[@]}"; do
            if [ "$USER_LANG" = "zh" ]; then
                echo -e "⚡ 正在尝试下载 $archive_name ..."
            else
                echo -e "⚡ Trying to download $archive_name ..."
            fi
            echo -e "   ${BLUE}$url${NC}"

            if curl -fL --connect-timeout 8 --max-time 300 --retry 2 --retry-delay 2 -# "$url" -o "$tmp_archive" 2>/dev/null; then
                download_ok=true
                break
            fi
        done

        if [ "$download_ok" != "true" ]; then
            rm -f "$tmp_archive"
            if [ "$USER_LANG" = "zh" ]; then
                echo -e "${RED}❌ 错误: 所有下载源均失败（$RELEASE_TAG）。${NC}"
                echo -e "${RED}   请检查网络或开启代理后重试。${NC}"
            else
                echo -e "${RED}❌ Error: All download sources failed ($RELEASE_TAG).${NC}"
                echo -e "${RED}   Please check your network or enable a proxy and retry.${NC}"
            fi
            exit 1
        fi

        if [ "$os_type" = "macos" ]; then
            unzip -q -o "$tmp_archive" -d "$INSTALL_DIR"
        else
            # Extract everything: the binary plus the bundled ms-playwright sidecar
            tar -xzf "$tmp_archive" -C "$INSTALL_DIR"
        fi
        rm -f "$tmp_archive"

        if [ ! -f "$INSTALL_DIR/$name" ]; then
            if [ "$USER_LANG" = "zh" ]; then
                echo -e "${RED}❌ 错误: 解压后未找到 $name。${NC}"
            else
                echo -e "${RED}❌ Error: $name not found after extraction.${NC}"
            fi
            exit 1
        fi
    fi

    chmod +x "$INSTALL_DIR/$name"

    # macOS: drop the quarantine attribute so Gatekeeper doesn't kill the binary
    if [ "$os_type" = "macos" ]; then
        xattr -dr com.apple.quarantine "$INSTALL_DIR/$name" 2>/dev/null || true
    fi
}

# Show the changelog for the version being installed (CLI + 全平台 entries)
show_changelog() {
    local version="${RELEASE_TAG#v}"
    local raw_url="https://raw.githubusercontent.com/$GITHUB_USER/$GITHUB_REPO/main/changelog.json"
    local -a MIRROR_URLS=(
        "$raw_url"
        "https://gh-proxy.com/$raw_url"
        "https://ghproxy.net/$raw_url"
        "https://fastly.jsdelivr.net/gh/$GITHUB_USER/$GITHUB_REPO@main/changelog.json"
    )
    local tmp_json
    tmp_json="$(mktemp)"
    for url in "${MIRROR_URLS[@]}"; do
        if curl -fsL --connect-timeout 8 --max-time 15 "$url" -o "$tmp_json" 2>/dev/null; then
            break
        fi
    done
    if [ -s "$tmp_json" ] && command -v python3 >/dev/null 2>&1; then
        python3 - "$tmp_json" "$version" "$USER_LANG" <<'PY' || true
import json, sys
path, version, lang = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    target = None
    for v in data.get("versions", []):
        if str(v.get("version", "")).lstrip("v") == version:
            target = v
            break
    if not target:
        sys.exit(0)
    entries = []
    bucket = target.get("entries") or {}
    for key in ("cli", "all"):
        entries.extend(bucket.get(key) or [])
    if not entries:
        sys.exit(0)
    title = "📝 本版本更新内容" if lang == "zh" else "📝 Changelog for this version"
    print()
    print(f"{title}  v{version}")
    print("-" * 50)
    for e in entries:
        for line in str(e).splitlines():
            print(f"  • {line}")
    print("-" * 50)
except Exception:
    pass
PY
    fi
    rm -f "$tmp_json"
}

# Install the unified auto-detecting CLI
install_binary "media-downloader"

# 2.5 Show the changelog of the installed version
show_changelog

# 3. Configure terminal command
echo -e "\n${YELLOW}💬 配置启动命令 / Configure Startup Commands:${NC}"
ln -sf "$INSTALL_DIR/media-downloader" "$BIN_DIR/media-downloader"

# 4. Check Environment $PATH
NEED_SOURCE=false
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]] && [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    if [ "$USER_LANG" = "zh" ]; then
        echo -e "\n⚙️  正在检测并配置环境变量..."
    else
        echo -e "\n⚙️  Detecting and configuring environment PATH..."
    fi
    
    # Write ~/.bashrc
    if [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$HOME/.bashrc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
            NEED_SOURCE=true
        fi
    fi
    
    # Write ~/.zshrc
    if [ -f "$HOME/.zshrc" ]; then
        if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$HOME/.zshrc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
            NEED_SOURCE=true
        fi
    fi
fi

# Print Success message
echo -e "${GREEN}==================================================${NC}"
if [ "$USER_LANG" = "zh" ]; then
    echo -e "${GREEN}🎉 安装与配置成功！${NC}"
    echo -e "${GREEN}==================================================${NC}"
    echo -e "📁 程序保存路径: ${BLUE}$INSTALL_DIR${NC}"
    echo -e "🚀 统一下载命令: ${BLUE}media-downloader \"分享文本或链接\"${NC}"
    echo -e "🔎 程序会自动识别抖音或 TikTok 链接。"
    echo -e ""
    echo -e "${YELLOW}🔔 使用提示:${NC}"
    if [ "$NEED_SOURCE" = true ]; then
        echo -e "1. 💡 ${YELLOW}请先运行 'source ~/.bashrc' (或 'source ~/.zshrc') 使配置生效！${NC}"
        echo -e "2. 之后在终端任意目录运行 ${GREEN}media-downloader \"分享文本或链接\"${NC} 即可下载！"
    else
        echo -e "1. 终端任意目录下直接运行 ${GREEN}media-downloader \"分享文本或链接\"${NC} 即可下载！"
    fi
else
    echo -e "${GREEN}🎉 Installation & Configuration Successful!${NC}"
    echo -e "${GREEN}==================================================${NC}"
    echo -e "📁 Installation Directory: ${BLUE}$INSTALL_DIR${NC}"
    echo -e "🚀 Unified command: ${BLUE}media-downloader \"share text or link\"${NC}"
    echo -e "🔎 The platform is detected automatically from the link."
    echo -e ""
    echo -e "${YELLOW}🔔 Note:${NC}"
    if [ "$NEED_SOURCE" = true ]; then
        echo -e "1. 💡 ${YELLOW}Please run 'source ~/.bashrc' (or 'source ~/.zshrc') to apply PATH changes!${NC}"
        echo -e "2. Then run ${GREEN}media-downloader \"share text or link\"${NC} anywhere in the terminal."
    else
        echo -e "1. Run ${GREEN}media-downloader \"share text or link\"${NC} anywhere in the terminal."
    fi
fi
echo -e "=================================================="
