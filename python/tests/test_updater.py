"""Unit tests for the CLI updater integrity helpers."""

import json

import pytest

from media_downloader.core.updater import _resolve_asset_sha256


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_resolves_asset_digest_from_api(monkeypatch):
    import urllib.request

    release = {
        "tag_name": "v2.0.1",
        "assets": [
            {"name": "MediaDownloader-Windows-x64-CLI-2.0.1.zip", "digest": None},
            {
                "name": "MediaDownloader-macOS-arm64-CLI-2.0.1.zip",
                "digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            },
        ],
    }

    def fake_urlopen(req, timeout=8):
        assert "api.github.com" in req.full_url
        return _FakeResponse(json.dumps(release).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    digest = _resolve_asset_sha256("2.0.1", "MediaDownloader-macOS-arm64-CLI-2.0.1.zip")
    assert digest == "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def test_returns_none_when_asset_has_no_digest(monkeypatch):
    import urllib.request

    release = {"tag_name": "v2.0.1", "assets": [{"name": "x.zip", "digest": None}]}
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda req, timeout=8: _FakeResponse(json.dumps(release).encode()),
    )
    assert _resolve_asset_sha256("2.0.1", "x.zip") is None


def test_returns_none_on_network_failure(monkeypatch):
    import urllib.request

    def boom(req, timeout=8):
        raise OSError("rate limited")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert _resolve_asset_sha256("2.0.1", "x.zip") is None
