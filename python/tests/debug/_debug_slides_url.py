#!/usr/bin/env python3
"""检查 Slides API 返回的完整 URL 是否带水印"""
import sys, os, json

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

    captured_api = [None]

    def on_response(response):
        if 'slidesinfo' in response.url and response.status == 200:
            try:
                body = response.text()
                if len(body) > 1000:
                    captured_api[0] = body
                    print(f"\n[捕获到 slidesinfo API!] 长度={len(body)}")
                    data = json.loads(body)
                    aweme_details = data.get('aweme_details') or data.get('item_list') or []

                    if aweme_details:
                        item = aweme_details[0]
                        images = item.get('images', [])

                        for idx, img in enumerate(images):
                            url_list = img.get('url_list', [])
                            download_url_list = img.get('download_url_list', [])

                            print(f"\n=== 第 {idx+1} 张图片 ===")
                            print(f"\nurl_list (共{len(url_list)}个):")
                            for j, u in enumerate(url_list):
                                has_water = 'water' in u.lower() or 'tplv-dy-w' in u or 'tplv-dy-a' in u
                                print(f"  [{j}] {'[有水印]' if has_water else '[无水印]'} {u}")

                            print(f"\ndownload_url_list (共{len(download_url_list)}个):")
                            for j, u in enumerate(download_url_list):
                                has_water = 'water' in u.lower() or 'tplv-dy-w' in u or 'tplv-dy-a' in u
                                print(f"  [{j}] {'[有水印]' if has_water else '[无水印]'} {u}")
            except Exception as e:
                import traceback
                print(f"  解析错误: {e}")
                traceback.print_exc()

    page.on('response', on_response)
    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(8000)

    if captured_api[0]:
        print(f"\n\n检查完成!")
    else:
        print("\n未捕获到 slidesinfo API 响应")

    browser.close()