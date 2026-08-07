#!/usr/bin/env python3
"""Generate changelog.json (machine-readable, per-platform) from CHANGELOG.md.

Single source of truth stays CHANGELOG.md. Every release should regenerate and
commit this file so all clients (CLI / Windows GUI / macOS / iOS) can fetch one
shared changelog via the raw-file mirrors and filter entries for their own
platform.

Entry tag convention in CHANGELOG.md (bullets):

    - **[全平台]** Entry that applies to every client.
    - **[CLI]** / **[Windows]** / **[macOS]** / **[iOS]** / **[Android]** Platform-scoped entry.

Untagged bullets are treated as [全平台]. Multi-line bullets are folded into a
single entry. The "## [Unreleased]" section is skipped (not shipped yet).

Usage:
    python3 scripts/update-changelog-json.py            # write repo-root changelog.json
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "CHANGELOG.md"
OUTPUT = ROOT / "changelog.json"

_VERSION_RE = re.compile(r"^##\s+\[([^\]]+)\]\s*-\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*$")
_BULLET_RE = re.compile(r"^-\s+(.*)$")
_SUBHEADER_RE = re.compile(r"^###\s+")
_LINKREF_RE = re.compile(r"^\[[^\]]+\]:\s*")
# Tag prefix: - **[全平台]** / - **[CLI]** / - **[Windows]** / - **[macOS]** / - **[iOS]**
_TAG_RE = re.compile(r"^\*\*\[([^\]]+)\]\*\*\s*(.*)$")

_TAG_TO_PLATFORM = {
    "全平台": "all",
    "CLI": "cli",
    "Linux": "cli",
    "Windows": "windows",
    "macOS": "macos",
    "Mac": "macos",
    "iOS": "ios",
    "Android": "android",
}

_MAX_VERSIONS = 10  # keep the file small; clients only need recent releases


def parse_changelog(text: str) -> list[dict]:
    """Return [{"version","date","entries":{platform:[str]}}] newest first."""
    versions: list[dict] = []
    current: dict | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        m = _VERSION_RE.match(line)
        if m:
            version, date = m.group(1), m.group(2)
            if version.lower() == "unreleased":
                current = None
                continue
            current = {"version": version, "date": date, "entries": {}}
            versions.append(current)
            continue

        if current is None:
            continue

        b = _BULLET_RE.match(line)
        if b:
            body = b.group(1).strip()
            tag_match = _TAG_RE.match(body)
            if tag_match:
                platform = _TAG_TO_PLATFORM.get(tag_match.group(1), "all")
                body = tag_match.group(2).strip()
            else:
                platform = "all"
            if body:
                current["entries"].setdefault(platform, []).append(body)
        elif line.strip() and not _SUBHEADER_RE.match(line) and not _LINKREF_RE.match(line):
            # continuation line of the previous bullet (append to the last bucket)
            target = None
            for bucket in current["entries"].values():
                if bucket:
                    target = bucket
            if target is not None:
                target[-1] += "\n" + line.strip()

    result = []
    for v in versions[: _MAX_VERSIONS]:
        entries = {p: v["entries"][p] for p in sorted(v["entries"]) if v["entries"][p]}
        result.append(
            {
                "version": v["version"],
                "date": v["date"],
                "entries": entries,
            }
        )
    return result


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    data = {
        "schema": 1,
        "updated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "versions": parse_changelog(text),
    }
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT} with {len(data['versions'])} version(s):")
    for v in data["versions"]:
        total = sum(len(e) for e in v["entries"].values())
        print(f"  v{v['version']} ({v['date']}): {total} entries")


if __name__ == "__main__":
    main()
