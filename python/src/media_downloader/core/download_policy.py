"""Remote download-policy enforcement, checked BEFORE every download.

Separate from version-policy.json: this governs whether the *download feature*
is currently enabled (e.g. temporary maintenance, or a bad version to quarantine),
whereas version-policy governs whether the *client build* itself is retired.

Per the maintainer's rule, this is **fail-closed**: if every source (direct
GitHub + all mirrors) is unreachable, downloads are blocked and the user is told
to file an issue. This is the opposite of version-policy's fail-open, because a
stale/garbled download-policy must never accidentally green-light downloads.

Sources are tried in order: direct GitHub first, then domestic mirrors. The first
source that returns valid JSON wins. A per-source short timeout means a dead
mirror is skipped quickly instead of stalling the download.

Client platforms: cli, windows, macos, ios.
"""

from __future__ import annotations

import json
from typing import Optional

from media_downloader.core.network import http_get_bytes
from media_downloader.core.updater import GITHUB_USER, GITHUB_REPO, VERSION
from media_downloader.i18n import translate

# One of the platform keys declared in download-policy.json. ``cli`` covers the
# CLI build, which is also what the macOS/Linux frozen binaries derive from.
PLATFORM = "cli"

_DEFAULT_BRANCH = "main"
_POLICY_FILE = "download-policy.json"

_TIMEOUT = 4

# Direct GitHub first, then domestic mirrors. Order matters: a reachable mirror
# earlier in the list wins. Mirrors are configurable — add a working prefix and
# it takes effect without code changes. Domains that are currently unreachable
# simply time out and are skipped.
_MIRROR_PREFIXES = [
    "https://gh-proxy.com/https://raw.githubusercontent.com",
    "https://ghproxy.net/https://raw.githubusercontent.com",
    "https://raw.gitmirror.com",
    "https://kgithub.com",
    "https://mirror.ghproxy.com/https://raw.githubusercontent.com",
    "https://github.moeyy.xyz/https://raw.githubusercontent.com",
    "https://ghproxy.1888866.xyz/https://raw.githubusercontent.com",
    "https://gh.api.99988866.xyz/https://raw.githubusercontent.com",
    "https://fastly.jsdelivr.net/gh",
]


def _raw_url(prefix: str) -> str:
    """Turn a mirror prefix into the full raw file URL."""
    if prefix.endswith("/gh"):  # jsDelivr special form
        return f"{prefix}/{GITHUB_USER}/{GITHUB_REPO}@{_DEFAULT_BRANCH}/{_POLICY_FILE}"
    if prefix.startswith("https://raw.gitmirror.com"):
        return f"{prefix}/{GITHUB_USER}/{GITHUB_REPO}/{_DEFAULT_BRANCH}/{_POLICY_FILE}"
    if prefix.startswith("https://kgithub.com"):
        return f"{prefix}/{GITHUB_USER}/{GITHUB_REPO}/raw/{_DEFAULT_BRANCH}/{_POLICY_FILE}"
    return f"{prefix}/{GITHUB_USER}/{GITHUB_REPO}/{_DEFAULT_BRANCH}/{_POLICY_FILE}"


# Built once at import: [direct, mirror1, mirror2, ...]
_SOURCES = [
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{_DEFAULT_BRANCH}/{_POLICY_FILE}",
    *(_raw_url(p) for p in _MIRROR_PREFIXES),
]


def _t(key: str, **kwargs) -> str:
    return translate(f"cli.common.{key}", **kwargs)


def parse_version(v_str: str):
    """\"1.6.0\" -> (1, 6, 0); unparseable -> (0,)."""
    import re
    try:
        return tuple(int(x) for x in re.findall(r"\d+", v_str))
    except Exception:
        return (0,)


def fetch_policy() -> Optional[dict]:
    """Try each source in order; return the first valid policy dict, else None.

    Direct GitHub is first; mirrors are tried on failure. Short timeout per
    source so a dead mirror is skipped quickly.
    """
    for url in _SOURCES:
        try:
            raw = http_get_bytes(url, timeout=_TIMEOUT, verify=True,
                                 headers={"User-Agent": "Mozilla/5.0 download-policy"})
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return None


class DownloadDecision:
    """Outcome of checking the download policy before a download."""

    ALLOW = "allow"
    BLOCK = "block"

    def __init__(self, status: str, reason: str = "", message: str = "",
                 issue_url: str = ""):
        self.status = status
        self.reason = reason          # "disabled" | "version" | "unreachable"
        self.message = message
        self.issue_url = issue_url

    @property
    def is_block(self) -> bool:
        return self.status == self.BLOCK


def evaluate(policy: Optional[dict], current_version: str = VERSION,
             platform: str = PLATFORM) -> DownloadDecision:
    """Decide whether a download may proceed.

    Fail-closed: a None policy (every source unreachable) blocks the download.
    """
    if policy is None:
        return DownloadDecision(
            DownloadDecision.BLOCK,
            reason="unreachable",
            message=_t("download_policy_unreachable"),
            issue_url=_t("policy_issue_url"),
        )

    download = policy.get("download")
    if not isinstance(download, dict):
        # Malformed policy -> treat as unreachable/stale -> block.
        return DownloadDecision(
            DownloadDecision.BLOCK,
            reason="unreachable",
            message=_t("download_policy_unreachable"),
            issue_url=_t("policy_issue_url"),
        )

    # Per-platform override takes precedence if present and non-empty.
    platforms = download.get("platforms") or {}
    entry = platforms.get(platform) if isinstance(platforms, dict) else None
    if isinstance(entry, dict):
        eff_enabled = entry.get("enabled", download.get("enabled", True))
        eff_min = entry.get("min_version", download.get("min_version", "0.0.0"))
        eff_message = entry.get("message", download.get("message", ""))
    else:
        eff_enabled = download.get("enabled", True)
        eff_min = download.get("min_version", "0.0.0")
        eff_message = download.get("message", "")

    if not eff_enabled:
        return DownloadDecision(
            DownloadDecision.BLOCK,
            reason="disabled",
            message=(eff_message or _t("download_policy_disabled")),
            issue_url=policy.get("issue_url") or _t("policy_issue_url"),
        )

    try:
        if parse_version(current_version) < parse_version(eff_min):
            return DownloadDecision(
                DownloadDecision.BLOCK,
                reason="version",
                message=(eff_message or _t("download_policy_min_version", min_version=eff_min)),
                issue_url=policy.get("issue_url") or _t("policy_issue_url"),
            )
    except Exception:
        # Version compare failure -> block rather than risk a bad download.
        return DownloadDecision(
            DownloadDecision.BLOCK,
            reason="unreachable",
            message=_t("download_policy_unreachable"),
            issue_url=policy.get("issue_url") or _t("policy_issue_url"),
        )

    return DownloadDecision(DownloadDecision.ALLOW)


def check_download_allowed(silent: bool = False) -> DownloadDecision:
    """Fetch + evaluate the download policy. Returns the decision so callers can
    abort the download when blocked.

    * BLOCK -> print the reason + issue link (and, on a TTY/CLI, open the issue
      page). Does NOT exit; the caller decides what to do next.
    * ALLOW -> return silently.
    """
    decision = evaluate(fetch_policy(), VERSION, PLATFORM)

    if decision.status == DownloadDecision.BLOCK:
        print("\n" + _t("download_blocked_header"))
        print(decision.message)
        if decision.issue_url:
            print(_t("policy_issue_hint", url=decision.issue_url))
            if not silent:
                import webbrowser
                try:
                    webbrowser.open(decision.issue_url)
                except Exception:
                    pass

    return decision
