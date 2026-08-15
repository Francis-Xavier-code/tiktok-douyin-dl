#!/usr/bin/env python3
"""Ed25519 sign / verify download-policy.json (shared by every client).

The canonical payload covered by the signature is (byte-identical to
PolicyVerifier.kt on Android and core/policy_verifier.py on the Python side):

    updated_at
    enabled          # "true" / "false"
    message
    min_version

Only the maintainer can sign (private key lives in secrets/, gitignored).
Clients verify against the embedded public key and treat an unsigned or
invalidly signed policy as untrusted (fail-closed).

Usage:
    python3 scripts/sign-policy.py [--key secrets/policy-private-key.pem] [policy.json]
    python3 scripts/sign-policy.py --verify [policy.json]     # public-key check only

Examples:
    ./scripts/toggle-download.sh off "下载功能已暂停。"   # signs automatically
    python3 scripts/sign-policy.py download-policy.json
    python3 scripts/sign-policy.py --verify download-policy.json
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

# Allow running straight from a checkout (no install needed).
_SRC = Path(__file__).resolve().parent.parent / "python" / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from media_downloader.core.policy_verifier import canonical_policy, verify_policy_signature  # noqa: E402

DEFAULT_KEY = Path(__file__).resolve().parent.parent / "secrets" / "policy-private-key.pem"


def extract_seed_from_pem(pem_path: Path) -> bytes:
    """Extract the raw 32-byte Ed25519 seed from a PKCS#8 PEM file.

    PKCS#8 wraps the seed as OCTET STRING { OCTET STRING { seed } }; we locate
    the 32-byte OCTET STRING (the only 0x04 0x20 length-tag in the DER body).
    """
    text = pem_path.read_text(encoding="utf-8")
    b64 = "".join(line.strip() for line in text.splitlines()
                  if line.strip() and not line.strip().startswith("-----"))
    der = base64.b64decode(b64)
    seed = None
    i = 0
    while i < len(der) - 2:
        if der[i] == 0x04 and der[i + 1] == 0x20:
            seed = der[i + 2:i + 34]
            break
        i += 1
    if seed is None or len(seed) != 32:
        raise ValueError("unsupported private key: expected PKCS#8 Ed25519")
    return seed


def sign_policy(policy_path: Path, key_path: Path) -> None:
    from nacl.signing import SigningKey

    data = json.loads(policy_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{policy_path}: policy must be a JSON object")

    seed = extract_seed_from_pem(key_path)
    payload = canonical_policy(data).encode("utf-8")
    signature = SigningKey(seed).sign(payload).signature
    data["signature"] = base64.b64encode(signature).decode("ascii")

    policy_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not verify_policy_signature(data):
        raise RuntimeError("signature did not verify; refusing to write")
    print(f"OK signed {policy_path} (Ed25519, {len(signature)} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ed25519 sign/verify download-policy.json")
    parser.add_argument("policy", nargs="?", default="download-policy.json",
                        help="path to download-policy.json (default: download-policy.json)")
    parser.add_argument("--key", default=str(DEFAULT_KEY),
                        help="path to the PKCS#8 Ed25519 private key (default: secrets/policy-private-key.pem)")
    parser.add_argument("--verify", action="store_true",
                        help="verify the embedded signature with the public key only")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    if not policy_path.is_file():
        print(f"error: {policy_path} does not exist", file=sys.stderr)
        return 2

    if args.verify:
        data = json.loads(policy_path.read_text(encoding="utf-8"))
        if verify_policy_signature(data):
            print(f"OK {policy_path}: valid Ed25519 signature")
            return 0
        print(f"FAIL {policy_path}: missing or invalid signature", file=sys.stderr)
        return 1

    key_path = Path(args.key)
    if not key_path.is_file():
        print(f"error: private key not found at {key_path} "
              f"(sign with the maintainer key; verify with --verify)", file=sys.stderr)
        return 2
    try:
        sign_policy(policy_path, key_path)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
