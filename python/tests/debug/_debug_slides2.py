#!/usr/bin/env python3
"""调试脚本：直接从 HTML 中提取 Slides 图片"""
import sys
import os

if getattr(sys, 'frozen', False):
    for key in ['LD_LIBRARY_PATH', 'LIBPATH', 'DYLD_LIBRARY_PATH']:
        orig_key = key + '_ORIG'
        if orig_key in os.environ:
            os.environ[key] = os.environ[orig_key]
        else:
            os.environ.pop(key, None)

os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser('~/.cache/ms-playwright')
os.environ['PLAYWRIGHT_DOWNLOAD_HOST'] = 'https://playwright-zh.oss-cn-hangzhou.aliyuncs.com'

import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

from playwright.sync_api import sync_playwright
import re
import urllib.request
import json

url = "https://v.douyin.com/Ya7DxSJ4oR0/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
        viewport={"width": 430, "height": 740},
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True
    )
    page = context.new_page()
    try:
        cdp_session = context.new_cdp_session(page)
        cdp_session.send("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                delete window.cdc_adoQpoasnfa4pcohlfhok;
                delete window.$cdc_asdjflasutopfhvcZLmcfl_;
            """
        })
    except Exception:
        pass

    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)  # 等待更长时间让 SPA 加载

    print(f"URL: {page.url}")
    print(f"标题: {page.title()}")

    # 方法 1：直接从 HTML 中搜索 douyinpic.com 图片链接
    html = page.content()
    pic_pattern = r'https://[^\s<>"]+(?:p[0-9]+-sign\.douyinpic\.com/[^\s<>"]+)'
    pics = re.findall(pic_pattern, html)
    print(f"\n从 HTML 提取到 douyinpic.com 链接: {len(pics)} 个")
    for i, pic in enumerate(pics[:10]):
        print(f"  [{i}] {pic[:120]}")

    # 方法 2：查找 img 标签的 src 和 data-src
    imgs = page.query_selector_all('img')
    real_imgs = []
    for img in imgs:
        src = img.get_attribute('src') or ''
        data_src = img.get_attribute('data-src') or ''
        alt = img.get_attribute('alt') or ''
        if ('douyinpic' in src or 'douyinpic' in data_src) and not src.startswith('data:'):
            real_imgs.append((src or data_src, alt))

    print(f"\n从 img 标签提取到真实图片: {len(real_imgs)} 个")
    for i, (img_url, alt) in enumerate(real_imgs[:10]):
        print(f"  [{i}] alt={alt[:30] if alt else 'N/A'}: {img_url[:120]}")

    # 方法 3：查找 JSON 数据中的图片列表
    json_pattern = r'"urlList"\s*:\s*\[([^\]]+)'
    matches = re.findall(json_pattern, html)
    print(f"\n从 JSON urlList 提取: {len(matches)} 个")
    for m in matches[:3]:
        urls = re.findall(r'"(https?://[^"]+)"', m)
        print(f"  {urls[:3]}")

    # 方法 4：如果有 video 标签，找 video src
    videos = page.query_selector_all('video')
    print(f"\n视频标签数量: {len(videos)}")
    for v in videos:
        src = v.get_attribute('src') or ''
        poster = v.get_attribute('poster') or ''
        if src:
            print(f"  video src: {src[:100]}")
        if poster:
            print(f"  video poster: {poster[:100]}")

    browser.close()
