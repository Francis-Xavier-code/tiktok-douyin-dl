"""Release-check and self-update logic shared by the CLI front-ends.

Public surface:
  * ``VERSION`` / ``GITHUB_USER`` / ``GITHUB_REPO`` -- single source of truth
  * ``parse_version`` -- "1.8.0" -> (1, 8, 0)
  * ``check_for_updates(silent)`` -- prints a prompt when a newer release exists
  * ``perform_self_update(download_url, expected_sha256=None)`` -- replaces the
    running executable **after** verifying its SHA-256 when a digest is supplied

Translations are resolved through ``media_downloader.i18n`` so the same code
serves both the Douyin and TikTok entry points.
"""

from __future__ import annotations

import os
import sys

from media_downloader.core.network import http_get_bytes, http_json
from media_downloader.core.versions import parse_version
from media_downloader.i18n import translate

# --- release identity (single source of truth) ---
VERSION = "2.1.0"
GITHUB_USER = "Francis-Xavier-code"
GITHUB_REPO = "tiktok-douyin-dl"

_WEB_LATEST = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"


def _t(key: str, **kwargs) -> str:
    return translate(f"cli.common.{key}", **kwargs)


# --- shared machine-readable changelog (changelog.json at repo root) ---------
# Single file consumed by every client (CLI / Windows GUI / macOS / iOS);
# generated from CHANGELOG.md by scripts/update-changelog-json.py. Entries are
# bucketed per platform so each client only shows updates relevant to itself.
_CHANGELOG_FILE = "changelog.json"
_CHANGELOG_SOURCES = [
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{_CHANGELOG_FILE}",
    f"https://gh-proxy.com/https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{_CHANGELOG_FILE}",
    f"https://ghproxy.net/https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{_CHANGELOG_FILE}",
    f"https://fastly.jsdelivr.net/gh/{GITHUB_USER}/{GITHUB_REPO}@main/{_CHANGELOG_FILE}",
]


def fetch_changelog(platform: str = "cli", max_versions: int = 3) -> list[dict]:
    """Fetch the shared changelog.json and return per-platform filtered entries.

    Returns a list of {"version", "date", "entries": [str]} for releases newer
    than the running VERSION (newest first, capped at max_versions). Fail-open:
    any network/parse error yields [] so an update prompt never breaks.
    """
    try:
        import json
        data = None
        for url in _CHANGELOG_SOURCES:
            try:
                data = http_json(url, timeout=5, verify=True,
                                 headers={"User-Agent": "Mozilla/5.0 updater"})
                break
            except Exception:
                continue
        if not isinstance(data, dict):
            return []
        result = []
        for v in data.get("versions", []):
            version = str(v.get("version", "")).lstrip("v")
            if parse_version(version) <= parse_version(VERSION):
                break  # versions are newest-first; older releases are irrelevant
            entries = []
            bucket = v.get("entries") or {}
            if isinstance(bucket, dict):
                for key in (platform, "all"):
                    for entry in bucket.get(key) or []:
                        if entry:
                            entries.append(entry)
            if entries:
                result.append({
                    "version": version,
                    "date": str(v.get("date", "")),
                    "entries": entries,
                })
            if len(result) >= max_versions:
                break
        return result
    except Exception:
        return []


def notify_update() -> bool:
    """Check for a newer release and print the per-platform changelog.

    Unlike check_for_updates(), this NEVER replaces the running binary or
    prompts — it only prints what changed, so the packaged CLI can show the
    changelog at startup without surprising the user. Fail-open (returns False
    on any network error). Uses the raw-file mirror path (fast in CN).
    """
    if "YOUR_GITHUB_" in GITHUB_USER or "YOUR_GITHUB_" in GITHUB_REPO:
        return False
    try:
        notes = fetch_changelog("cli", max_versions=1)
        if not notes:
            return False
        latest = notes[0]["version"]
        if parse_version(latest) <= parse_version(VERSION):
            return False
        print(_t("update_found", latest_version=latest, version=VERSION))
        print(_t("changelog_title"))
        print("─" * 50)
        for entry in notes[0]["entries"]:
            for line in entry.splitlines():
                print(f"  • {line}")
        print("─" * 50)
        print(_t("update_hint", cmd="media-downloader"))
        return True
    except Exception:
        return False


