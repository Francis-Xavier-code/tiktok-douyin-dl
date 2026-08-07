#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="Francis-Xavier-code/tiktok-douyin-dl"
DEFAULT_OUTPUT="downloads"

managed_root="${MEDIA_DOWNLOADER_HOME:-}"
if [[ -z "$managed_root" ]]; then
  if [[ -n "${XDG_DATA_HOME:-}" ]]; then
    managed_root="$XDG_DATA_HOME/media-downloader-skill"
  else
    : "${HOME:?HOME is required when MEDIA_DOWNLOADER_HOME and XDG_DATA_HOME are unset}"
    managed_root="$HOME/.local/share/media-downloader-skill"
  fi
fi

managed_binary="$managed_root/media-downloader"
version_file="$managed_root/version"
custom_binary="${MEDIA_DOWNLOADER_BIN:-}"
output_directory="$DEFAULT_OUTPUT"
platform_override=""
share_text=""
install_requested=false
update_requested=false
temporary_directory=""

cleanup() {
  if [[ -n "$temporary_directory" && -d "$temporary_directory" ]]; then
    rm -rf -- "$temporary_directory"
  fi
}
trap cleanup EXIT

usage() {
  cat <<'USAGE'
Usage:
  download.sh [--output DIR] [--platform douyin|tiktok] -- "SHARE TEXT OR URL"
  download.sh --install
  download.sh --update
  download.sh --version

Environment:
  MEDIA_DOWNLOADER_BIN       Use an existing CLI executable.
  MEDIA_DOWNLOADER_HOME      Override the managed installation directory.
  MEDIA_DOWNLOADER_VERSION   Install a specific release, for example v1.8.0.
USAGE
}

fail() {
  printf 'media-downloader skill: %s\n' "$*" >&2
  exit 1
}

require_value() {
  local option_name="$1"
  local option_value="${2:-}"
  [[ -n "$option_value" ]] || fail "$option_name requires a value"
}

normalize_share_text() {
  local input="$1"
  local search_result_pattern='https?://([A-Za-z0-9-]+\.)*douyin\.com/[^[:space:]]*[?&]modal_id=([0-9]{10,})'
  local direct_video_pattern='https?://([A-Za-z0-9-]+\.)*douyin\.com/[^[:space:]]*/video/([0-9]{10,})'
  local direct_note_pattern='https?://([A-Za-z0-9-]+\.)*douyin\.com/[^[:space:]]*/note/([0-9]{10,})'
  local search_page_pattern='https?://([A-Za-z0-9-]+\.)*douyin\.com/(root/)?search/'
  if [[ "$input" =~ $search_result_pattern ]]; then
    printf 'https://www.douyin.com/video/%s\n' "${BASH_REMATCH[2]}"
  elif [[ "$input" =~ $direct_video_pattern ]]; then
    printf 'https://www.douyin.com/video/%s\n' "${BASH_REMATCH[2]}"
  elif [[ "$input" =~ $direct_note_pattern ]]; then
    printf 'https://www.douyin.com/note/%s\n' "${BASH_REMATCH[2]}"
  elif [[ "$input" =~ $search_page_pattern ]]; then
    fail "the Douyin search page does not identify one work; select a result URL containing modal_id"
  else
    printf '%s\n' "$input"
  fi
}

