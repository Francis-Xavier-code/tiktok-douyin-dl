"""Single implementation of version parsing/comparison for every core module.

Previously duplicated verbatim in ``updater``, ``version_policy`` and
``download_policy``; keep the helpers here so semantic-version handling can
never drift between call sites.
"""

from __future__ import annotations

import re


def parse_version(v_str: str):
    """"1.8.0" -> (1, 8, 0); unparseable -> (0,).

    ``re.findall`` picks out every run of digits, so pre-release suffixes
    ("2.0.1-beta") compare equal to their release (matching the historical
    behavior of every client).
    """
    try:
        return tuple(int(x) for x in re.findall(r"\d+", v_str))
    except Exception:
        return (0,)


def compare_versions(a: str, b: str) -> int:
    """1 if a > b, 0 if equal, -1 if a < b (tuple comparison)."""
    pa, pb = parse_version(a), parse_version(b)
    if pa == pb:
        return 0
    return 1 if pa > pb else -1