def _print_changelog(platform: str) -> bool:
    """Print per-platform changelog entries for newer releases (fail-open).

    Returns True when entries were printed, False otherwise.
    """
    notes = fetch_changelog(platform)
    if not notes:
        return False
    print(_t("changelog_title"))
    print("─" * 50)
    for item in notes:
        header = f"[v{item['version']}]"
        if item.get("date"):
            header += f" ({item['date']})"
        print(header)
        for entry in item["entries"]:
            for line in entry.splitlines():
                print(f"  • {line}")
        print()
    return True


def check_for_updates(silent: bool = False) -> None:
    """Check for a newer release and prompt to self-update (API-free).

    Uses the shared changelog.json mirrors (raw + CN mirrors, the same source the
    GUI / macOS / iOS clients use) instead of api.github.com, so the anonymous
    REST API rate limit (60/h) never blocks the check. Falls back to the
    /releases/latest web-page redirect for the version only.
    """
    if "YOUR_GITHUB_" in GITHUB_USER or "YOUR_GITHUB_" in GITHUB_REPO:
        return  # not configured yet

    latest_version = None
    notes = []

    # 1. Preferred: shared changelog.json via raw-file mirrors (no REST API).
    try:
        notes = fetch_changelog("cli", max_versions=1)
        if notes:
            latest_version = notes[0]["version"]
    except Exception:
        notes = []

    # 2. Fallback: /releases/latest web-page redirect for the version only.
    if not latest_version:
        import urllib.request
        try:
            probe = urllib.request.Request(
                _WEB_LATEST, headers={"User-Agent": "Mozilla/5.0 updater"}, method="HEAD"
            )
            with urllib.request.urlopen(probe, timeout=5) as resp:
                final_url = resp.geturl()
            if "/releases/tag/" in final_url:
                tag_name = final_url.split("/releases/tag/")[-1].split("?")[0].split("#")[0].strip("/")
                latest_version = tag_name.lstrip("v")
        except Exception as e:
            if not silent:
                print(_t("update_failed", err=e))
            return

    # 3. Compare and prompt.
    if latest_version and parse_version(latest_version) > parse_version(VERSION):
        print(_t("update_found", latest_version=latest_version, version=VERSION))

        # 打印本端更新日志（changelog.json 镜像已按 CLI 平台过滤）
        if notes:
            print(_t("changelog_title"))
            print("─" * 50)
            for entry in notes[0]["entries"]:
                for line in entry.splitlines():
                    print(f"  • {line}")
            print("─" * 50)

        download_url = _cli_asset_url(latest_version)
        if download_url:
            # Best-effort integrity check: the GitHub API exposes the asset
            # digest; when the API is unreachable (rate limit / CN network) we
            # fall back to an unverified update rather than breaking the flow.
            expected_sha256 = _resolve_asset_sha256(
                latest_version, os.path.basename(download_url)
            )
            if getattr(sys, "frozen", False):
                if not silent:
                    confirm = input(_t("update_confirm")).strip().lower()
                    if confirm in ["y", "yes"]:
                        perform_self_update(download_url, expected_sha256=expected_sha256)
                else:
                    # Silent mode: auto-update frozen binary without prompting.
                    perform_self_update(download_url, expected_sha256=expected_sha256)
            else:
                if not silent:
                    print(_t("source_mode_update_skipped"))


