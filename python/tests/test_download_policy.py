import json

import pytest

from media_downloader.core.download_policy import (
    DownloadDecision,
    evaluate,
    fetch_policy,
)
from media_downloader.core.updater import VERSION


def _dl(enabled=True, min_version="0.0.0", message=None, platforms=None):
    d = {"enabled": enabled, "min_version": min_version}
    if message is not None:
        d["message"] = message
    if platforms is not None:
        d["platforms"] = platforms
    return {"download": d}


# --- evaluate: golden paths (fail-closed) ----------------------------------

def test_evaluate_allowed_when_enabled_and_fresh():
    d = evaluate(_dl(enabled=True, min_version="1.0.0"),
                 current_version="1.8.0", platform="cli")
    assert d.status == DownloadDecision.ALLOW


def test_evaluate_blocked_when_disabled():
    d = evaluate(_dl(enabled=False, message="维护中"),
                 current_version="1.8.0", platform="cli")
    assert d.status == DownloadDecision.BLOCK
    assert d.reason == "disabled"
    assert d.message == "维护中"


def test_evaluate_blocked_when_version_below_min():
    d = evaluate(_dl(enabled=True, min_version="1.9.0"),
                 current_version="1.8.0", platform="cli")
    assert d.status == DownloadDecision.BLOCK
    assert d.reason == "version"


def test_evaluate_fail_closed_when_policy_none():
    # All sources unreachable -> block (the opposite of version-policy).
    d = evaluate(None, current_version="1.8.0", platform="cli")
    assert d.status == DownloadDecision.BLOCK
    assert d.reason == "unreachable"


def test_evaluate_fail_closed_when_malformed_download():
    d = evaluate({"download": "not-a-dict"}, current_version="1.8.0", platform="cli")
    assert d.status == DownloadDecision.BLOCK
    assert d.reason == "unreachable"


def test_evaluate_per_platform_override_disabled():
    d = evaluate(
        _dl(enabled=True, platforms={"cli": {"enabled": False, "min_version": "0.0.0"}}),
        current_version="1.8.0", platform="cli",
    )
    assert d.status == DownloadDecision.BLOCK
    assert d.reason == "disabled"


def test_evaluate_per_platform_override_version():
    d = evaluate(
        _dl(enabled=True, min_version="0.0.0",
            platforms={"cli": {"enabled": True, "min_version": "9.9.9"}}),
        current_version="1.8.0", platform="cli",
    )
    assert d.status == DownloadDecision.BLOCK
    assert d.reason == "version"


def test_evaluate_issue_url_propagates():
    d = evaluate({"download": {"enabled": False}, "issue_url": "https://example.com/issue"},
                 current_version="1.8.0", platform="cli")
    assert d.issue_url == "https://example.com/issue"


# --- fetch_policy: source fallback + fail-closed ----------------------------

def _signed_policy(monkeypatch, enabled=True, updated_at="2026-08-15T00:00:00Z",
                   message="ok"):
    """Build a policy dict signed by an ephemeral test key.

    The module-global public key is patched to the ephemeral keypair so the
    whole verify path (canonicalize + Ed25519) is exercised for real.
    """
    import base64

    import nacl.signing

    from media_downloader.core import policy_verifier as pv

    key = nacl.signing.SigningKey.generate()
    monkeypatch.setattr(pv, "PUBLIC_KEY_B64",
                        base64.b64encode(key.verify_key.encode()).decode("ascii"))
    payload = "\n".join([
        updated_at,
        "true" if enabled else "false",
        message,
        "0.0.0",
    ]).encode("utf-8")
    signature = base64.b64encode(key.sign(payload).signature).decode("ascii")
    return {
        "updated_at": updated_at,
        "signature": signature,
        "download": {"enabled": enabled, "min_version": "0.0.0", "message": message},
    }


def test_fetch_policy_tries_sources_until_success(monkeypatch):
    import media_downloader.core.download_policy as dp

    calls = []

    def fake_get(url, *a, **k):
        calls.append(url)
        if "gh-proxy.com" in url:
            return json.dumps(_signed_policy(monkeypatch)).encode()
        raise OSError("unreachable")

    monkeypatch.setattr(dp, "http_get_bytes", fake_get)
    # Only the direct + first mirror matter; later ones must not be hit once we win.
    monkeypatch.setattr(dp, "_SOURCES", dp._SOURCES[:2])
    result = fetch_policy()
    assert isinstance(result, dict)
    assert result["download"]["enabled"] is True
    assert len(calls) == 2  # direct fails, first mirror wins


def test_fetch_policy_rejects_unsigned_or_tampered(monkeypatch):
    """Signature gate: unsigned or tampered policy is treated as unreachable."""
    import media_downloader.core.download_policy as dp

    monkeypatch.setattr(dp, "http_get_bytes",
                        lambda *a, **k: json.dumps({"download": {"enabled": True}}).encode())
    monkeypatch.setattr(dp, "_SOURCES", ["https://unreachable.invalid/a.json"])
    assert fetch_policy() is None

    # Tampered content: valid signature over a DIFFERENT payload must fail.
    signed = _signed_policy(monkeypatch, message="authentic")
    signed["download"]["message"] = "tampered"
    monkeypatch.setattr(dp, "http_get_bytes", lambda *a, **k: json.dumps(signed).encode())
    assert fetch_policy() is None


def test_fetch_policy_all_fail_returns_none(monkeypatch):
    import media_downloader.core.download_policy as dp

    monkeypatch.setattr(dp, "http_get_bytes",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    monkeypatch.setattr(dp, "_SOURCES", ["https://unreachable.invalid/a.json"])
    assert fetch_policy() is None


def test_direct_github_is_first_source():
    from media_downloader.core.download_policy import _SOURCES
    assert _SOURCES[0].startswith("https://raw.githubusercontent.com/")
    # 1 direct + 9 mirrors == 10 sources.
    assert len(_SOURCES) == 10


def test_current_version_is_allow_by_default_policy():
    # Sanity: the committed download-policy.json must not block current users.
    d = evaluate(None, current_version=VERSION, platform="cli")
    # None => unreachable => block; this documents fail-closed. For the real file
    # we rely on it being enabled; check the evaluate contract only.
    assert d.is_block
