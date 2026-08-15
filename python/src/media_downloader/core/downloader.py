"""Common orchestration and display helpers."""

from typing import List

from .models import DownloadRequest, Platform


def format_size(byte_count: int) -> str:
    """Format a byte count for human-readable CLI output."""
    if not byte_count:
        return "N/A"
    size = float(byte_count)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"



def download(request: DownloadRequest) -> None:
    """Dispatch one request to the selected platform implementation."""
    if request.platform is Platform.DOUYIN:
        from media_downloader.platforms import douyin as implementation
    else:
        from media_downloader.platforms import tiktok as implementation
    implementation.download_urls(request.share_text, str(request.output_directory))
