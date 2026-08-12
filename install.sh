#!/bin/bash
# -----------------------------------------------------------------------------
# TikTok & Douyin Downloader - Linux / macOS One-Click Installer
#
#   curl -fsSL https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/install.sh | bash
#
# Options:
#   --lang zh|en     Force language (auto-detected from $LANG by default)
#   --yes, -y        Skip all prompts (non-interactive mode)
#   --force          Reinstall even when the same version is already installed
#   --uninstall      Remove the installation, the command link and PATH entries
#   --no-color       Disable ANSI colors
#   --quiet          Only print warnings and errors
#   --help, -h       Show this help
# -----------------------------------------------------------------------------

set -euo pipefail

# GitHub Repository Configuration
GITHUB_USER="Francis-Xavier-code"
GITHUB_REPO="tiktok-douyin-dl"
RELEASE_TAG="v2.0.0"

INSTALL_DIR="$HOME/.local/share/tiktok-douyin-dl"
BIN_DIR="$HOME/.local/bin"
CLI_NAME="media-downloader"

# -----------------------------------------------------------------------------
# Global state
# -----------------------------------------------------------------------------
USE_COLOR=0
ANIMATE=0
QUIET=0
NO_COLOR=0
INTERACTIVE=0
ASSUME_YES=0
FORCE=0
DO_UNINSTALL=0
FORCE_LANG=""
NEED_SOURCE=false
USER_LANG=""
SHOW_CHANGELOG=0
INSTALLED_VER=""

TMP_FILES=()
cleanup() {
    local f
    for f in "${TMP_FILES[@]:-}"; do
        rm -f "$f"
    done
}
trap cleanup EXIT

# -----------------------------------------------------------------------------
# Output helpers — colors and the spinner only run on a real terminal
# -----------------------------------------------------------------------------
# color <ansi-code> <text>
color() {
    if [ "$USE_COLOR" = "1" ]; then
        printf '\033[%sm%s\033[0m' "$1" "$2"
    else
        printf '%s' "$2"
    fi
}

log()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }
info() { [ "$QUIET" = "1" ] || printf '    %s %s\n' "$(color '36' 'ℹ')" "$*"; }
ok()   { [ "$QUIET" = "1" ] || printf '    %s %s\n' "$(color '32' '✔')" "$*"; }
warn() { printf '    %s %s\n' "$(color '33' '⚠')" "$*" >&2; }
err()  { printf '    %s %s\n' "$(color '31' '✖')" "$*" >&2; }

# --- step framework: "[1/5] ▸ description" --------------------------------
STEP_TOTAL=0
STEP_CURRENT=0
step() {
    STEP_CURRENT=$((STEP_CURRENT + 1))
    [ "$QUIET" = "1" ] && return
    printf '    %s %s %s\n' \
        "$(color '90' "[$STEP_CURRENT/$STEP_TOTAL]")" \
        "$(color '1;36' '▸')" \
        "$*"
}

# --- i18n: T "中文" "English" ---------------------------------------------
T() {
    if [ "$USER_LANG" = "zh" ]; then
        printf '%s' "$1"
    else
        printf '%s' "$2"
    fi
}

# -----------------------------------------------------------------------------
# CLI arguments
# -----------------------------------------------------------------------------
usage() {
    cat <<'EOF'
Usage: install.sh [options]

Run without options on an interactive terminal to choose an action from a menu
(install / force-reinstall / uninstall / exit). Options are for scripting and
piped installs (curl URL | bash -s -- <option>):

Options:
  --lang zh|en     Force language (auto-detected from $LANG by default)
  --yes, -y        Skip all prompts (non-interactive mode)
  --force          Reinstall even when the same version is already installed
  --uninstall      Remove the installation, the command link and PATH entries
  --no-color       Disable ANSI colors
  --quiet          Only print warnings and errors
  --help, -h       Show this help
EOF
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --lang)
                FORCE_LANG="${2:-}"
                if [ "$FORCE_LANG" != "zh" ] && [ "$FORCE_LANG" != "en" ]; then
                    err "Invalid --lang value: '$FORCE_LANG' (expected zh or en)"
                    exit 2
                fi
                shift 2
                ;;
            --yes|-y) ASSUME_YES=1; shift ;;
            --force|-f) FORCE=1; shift ;;
            --uninstall) DO_UNINSTALL=1; shift ;;
            --no-color) NO_COLOR=1; shift ;;
            --quiet|-q) QUIET=1; shift ;;
            --help|-h) usage; exit 0 ;;
            *) err "Unknown option: $1"; usage >&2; exit 2 ;;
        esac
    done
}

