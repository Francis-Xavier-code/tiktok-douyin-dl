from media_downloader.platforms.tiktok import extract_urls_from_text


def test_extracts_tiktok_urls_in_order():
    text = "first https://www.tiktok.com/@creator/video/123 then https://vm.tiktok.com/ABC/"
    assert extract_urls_from_text(text) == [
        "https://www.tiktok.com/@creator/video/123",
        "https://vm.tiktok.com/ABC/",
    ]