managed_install() {
  [[ -z "$custom_binary" ]] || fail "cannot install or update when MEDIA_DOWNLOADER_BIN is set"
  command -v curl >/dev/null 2>&1 || fail "curl is required to install the CLI"

  local operating_system architecture requested_version asset_url resolved_version archive_fmt
  operating_system="$(uname -s)"
  architecture="$(uname -m)"
  case "$operating_system" in
    Linux)
      case "$architecture" in
        x86_64|amd64) archive_fmt="MediaDownloader-Linux-x86_64-%s.tar.gz" ;;
        *) fail "no official Linux release binary is available for architecture $architecture" ;;
      esac
      ;;
    Darwin)
      command -v unzip >/dev/null 2>&1 || fail "unzip is required to install the macOS CLI"
      case "$architecture" in
        arm64) archive_fmt="MediaDownloader-macOS-arm64-CLI-%s.zip" ;;
        x86_64) archive_fmt="MediaDownloader-macOS-x86_64-CLI-%s.zip" ;;
        *) fail "no official macOS release binary is available for architecture $architecture" ;;
      esac
      ;;
    *)
      fail "automatic installation supports Linux and macOS only; set MEDIA_DOWNLOADER_BIN on $operating_system"
      ;;
  esac

  requested_version="${MEDIA_DOWNLOADER_VERSION:-}"
  if [[ -n "$requested_version" ]]; then
    [[ "$requested_version" == v* ]] || requested_version="v$requested_version"
    [[ "$requested_version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "invalid MEDIA_DOWNLOADER_VERSION: $requested_version"
    resolved_version="$requested_version"
  else
    # Resolve the latest release version from the shared changelog.json (raw-file
    # mirrors, reliable in CN); fall back to the /releases/latest redirect.
    resolved_version="$(curl -fsSL --retry 3 --proto '=https' --tlsv1.2 \
      "https://raw.githubusercontent.com/$REPOSITORY/main/changelog.json" 2>/dev/null \
      | grep -o '"version": *"[^"]*"' | head -1 \
      | sed 's/.*"version": *"\([^"]*\)".*/\1/' || true)"
    if [[ -z "$resolved_version" ]]; then
      resolved_version="$(curl -fsSI --retry 2 -o /dev/null -w '%{url_effective}' \
        "https://github.com/$REPOSITORY/releases/latest" 2>/dev/null \
        | sed -n 's#.*/tag/\(v[0-9.]*\)[^0-9]*.*#\1#p' || true)"
    fi
    [[ -n "$resolved_version" ]] || fail "could not resolve the latest release version"
  fi

  local archive_name
  printf -v archive_name "$archive_fmt" "${resolved_version#v}"
  asset_url="https://github.com/$REPOSITORY/releases/download/$resolved_version/$archive_name"

  temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/media-downloader-skill.XXXXXX")"
  printf 'Downloading official CLI from %s\n' "$asset_url" >&2
  local tmp_archive="$temporary_directory/archive"
  local download_ok=false
  for url in "$asset_url" "https://gh-proxy.com/$asset_url" "https://ghproxy.net/$asset_url"; do
    if curl --fail --location --retry 2 --proto '=https' --tlsv1.2 --output "$tmp_archive" "$url" 2>/dev/null; then
      download_ok=true
      break
    fi
  done
  [[ "$download_ok" == true ]] || fail "failed to download $asset_url"

  if [[ "$operating_system" == "Linux" ]]; then
    tar -xzf "$tmp_archive" -C "$temporary_directory"
  else
    unzip -q -o "$tmp_archive" -d "$temporary_directory"
    # macOS: drop the quarantine attribute so Gatekeeper doesn't block first run
    xattr -dr com.apple.quarantine "$temporary_directory/media-downloader" 2>/dev/null || true
  fi
  chmod 0755 "$temporary_directory/media-downloader"
  mkdir -p "$managed_root"
  mv "$temporary_directory/media-downloader" "$managed_binary"
  printf '%s\n' "$resolved_version" > "$version_file"
  printf 'Installed %s at %s\n' "$resolved_version" "$managed_binary" >&2
}

show_version() {
  if [[ -n "$custom_binary" ]]; then
    [[ -x "$custom_binary" ]] || fail "MEDIA_DOWNLOADER_BIN is not executable: $custom_binary"
    printf 'media-downloader custom executable %s\n' "$custom_binary"
  elif [[ -r "$version_file" ]]; then
    printf 'media-downloader managed release %s\n' "$(sed -n '1p' "$version_file")"
  elif [[ -x "$managed_binary" ]]; then
    printf 'media-downloader managed executable %s\n' "$managed_binary"
  else
    printf 'media-downloader is not installed\n'
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      require_value "$1" "${2:-}"
      output_directory="$2"
      shift 2
      ;;
    --platform)
      require_value "$1" "${2:-}"
      case "$2" in
        douyin|tiktok) platform_override="$2" ;;
        *) fail "--platform must be douyin or tiktok" ;;
      esac
      shift 2
      ;;
    --install)
      install_requested=true
      shift
      ;;
    --update)
      update_requested=true
      shift
      ;;
    --version)
      show_version
      exit 0
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      [[ $# -eq 1 ]] || fail "pass exactly one quoted share-text argument after --"
      share_text="$1"
      shift
      ;;
    -*)
      fail "unknown option: $1"
      ;;
    *)
      [[ -z "$share_text" ]] || fail "pass share text as one quoted argument"
      share_text="$1"
      shift
      ;;
  esac
done

if [[ "$install_requested" == true || "$update_requested" == true ]]; then
  managed_install
fi

if [[ -z "$share_text" ]]; then
  if [[ "$install_requested" == true || "$update_requested" == true ]]; then
    exit 0
  fi
  usage >&2
  exit 2
fi

share_text="$(normalize_share_text "$share_text")"
selected_binary="$custom_binary"
if [[ -z "$selected_binary" ]]; then
  selected_binary="$managed_binary"
  [[ -x "$selected_binary" ]] || managed_install
fi
[[ -x "$selected_binary" ]] || fail "CLI is not executable: $selected_binary"

mkdir -p "$output_directory"
if [[ -n "$platform_override" ]]; then
  "$selected_binary" --platform "$platform_override" "$share_text" "$output_directory"
else
  "$selected_binary" "$share_text" "$output_directory"
fi