detect_tty() {
    [ -t 1 ] && USE_COLOR=1 || USE_COLOR=0
    [ -t 1 ] && ANIMATE=1 || ANIMATE=0
    [ -t 0 ] && INTERACTIVE=1 || INTERACTIVE=0
    [ "$NO_COLOR" = "1" ] && USE_COLOR=0
    [ "$QUIET" = "1" ] && { ANIMATE=0; USE_COLOR=0; }
    return 0
}

# -----------------------------------------------------------------------------
# Language selection
# -----------------------------------------------------------------------------
detect_lang() {
    case "${LC_ALL:-}${LANG:-}" in
        *zh*) echo "zh" ;;
        *) echo "en" ;;
    esac
}

choose_language() {
    local detected
    detected=$(detect_lang)
    USER_LANG="$detected"

    if [ -n "$FORCE_LANG" ]; then
        USER_LANG="$FORCE_LANG"
        ok "Language forced to: $USER_LANG"
        return 0
    fi

    if [ "$INTERACTIVE" = "1" ] && [ "$ASSUME_YES" = "0" ]; then
        local default_num=1
        [ "$detected" = "en" ] && default_num=2
        printf '\n    %s %s\n' "$(color '1;33' '🌐')" "$(T "请选择语言 / Choose a language:" "Please choose a language:")"
        printf '        1) 简体中文\n        2) English\n'
        printf '    %s [1-2]（回车 = %s）: ' "$(color '1;33' '请输入序号 / Enter option')" "$default_num"
        local ans=""
        if read -r ans < /dev/tty; then :; else ans=""; fi
        case "$ans" in
            2|en|EN|english) USER_LANG="en" ;;
            1|zh|ZH|zh_CN) USER_LANG="zh" ;;
            *) USER_LANG="$detected" ;;
        esac
    fi

    ok "$(T "语言：简体中文" "Language: English")"
}

# -----------------------------------------------------------------------------
# Banner
# -----------------------------------------------------------------------------
print_banner() {
    [ "$QUIET" = "1" ] && return
    local line
    line=$(color '36' "──────────────────────────────────────────────")
    printf '\n%s\n' "$line"
    printf '%s\n' "$(color '1;36' "   🚀  TikTok & Douyin Downloader  一键安装 / One-Click Installer")"
    printf '%s\n' "$(color '36' "       $GITHUB_USER/$GITHUB_REPO  ·  $RELEASE_TAG")"
    printf '%s\n' "$line"
    printf '\n'
}

# -----------------------------------------------------------------------------
# Step 1 · System / architecture detection
# -----------------------------------------------------------------------------
detect_env() {
    step "$(T "检测系统环境" "Detecting system environment")"

    OS="$(uname -s)"
    case "$OS" in
        Darwin|Linux) : ;;
        *)
            err "$(T "不支持的系统: ${OS}（仅支持 Linux / macOS）。" "Unsupported OS: $OS (Linux / macOS only).")"
            exit 1
            ;;
    esac

    if [ "$OS" = "Darwin" ]; then
        # Detect the native arch even when running under Rosetta.
        if [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = "1" ]; then
            ARCH="arm64"
        else
            ARCH="$(uname -m)"
        fi
        ok "$(T "系统: macOS ($ARCH)" "System: macOS ($ARCH)")"
    else
        ARCH="$(uname -m)"
        if [ "$ARCH" != "x86_64" ]; then
            warn "$(T "当前架构 $ARCH 没有原生构建，将安装 x86_64 版本（可能需要兼容层运行）。" "No native build for $ARCH; installing the x86_64 build (may need emulation).")"
        fi
        ok "$(T "系统: Linux ($ARCH)" "System: Linux ($ARCH)")"
    fi
}

