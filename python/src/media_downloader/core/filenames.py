"""Collision-free media filename generation."""

import re
from pathlib import Path

_MEDIA_PATTERN = re.compile(r"^\[(\d+)\](?:image|video)\.\w+$", re.IGNORECASE)
_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"}


def next_media_filename(output_directory: str, extension: str) -> str:
    directory = Path(output_directory)
    normalized_extension = extension.lower().lstrip(".")
    max_index = 0

    if directory.exists():
        for entry in directory.iterdir():
            match = _MEDIA_PATTERN.match(entry.name)
            if match:
                max_index = max(max_index, int(match.group(1)))

    prefix = "image" if normalized_extension in _IMAGE_EXTENSIONS else "video"
    next_index = max_index + 1
    while True:
        candidate = f"[{next_index}]{prefix}.{normalized_extension}"
        if not (directory / candidate).exists():
            return candidate
        next_index += 1
