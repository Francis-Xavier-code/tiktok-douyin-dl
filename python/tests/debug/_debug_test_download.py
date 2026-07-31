#!/usr/bin/env python3
"""测试下载 url_list[0] 的图片，检查是否带水印"""
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
import urllib.request

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
        import json
        data = json.loads(captured['body'])
        aweme_details = data.get('aweme_details') or []
        if aweme_details:
            images = aweme_details[0].get('images', [])
            print(f"图片数量: {len(images)}")

            if images:
                # 尝试 url_list[0]
                url_list = images[0].get('url_list', [])
                download_url_list = images[0].get('download_url_list', [])

                if url_list:
                    img_url = url_list[0]
                    print(f"\n尝试下载 url_list[0]:")
                    print(f"  URL: {img_url[:150]}")
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
                            "Referer": "https://www.iesdouyin.com/"
                        }
                        req = urllib.request.Request(img_url, headers=headers)
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            img_data = resp.read()
                            out_path = os.path.expanduser("~/url_list_0.jpg")
                            with open(out_path, 'wb') as f:
                                f.write(img_data)
                            print(f"  下载成功! 大小: {len(img_data)} bytes -> {out_path}")
                    except Exception as e:
                        print(f"  下载失败: {e}")

                if download_url_list:
                    img_url = download_url_list[0]
                    print(f"\n尝试下载 download_url_list[0]:")
                    print(f"  URL: {img_url[:150]}")
                    try:
                        headers = {
                            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
                            "Referer": "https://www.iesdouyin.com/"
                        }
                        req = urllib.request.Request(img_url, headers=headers)
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            img_data = resp.read()
                            out_path = os.path.expanduser("~/download_url_list_0.jpg")
                            with open(out_path, 'wb') as f:
                                f.write(img_data)
                            print(f"  下载成功! 大小: {len(img_data)} bytes -> {out_path}")
                    except Exception as e:
                        print(f"  下载失败: {e}")

    else:
        print("未捕获到 slidesinfo 响应")

    browser.close()