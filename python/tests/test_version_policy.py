import pytest

from media_downloader.core.version_policy import (
    PolicyDecision,
    evaluate,
    fetch_policy,
    parse_version,
)


# --- parse_version ---------------------------------------------------------

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.7.0", (1, 7, 0)),
        ("v1.6.4", (1, 6, 4)),
        ("0.0.0", (0, 0, 0)),
        ("not-a-version", ()),
        ("1.2", (1, 2)),
    ],
)
def test_parse_version(raw, expected):
    assert parse_version(raw) == expected


# --- evaluate: golden paths ------------------------------------------------

def _policy(min_version, hard_block, *, message=None, update_url=None):
    p = {
        "platforms": {
            "cli": {"min_version": min_version, "hard_block": hard_block},
        },
    }
    if message is not None:
        p["message"] = message
    if update_url is not None:
        p["update_url"] = update_url
    return p


def test_evaluate_allows_equal_version():
    d = evaluate(_policy("1.7.0", False), current_version="1.7.0", platform="cli")
    assert d.status == PolicyDecision.ALLOW


def test_evaluate_allows_newer_version():
    d = evaluate(_policy("1.6.0", False), current_version="1.7.0", platform="cli")
    assert d.status == PolicyDecision.ALLOW


def test_evaluate_nags_below_min_soft():
    d = evaluate(_policy("1.7.1", False), current_version="1.7.0", platform="cli")
    assert d.status == PolicyDecision.NAG
    assert d.min_version == "1.7.1"


def test_evaluate_blocks_below_min_hard():
    d = evaluate(_policy("1.7.1", True), current_version="1.7.0", platform="cli")
    assert d.status == PolicyDecision.BLOCK
    assert d.is_block


def test_evaluate_uses_policy_message_and_url():
    d = evaluate(
        _policy("1.7.1", True, message="请升级", update_url="https://example.com/u"),
        current_version="1.7.0",
        platform="cli",
    )
    assert d.message == "请升级"
    assert d.update_url == "https://example.com/u"


# --- evaluate: fail-open ---------------------------------------------------

def test_evaluate_missing_policy_is_allow():
    assert evaluate(None, current_version="0.0.1", platform="cli").status == PolicyDecision.ALLOW


def test_evaluate_missing_platform_is_allow():
    assert (
        evaluate({"platforms": {}}, current_version="0.0.1", platform="cli").status
        == PolicyDecision.ALLOW
    )


def test_evaluate_unknown_platform_is_allow():
    assert (
        evaluate(_policy("9.9.9", True), current_version="0.0.1", platform="does-not-exist").status
        == PolicyDecision.ALLOW
    )


def test_evaluate_malformed_version_is_allow():
    # min_version not a version string -> fail-open
    assert (
        evaluate({"platforms": {"cli": {"min_version": "???", "hard_block": True}}},
                 current_version="1.0.0", platform="cli").status
        == PolicyDecision.ALLOW
    )


# --- fetch_policy ----------------------------------------------------------

def test_fetch_policy_returns_none_on_unreachable(monkeypatch):
    # Force every candidate URL to fail; must return None (fail-open).
    import media_downloader.core.version_policy as vp

    def boom(*args, **kwargs):
        raise OSError("forced network failure")

    monkeypatch.setattr(vp, "http_get_bytes", boom)
    # Re-point URLs to something that will hit the mocked helper regardless.
    monkeypatch.setattr(vp, "_POLICY_URLS", ["https://unreachable.invalid/policy.json"])
    assert fetch_policy() is None
