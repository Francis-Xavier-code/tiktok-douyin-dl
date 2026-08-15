"""Unit tests for media_downloader.core.policy_verifier (Ed25519 policy signing).

The canonical payload must stay byte-identical with the Android client
(PolicyVerifier.kt) and the Swift client (PolicyServices.swift):
    updated_at
    enabled
    message
    min_version
"""

import base64

import pytest

from media_downloader.core import policy_verifier as pv


def _sign(policy: dict, key) -> dict:
    payload = pv.canonical_policy(policy).encode("utf-8")
    policy["signature"] = base64.b64encode(key.sign(payload).signature).decode("ascii")
    return policy


@pytest.fixture()
def keypair(monkeypatch):
    import nacl.signing

    key = nacl.signing.SigningKey.generate()
    monkeypatch.setattr(pv, "PUBLIC_KEY_B64",
                        base64.b64encode(key.verify_key.encode()).decode("ascii"))
    return key


def test_canonical_payload_format(keypair):
    policy = {
        "schema": 1,
        "updated_at": "2026-08-15T00:00:00Z",
        "issue_url": "https://example.com/issues",
        "download": {
            "enabled": True,
            "message": "下载功能已恢复。",
            "min_version": "1.7.0",
            "platforms": {"android": {"enabled": True, "min_version": "2.0.0"}},
        },
    }
    # Only the four signed fields participate, in the documented order.
    assert pv.canonical_policy(policy) == (
        "2026-08-15T00:00:00Z\ntrue\n下载功能已恢复。\n1.7.0"
    )


def test_canonical_missing_fields_use_kotlin_defaults(keypair):
    # optString("updated_at", "") / optBoolean("enabled", true) / optString("min_version", "0.0.0")
    assert pv.canonical_policy({"download": {}}) == "\ntrue\n\n0.0.0"
    assert pv.canonical_policy({}) == "\ntrue\n\n0.0.0"
    assert pv.canonical_policy({"download": {"enabled": "FALSE"}}) == "\nfalse\n\n0.0.0"
    # Non-string values fall back like org.json optString.
    assert pv.canonical_policy({"download": {"min_version": 7}}) == "\ntrue\n\n0.0.0"


def test_verify_roundtrip_valid(keypair):
    policy = _sign({
        "updated_at": "2026-08-15T00:00:00Z",
        "download": {"enabled": True, "message": "ok", "min_version": "0.0.0"},
    }, keypair)
    assert pv.verify_policy_signature(policy) is True


def test_verify_missing_signature_fails(keypair):
    assert pv.verify_policy_signature({"updated_at": "x", "download": {}}) is False
    assert pv.verify_policy_signature(None) is False


def test_verify_tampered_payload_fails(keypair):
    policy = _sign({
        "updated_at": "2026-08-15T00:00:00Z",
        "download": {"enabled": True, "message": "ok", "min_version": "0.0.0"},
    }, keypair)
    policy["download"]["message"] = "evil"  # not covered by the signature anymore
    assert pv.verify_policy_signature(policy) is False


def test_verify_wrong_key_fails(monkeypatch):
    import nacl.signing

    policy = _sign({
        "updated_at": "2026-08-15T00:00:00Z",
        "download": {"enabled": True},
    }, nacl.signing.SigningKey.generate())
    # Public key stays the DEFAULT embedded key (not patched) -> mismatch.
    assert pv.verify_policy_signature(policy) is False


def test_extra_fields_do_not_break_signature(keypair):
    # Adding unrelated JSON fields must not invalidate an existing signature.
    policy = _sign({
        "updated_at": "2026-08-15T00:00:00Z",
        "download": {"enabled": True, "message": "ok", "min_version": "0.0.0"},
    }, keypair)
    policy["issue_url"] = "https://example.com/issues"
    policy["schema"] = 1
    assert pv.verify_policy_signature(policy) is True
