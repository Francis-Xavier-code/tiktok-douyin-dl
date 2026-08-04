"""Remote version-policy enforcement (fail-open).

This lets the maintainer retire old clients WITHOUT re-shipping every binary:
a single ``version-policy.json`` on the default branch declares the minimum
allowed version per platform and whether a violation should be a hard block
(refuse to run) or a soft nag (warn, but keep working).

Design rules (see docs/version-policy.md):
  * This is a pure-client app with no backend, so already-shipped builds that
    lack this check can never be reached remotely. This only affects builds
    that include this module.
  * Loading the policy MUST fail open: any network/parse error -> ALLOW.
  * Short timeout + CDN/mirror fallbacks so a flaky network never blocks the app.

Client platforms: cli, windows, macos, ios.
"""

from __future__ import annotations

import json
from typing import Optional

from media_downloader.core.network import http_get_bytes
from media_downloader.core.updater import GITHUB_USER, GITHUB_REPO, VERSION
from media_downloader.i18n import translate

# One of the platform keys declared in version-policy.json. ``cli`` covers the
# CLI build, which is also what the macOS/Linux frozen binaries derive from.
PLATFORM = "cli"

_DEFAULT_BRANCH = "main"

_POLICY_URLS = [
    f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{_DEFAULT_BRANCH}/version-policy.json",
    f"https://gh-proxy.com/https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{_DEFAULT_BRANCH}/version-policy.json",
    f"https://ghproxy.net/https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{_DEFAULT_BRANCH}/version-policy.json",
]

_TIMEOUT = 6


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
    """Fetch and parse version-policy.json. Returns None on any failure."""
    for url in _POLICY_URLS:
        try:
            raw = http_get_bytes(url, timeout=_TIMEOUT, verify=True,
                                 headers={"User-Agent": "Mozilla/5.0 version-policy"})
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return None


class PolicyDecision:
    """Result of evaluating the running client against the policy."""

    ALLOW = "allow"
    NAG = "nag"
    BLOCK = "block"

    def __init__(self, status: str, message: str = "", update_url: str = "",
                 min_version: str = ""):
        self.status = status
        self.message = message
        self.update_url = update_url
        self.min_version = min_version

    @property
    def is_block(self) -> bool:
        return self.status == self.BLOCK


def evaluate(policy: Optional[dict], current_version: str = VERSION,
             platform: str = PLATFORM) -> PolicyDecision:
    """Decide what to do about ``current_version`` for ``platform``.

    Fail-open: missing policy, missing platform entry, unparseable versions,
    or a semantic mismatch all resolve to ALLOW.
    """
    if not policy:
        return PolicyDecision(PolicyDecision.ALLOW)

    platforms = policy.get("platforms") or {}
    entry = platforms.get(platform)
    if not isinstance(entry, dict):
        return PolicyDecision(PolicyDecision.ALLOW)

    min_version = entry.get("min_version") or "0.0.0"
    hard_block = bool(entry.get("hard_block", False))

    try:
        if parse_version(current_version) >= parse_version(min_version):
            return PolicyDecision(PolicyDecision.ALLOW)
    except Exception:
        return PolicyDecision(PolicyDecision.ALLOW)

    message = (policy.get("message") or "").strip() or _t("policy_update_required")
    update_url = policy.get("update_url") or _t("policy_release_url")
    status = PolicyDecision.BLOCK if hard_block else PolicyDecision.NAG
    return PolicyDecision(status, message=message, update_url=update_url,
                          min_version=min_version)


def check_version_policy(silent: bool = True) -> PolicyDecision:
    """Fetch policy, evaluate for this client, and surface the result.

    * BLOCK  -> print the message, open update_url, and exit(1).
    * NAG    -> print a non-fatal upgrade reminder (unless ``silent``).
    * ALLOW  -> do nothing.

    Returns the decision so callers can react programmatically too.
    """
    decision = evaluate(fetch_policy(), VERSION, PLATFORM)

    if decision.status == PolicyDecision.BLOCK:
        print("\n" + _t("policy_block_header"))
        print(decision.message)
        print(_t("policy_min_version", min_version=decision.min_version))
        print(_t("policy_update_link", url=decision.update_url))
        import webbrowser
        try:
            webbrowser.open(decision.update_url)
        except Exception:
            pass
        import sys
        sys.exit(1)

    if decision.status == PolicyDecision.NAG and not silent:
        print("\n" + _t("policy_nag_header"))
        print(decision.message)
        print(_t("policy_update_link", url=decision.update_url))

    return decision
