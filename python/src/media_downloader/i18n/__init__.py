"""Small, dependency-free i18n service shared by the GUI and CLI entry points."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_LOCALE = "zh"
SUPPORTED_LOCALES = {"zh", "en"}
LOCALES_DIRECTORY = Path(__file__).with_name("locales")


def get_locale() -> str:
    """Read the persisted UI locale without coupling callers to a GUI module."""
    try:
        config_path = Path(sys.argv[0]).resolve().with_name("config.json")
        locale = json.loads(config_path.read_text(encoding="utf-8")).get("lang", DEFAULT_LOCALE)
        return normalize_locale(locale)
    except (OSError, ValueError, AttributeError):
        return DEFAULT_LOCALE


def normalize_locale(locale: str | None) -> str:
    candidate = (locale or DEFAULT_LOCALE).replace("_", "-").lower()
    return candidate.split("-", maxsplit=1)[0] if candidate.split("-", maxsplit=1)[0] in SUPPORTED_LOCALES else DEFAULT_LOCALE


@lru_cache(maxsize=len(SUPPORTED_LOCALES))
def _catalog(locale: str) -> dict[str, Any]:
    path = LOCALES_DIRECTORY / f"{normalize_locale(locale)}.json"
    try:
        with path.open(encoding="utf-8") as source:
            return json.load(source)
    except FileNotFoundError:
        from .catalogs import CATALOGS
        return CATALOGS[normalize_locale(locale)]


def translate(key: str, *, locale: str | None = None, **variables: object) -> str:
    """Return a localized value addressed by a dotted key, falling back to Chinese."""
    for candidate in (normalize_locale(locale or get_locale()), DEFAULT_LOCALE):
        value: Any = _catalog(candidate)
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        if isinstance(value, str):
            try:
                return value.format(**variables)
            except (KeyError, ValueError):
                return value
    return key