# -----------------------------------------------------------------------------
# Download progress helpers
# -----------------------------------------------------------------------------
PROGRESS_WIDTH=30
PROGRESS_ESC=$(printf '\033')

progress_spinner() {
    case $(($1 % 10)) in
        0) printf '⠋' ;; 1) printf '⠙' ;; 2) printf '⠹' ;; 3) printf '⠸' ;; 4) printf '⠼' ;;
        5) printf '⠴' ;; 6) printf '⠦' ;; 7) printf '⠧' ;; 8) printf '⠇' ;; *) printf '⠏' ;;
    esac
}

file_size() {
    local f=$1
    if [ -f "$f" ]; then
        if [ "$(uname -s)" = "Darwin" ]; then
            stat -f%z "$f" 2>/dev/null || echo 0
        else
            stat -c%s "$f" 2>/dev/null || echo 0
        fi
    else
        echo 0
    fi
}

remote_size() {
    local url=$1
    curl -sIL --connect-timeout 8 --max-time 20 "$url" 2>/dev/null \
        | tr -d '\r' \
        | awk -F': ' 'tolower($1)=="content-length" {len=$2} END {gsub(/[^0-9]/,"",len); print len+0}'
}

human_size() {
    local bytes=$1
    if [ "$bytes" -lt 1024 ]; then
        echo "${bytes} B"
    elif [ "$bytes" -lt 1048576 ]; then
        awk -v b="$bytes" 'BEGIN { printf "%.1f KiB", b/1024 }'
    elif [ "$bytes" -lt 1073741824 ]; then
        awk -v b="$bytes" 'BEGIN { printf "%.1f MiB", b/1048576 }'
    else
        awk -v b="$bytes" 'BEGIN { printf "%.2f GiB", b/1073741824 }'
    fi
}

# Render one frame: $1=pct(-1 unknown) $2=frame $3=label $4=downloaded $5=total
render_progress() {
    local pct=$1 frame=$2 label=$3 got=$4 total=$5
    local esc="$PROGRESS_ESC"
    local width=$PROGRESS_WIDTH
    local reset="${esc}[0m" dim="${esc}[2m" bold="${esc}[1m"
    local green="${esc}[32m" cyan="${esc}[36m" yellow="${esc}[33m"
    local spinner
    spinner=$(progress_spinner "$frame")

    local filled=0 third=$((width / 3)) i=0
    if [ "$pct" -ge 0 ]; then
        filled=$(( pct * width / 100 ))
        [ "$filled" -gt "$width" ] && filled=$width
    fi
    local bar=""
    while [ "$i" -lt "$width" ]; do
        if [ "$i" -lt "$filled" ]; then
            if [ "$i" -lt "$third" ]; then
                bar="${bar}${green}█${reset}"
            elif [ "$i" -lt $((third * 2)) ]; then
                bar="${bar}${cyan}█${reset}"
            else
                bar="${bar}${yellow}█${reset}"
            fi
        elif [ "$i" -eq "$filled" ] && [ "$pct" -ge 0 ]; then
            bar="${bar}${bold}${esc}[37m▓${reset}"
        else
            bar="${bar}${dim}░${reset}"
        fi
        i=$((i + 1))
    done

    local pct_str size_str=""
    if [ "$pct" -lt 0 ]; then
        pct_str="  --"
    else
        pct_str=$(printf '%3d' "$pct")
    fi
    if [ "$total" -gt 0 ]; then
        size_str=" $(human_size "$got")/$(human_size "$total")"
    elif [ "$got" -gt 0 ]; then
        size_str=" $(human_size "$got")"
    fi

    printf '\r\033[K  %s %s %s%%%s %s ' "$spinner" "$bar" "$pct_str" "$size_str" "$label"
}

