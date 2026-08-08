#!/usr/bin/env python3
"""Sync all per-platform version constants from the single source of truth.

version.json (repo root) is THE version source of truth. This script propagates
its values to every place that currently hard-codes a version, so preparing a
new release means editing ONE file and running:

    python3 scripts/sync-versions.py            # sync constants everywhere
    python3 scripts/sync-versions.py --policies # also bump policy min_versions

version.json layout:
    main: "2.0.0"               # shared by CLI / Windows GUI / macOS / iOS
    android.versionName: "2.0.0"  # Android aligned with the main line
    android.versionCode: 4
    apple.buildNumber: 1        # APPLE_BUILD_NUMBER / CURRENT_PROJECT_VERSION

Locations rewritten (kept in sync by scripts/release.sh before tagging):
    python/src/media_downloader/__init__.py      __version__
    python/pyproject.toml                        version
    python/src/media_downloader/core/updater.py  VERSION
    apps/windows/gui/auto_updater.py             CURRENT_VERSION
    install.sh                                   RELEASE_TAG
    install.ps1                                  RELEASE_TAG
    Casks/tiktok-douyin-dl.rb                    version
    apps/{macos,ios}/MediaDownloader.xcodeproj/project.pbxproj   MARKETING_VERSION
    apps/macos/MediaDownloader/AppUpdateService.swift            Bundle fallback
    apps/ios/MediaDownloader/Views/SettingsView.swift            Bundle fallback
    apps/android/app/build.gradle.kts            versionName / versionCode
(scripts/build-apple.sh and scripts/build-windows.ps1 read version.json
 directly at runtime, so they need no sync.)
With --policies, also mirrors version-policy.json platforms.*.min_version and
download-policy.json platforms.android.min_version (hard_block flags untouched).
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "version.json"

_MAIN_RE = re.compile(r"^\d+\.\d+\.\d+$")
_ANDROID_NAME_RE = re.compile(r"^\d+\.\d+\.\d+$")


def load_config(path: Path = CONFIG) -> dict:
    """Read + validate version.json; raise ValueError on bad shape."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    main = str(data.get("main", "")).strip()
    if not _MAIN_RE.match(main):
        raise ValueError(f"{path}: main version {main!r} must match X.Y.Z")
    android = data.get("android") or {}
    version_name = str(android.get("versionName", "")).strip()
    if not _ANDROID_NAME_RE.match(version_name):
        raise ValueError(f"{path}: android.versionName {version_name!r} must match X.Y.Z")
    if not isinstance(android.get("versionCode"), int):
        raise ValueError(f"{path}: android.versionCode must be an int")
    apple = data.get("apple") or {}
    if not isinstance(apple.get("buildNumber", 1), int):
        raise ValueError(f"{path}: apple.buildNumber must be an int")
    return data


def _sub(path: Path, pattern: str, replacement: str, replace_all: bool = False) -> bool:
    """Replace regex match(es) in a file. Returns True when changed.

    By default exactly one match is required (fails loudly if a location has
    drifted). replace_all=True rewrites every match (used for pbxproj where
    Debug and Release configs both carry MARKETING_VERSION).
    """
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    if not matches or (not replace_all and len(matches) != 1):
        raise ValueError(
            f"{path}: expected {'1' if not replace_all else '>=1'} match for "
            f"{pattern!r}, found {len(matches)}"
        )
    new_text = text
    for m in reversed(matches):
        new_text = new_text[: m.start()] + replacement + new_text[m.end():]
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def sync_versions(root: Path, data: dict, policies: bool = False) -> list[str]:
    """Propagate version.json values to every hard-coded location.

    Returns the list of files that were modified. Raises ValueError when a
    location can no longer be found (i.e. someone refactored a file away).
    """
    main = str(data["main"])
    android_name = str(data["android"]["versionName"])
    android_code = int(data["android"]["versionCode"])

    changed: list[str] = []
    rel = lambda p: str(p.relative_to(root))  # noqa: E731

    edits = [
        (root / "python/src/media_downloader/__init__.py",
         r'__version__ = "[^"]*"', f'__version__ = "{main}"'),
        (root / "python/pyproject.toml",
         r'^version = "[^"]*"', f'version = "{main}"'),
        (root / "python/src/media_downloader/core/updater.py",
         r'VERSION = "[^"]*"', f'VERSION = "{main}"'),
        (root / "apps/windows/gui/auto_updater.py",
         r'CURRENT_VERSION = "[^"]*"', f'CURRENT_VERSION = "{main}"'),
        (root / "install.sh",
         r'RELEASE_TAG="v[^"]*"', f'RELEASE_TAG="v{main}"'),
        (root / "install.ps1",
         r'\$RELEASE_TAG = "v[^"]*"', f'$RELEASE_TAG = "v{main}"'),
        (root / "Casks/tiktok-douyin-dl.rb",
         r'version "[^"]*"', f'version "{main}"'),
        (root / "apps/macos/MediaDownloader.xcodeproj/project.pbxproj",
         r'MARKETING_VERSION = [^;]*;', f'MARKETING_VERSION = {main};', True),
        (root / "apps/ios/MediaDownloader.xcodeproj/project.pbxproj",
         r'MARKETING_VERSION = [^;]*;', f'MARKETING_VERSION = {main};', True),
        (root / "apps/macos/MediaDownloader/AppUpdateService.swift",
         r'as\? String \?\? "[^"]*"', f'as? String ?? "{main}"'),
        (root / "apps/ios/MediaDownloader/Views/SettingsView.swift",
         r'CFBundleShortVersionString"\n\s*\) as\? String \?\? "[^"]*"',
         f'CFBundleShortVersionString"\n        ) as? String ?? "{main}"'),
        (root / "apps/android/app/build.gradle.kts",
         r'versionName = "[^"]*"', f'versionName = "{android_name}"'),
        (root / "apps/android/app/build.gradle.kts",
         r'versionCode = \d+', f'versionCode = {android_code}'),
    ]
    for item in edits:
        path, pattern, replacement = item[0], item[1], item[2]
        replace_all = item[3] if len(item) > 3 else False
        if not path.exists():
            raise ValueError(f"{path}: expected to exist for version sync; was it moved?")
        if _sub(path, pattern, replacement, replace_all):
            changed.append(rel(path))

    if policies:
        vp = root / "version-policy.json"
        if vp.exists():
            policy = json.loads(vp.read_text(encoding="utf-8"))
            platforms = policy.setdefault("platforms", {})
            for key in ("cli", "windows", "macos", "ios"):
                if isinstance(platforms.get(key), dict):
                    platforms[key]["min_version"] = main
            if isinstance(platforms.get("android"), dict):
                platforms["android"]["min_version"] = android_name
            vp.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
            changed.append(rel(vp))

        dp = root / "download-policy.json"
        if dp.exists():
            policy = json.loads(dp.read_text(encoding="utf-8"))
            platforms = policy.setdefault("download", {}).setdefault("platforms", {})
            if isinstance(platforms.get("android"), dict):
                platforms["android"]["min_version"] = android_name
            dp.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
            changed.append(rel(dp))

    return changed


def main() -> None:
    data = load_config()
    sync_versions(ROOT, data, policies="--policies" in __import__("sys").argv[1:])
    # Bump updated_at so the JSON records when versions last changed.
    data["updated_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"version.json -> main {data['main']}, "
          f"android {data['android']['versionName']} "
          f"(code {data['android']['versionCode']}), "
          f"apple build {data.get('apple', {}).get('buildNumber')}")
    print("All version constants are in sync.")


if __name__ == "__main__":
    main()
