"""Bilingual disclaimer text and agreement check (shared by the CLI entry points)."""

import json
import os
import sys
from pathlib import Path

DISCLAIMER = """================================================================================
                                【 免 责 声 明 】
================================================================================
 1. 本工具（以下简称"本软件"）仅限用于个人学习研究、学术交流及网页技术备份
    测试，严禁用于任何商业用途、非法抓取或网络攻击。
 2. 本软件所下载的所有音视频、图文等媒体资源，其知识产权及著作权归原作者/
    版权所有者或相关平台所有。用户下载后应于24小时内删除，且不得在未经原作者
    授权的情况下进行二次传播、修改、上传或用于任何盈利性活动。
 3. 用户在使用本软件时，必须遵守当地法律法规、目的平台用户协议及相关服务条款。
    因使用本软件导致的一切直接或间接法律纠纷、版权诉讼、经济赔偿，或因频繁请求
    导致的平台账号限制、IP风控封禁等后果，均由使用者自行承担全部责任。
 4. 本软件按"原样"（AS IS）提供，不附带任何明示或暗示的保证，包括但不限于
    对特定用途的适用性。作者在任何情况下均不对因使用或无法使用本软件而产生的
    任何直接、间接、偶然、特殊或惩罚性损害（包括法律处罚）承担任何赔偿责任。
 5. 任何复制、运行、分发或以任何方式使用本软件的行为，即视为您已完全阅读、
    理解并无条件接受本声明的所有条款。如果您不同意本声明的任何内容，请立即
    停止使用并卸载本软件。
================================================================================"""

DISCLAIMER_EN = """================================================================================
                                【 DISCLAIMER 】
================================================================================
 1. This tool (hereinafter referred to as "the software") is strictly for personal
    learning, research, academic exchanges, and technical backup tests. Commercial
    use, malicious scraping, or network attacks are strictly prohibited.
 2. All media resources (videos, images, etc.) downloaded belong to the original
    creators/copyright owners. Users must delete them within 24 hours and must not
    redistribute, modify, upload, or use them for profit without authorization.
 3. Users must comply with local laws and platform Terms of Service. The user assumes
    the full responsibility for any legal disputes, copyright lawsuits, financial
    damages, account restrictions, or IP bans caused by using this software.
 4. This software is provided "AS IS" without warranties of any kind. Under no
    circumstances shall the author be liable for any direct, indirect, incidental,
    or special damages arising from the use or inability to use this software.
 5. Running, distributing, or using this software constitutes unconditional acceptance
    of this disclaimer. If you disagree with any terms, please stop using and uninstall
    this software immediately.
================================================================================"""


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