# Download a file. Animates a colored progress bar on a TTY, stays silent
# otherwise. Returns curl's exit status.
download_with_progress() {
    local url=$1 output=$2 label=$3
    local total err_file status=0
    total=$(remote_size "$url")
    err_file="${output}.err"
    rm -f "$err_file" "$output"

    if [ "$ANIMATE" = "1" ]; then
        curl -fL --connect-timeout 8 --max-time 300 --retry 2 --retry-delay 2 -sS "$url" -o "$output" 2>"$err_file" &
        local pid=$!
        local downloaded=0 pct=-1 frame=0
        while kill -0 "$pid" 2>/dev/null; do
            downloaded=$(file_size "$output")
            if [ "$total" -gt 0 ]; then
                pct=$((downloaded * 100 / total))
                [ "$pct" -gt 100 ] && pct=100
            else
                pct=-1
            fi
            render_progress "$pct" "$frame" "$label" "$downloaded" "$total"
            frame=$((frame + 1))
            sleep 0.08
        done
        wait "$pid" || status=$?
        if [ "$status" -eq 0 ]; then
            if [ "$total" -gt 0 ]; then
                render_progress 100 "$frame" "$label" "$total" "$total"
            else
                render_progress -1 "$frame" "$label" "$(file_size "$output")" 0
            fi
        fi
        printf '\r\033[K'
    else
        curl -fL --connect-timeout 8 --max-time 300 --retry 2 --retry-delay 2 -sS "$url" -o "$output" 2>"$err_file" || status=$?
    fi

    if [ "$status" -ne 0 ] && [ -s "$err_file" ]; then
        sed 's/^/    /' "$err_file" >&2 || true
    fi
    rm -f "$err_file"
    return "$status"
}

# -----------------------------------------------------------------------------
# SHA256 verification (fail-open: skips when no checksum file is published)
# -----------------------------------------------------------------------------
verify_checksum() {
    local archive=$1 file=$2
    local checksum_url="https://github.com/$GITHUB_USER/$GITHUB_REPO/releases/download/$RELEASE_TAG/SHA256SUMS.txt"
    local -a mirrors=(
        "$checksum_url"
        "https://gh-proxy.com/$checksum_url"
        "https://ghproxy.net/$checksum_url"
        "https://fastly.jsdelivr.net/gh/$GITHUB_USER/$GITHUB_REPO@$RELEASE_TAG/SHA256SUMS.txt"
    )
    local tmp_sum url got=false
    tmp_sum="$(mktemp)"
    TMP_FILES+=("$tmp_sum")
    for url in "${mirrors[@]}"; do
        if curl -fsL --connect-timeout 8 --max-time 15 "$url" -o "$tmp_sum" 2>/dev/null; then
            got=true
            break
        fi
    done
    if [ "$got" != "true" ]; then
        warn "$(T "无法获取 SHA256 校验文件，跳过校验。" "SHA256 checksum file unavailable; skipping verification.")"
        return 0
    fi

    local expected actual
    expected=$(awk -v name="$archive" '$2==name {print $1}' "$tmp_sum" | head -1)
    rm -f "$tmp_sum"
    if [ -z "$expected" ]; then
        warn "$(T "发布包中未找到 $archive 的校验值，跳过校验。" "No checksum entry for $archive; skipping verification.")"
        return 0
    fi

    if command -v sha256sum >/dev/null 2>&1; then
        actual=$(sha256sum "$file" | awk '{print $1}')
    else
        actual=$(shasum -a 256 "$file" | awk '{print $1}')
    fi
    if [ "$actual" = "$expected" ]; then
        ok "$(T "SHA256 校验通过" "SHA256 verification passed")"
        return 0
    fi
    err "$(T "SHA256 校验失败：文件可能损坏或被篡改。" "SHA256 verification failed: file may be corrupted or tampered with.")"
    return 1
}

