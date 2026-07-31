from media_downloader.platforms.douyin import (
    extract_aweme_id,
    extract_urls_from_text,
    normalize_douyin_url,
)


SEARCH_RESULT_URL = (
    "https://www.douyin.com/root/search/%E7%BE%8E%E5%A5%B3"
    "?aid=837421e4-62fa-4955-a6db-cc4911e4e7db"
    "&modal_id=7667973004903269546&type=general"
)


def test_extracts_douyin_url_from_share_text():
    text = "复制打开抖音 https://v.douyin.com/AbCd123/ 查看作品"
    assert extract_urls_from_text(text) == ["https://v.douyin.com/AbCd123/"]


def test_extracts_aweme_id_from_video_and_note_urls():
    assert extract_aweme_id("https://www.douyin.com/video/1234567890") == "1234567890"
    assert extract_aweme_id("https://www.douyin.com/note/9876543210") == "9876543210"


def test_extracts_aweme_id_from_search_result_modal():
    assert extract_aweme_id(SEARCH_RESULT_URL) == "7667973004903269546"


def test_normalizes_search_result_url_to_direct_work_url():
    expected = "https://www.douyin.com/video/7667973004903269546"
    assert normalize_douyin_url(SEARCH_RESULT_URL) == expected
    assert extract_urls_from_text(f"搜索结果：{SEARCH_RESULT_URL}") == [expected]


def test_preserves_share_short_link_during_normalization():
    short_url = "https://v.douyin.com/AbCd123/"
    assert normalize_douyin_url(short_url) == short_url


def test_normalizes_web_search_result_from_douyin_selected():
    result_url = "https://jingxuan.douyin.com/m/video/7667973004903269546"
    assert normalize_douyin_url(result_url) == (
        "https://www.douyin.com/video/7667973004903269546"
    )
