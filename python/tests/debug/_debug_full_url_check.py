#!/usr/bin/env python3
"""完整检查 url_list 所有 URL 的水印特征"""
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

    captured = {}

    def on_response(response):
        if 'slidesinfo' in response.url and response.status == 200:
            try:
                body = response.text()
                if len(body) > 1000:
                    captured['body'] = body
            except:
                pass

    context.on('response', on_response)

    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(8000)

    if captured.get('body'):
        data = json.loads(captured['body'])
        aweme_details = data.get('aweme_details') or []
        if aweme_details:
            images = aweme_details[0].get('images', [])
            print(f"图片数量: {len(images)}")

            for idx, img in enumerate(images):
                print(f"\n=== 第 {idx+1} 张 ===")
                url_list = img.get('url_list', [])
                download_list = img.get('download_url_list', [])

                for j, u in enumerate(url_list):
                    water = 'water' in u.lower() or 'tplv-dy-w' in u
                    print(f"  url_list[{j}]: {'[水印]' if water else '[无水印]'} {u[:120]}")

                for j, u in enumerate(download_list):
                    water = 'water' in u.lower() or 'tplv-dy-w' in u
                    print(f"  download[{j}]: {'[水印]' if water else '[无水印]'} {u[:120]}")

                # 检查 uri 字段
                uri = img.get('uri', '')
                print(f"  uri: {uri}")

                # 检查是否还有其他 URL 相关字段
                for key in img.keys():
                    if 'url' in key.lower() or 'src' in key.lower() or 'img' in key.lower():
                        val = img[key]
                        if isinstance(val, list) and len(val) > 0:
                            print(f"  {key}: list[{len(val)}]")
                        elif isinstance(val, str) and len(val) > 20:
                            print(f"  {key}: {val[:80]}")
    else:
        print("未捕获到 slidesinfo 响应")

    browser.close()