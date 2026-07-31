"""Data models shared by the CLI, GUI, and WebUI adapters."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class Platform(str, Enum):
    DOUYIN = "douyin"
    TIKTOK = "tiktok"


@dataclass(frozen=True)
class DownloadRequest:
    platform: Platform
    share_text: str
    output_directory: Path


@dataclass
class DownloadResult:
    source_url: str
    files: List[Path] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.error is None
