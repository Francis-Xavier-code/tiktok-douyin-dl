import pytest

from media_downloader.cli import detect_platform
from media_downloader.core.models import Platform


@pytest.mark.parametrize(
    ("share_text", "expected"),
    [
        ("复制打开抖音 https://v.douyin.com/AbCd123/", Platform.DOUYIN),
        ("Watch https://www.tiktok.com/@creator/video/123", Platform.TIKTOK),
        ("Watch https://vm.tiktok.com/ZTest/", Platform.TIKTOK),
    ],
)
def test_detect_platform(share_text, expected):
    assert detect_platform(share_text) is expected


def test_detect_platform_rejects_unknown_text():
    with pytest.raises(ValueError, match="no supported"):
        detect_platform("https://example.com/video/123")


def test_detect_platform_rejects_mixed_platforms():
    with pytest.raises(ValueError, match="both Douyin and TikTok"):
        detect_platform("https://v.douyin.com/abc https://vm.tiktok.com/xyz")
