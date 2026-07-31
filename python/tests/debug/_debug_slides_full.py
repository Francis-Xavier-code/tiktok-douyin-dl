#!/usr/bin/env python3
"""深度解析 Slides API 响应，找到无水印图片 URL"""
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
                    # 深度解析结构
                    aweme_details = data.get('aweme_details') or data.get('item_list') or []
                    print(f"aweme_details: {type(aweme_details)}, 长度: {len(aweme_details) if aweme_details else 0}")

                    if aweme_details:
                        item = aweme_details[0]
                        print(f"  desc: {item.get('desc', '')[:50]}")
                        print(f"  aweme_id: {item.get('aweme_id', '')}")

                        # 找图片
                        images = item.get('images', [])
                        image_list = item.get('image_list', [])
                        video = item.get('video', {})
                        print(f"  images: {len(images) if images else 0} 个")
                        print(f"  image_list: {len(image_list) if image_list else 0} 个")

                        if images:
                            print(f"\n  第一张图片的 urlList:")
                            for j, img in enumerate(images[:3]):
                                url_list = img.get('urlList', [])
                                print(f"    [{j}] urlList 有 {len(url_list)} 个URL:")
                                for k, u in enumerate(url_list[:3]):
                                    print(f"      [{k}] {u[:100]}")
                    else:
                        print(f"  aweme_details 为空，完整响应:")
                        print(f"  {body[:500]}")
            except Exception as e:
                print(f"  解析错误: {e}")

    page.on('response', on_response)
    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(8000)

    if captured_api[0]:
        print(f"\n\n解析完成!")
    else:
        print("\n未捕获到 slidesinfo API 响应")

    browser.close()
