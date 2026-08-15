"""Ed25519 signature verification for remote policy files.

The Android client (apps/android/.../PolicyVerifier.kt) pioneered this scheme:
the maintainer signs download-policy.json with a private key that never
leaves the release machine (scripts/sign-policy.py + secrets/), and every
client verifies the ``signature`` field against this embedded public key
before trusting the policy. Fail-closed: a missing/invalid signature means
the policy is not trusted.

Canonical payload (must stay byte-identical across ALL clients):

    updated_at
    enabled          # "true" / "false"
    message
    min_version

The public key below MUST match PolicyVerifier.kt and any other client.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, Optional

# Ed25519 public key (base64, 32 bytes) -- keep in sync with
# apps/android/app/src/main/java/com/douyindownload/PolicyVerifier.kt
# and apple/Sources/MediaDownloaderCore/PolicyServices.swift
PUBLIC_KEY_B64 = "TfI3/szbWh13QZr/FunFipeal2vb+vkrYoazGJHf6iw="


def _as_str(value: Any, default: str = "") -> str:
    """Mirror org.json optString semantics: non-string values -> default."""
    return value if isinstance(value, str) else default


def canonical_policy(policy: dict) -> str:
    """Serialize the signed fields exactly like PolicyVerifier.canonicalPolicy().

    Only updated_at / enabled / message / min_version are covered by the
    signature, so adding other JSON fields (issue_url, platforms, ...) does
    not invalidate existing signatures.
    """
    download = policy.get("download")
    if not isinstance(download, dict):
        download = {}
    enabled = download.get("enabled", True)
    if isinstance(enabled, bool):
        enabled_text = "true" if enabled else "false"
    else:
        enabled_text = "true" if str(enabled).lower() == "true" else "false"
    return "\n".join([
        _as_str(policy.get("updated_at")),
        enabled_text,
        _as_str(download.get("message")),
        _as_str(download.get("min_version"), "0.0.0"),
    ])


def verify_policy_signature(policy: dict) -> bool:
    """Return True only when ``policy`` carries a valid Ed25519 signature.

    Missing signature, malformed base64 or any verification failure -> False
    (the caller must treat the policy as untrusted / unreachable).
    """
    signature = policy.get("signature") if isinstance(policy, dict) else None
    if not isinstance(signature, str) or not signature.strip():
        return False
    try:
        from nacl.exceptions import BadSignatureError
        from nacl.signing import VerifyKey

        key_bytes = base64.b64decode(PUBLIC_KEY_B64)
        signature_bytes = base64.b64decode(signature.strip())
        payload = canonical_policy(policy).encode("utf-8")
        VerifyKey(key_bytes).verify(payload, signature_bytes)
        return True
    except (BadSignatureError, ValueError, TypeError, ImportError):
        return False
