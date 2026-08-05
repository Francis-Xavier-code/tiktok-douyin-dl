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
from media_downloader.i18n import translate

# --- release identity (single source of truth) ---
VERSION = "1.8.1"
GITHUB_USER = "Francis-Xavier-code"
GITHUB_REPO = "tiktok-douyin-dl"

_API_LATEST = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
_WEB_LATEST = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"


def parse_version(v_str: str):
    """Parse a version string into a comparable tuple of ints."""
    try:
        return tuple(int(x) for x in __import__("re").findall(r"\d+", v_str))
    except Exception:
        return (0,)


def _t(key: str, **kwargs) -> str:
    return translate(f"cli.common.{key}", **kwargs)


def check_for_updates(silent: bool = False) -> None:
    """Check GitHub for a newer release and prompt to self-update."""
    if "YOUR_GITHUB_" in GITHUB_USER or "YOUR_GITHUB_" in GITHUB_REPO:
        return  # not configured yet

    latest_version = None
    changelog = ""
    download_url = ""
    tag_name = ""

    # 1. GitHub API first.
    api_success = False
    try:
        data = http_json(_API_LATEST, timeout=5, verify=True,
                         headers={"User-Agent": "Mozilla/5.0 updater"})
        tag_name = data.get("tag_name", "").strip()
        latest_version = tag_name.lstrip("v")
        changelog = data.get("body", "").strip()
        asset_name = os.path.basename(sys.argv[0])
        for asset in data.get("assets", []):
            if asset.get("name") == asset_name:
                download_url = asset.get("browser_download_url")
                break
        api_success = True
    except Exception:
        api_success = False

    # 2. Fall back to the redirect of the /releases/latest web page.
    if not api_success:
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
                download_url = (
                    f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}"
                    f"/releases/download/{tag_name}/{os.path.basename(sys.argv[0])}"
                )
                changelog = _t("update_changelog_unavailable")
        except Exception as e:
            if not silent:
                print(_t("update_failed", err=e))
            return

    # 3. Compare and prompt.
    if latest_version and parse_version(latest_version) > parse_version(VERSION):
        print(_t("update_found", latest_version=latest_version, version=VERSION))

        if changelog:
            print(_t("changelog_title"))
            print("─" * 50)
            print(changelog)
            print("─" * 50)

        if download_url:
            if getattr(sys, "frozen", False):
                if not silent:
                    confirm = input(_t("update_confirm")).strip().lower()
                    if confirm in ["y", "yes"]:
                        perform_self_update(download_url)
                else:
                    print(_t("update_hint", cmd=os.path.basename(sys.argv[0])))
            else:
                if not silent:
                    print(_t("source_mode_update_skipped"))


def perform_self_update(download_url: str, expected_sha256: str | None = None) -> None:
    """Download the newer executable and replace this process in place.

    When ``expected_sha256`` is provided the download is verified before the
    running binary is overwritten. A mismatch aborts the update.
    """
    temp_exe = ""
    try:
        current_exe = os.path.abspath(sys.argv[0])
        temp_exe = current_exe + ".tmp"

        print(_t("update_downloading"))
        data = http_get_bytes(download_url, timeout=120, verify=True,
                              headers={"User-Agent": "Mozilla/5.0 updater"})

        # Verify integrity before touching the live binary.
        import tempfile
        tmp_path = temp_exe
        with open(tmp_path, "wb") as f:
            f.write(data)

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
        if temp_exe and os.path.exists(temp_exe):
            try:
                os.remove(temp_exe)
            except Exception:
                pass
