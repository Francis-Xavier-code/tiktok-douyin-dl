#!/usr/bin/env python3
"""
抖音图文/视频批量下载器
用法:
  douyin-dl <链接/分享文本> [输出目录]
"""

import json
import re
import time
import urllib.parse
from datetime import datetime

from media_downloader.core.download_policy import check_download_allowed
from media_downloader.core.downloader import format_size
from media_downloader.core.filenames import next_media_filename
from media_downloader.core.launch import (
    apply_frozen_env_fixes,
    configure_browser_env,
    ensure_browser_installed,
)
from media_downloader.core.network import http_get_bytes, http_json
from media_downloader.core.updater import check_for_updates
from media_downloader.core.version_policy import check_version_policy
from media_downloader.i18n import get_locale, translate

# Apply PyInstaller / browser-env fixes up front.
apply_frozen_env_fixes()
configure_browser_env()

# Compatibility value for callers that inspect the selected locale. User-facing
# strings are resolved by the JSON catalogs through t().
LANG = get_locale()

# User-facing text is maintained by media_downloader.i18n.


def t(key, **kwargs):
    platform_key = f"cli.douyin.{key}"
    localized = translate(platform_key, locale=LANG, **kwargs)
    return localized if localized != platform_key else translate(f"cli.common.{key}", locale=LANG, **kwargs)


def extract_aweme_id(url_or_id: str) -> str:
    """提取作品 ID，支持作品 URL、搜索结果 URL 或纯数字 ID。"""
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id

    parsed = urllib.parse.urlparse(url_or_id)
    path_match = re.search(r'/(?:video|note)/(\d+)(?:/|$)', parsed.path)
    if path_match:
        return path_match.group(1)

    query = urllib.parse.parse_qs(parsed.query)
    for key in ("modal_id", "aweme_id", "item_id", "item_ids"):
        for value in query.get(key, []):
            id_match = re.search(r'\d{10,}', value)
            if id_match:
                return id_match.group(0)
    return ""


def normalize_douyin_url(url: str) -> str:
    """将搜索/精选结果 URL 规范化成 www.douyin.com 直接作品 URL。"""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "douyin.com" or host.endswith(".douyin.com"):
        query_keys = {key.lower() for key in urllib.parse.parse_qs(parsed.query)}
        if query_keys.intersection({"modal_id", "aweme_id", "item_id", "item_ids"}):
            aweme_id = extract_aweme_id(url)
            if aweme_id:
                return f"https://www.douyin.com/video/{aweme_id}"
        aweme_id = extract_aweme_id(url)
        if aweme_id:
            work_type = "note" if "/note/" in parsed.path else "video"
            return f"https://www.douyin.com/{work_type}/{aweme_id}"
    return url


def extract_urls_from_text(text: str) -> list:
    """提取抖音链接，并规范化搜索结果中的作品链接。"""
    url_pattern = re.compile(r'https?://[a-zA-Z0-9][-a-zA-Z0-9\\._]*\bdouyin\.com\b[-a-zA-Z0-9@:%_+.~#?&//=]*')
    return [normalize_douyin_url(url) for url in url_pattern.findall(text)]


def get_image_urls_from_dom(page) -> list:
    """如果 JSON 提取失败，从 DOM 结构备份提取图文列表"""
    image_urls = []
    img_elements = page.query_selector_all('img')
    for el in img_elements:
        src = el.get_attribute('src')
        if src and ('tos-cn-i-' in src or 'img-s.dyimg.cn' in src):
            if src.startswith('//'):
                src = 'https:' + src
            if src not in image_urls:
                image_urls.append(src)
    return image_urls


def get_image_urls_from_page(page_content: str) -> list:
    """从页面源代码备份正则提取图文列表"""
    image_urls = []
    matches = re.findall(r'"src"\s*:\s*"([^"]+)"', page_content)
    for match in matches:
        url = match.replace('\\u002F', '/')
        if 'tos-cn-i-' in url or 'img-s.dyimg.cn' in url:
            if url.startswith('//'):
                url = 'https:' + url
            if url not in image_urls:
                image_urls.append(url)
    return image_urls


