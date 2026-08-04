#!/bin/bash
# -----------------------------------------------------------------------------
# TikTok & Douyin Downloader - Linux One-Click Installer
# -----------------------------------------------------------------------------

set -e

# GitHub Repository Configuration
GITHUB_USER="Francis-Xavier-code"
GITHUB_REPO="tiktok-douyin-dl"
RELEASE_TAG="v1.8.0"

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
    
    if [ -f "$local_file" ]; then
        if [ "$USER_LANG" = "zh" ]; then
            echo -e "📦 检测到本地已编译好的二进制文件，正在安装 $name ..."
        else
            echo -e "📦 Local pre-compiled binary found, installing $name ..."
        fi
        cp "$local_file" "$INSTALL_DIR/"
    else
        if [ "$GITHUB_USER" = "YOUR_GITHUB_USERNAME" ] || [ "$GITHUB_REPO" = "YOUR_GITHUB_REPO" ]; then
            echo -e "${RED}❌ Error: GITHUB_USER / GITHUB_REPO not configured in install.sh.${NC}"
            exit 1
        fi

        DOWNLOAD_URL="https://github.com/$GITHUB_USER/$GITHUB_REPO/releases/download/$RELEASE_TAG/$name"

        if [ "$USER_LANG" = "zh" ]; then
            echo -e "⚡ 正在从 GitHub $RELEASE_TAG 下载 $name ..."
        else
            echo -e "⚡ Downloading $name from GitHub release $RELEASE_TAG ..."
        fi

        if ! curl -fL --retry 3 --retry-delay 2 -# "$DOWNLOAD_URL" -o "$INSTALL_DIR/$name"; then
            rm -f "$INSTALL_DIR/$name"
            if [ "$USER_LANG" = "zh" ]; then
                echo -e "${RED}❌ 错误: 无法从 $RELEASE_TAG 下载 $name。${NC}"
            else
                echo -e "${RED}❌ Error: Failed to download $name from $RELEASE_TAG.${NC}"
            fi
            exit 1
        fi
    fi
    
    chmod +x "$INSTALL_DIR/$name"
}

# Install the unified auto-detecting CLI
install_binary "media-downloader"

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
