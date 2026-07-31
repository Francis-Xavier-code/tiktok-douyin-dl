#!/usr/bin/env python3
"""深度解析 Slides API 响应，找到无水印图片 URL - 完整字段扫描"""
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
                        print(f"  desc: {item.get('desc', '')[:80]}")
                        print(f"  aweme_id: {item.get('aweme_id', '')}")

                        images = item.get('images', [])
                        print(f"\n  images 数组长度: {len(images)}")

                        for idx, img in enumerate(images):
                            print(f"\n  === 第 {idx+1} 张图片的完整字段 ===")
                            # 打印所有顶层字段
                            for key, val in img.items():
                                if isinstance(val, list):
                                    print(f"    {key}: list[{len(val)}]")
                                    if len(val) > 0 and len(val) <= 5:
                                        for j, v in enumerate(val):
                                            if isinstance(v, dict):
                                                print(f"      [{j}] dict keys: {list(v.keys())[:10]}")
                                                for k2, v2 in v.items():
                                                    if isinstance(v2, str) and len(v2) < 200:
                                                        print(f"          {k2}: {v2[:100]}")
                                                    elif isinstance(v2, list):
                                                        print(f"          {k2}: list[{len(v2)}]")
                                                    else:
                                                        print(f"          {k2}: {type(v2).__name__}")
                                            else:
                                                print(f"      [{j}] {type(v).__name__}: {str(v)[:100]}")
                                elif isinstance(val, dict):
                                    print(f"    {key}: dict, keys={list(val.keys())[:10]}")
                                    for k2, v2 in val.items():
                                        if isinstance(v2, str):
                                            print(f"      {k2}: {v2[:100]}")
                                        else:
                                            print(f"      {k2}: {type(v2).__name__}")
                                elif isinstance(val, str):
                                    print(f"    {key}: {val[:100]}")
                                else:
                                    print(f"    {key}: {type(val).__name__} = {val}")
            except Exception as e:
                import traceback
                print(f"  解析错误: {e}")
                traceback.print_exc()

    page.on('response', on_response)
    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(8000)

    if captured_api[0]:
        print(f"\n\n解析完成!")
    else:
        print("\n未捕获到 slidesinfo API 响应")

    browser.close()