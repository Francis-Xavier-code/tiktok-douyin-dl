"""Unit tests for the shared machine-readable changelog (changelog.json).

Covers the generator (CHANGELOG.md -> changelog.json, per-platform buckets) and
the CLI consumer (core/updater.fetch_changelog filtering + fail-open).
"""

import importlib.util
import json
from pathlib import Path

import pytest

from media_downloader.core import updater

_GEN = Path(__file__).resolve().parents[2] / "scripts" / "update-changelog-json.py"
_spec = importlib.util.spec_from_file_location("update_changelog_json", _GEN)
GEN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(GEN)

_SAMPLE = """# Changelog

## [Unreleased]

### Added

- **[CLI]** Not shipped yet: placeholder entry.

## [1.8.2] - 2026-08-06

### Added

- **[全平台]** Version display for every client.
- **[CLI]** CLI disclaimer dialog.
- **[macOS]** Silent auto-update.
- untagged entry treated as all-platform.

### Fixed

- **[iOS]** Update tag fix: first line.
  continuation line of the same entry.

## [1.8.1] - 2026-08-06

### Added

- **[Windows]** Policy per-platform override.
- **[全平台]** Policy upgrade.

[Unreleased]: https://github.com/example/repo/compare/v1.8.2...HEAD
[1.8.2]: https://github.com/example/repo/releases/tag/v1.8.2
"""


def test_parse_changelog_buckets_and_skips_unreleased():
    versions = GEN.parse_changelog(_SAMPLE)
    assert [v["version"] for v in versions] == ["1.8.2", "1.8.1"]
    # Unreleased is not shipped -> excluded.

    v182 = versions[0]
    assert v182["date"] == "2026-08-06"
    assert v182["entries"]["all"] == [
        "Version display for every client.",
        "untagged entry treated as all-platform.",
    ]
    assert v182["entries"]["cli"] == ["CLI disclaimer dialog."]
    assert v182["entries"]["macos"] == ["Silent auto-update."]
    # Multi-line entry folded into one string.
    assert v182["entries"]["ios"] == [
        "Update tag fix: first line.\ncontinuation line of the same entry."
    ]
    assert "windows" not in v182["entries"]

    v181 = versions[1]
    assert v181["entries"]["windows"] == ["Policy per-platform override."]
    assert v181["entries"]["all"] == ["Policy upgrade."]


def test_parse_changelog_ignores_headers_and_linkrefs():
    versions = GEN.parse_changelog(_SAMPLE)
    for v in versions:
        for entries in v["entries"].values():
            for e in entries:
                assert "###" not in e
                assert "https://github.com/example" not in e


def test_parse_changelog_android_tag():
    # Android is a reserved first-class platform (versioned independently 0.1.x).
    versions = GEN.parse_changelog(
        "## [0.1.3] - 2026-08-07\n\n- **[Android]** APK release.\n- **[全平台]** Shared entry.\n"
    )
    assert versions[0]["entries"]["android"] == ["APK release."]
    assert versions[0]["entries"]["all"] == ["Shared entry."]


def test_fetch_changelog_filters_platform(monkeypatch):
    fake = {
        "versions": [
            {"version": "1.8.2", "date": "2026-08-06",
             "entries": {"all": ["A1"], "cli": ["C1"], "windows": ["W1"]}},
            {"version": "1.8.1", "date": "2026-08-06",
             "entries": {"windows": ["W2"]}},
            {"version": "1.8.0", "date": "2026-08-04",
             "entries": {"all": ["O"]}},
        ]
    }
    monkeypatch.setattr(updater, "VERSION", "1.8.0")
    monkeypatch.setattr(updater, "http_json", lambda *a, **k: fake)

    result = updater.fetch_changelog("windows", max_versions=5)
    assert [r["version"] for r in result] == ["1.8.2", "1.8.1"]
    assert result[0]["entries"] == ["W1", "A1"]  # platform bucket first, then all
    assert result[1]["entries"] == ["W2"]


def test_fetch_changelog_stops_at_current_version(monkeypatch):
    fake = {
        "versions": [
            {"version": "1.8.2", "date": "", "entries": {"all": ["X"]}},
            {"version": "1.8.1", "date": "", "entries": {"all": ["Y"]}},
        ]
    }
    monkeypatch.setattr(updater, "VERSION", "1.8.1")
    monkeypatch.setattr(updater, "http_json", lambda *a, **k: fake)
    result = updater.fetch_changelog("cli")
    assert [r["version"] for r in result] == ["1.8.2"]


def test_fetch_changelog_fail_open(monkeypatch):
    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(updater, "http_json", boom)
    assert updater.fetch_changelog("windows") == []

    monkeypatch.setattr(updater, "http_json", lambda *a, **k: {"versions": "garbage"})
    assert updater.fetch_changelog("windows") == []
