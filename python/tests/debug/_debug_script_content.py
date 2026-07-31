#!/usr/bin/env python3
"""调试：看 domcontentloaded 后 script 标签里有什么"""
import sys, os

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

    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    print(f"domcontentloaded 后立即检查...")
    print(f"  page.url: {page.url}")

    # 检查所有 script 标签内容
    scripts = page.query_selector_all('script')
    print(f"  找到 {len(scripts)} 个 script 标签")
    for i, script in enumerate(scripts):
        try:
            text = script.inner_text()
            if not text:
                continue
            keywords = ['RENDER_DATA', '_ROUTER_DATA', 'images', 'urlList', 'aweme_detail', 'item_list', 'slides']
            matched = [kw for kw in keywords if kw in text]
            if matched:
                print(f"  script[{i}] (长度={len(text)}) 包含: {matched}")
                print(f"    预览: {text[:300]}")
        except Exception as e:
            pass

    # 等待 3 秒后再检查
    page.wait_for_timeout(3000)
    print(f"\n3 秒后...")
    print(f"  page.url: {page.url}")

    # 再次检查
    scripts2 = page.query_selector_all('script')
    for i, script in enumerate(scripts2):
        try:
            text = script.inner_text()
            if not text:
                continue
            if 'RENDER_DATA' in text or '_ROUTER_DATA' in text:
                print(f"  script[{i}] 仍有 RENDER_DATA (长度={len(text)})")
                print(f"    预览: {text[:300]}")
        except:
            pass

    # 检查 HTML 中是否有 RENDER_DATA
    html = page.content()
    if 'RENDER_DATA' in html:
        print(f"\nHTML 中包含 RENDER_DATA")
        idx = html.find('RENDER_DATA')
        print(f"  上下文: {html[max(0,idx-20):idx+200]}")
    else:
        print(f"\nHTML 中没有 RENDER_DATA")

    browser.close()