# -----------------------------------------------------------------------------
# Upgrade detection
# -----------------------------------------------------------------------------
installed_version() {
    if [ -x "$INSTALL_DIR/$CLI_NAME" ]; then
        "$INSTALL_DIR/$CLI_NAME" --version 2>/dev/null \
            | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
    fi
}

# Returns 0 when we should (re)install, 1 when the user wants to skip.
check_upgrade() {
    local current target
    current="$(installed_version 2>/dev/null)" || current=""
    target="${RELEASE_TAG#v}"

    if [ -n "$current" ] && [ "$current" = "$target" ]; then
        if [ "$FORCE" = "1" ]; then
            return 0
        fi
        if [ "$ASSUME_YES" = "0" ] && [ "$INTERACTIVE" = "1" ]; then
            printf '    %s ' "$(T "已安装 v${current}，是否重新安装？[y/N]：" "v${current} is already installed. Reinstall? [y/N]: ")"
            local ans=""
            if read -r ans < /dev/tty; then :; else ans=""; fi
            if [ "$ans" = "y" ] || [ "$ans" = "Y" ] || [ "$ans" = "yes" ]; then
                return 0
            fi
            info "$(T "跳过安装。" "Skipping installation.")"
            return 1
        fi
        info "$(T "已安装 v${current}，跳过（--force 可强制重装）。" "v${current} already installed; skipping (use --force to reinstall).")"
        return 1
    fi

    if [ -n "$current" ]; then
        info "$(T "检测到已安装 v${current}，将升级到 v${target}。" "Found v${current}; upgrading to v${target}.")"
    fi
    return 0
}

