from media_downloader.platforms.douyin import extract_aweme_id, extract_urls_from_text


def test_extracts_douyin_url_from_share_text():
    text = "复制打开抖音 https://v.douyin.com/AbCd123/ 查看作品"
    assert extract_urls_from_text(text) == ["https://v.douyin.com/AbCd123/"]


def test_extracts_aweme_id_from_video_and_note_urls():
    assert extract_aweme_id("https://www.douyin.com/video/1234567890") == "1234567890"
    assert extract_aweme_id("https://www.douyin.com/note/9876543210") == "9876543210"
