#!/usr/bin/env python3
"""拦截页面 JS 实际发送的 slidesinfo 请求"""
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

    def on_request(request):
        if 'slidesinfo' in request.url:
            captured['url'] = request.url
            captured['headers'] = dict(request.headers)
            captured['method'] = request.method

    def on_response(response):
        if 'slidesinfo' in response.url and response.status == 200:
            try:
                body = response.text()
                captured['body'] = body
                captured['body_len'] = len(body)
            except:
                pass

    page.on('request', on_request)
    page.on('response', on_response)

    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    if captured.get('url'):
        print(f"\nJS 实际请求:")
        print(f"  URL: {captured['url']}")
        print(f"  Method: {captured['method']}")
        print(f"  Headers:")
        for k, v in captured.get('headers', {}).items():
            if k.lower() not in ['cookie', 'authorization']:
                print(f"    {k}: {v[:80]}")
        print(f"  Body 长度: {captured.get('body_len', 0)}")
        if captured.get('body'):
            data = json.loads(captured['body'])
            ad = data.get('aweme_details') or data.get('item_list') or []
            print(f"  aweme_details 数量: {len(ad)}")
    else:
        print("\n未捕获到 slidesinfo 请求")

    browser.close()