# -----------------------------------------------------------------------------
# Step 2 · Download / extract / install the binary
# -----------------------------------------------------------------------------
install_binary() {
    local name=$1
    local local_file="dist/$name"
    local version="${RELEASE_TAG#v}"
    local os_type archive_name arch

    step "$(T "下载并安装程序" "Downloading and installing")"

    # Prefer a locally compiled binary (dev workflow).
    if [ -f "$local_file" ]; then
        cp "$local_file" "$INSTALL_DIR/"
        if [ -d "dist/ms-playwright" ]; then
            cp -r "dist/ms-playwright" "$INSTALL_DIR/"
        fi
        chmod +x "$INSTALL_DIR/$name"
        ok "$(T "已安装本地构建 $name" "Installed local build $name")"
        return 0
    fi

    if [ "$GITHUB_USER" = "YOUR_GITHUB_USERNAME" ] || [ "$GITHUB_REPO" = "YOUR_GITHUB_REPO" ]; then
        err "GITHUB_USER / GITHUB_REPO not configured in install.sh."
        exit 1
    fi

    if ! check_upgrade; then
        return 1
    fi

    if [ "$OS" = "Darwin" ]; then
        os_type="macos"
        arch="$ARCH"
        archive_name="MediaDownloader-macOS-${arch}-CLI-${version}.zip"
    else
        os_type="linux"
        arch="x86_64"
        archive_name="MediaDownloader-Linux-x86_64-${version}.tar.gz"
    fi
    local raw_url="https://github.com/$GITHUB_USER/$GITHUB_REPO/releases/download/$RELEASE_TAG/$archive_name"

    # Mirror URLs: direct GitHub first, then domestic accelerators.
    local -a MIRROR_URLS=(
        "$raw_url"
        "https://gh-proxy.com/$raw_url"
        "https://ghproxy.net/$raw_url"
    )

    local tmp_archive
    tmp_archive="$(mktemp)"
    TMP_FILES+=("$tmp_archive")

    local download_ok=false mirror_idx=1 mirror_total=${#MIRROR_URLS[@]}
    for url in "${MIRROR_URLS[@]}"; do
        local dl_label
        if [ "$USER_LANG" = "zh" ]; then
            dl_label="下载 $archive_name (镜像 $mirror_idx/$mirror_total)"
        else
            dl_label="Downloading $archive_name (mirror $mirror_idx/$mirror_total)"
        fi
        if download_with_progress "$url" "$tmp_archive" "$dl_label" \
            && verify_checksum "$archive_name" "$tmp_archive"; then
            download_ok=true
            break
        fi
        rm -f "$tmp_archive"
        if [ "$mirror_idx" -lt "$mirror_total" ]; then
            warn "$(T "下载失败，尝试下一个镜像..." "Download failed, trying next mirror...")"
        fi
        mirror_idx=$((mirror_idx + 1))
    done

    if [ "$download_ok" != "true" ]; then
        err "$(T "错误: 所有下载源均失败（${RELEASE_TAG}）。" "Error: All download sources failed ($RELEASE_TAG).")"
        err "$(T "请检查网络或开启代理后重试。" "Please check your network or enable a proxy and retry.")"
        exit 1
    fi

    if [ "$os_type" = "macos" ]; then
        if ! command -v unzip >/dev/null 2>&1; then
            err "$(T "未找到 unzip，请先安装（如: brew install unzip）。" "unzip is required; install it first (e.g. brew install unzip).")"
            exit 1
        fi
        unzip -q -o "$tmp_archive" -d "$INSTALL_DIR"
    else
        tar -xzf "$tmp_archive" -C "$INSTALL_DIR"
    fi

    if [ ! -f "$INSTALL_DIR/$name" ]; then
        err "$(T "错误: 解压后未找到 ${name}。" "Error: $name not found after extraction.")"
        exit 1
    fi

    chmod +x "$INSTALL_DIR/$name"

    # macOS: drop the quarantine attribute so Gatekeeper doesn't kill the binary
    if [ "$os_type" = "macos" ]; then
        xattr -dr com.apple.quarantine "$INSTALL_DIR/$name" 2>/dev/null || true
    fi

    ok "$(T "已安装到 $INSTALL_DIR" "Installed to $INSTALL_DIR")"
    return 0
}

# -----------------------------------------------------------------------------
# Step 3 · Link the command
# -----------------------------------------------------------------------------
configure_command() {
    step "$(T "配置启动命令" "Configuring command")"
    ln -sf "$INSTALL_DIR/$CLI_NAME" "$BIN_DIR/$CLI_NAME"
    ok "$(T "命令已链接: $BIN_DIR/$CLI_NAME" "Command linked: $BIN_DIR/$CLI_NAME")"
}

# -----------------------------------------------------------------------------
# Step 4 · PATH configuration (shell-aware)
# -----------------------------------------------------------------------------
configure_path() {
    step "$(T "配置环境变量" "Configuring PATH")"
    if [[ ":$PATH:" == *":$BIN_DIR:"* ]]; then
        ok "$(T "已在 PATH 中，跳过配置。" "Already on PATH; skipping.")"
        return 0
    fi

    local -a rc_files=()
    case "${SHELL:-}" in
        */zsh) rc_files=("$HOME/.zshrc") ;;
        */bash) rc_files=("$HOME/.bashrc") ;;
        *)
            warn "$(T "无法识别的 shell: ${SHELL:-unknown}。请手动将以下内容加入你的配置文件：" "Unrecognized shell: ${SHELL:-unknown}. Add the following line to your shell config manually:")"
            warn 'export PATH="$HOME/.local/bin:$PATH"'
            return 1
            ;;
    esac

    local updated=false rc
    for rc in "${rc_files[@]}"; do
        if [ -f "$rc" ] && ! grep -qF 'export PATH="$HOME/.local/bin:$PATH"' "$rc"; then
            printf '\n# added by tiktok-douyin-dl installer\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
            updated=true
        elif [ ! -f "$rc" ]; then
            printf '# added by tiktok-douyin-dl installer\nexport PATH="$HOME/.local/bin:$PATH"\n' > "$rc"
            updated=true
        fi
    done

    if [ "$updated" = "true" ]; then
        NEED_SOURCE=true
        ok "$(T "已写入 $(basename "${rc_files[0]}")，新终端生效。" "Written to $(basename "${rc_files[0]}"); effective in new terminals.")"
    else
        ok "$(T "PATH 配置已就绪。" "PATH configuration is already in place.")"
    fi
}