def _resolve_asset_sha256(version: str, asset_name: str) -> str | None:
    """Best-effort SHA-256 digest (hex) of a release asset via the GitHub API.

    Returns None on any failure (rate limit, network, missing digest) so the
    self-update path degrades gracefully to an unverified download. The digest
    only helps when GitHub itself is reachable, but that is also the host we
    download the archive from.
    """
    import json as _json
    import urllib.request as _request

    api_url = (
        f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}"
        f"/releases/tags/v{version}"
    )
    try:
        req = _request.Request(
            api_url,
            headers={
                "User-Agent": "Mozilla/5.0 updater",
                "Accept": "application/vnd.github+json",
            },
        )
        with _request.urlopen(req, timeout=8) as resp:
            release = _json.loads(resp.read().decode("utf-8"))
        for asset in release.get("assets") or []:
            if asset.get("name") == asset_name:
                digest = str(asset.get("digest") or "").strip()
                if digest.startswith("sha256:"):
                    return digest[len("sha256:"):].strip().lower()
                return None
    except Exception:
        return None
    return None


def _cli_asset_url(version: str) -> str:
    """Build the CLI release asset URL for the current OS/arch.

    Assets: MediaDownloader-Windows-x64-CLI-<v>.zip,
    MediaDownloader-Linux-x86_64-<v>.tar.gz,
    MediaDownloader-macOS-arm64-CLI-<v>.zip. Returns "" for unknown platforms
    (macOS x86_64 CLI is no longer built since the Intel runner was retired).
    """
    base = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/v{version}"
    if sys.platform.startswith("win"):
        return f"{base}/MediaDownloader-Windows-x64-CLI-{version}.zip"
    if sys.platform.startswith("linux"):
        return f"{base}/MediaDownloader-Linux-x86_64-{version}.tar.gz"
    if sys.platform == "darwin":
        import platform
        if platform.machine() != "arm64":
            return ""
        return f"{base}/MediaDownloader-macOS-arm64-CLI-{version}.zip"
    return ""


def perform_self_update(download_url: str, expected_sha256: str | None = None) -> None:
    """Download the newer CLI archive and replace this process in place.

    Release assets are archives (zip / tar.gz) containing the binary plus the
    ms-playwright sidecar. The archive is unpacked into a temp dir, the binary
    is swapped in (SHA-256 verified when supplied), and the browser sidecar is
    refreshed next to the running executable.
    """
    temp_dir = ""
    try:
        import io
        import shutil
        import tarfile
        import tempfile
        import zipfile

        current_exe = os.path.abspath(sys.argv[0])
        binary_name = os.path.basename(current_exe)

        print(_t("update_downloading"))
        data = http_get_bytes(download_url, timeout=120, verify=True,
                              headers={"User-Agent": "Mozilla/5.0 updater"})

        temp_dir = tempfile.mkdtemp(prefix="md-update-")
        if download_url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(temp_dir)
        else:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                tf.extractall(temp_dir)

        # 定位新二进制（归档顶层：media-downloader / media-downloader.exe）
        new_binary = os.path.join(temp_dir, binary_name)
        if not os.path.isfile(new_binary):
            candidates = [
                os.path.join(temp_dir, name)
                for name in os.listdir(temp_dir)
                if os.path.isfile(os.path.join(temp_dir, name))
            ]
            new_binary = next((p for p in candidates if os.access(p, os.X_OK)), "")
        if not new_binary or not os.path.isfile(new_binary):
            raise RuntimeError("binary not found in release archive")

        # 浏览器侧车同步到当前二进制同目录
        sidecar = os.path.join(temp_dir, "ms-playwright")
        if os.path.isdir(sidecar):
            dst = os.path.join(os.path.dirname(current_exe), "ms-playwright")
            shutil.copytree(sidecar, dst, dirs_exist_ok=True)

        tmp_path = current_exe + ".tmp"
        shutil.copy2(new_binary, tmp_path)

        if expected_sha256:
            from media_downloader.core.network import verify_sha256
            if not verify_sha256(tmp_path, expected_sha256):
                os.remove(tmp_path)
                print(_t("update_failed_install", error="SHA-256 checksum mismatch"))
                return

        os.chmod(tmp_path, 0o755)
        os.replace(tmp_path, current_exe)
        print(_t("update_success"))
        sys.exit(0)
    except Exception as e:
        print(_t("update_failed_install", error=e))
        if temp_dir and os.path.isdir(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
