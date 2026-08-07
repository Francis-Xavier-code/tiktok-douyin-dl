"""Unit tests for media_downloader.core.launch (browser provisioning)."""

import os
import sys

import pytest

from media_downloader.core import launch


# --- bundled_browser_path ---------------------------------------------------

def _fake_frozen(monkeypatch, *, frozen=True, meipass=None, exe_dir="/opt/app"):
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    if meipass is None:
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    else:
        monkeypatch.setattr(sys, "_MEIPASS", meipass, raising=False)
    monkeypatch.setattr(sys, "executable", os.path.join(exe_dir, "media-downloader"))


def test_bundled_path_none_when_source(monkeypatch, tmp_path):
    _fake_frozen(monkeypatch, frozen=False)
    assert launch.bundled_browser_path() is None


def test_bundled_path_sidecar_next_to_exe(monkeypatch, tmp_path):
    exe_dir = tmp_path / "app"
    exe_dir.mkdir()
    (exe_dir / "ms-playwright" / "chromium-1234").mkdir(parents=True)
    _fake_frozen(monkeypatch, exe_dir=str(exe_dir))
    assert launch.bundled_browser_path() == str(exe_dir / "ms-playwright")


def test_bundled_path_meipass_takes_precedence(monkeypatch, tmp_path):
    exe_dir = tmp_path / "app"
    meipass = tmp_path / "mei"
    for base in (exe_dir, meipass):
        (base / "ms-playwright" / "chromium-1234").mkdir(parents=True)
    _fake_frozen(monkeypatch, meipass=str(meipass), exe_dir=str(exe_dir))
    assert launch.bundled_browser_path() == str(meipass / "ms-playwright")


def test_bundled_path_none_when_frozen_without_browser(monkeypatch, tmp_path):
    exe_dir = tmp_path / "app"
    exe_dir.mkdir()
    _fake_frozen(monkeypatch, exe_dir=str(exe_dir))
    assert launch.bundled_browser_path() is None


# --- configure_browser_env --------------------------------------------------

def test_configure_prefers_user_env(monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "/custom/path")
    launch.configure_browser_env()
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == "/custom/path"


def test_configure_points_at_bundled_when_frozen(monkeypatch, tmp_path):
    exe_dir = tmp_path / "app"
    (exe_dir / "ms-playwright" / "chromium-1234").mkdir(parents=True)
    _fake_frozen(monkeypatch, exe_dir=str(exe_dir))
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    launch.configure_browser_env()
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == str(exe_dir / "ms-playwright")


def test_configure_falls_back_to_user_cache(monkeypatch, tmp_path):
    _fake_frozen(monkeypatch, exe_dir=str(tmp_path / "app"))
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    launch.configure_browser_env()
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == launch.PLAYWRIGHT_BROWSERS_PATH
