"""Unit tests for scripts/sync-versions.py (single source of truth: version.json).

Exercises the sync against fixture files in a temp directory: version bump
propagation, idempotency, and the optional --policies mirroring.
"""

import importlib.util
import json
from pathlib import Path

import pytest

_GEN = Path(__file__).resolve().parents[2] / "scripts" / "sync-versions.py"
_spec = importlib.util.spec_from_file_location("sync_versions", _GEN)
SV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SV)

FIXTURES = {
    "python/src/media_downloader/__init__.py": '__version__ = "1.8.2"\n',
    "python/pyproject.toml": '[project]\nname = "media-downloader"\nversion = "1.8.2"\n',
    "python/src/media_downloader/core/updater.py": 'VERSION = "1.8.2"\n',
    "apps/windows/gui/auto_updater.py": 'CURRENT_VERSION = "1.8.2"\n',
    "install.sh": 'RELEASE_TAG="v1.8.2"\n',
    "Casks/tiktok-douyin-dl.rb": 'cask "tiktok-douyin-dl"\nversion "1.8.2"\n',
    "apps/macos/MediaDownloader.xcodeproj/project.pbxproj":
        "MARKETING_VERSION = 1.8.2;\nMARKETING_VERSION = 1.8.2;\n",
    "apps/ios/MediaDownloader.xcodeproj/project.pbxproj":
        "MARKETING_VERSION = 1.8.2;\n",
    "apps/macos/MediaDownloader/AppUpdateService.swift":
        '        ) as? String ?? "1.8.1"\n',
    "apps/ios/MediaDownloader/Views/SettingsView.swift":
        '            forInfoDictionaryKey: "CFBundleShortVersionString"\n'
        '        ) as? String ?? "1.8.2"\n'
        '            forInfoDictionaryKey: "CFBundleVersion"\n'
        '        ) as? String ?? "1"\n',
    "apps/android/app/build.gradle.kts":
        '        versionCode = 4\n        versionName = "0.1.3"\n',
    "version-policy.json": json.dumps({
        "platforms": {
            "cli": {"min_version": "1.8.2", "hard_block": True},
            "android": {"min_version": "0.1.3", "hard_block": True},
        }
    }, indent=2) + "\n",
    "download-policy.json": json.dumps({
        "download": {"platforms": {"android": {"min_version": "0.1.2"}}}
    }, indent=2) + "\n",
}


@pytest.fixture()
def repo(tmp_path):
    for rel, content in FIXTURES.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    (tmp_path / "version.json").write_text(json.dumps({
        "main": "1.9.0",
        "android": {"versionName": "0.1.4", "versionCode": 5},
        "apple": {"buildNumber": 2},
    }), encoding="utf-8")
    return tmp_path


def _read(repo: Path, rel: str) -> str:
    return (repo / rel).read_text(encoding="utf-8")


def test_sync_propagates_all_locations(repo):
    data = SV.load_config(repo / "version.json")
    changed = SV.sync_versions(repo, data)

    assert "python/src/media_downloader/__init__.py" in changed
    assert '__version__ = "1.9.0"' in _read(repo, "python/src/media_downloader/__init__.py")
    assert 'version = "1.9.0"' in _read(repo, "python/pyproject.toml")
    assert 'VERSION = "1.9.0"' in _read(repo, "python/src/media_downloader/core/updater.py")
    assert 'CURRENT_VERSION = "1.9.0"' in _read(repo, "apps/windows/gui/auto_updater.py")
    assert 'RELEASE_TAG="v1.9.0"' in _read(repo, "install.sh")
    assert 'version "1.9.0"' in _read(repo, "Casks/tiktok-douyin-dl.rb")
    # pbxproj: every MARKETING_VERSION rewritten (both Debug+Release rows)
    assert _read(repo, "apps/macos/MediaDownloader.xcodeproj/project.pbxproj") == \
        "MARKETING_VERSION = 1.9.0;\nMARKETING_VERSION = 1.9.0;\n"
    assert '?? "1.9.0"' in _read(repo, "apps/macos/MediaDownloader/AppUpdateService.swift")
    assert '?? "1.9.0"' in _read(repo, "apps/ios/MediaDownloader/Views/SettingsView.swift")
    gradle = _read(repo, "apps/android/app/build.gradle.kts")
    assert 'versionName = "0.1.4"' in gradle
    assert 'versionCode = 5' in gradle


def test_sync_is_idempotent(repo):
    data = SV.load_config(repo / "version.json")
    first = SV.sync_versions(repo, data)
    second = SV.sync_versions(repo, data)
    assert first
    assert second == []


def test_sync_policies_mirrors_min_versions(repo):
    data = SV.load_config(repo / "version.json")
    changed = SV.sync_versions(repo, data, policies=True)
    assert "version-policy.json" in changed
    assert "download-policy.json" in changed

    vp = json.loads(_read(repo, "version-policy.json"))
    assert vp["platforms"]["cli"]["min_version"] == "1.9.0"
    assert vp["platforms"]["cli"]["hard_block"] is True  # flags untouched
    assert vp["platforms"]["android"]["min_version"] == "0.1.4"
    dp = json.loads(_read(repo, "download-policy.json"))
    assert dp["download"]["platforms"]["android"]["min_version"] == "0.1.4"


def test_load_config_rejects_bad_version(repo):
    (repo / "version.json").write_text(json.dumps({"main": "1.9"}), encoding="utf-8")
    with pytest.raises(ValueError):
        SV.load_config(repo / "version.json")


def test_sync_raises_when_location_drifted(repo):
    data = SV.load_config(repo / "version.json")
    # Break a location so the sync cannot find it -> fails loudly instead of
    # silently shipping a stale version.
    (repo / "python/pyproject.toml").write_text('[project]\nversion = "9.9.9"\n'
                                                'version = "9.9.9"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        SV.sync_versions(repo, data)
