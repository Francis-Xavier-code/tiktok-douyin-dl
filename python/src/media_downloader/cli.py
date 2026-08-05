"""Console entry points for the Python package."""

import argparse
import re
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlparse

from media_downloader.core.downloader import download
from media_downloader.core.models import DownloadRequest, Platform

_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def detect_platform(share_text: str) -> Platform:
    """Detect the supported platform from URLs contained in share text."""
    detected = set()
    for raw_url in _URL_PATTERN.findall(share_text):
        host = (urlparse(raw_url).hostname or "").lower()
        if host == "douyin.com" or host.endswith(".douyin.com"):
            detected.add(Platform.DOUYIN)
        elif host == "tiktok.com" or host.endswith(".tiktok.com"):
            detected.add(Platform.TIKTOK)

    if len(detected) == 1:
        return detected.pop()
    if len(detected) > 1:
        raise ValueError("share text contains both Douyin and TikTok links")
    raise ValueError("no supported Douyin or TikTok link was found")


def _parser() -> argparse.ArgumentParser:
    from media_downloader.core.updater import VERSION
    parser = argparse.ArgumentParser(prog="media-downloader")
    parser.add_argument("share_text", nargs="?", help="Share text, URL, or a newline-separated URL list")
    parser.add_argument("output", nargs="?", default="downloads", help="Output directory")
    parser.add_argument(
        "-p",
        "--platform",
        choices=[item.value for item in Platform],
        help="Override automatic platform detection",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.share_text:
        parser.print_help()
        return
    try:
        platform = Platform(args.platform) if args.platform else detect_platform(args.share_text)
    except ValueError as error:
        parser.error(str(error))

    download(
        DownloadRequest(
            platform=platform,
            share_text=args.share_text,
            output_directory=Path(args.output).expanduser(),
        )
    )


def douyin_main() -> None:
    from media_downloader.platforms.douyin import main as platform_main
    platform_main()


def tiktok_main() -> None:
    from media_downloader.platforms.tiktok import main as platform_main
    platform_main()


if __name__ == "__main__":
    main()