# -----------------------------------------------------------------------------
# Step 5 · Verify the installation
# -----------------------------------------------------------------------------
verify_install() {
    step "$(T "验证安装" "Verifying installation")"
    if [ -x "$INSTALL_DIR/$CLI_NAME" ]; then
        INSTALLED_VER="$(installed_version 2>/dev/null)" || INSTALLED_VER=""
        if [ -n "$INSTALLED_VER" ]; then
            ok "$(T "安装成功，版本 v$INSTALLED_VER" "Installed successfully, v$INSTALLED_VER")"
        else
            ok "$(T "安装成功" "Installed successfully")"
        fi
    else
        err "$(T "验证失败：未找到可执行文件。" "Verification failed: executable not found.")"
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Changelog for the installed version (CLI + 全平台 entries)
# -----------------------------------------------------------------------------
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
    TMP_FILES+=("$tmp_json")
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
    print(f"  {title}  v{version}")
    print("  " + "-" * 48)
    for e in entries:
        for line in str(e).splitlines():
            print(f"    • {line}")
    print("  " + "-" * 48)
except Exception:
    pass
PY
    fi
}

# -----------------------------------------------------------------------------
# Success message
# -----------------------------------------------------------------------------
print_success() {
    [ "$QUIET" = "1" ] && return
    local bar success cmd notes_header source_msg
    bar=$(color '32' "──────────────────────────────────────────────")
    success="$(T "🎉 安装与配置成功！" "🎉 Installation & Configuration Successful!")"
    cmd="media-downloader \"$(T "分享文本或链接" "share text or link")\""
    notes_header="$(T "使用提示 / Notes:" "Notes:")"
    source_msg="$(T "新开一个终端窗口（或运行 source ~/.zshrc / ~/.bashrc）使 PATH 生效。" "Open a new terminal window (or run 'source ~/.zshrc') to apply PATH.")"

    printf '\n%s\n' "$bar"
    printf '    %s\n' "$(color '1;32' "$success")"
    printf '%s\n' "$bar"
    printf '    %s\n' "$(color '34' "📁  $INSTALL_DIR")"
    printf '    %s\n' "$(color '1;32' "🚀  $cmd")"
    printf '    %s\n' "$(T "🔎  自动识别抖音或 TikTok 链接。" "🔎  Platform is auto-detected from the link.")"
    printf '\n'
    printf '    %s\n' "$(color '33' "🔔  $notes_header")"
    local n=1
    if [ "$NEED_SOURCE" = "true" ]; then
        printf '    %d. %s\n' "$n" "$(color '33' "$source_msg")"
        n=$((n + 1))
    fi
    printf '    %d. %s\n' "$n" "$(T "查看帮助: media-downloader --help" "See help: media-downloader --help")"
    n=$((n + 1))
    printf '    %d. %s\n' "$n" "$(T "卸载: 重新运行本脚本选“卸载”菜单项（或加 --uninstall 参数）" "Uninstall: rerun this script and pick Uninstall in the menu (or pass --uninstall)")"
    printf '\n'
}

