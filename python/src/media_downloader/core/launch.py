"""Startup environment fixes and Playwright browser provisioning.

This consolidates the boilerplate that previously lived in *every* platform
entry point (the PyInstaller ``LD_LIBRARY_PATH`` fix, the Playwright browser
cache path, and the missing-browser auto-installer). The browser installer is
now platform-aware instead of hard-coding ``chromium-win64.zip``.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys

# Cache directory for browser binaries (mirrors PyInstaller behaviour).
PLAYWRIGHT_BROWSERS_PATH = os.path.expanduser("~/.cache/ms-playwright")

# Domestic mirror candidates used when the official CDN is unreachable.
DEFAULT_MIRRORS = [
    "https://playwright-zh.oss-cn-hangzhou.aliyuncs.com",
    "https://cdn.npmmirror.com/binaries/playwright",
    "https://ghproxy.com/https://playwright.azureedge.net",
    "https://playwright.azureedge.net",
]

NPM_MIRROR = "https://registry.npmmirror.com"


def apply_frozen_env_fixes() -> None:
    """Undo PyInstaller's library-path pollution when running frozen."""
    if not getattr(sys, "frozen", False):
        return
    for key in ("LD_LIBRARY_PATH", "LIBPATH", "DYLD_LIBRARY_PATH"):
        orig = key + "_ORIG"
        if orig in os.environ:
            os.environ[key] = os.environ[orig]
        else:
            os.environ.pop(key, None)


def bundled_browser_path() -> str | None:
    """Locate a Playwright browser directory shipped with a frozen build.

    Precedence: inside the PyInstaller bundle (``sys._MEIPASS``), then a
    sidecar ``ms-playwright`` folder next to the executable. Returns None
    when running from source or when no bundled browser is present, so the
    caller falls back to the user cache + auto-install.
    """
    if not getattr(sys, "frozen", False):
        return None
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "ms-playwright"))
    candidates.append(
        os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "ms-playwright")
    )
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return None


def configure_browser_env(mirror: str | None = None) -> None:
    """Set PLAYWRIGHT_BROWSERS_PATH and a domestic download mirror if unset.

    A user-provided PLAYWRIGHT_BROWSERS_PATH always wins. Frozen builds that
    ship a bundled/sidecar browser are pointed at it (no first-run download);
    otherwise the user cache is used and ensure_browser_installed() will
    auto-install when missing.
    """
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled_browser_path() or PLAYWRIGHT_BROWSERS_PATH
    if mirror and "PLAYWRIGHT_DOWNLOAD_HOST" not in os.environ:
        os.environ["PLAYWRIGHT_DOWNLOAD_HOST"] = mirror
    if "npm_config_registry" not in os.environ:
        os.environ["npm_config_registry"] = NPM_MIRROR


def ensure_browser_installed(playwright_inst, *, mirror: str | None = None,
                             t: callable = lambda k, **kw: k) -> None:
    """Launch Chromium once to confirm it exists, auto-installing if missing.

    Works on Windows, macOS, and Linux.
    """
    try:
        browser = playwright_inst.chromium.launch(headless=True)
        browser.close()
        return
    except Exception as e:
        err_msg = str(e)
        if not ("Executable doesn't exist" in err_msg
                or "looks like Playwright was just installed" in err_msg
                or "executable doesn't exist" in err_msg.lower()):
            raise e

    print(t("browser_not_found"))
    configure_browser_env(mirror)

    try:
        import os as _os
        creationflags = 0
        if _os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        from playwright._impl._driver import compute_driver_executable, get_driver_env

        driver_executable, driver_cli = compute_driver_executable()
        subprocess.run(
            [driver_executable, driver_cli, "install", "chromium"],
            env=get_driver_env(),
            check=True,
            creationflags=creationflags,
        )
        print(t("browser_install_success"))
    except subprocess.CalledProcessError as exit_err:
        print(t("browser_install_failed", code=exit_err.returncode))
        sys.exit(1)
    except Exception as inner_e:
        print(t("browser_install_failed", code=str(inner_e)))
        sys.exit(1)