def get_video_id_from_iesdouyin(aweme_id: str) -> str:
    """通过 iesdouyin 备用 API 解析真实的无水印视频 vid"""
    api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={aweme_id}"
    try:
        data = http_json(
            api_url,
            timeout=5,
            verify=False,  # first-party host; per-request opt-out only
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        )
        item_list = data.get("item_list", [])
        if item_list:
            return item_list[0].get("video", {}).get("play_addr", {}).get("uri", "")
    except Exception:
        pass
    return ""


def download_video(aweme_id: str, filepath: str) -> tuple:
    """下载无水印视频 (优先使用直接 API，支持多重 CDN 备用地址)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 构造抖音官方源生无水印播放 API 链接
    api_urls = [
        f"https://aweme.snssdk.com/aweme/v1/play/?video_id={aweme_id}&ratio=1080p&line=0",
        f"https://aweme.snssdk.com/aweme/v1/playwm/?video_id={aweme_id}"  # 降级方案
    ]

    # 如果能获取到真实的 vid，加入首选队列
    vid = get_video_id_from_iesdouyin(aweme_id)
    if vid:
        api_urls.insert(0, f"https://aweme.snssdk.com/aweme/v1/play/?video_id={vid}&ratio=1080p&line=0")

    last_err = None
    for url in api_urls:
        try:
            # First-party host; opt out of verification for this request only.
            # urllib follows the API's 302 redirect to the real CDN file internally.
            cdn_data = http_get_bytes(url, timeout=60, verify=False, headers=headers)
            with open(filepath, "wb") as f:
                f.write(cdn_data)
            return len(cdn_data), "1080p" if "playwm" not in url else "720p (watermark)"
        except Exception as e:
            last_err = e
            continue

    raise last_err or Exception("All video download CDN sources failed.")


def get_next_filename(output_dir, extension):
    return next_media_filename(output_dir, extension)


def process_single(url, browser, output_base, index, total):
    """处理并下载单个抖音链接"""
    print(f"\n[{index}/{total}] {t('parsing')}")

    page = None
    try:
        # 使用移动端 (iPhone) 模拟，以绕过 PC 端的滑块验证码
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
            viewport={"width": 430, "height": 740},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True
        )
        page = context.new_page()

        # 引入反爬伪装，擦除 WebDriver 指纹
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(page)
        except ImportError:
            pass

        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)  # 等待完整渲染与状态注水

        # 尝试提取页面中的注水数据 (兼容 PC 端的 RENDER_DATA 与移动端的 _ROUTER_DATA)
        render_data = None
        scripts = page.query_selector_all('script')
        for script in scripts:
            text = script.inner_text()
            if not text:
                continue
            if 'RENDER_DATA' in text:
                match = re.search(r'RENDER_DATA\s*=\s*(.*?)\s*;?\s*$', text, re.MULTILINE)
                if match:
                    try:
                        json_str = match.group(1).strip()
                        if json_str.endswith(';'):
                            json_str = json_str[:-1]
                        if '%' in json_str:
                            json_str = urllib.parse.unquote(json_str)
                        render_data = json.loads(json_str)
                        break
                    except Exception:
                        pass
            elif '_ROUTER_DATA' in text:
                match = re.search(r'_ROUTER_DATA\s*=\s*(.*?)\s*;?\s*$', text, re.MULTILINE)
                if match:
                    try:
                        json_str = match.group(1).strip()
                        if json_str.endswith(';'):
                            json_str = json_str[:-1]
                        if '%' in json_str:
                            json_str = urllib.parse.unquote(json_str)
                        render_data = json.loads(json_str)
                        break
                    except Exception:
                        pass

        if not render_data:
            # 备用方案：尝试直接从 HTML 正则搜索
            html = page.content()
            match = re.search(r'id="RENDER_DATA"[^>]*>(.*?)</script>', html)
            if match:
                try:
                    json_str = urllib.parse.unquote(match.group(1))
                    render_data = json.loads(json_str)
                except Exception:
                    pass
            else:
                match_router = re.search(r'_ROUTER_DATA\s*=\s*(.*?)\s*;?\s*$', html, re.MULTILINE)
                if match_router:
                    try:
                        json_str = match_router.group(1).strip()
                        if json_str.endswith(';'):
                            json_str = json_str[:-1]
                        if '%' in json_str:
                            json_str = urllib.parse.unquote(json_str)
                        render_data = json.loads(json_str)
                    except Exception:
                        pass

        # 若定位不到数据，尝试抛出异常走 DOM 兜底
        if not render_data:
            raise Exception("Neither RENDER_DATA nor _ROUTER_DATA JSON script tag found.")

        # 寻找作品数据节点
        aweme_detail = None
        # RENDER_DATA 结构经常发生微调，使用通用递归搜索找 aweme/awemeDetail/item_list
        def find_aweme_detail(obj):
            if not isinstance(obj, dict):
                return None
            if 'aweme' in obj and isinstance(obj['aweme'], dict):
                return obj['aweme']
            if 'awemeDetail' in obj and isinstance(obj['awemeDetail'], dict):
                return obj['awemeDetail']
            if 'detail' in obj and isinstance(obj['detail'], dict) and 'awemeId' in obj['detail']:
                return obj['detail']
            if 'item_list' in obj and isinstance(obj['item_list'], list) and len(obj['item_list']) > 0:
                return obj['item_list'][0]
            for v in obj.values():
                res = find_aweme_detail(v)
                if res:
                    return res
            return None

        aweme_detail = find_aweme_detail(render_data)

        if not aweme_detail:
            raise Exception("Aweme detail node not found in JSON data.")

        desc = aweme_detail.get('desc', 'douyin_media').strip()
        # 清洗文件名安全字符，去掉换行，并限制长度防止过长
        desc_clean = re.sub(r'[\\/*?:"<>|]', "", desc).replace("\n", " ").replace("\r", " ").strip()[:20] or "douyin_media"
        aweme_id = aweme_detail.get('awemeId') or aweme_detail.get('aweme_id')
        if not aweme_id:
            # 尝试从当前重定向后的 URL 提取 ID
            aweme_id = extract_aweme_id(page.url)

        if not aweme_id:
            raise Exception("Failed to parse aweme_id.")

        # 获取作者信息用于归档（不再创建子文件夹，仅做保留）
        author_info = aweme_detail.get('author', {})
        author_name = author_info.get('nickname') or author_info.get('sec_uid') or "Unknown_Author"
        author_clean = re.sub(r'[\\/*?:"<>|]', "", str(author_name)).strip()[:30]

        # 1. 优先提取图文相册
        images = aweme_detail.get('images')
        if images and isinstance(images, list):
            title_log = t("image_found", title=desc_clean, id=aweme_id, count=len(images))
            print(title_log)

            # 不再创建子目录，直接在 output_base
            import os
            os.makedirs(output_base, exist_ok=True)

            for i, img_obj in enumerate(images, 1):
                url_list = img_obj.get('urlList') or img_obj.get('url_list')
                if not url_list:
                    continue
                img_filename = get_next_filename(output_base, "jpg")
                img_path = os.path.join(output_base, img_filename)

                # 预占位防止循环内重名
                with open(img_path, "wb") as f:
                    pass

                # 遍历备用链接，防止某个 CDN 节点 403
                success_img = False
                for img_url in url_list:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url

                    try:
                        # 尝试通过 Playwright 获取
                        pw_resp = page.request.get(img_url, headers={"Referer": "https://www.douyin.com/"})
                        if pw_resp.status != 200:
                            pw_resp = page.request.get(img_url)

                        if pw_resp.status == 200:
                            img_data = pw_resp.body()
                        else:
                            # 降级使用 urllib（仅首方 CDN，按请求关闭校验）
                            img_data = http_get_bytes(img_url, verify=False)

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        # 尝试利用 Pillow 获取图片尺寸
                        resolution = "N/A"
                        try:
                            from PIL import Image as PILImage
                            with PILImage.open(img_path) as p_img:
                                resolution = f"{p_img.width}x{p_img.height}"
                        except Exception:
                            pass
                        print(t("download_success", filename=img_filename, size=format_size(len(img_data)), resolution=resolution))
                        success_img = True
                        break  # 只要有一个链接下载成功就跳出循环
                    except Exception:
                        continue  # 失败则尝试下一个备用链接

                if not success_img:
                    print(t("download_failed", err="All fallback URLs returned 403 or failed."))

        # 2. 若不是图文，则提取视频
        else:
            title_log = t("video_found", title=desc_clean, id=aweme_id)
            print(title_log)

            import os
            os.makedirs(output_base, exist_ok=True)
            filename = get_next_filename(output_base, "mp4")
            filepath = os.path.join(output_base, filename)

            # 预占位
            with open(filepath, "wb") as f:
                pass

            # 尝试通过真实的无水印 API 体系下载视频
            try:
                video_node = aweme_detail.get('video') or {}
                vid = video_node.get('playAddr', [{}])[0].get('uri') or video_node.get('play_addr', {}).get('uri')
                if not vid:
                    vid = aweme_id
                size, res = download_video(vid, filepath)
                print(t("download_success", filename=filename, size=format_size(size), resolution=res))
            except Exception as e:
                print(f"[warn] 无水印 API 下载失败，准备降级。原因: {e}")
                # 备用方案：尝试直接提取当前页面的 video src (常含水印，作为兜底)
                video_element = page.query_selector('video')
                if video_element:
                    video_src = video_element.get_attribute('src')
                    if video_src:
                        if video_src.startswith('//'):
                            video_src = 'https:' + video_src
                        try:
                            video_data = http_get_bytes(video_src, verify=False,
                                                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
                            with open(filepath, "wb") as f:
                                f.write(video_data)
                            print(t("download_success", filename=filename, size=format_size(len(video_data)), resolution="N/A (Backup CDN)"))
                        except Exception as fwd_e:
                            raise Exception(f"Video detail download failed and no backup DOM video tag found. Err: {fwd_e}")
                    else:
                        raise Exception("Fallback video element found but has no src attribute.")
                else:
                    raise Exception(f"Video detail download failed and no backup DOM video tag found. Err: {e}")

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
    """批量下载抖音链接"""
    # Remote download-policy gate: block before any network/parse work.
    decision = check_download_allowed(silent=False)
    if decision.is_block:
        return False

    urls = extract_urls_from_text(raw_input)
    if not urls:
        # 尝试将输入直接视为单个作品 ID
        clean_input = raw_input.strip()
        if clean_input.isdigit() and len(clean_input) >= 15:
            urls = [clean_input]
        else:
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
        output_dir = "douyin_downloads"
    import os
    os.makedirs(output_dir, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ensure_browser_installed(p, t=t)
        browser = p.chromium.launch(headless=True)
        success = 0
        fail = 0
        for i, url in enumerate(urls, 1):
            # 补全如果是纯数字 ID 类型的 URL 格式
            if url.isdigit():
                url = f"https://www.douyin.com/video/{url}"
            if process_single(url, browser, output_dir, i, total):
                success += 1
            else:
                fail += 1
        browser.close()

    print(t("download_done", success=success, fail=fail))
    print(t("save_dir_info", path=os.path.abspath(output_dir)))
    return True


def download_douyin_links(links, output_dir):
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
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "douyin_downloads"
        download_urls(raw_input, output_dir)
    else:
        # Interactive mode
        from media_downloader.core.disclaimer import check_disclaimer_agreement
        check_disclaimer_agreement(locale=get_locale())

        print(t("title_banner"))
        check_for_updates(silent=False)
        check_version_policy(silent=False)  # nag or hard-block old builds

        try:
            while True:
                raw_input = input(t("input_prompt")).strip()
                if not raw_input or raw_input.lower() in ['q', 'exit']:
                    print(t("exited_safely"))
                    break

                output_dir = input(t("save_dir_prompt", default_dir="douyin_downloads")).strip()
                if not output_dir:
                    output_dir = "douyin_downloads"

                print(t("parsing"))
                download_urls(raw_input, output_dir)
        except (KeyboardInterrupt, EOFError):
            print("\n" + t("exited_safely"))


if __name__ == "__main__":
    main()
