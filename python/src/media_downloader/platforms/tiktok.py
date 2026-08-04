#!/usr/bin/env python3
"""
TikTok Media Downloader (Linux Standalone)
Usage:
  tiktok-dl <Link/Sharing Text> [Output Directory]
"""

import json
import re
import time
import urllib.parse

from media_downloader.core.downloader import format_size
from media_downloader.core.filenames import next_media_filename
from media_downloader.core.launch import (
    apply_frozen_env_fixes,
    configure_browser_env,
    ensure_browser_installed,
)
from media_downloader.core.disclaimer import DISCLAIMER, DISCLAIMER_EN
from media_downloader.core.network import http_get_bytes
from media_downloader.core.updater import VERSION, check_for_updates
from media_downloader.core.version_policy import check_version_policy
from media_downloader.core.download_policy import check_download_allowed
from media_downloader.i18n import get_locale, translate

# Apply PyInstaller / browser-env fixes up front.
apply_frozen_env_fixes()
configure_browser_env()

# Compatibility value for callers that inspect the selected locale. User-facing
# strings are resolved by the JSON catalogs through t().
LANG = get_locale()

# User-facing text is maintained by media_downloader.i18n.


def t(key, **kwargs):
    platform_key = f"cli.tiktok.{key}"
    localized = translate(platform_key, locale=LANG, **kwargs)
    return localized if localized != platform_key else translate(f"cli.common.{key}", locale=LANG, **kwargs)


def extract_urls_from_text(text: str) -> list:
    """提取文本中的所有 TikTok 链接"""
    url_pattern = re.compile(r'https?://[a-zA-Z0-9][-a-zA-Z0-9\\._]*\btiktok\.com\b[-a-zA-Z0-9@:%_+.~#?&//=]*')
    return url_pattern.findall(text)


def get_next_filename(output_dir, extension):
    return next_media_filename(output_dir, extension)