# -----------------------------------------------------------------------------
# Uninstall
# -----------------------------------------------------------------------------
do_uninstall() {
    printf '\n%s\n' "$(color '1;36' "🗑  TikTok & Douyin Downloader 卸载 / Uninstall")"
    printf '\n'

    rm -f "$BIN_DIR/$CLI_NAME"
    ok "$(T "已删除命令链接 $BIN_DIR/$CLI_NAME" "Removed command link $BIN_DIR/$CLI_NAME")"

    rm -rf "$INSTALL_DIR"
    ok "$(T "已删除安装目录 $INSTALL_DIR" "Removed installation directory $INSTALL_DIR")"

    local -a rc_files=("$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.zprofile")
    local rc
    for rc in "${rc_files[@]}"; do
        if [ -f "$rc" ] && grep -qF 'export PATH="$HOME/.local/bin:$PATH"' "$rc"; then
            sed -i.bak \
                '/# added by tiktok-douyin-dl installer/d; /^export PATH="\$HOME\/\.local\/bin:\$PATH"$/d' \
                "$rc" && rm -f "$rc.bak"
            ok "$(T "已从 $rc 移除 PATH 配置。" "Removed PATH entry from $rc.")"
        fi
    done

    local done_msg
    done_msg="$(T "卸载完成。" "Uninstall complete.")"
    printf '\n%s\n' "$(color '1;32' "✔  $done_msg")"
}

# -----------------------------------------------------------------------------
# Interactive action menu (shown when run without options on a real terminal)
# -----------------------------------------------------------------------------
run_menu() {
    while true; do
        local installed=""
        if [ -x "$INSTALL_DIR/$CLI_NAME" ]; then
            installed="$(installed_version 2>/dev/null)" || installed=""
            printf '    %s\n' "$(color '1;33' "⚙  $(T "当前已安装:" "Currently installed:") v${installed:-?}")"
        else
            printf '    %s\n' "$(color '33' "ℹ  $(T "未检测到已安装的程序" "No installation detected")")"
        fi
        printf '\n    %s\n' "$(color '1;36' "$(T "请选择操作 / Choose an action:" "Choose an action:")")"
        printf '    1) %s\n' "$(T "🚀 安装 / 重新安装" "🚀 Install / Reinstall")"
        printf '    2) %s\n' "$(T "🔁 强制重新安装" "🔁 Force reinstall")"
        printf '    3) %s\n' "$(T "🗑  卸载" "🗑  Uninstall")"
        printf '    4) %s\n' "$(T "退出" "Exit")"
        printf '    %s [1-4]: ' "$(color '1;33' "$(T "请输入 / Enter" "Enter")")"
        local choice=""
        if read -r choice < /dev/tty; then :; else choice=""; fi
        case "$choice" in
            1) FORCE=0; printf '\n'; return 0 ;;
            2) FORCE=1; printf '\n'; return 0 ;;
            3) do_uninstall; exit 0 ;;
            4|q|Q|exit) printf '\n'; exit 0 ;;
            *) warn "$(T "无效选项: $choice" "Invalid option: $choice")"; printf '\n' ;;
        esac
    done
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    parse_args "$@"
    if [ "$DO_UNINSTALL" = "1" ]; then
        do_uninstall
        exit 0
    fi
    detect_tty

    mkdir -p "$INSTALL_DIR" "$BIN_DIR"

    STEP_TOTAL=5
    choose_language
    print_banner

    # Interactive menu unless an explicit action was given on the command line.
    if [ "$INTERACTIVE" = "1" ] && [ "$ASSUME_YES" = "0" ] \
        && [ "$FORCE" = "0" ] && [ -z "$FORCE_LANG" ]; then
        run_menu
    fi

    # Write language configuration
    printf '{"lang": "%s"}\n' "$USER_LANG" > "$INSTALL_DIR/config.json"

    detect_env
    if install_binary "$CLI_NAME"; then
        SHOW_CHANGELOG=1
    fi
    configure_command
    configure_path || true
    verify_install
    if [ "$SHOW_CHANGELOG" = "1" ] && [ "$QUIET" = "0" ]; then
        show_changelog
    fi
    print_success
}

main "$@"
