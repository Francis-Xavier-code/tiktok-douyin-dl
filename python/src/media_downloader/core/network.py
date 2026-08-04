"""Safe, explicit HTTP helpers shared by the downloader.

These wrappers never mutate the global SSL context. When a caller must talk
to a host whose root CA is missing in the frozen/portable runtime, it opts in
per-request via ``verify=False`` instead of disabling certificate checks for
the whole process.
"""

from __future__ import annotations

import hashlib
import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Optional

DEFAULT_TIMEOUT = 15
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _context(verify: bool) -> Optional[ssl.SSLContext]:
    if verify:
        return ssl.create_default_context()
    # Opt-in only: build an unverified context for this one request.
    return ssl._create_unverified_context()


def http_json(url: str, *, timeout: int = DEFAULT_TIMEOUT, verify: bool = True,
              headers: Optional[dict] = None) -> Any:
    """GET ``url`` and parse the body as JSON."""
    req = urllib.request.Request(url, headers=headers or {"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_context(verify)) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_bytes(url: str, *, timeout: int = 60, verify: bool = True,
                   headers: Optional[dict] = None) -> bytes:
    """GET ``url`` and return the raw response body."""
    req = urllib.request.Request(url, headers=headers or {"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_context(verify)) as resp:
        return resp.read()


def http_stream(url: str, *, chunk_size: int = 8192, timeout: int = 60,
                verify: bool = True, headers: Optional[dict] = None):
    """Yield response body in chunks (for large media/asset downloads)."""
    req = urllib.request.Request(url, headers=headers or {"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_context(verify)) as resp:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            yield chunk


def verify_sha256(path: str, expected: str) -> bool:
    """Return True when the file at ``path`` matches ``expected`` (hex digest)."""
    expected = expected.strip().lower()
    if not expected or len(expected) != 64:
        # No usable checksum provided: do not block the update, but do not claim success.
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest() == expected