def process_single(url, browser, output_base, index, total):
    """处理并下载单个 TikTok 链接"""
    print(f"\n[{index}/{total}] {t('parsing')}")

    # 用 Playwright 加载页面并等待 JSON
    page = None
    try:
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = context.new_page()

        # 引入反爬伪装，擦除 WebDriver 指纹
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(page)
        except ImportError:
            pass
        # CDP 注入：隐藏 Playwright 自动化特征，防止被 TikTok 检测
        # 注意：新版 Playwright Python 需要用 context.new_cdp_session(page)
        try:
            cdp_session = context.new_cdp_session(page)
            cdp_session.send("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
                    window.chrome = { runtime: {} };
                    delete window.cdc_adoQpoasnfa4pcohlfhok;
                    delete window.$cdc_asdjflasutopfhvcZLmcfl_;
                """
            })
        except Exception:
            pass  # CDP 不可用时静默跳过
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6000)  # 等待完整渲染与状态注水

        rehyd_script = page.query_selector("script#__UNIVERSAL_DATA_FOR_REHYDRATION__")
        if not rehyd_script:
            # 备用：如果直接有 video src
            video_el = page.query_selector("video")
            if video_el:
                src = video_el.get_attribute("src")
                if src and not src.startswith("blob:"):
                    # 下载该非 blob 地址
                    import os
                    filepath = os.path.join(output_base, f"tiktok_{int(time.time())}.mp4")
                    resp = page.request.get(src, headers={"Referer": "https://www.tiktok.com/"})
                    if resp.status == 200:
                        data = resp.body()
                        with open(filepath, "wb") as f:
                            f.write(data)
                    else:
                        raise Exception(f"HTTP {resp.status}")
                    print(t("download_success", filename=os.path.basename(filepath), size=format_size(len(data)), resolution="N/A"))
                    context.close()
                    return True
            raise Exception("No JSON script __UNIVERSAL_DATA_FOR_REHYDRATION__ or direct video src found.")

        json_content = rehyd_script.inner_text()
        data = json.loads(json_content)

        # 尝试提取 itemStruct 节点
        item = data.get("__DEFAULT_SCOPE__", {}).get("webapp.video-detail", {}).get("itemInfo", {}).get("itemStruct", {})
        if not item:
            # 备用路径寻找 (有时结构不同)
            for k, v in data.get("__DEFAULT_SCOPE__", {}).items():
                if isinstance(v, dict) and "itemInfo" in v:
                    item = v.get("itemInfo", {}).get("itemStruct", {})
                    break

        if not item:
            raise Exception("Failed to locate itemStruct in JSON data.")

        desc = item.get("desc", "tiktok_media").strip()
        # 清洗文件名安全字符，去掉换行，并限制长度防止过长
        desc_clean = re.sub(r'[\\/*?:"<>|]', "", desc).replace("\n", " ").replace("\r", " ").strip()[:20] or "tiktok_media"
        aweme_id = item.get("id")
        if not aweme_id:
            aweme_id = str(int(time.time()))

        # 获取作者信息用于归档 (不再创建子文件夹)
        author_info = item.get("author", {})
        author_name = author_info.get("nickname") or author_info.get("uniqueId") or "Unknown_Author"
        author_clean = re.sub(r'[\\/*?:"<>|]', "", str(author_name)).replace("\n", " ").replace("\r", " ").strip()[:30]

        video_info = item.get("video", {})
        play_addr = video_info.get("playAddr")

        # 区分是视频还是图文
        images = item.get("imagePostInfo", {}).get("images", [])

        if images:
            # 图文相册下载
            title_log = t("image_found", title=desc_clean, id=aweme_id, count=len(images))
            print(title_log)

            import os
            os.makedirs(output_base, exist_ok=True)

            for i, img in enumerate(images, 1):
                urls_to_try = []
                if "displayAddr" in img and isinstance(img["displayAddr"], dict) and "urlList" in img["displayAddr"]:
                    urls_to_try.extend(img["displayAddr"]["urlList"])
                elif "displayAddr" in img and isinstance(img["displayAddr"], str):
                    urls_to_try.append(img["displayAddr"])
                if "imageURL" in img and "urlList" in img["imageURL"]:
                    urls_to_try.extend(img["imageURL"]["urlList"])
                if "thumbnail" in img and "urlList" in img["thumbnail"]:
                    urls_to_try.extend(img["thumbnail"]["urlList"])

                if not urls_to_try:
                    continue

                img_filename = get_next_filename(output_base, "jpg")
                img_path = os.path.join(output_base, img_filename)

                # 预占位防止循环内重名
                with open(img_path, "wb") as f:
                    pass

                success_img = False
                for img_url in urls_to_try:
                    try:
                        resp = page.request.get(img_url, headers={"Referer": "https://www.tiktok.com/"})
                        if resp.status != 200:
                            resp = page.request.get(img_url)

                        if resp.status == 200:
                            img_data = resp.body()
                            with open(img_path, "wb") as f:
                                f.write(img_data)
                        else:
                            raise Exception(f"HTTP {resp.status}")

                        # 使用 Pillow 分析尺寸
                        resolution = "N/A"
                        try:
                            from PIL import Image as PILImage
                            with PILImage.open(img_path) as p_img:
                                resolution = f"{p_img.width}x{p_img.height}"
                        except Exception:
                            pass
                        print(t("download_success", filename=img_filename, size=format_size(len(img_data)), resolution=resolution))
                        success_img = True
                        break
                    except Exception:
                        continue

                if not success_img:
                    print(t("download_failed", err="All fallback URLs returned 403 or failed."))

        elif play_addr:
            # 视频下载
            title_log = t("video_found", title=desc_clean, id=aweme_id)
            print(title_log)

            # 确定文件名和保存路径
            import os
            os.makedirs(output_base, exist_ok=True)
            filename = get_next_filename(output_base, "mp4")
            filepath = os.path.join(output_base, filename)

            # 预占位
            with open(filepath, "wb") as f:
                pass

            # 使用 Playwright page.request 下载直接的 playAddr（不需要水印提取，原始 CDN 无水印）
            resp = page.request.get(play_addr, headers={"Referer": "https://www.tiktok.com/"})
            if resp.status == 200:
                video_data = resp.body()
                with open(filepath, "wb") as f:
                    f.write(video_data)
            else:
                raise Exception(f"HTTP {resp.status}")

            resolution = video_info.get("definition", "N/A")
            print(t("download_success", filename=filename, size=format_size(len(video_data)), resolution=resolution))
        else:
            raise Exception("Neither playAddr nor images found in JSON state.")

        context.close()
        return True
    except Exception as e:
        print(t("parse_failed", err=e))
        if page:
            try:
                page.context.close()
            except Exception:
                pass
        return False


def download_urls(raw_input: str, output_dir: str):
    """批量下载 TikTok 链接"""
    # Remote download-policy gate: block before any network/parse work.
    decision = check_download_allowed(silent=False)
    if decision.is_block:
        return False

    urls = extract_urls_from_text(raw_input)
    if not urls:
        print(t("no_links"))
        return False

    # 数组去重
    unique_urls = []
    seen = set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    urls = unique_urls

    total = len(urls)

    if not output_dir:
        output_dir = "tiktok_downloads"
    import os
    os.makedirs(output_dir, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ensure_browser_installed(p, t=t)
        browser = p.chromium.launch(headless=True)
        success = 0
        fail = 0
        for i, url in enumerate(urls, 1):
            if process_single(url, browser, output_dir, i, total):
                success += 1
            else:
                fail += 1
        browser.close()

    print(t("download_done", success=success, fail=fail))
    print(t("save_dir_info", path=os.path.abspath(output_dir)))
    return True


def download_tiktok_links(links, output_dir):
    """供 WebUI 调用的批量下载接口"""
    if isinstance(links, list):
        raw_input = "\n".join(links)
    else:
        raw_input = str(links)
    return download_urls(raw_input, output_dir)


def main():
    import sys
    import os
    if len(sys.argv) >= 2:
        # Command line parameter mode
        print(t("legal_warning"))

        check_for_updates(silent=True)
        check_version_policy(silent=True)  # fail-open; exits(1) only on hard block
        raw_input = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "tiktok_downloads"
        download_urls(raw_input, output_dir)
    else:
        # Interactive mode
        print(t("disclaimer_title"))
        print(t("disclaimer_text"))

        try:
            agree = input(t("disclaimer_agree")).strip().lower()
            if agree not in ['y', 'yes']:
                print(t("disclaimer_declined"))
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            print("\n" + t("exited_safely"))
            sys.exit(0)

        print(t("title_banner"))
        check_for_updates(silent=False)
        check_version_policy(silent=False)  # nag or hard-block old builds

        try:
            while True:
                raw_input = input(t("input_prompt")).strip()
                if not raw_input or raw_input.lower() in ['q', 'exit']:
                    print(t("exited_safely"))
                    break

                output_dir = input(t("save_dir_prompt", default_dir="tiktok_downloads")).strip()
                if not output_dir:
                    output_dir = "tiktok_downloads"

                print(t("parsing"))
                download_urls(raw_input, output_dir)
        except (KeyboardInterrupt, EOFError):
            print("\n" + t("exited_safely"))


if __name__ == "__main__":
    main()
