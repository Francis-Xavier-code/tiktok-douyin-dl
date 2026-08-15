"""Bilingual disclaimer text and agreement check (shared by the CLI entry points)."""

import json
import os
import sys
from pathlib import Path


def _config_path() -> Path:
    """Return the path to the CLI config file (~/.config/tiktok-douyin-dl/config.json)."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "tiktok-douyin-dl" / "config.json"


def _load_config() -> dict:
    try:
        path = _config_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_config(cfg: dict) -> None:
    try:
        path = _config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def check_disclaimer_agreement(locale: str = "zh") -> None:
    """Check if the user has agreed to the disclaimer. Show it if not.

    On first run (or if not yet agreed), prints the disclaimer, asks for
    agreement, and optionally offers 'don't show again'. Agreement is persisted
    to ~/.config/tiktok-douyin-dl/config.json.
    """
    from media_downloader.i18n import translate

    cfg = _load_config()
    if cfg.get("disclaimer_agreed"):
        return

    t = lambda key: translate(f"cli.common.{key}", locale=locale)

    print(t("disclaimer_title"))
    print(t("disclaimer_text"))

    try:
        agree = input(t("disclaimer_agree")).strip().lower()
        if agree not in ("y", "yes"):
            print(t("disclaimer_declined"))
            sys.exit(0)
    except (KeyboardInterrupt, EOFError):
        print("\n" + t("exited_safely"))
        sys.exit(0)

    # Ask 'don't show again'
    try:
        dont_show = input(t("disclaimer_dont_show")).strip().lower()
        if dont_show in ("y", "yes"):
            cfg["disclaimer_agreed"] = True
            _save_config(cfg)
    except (KeyboardInterrupt, EOFError):
        pass
