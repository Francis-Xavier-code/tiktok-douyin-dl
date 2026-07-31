#!/usr/bin/env python3
"""从页面提取正确的 slidesinfo API 参数"""
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

    # 拦截 slidesinfo 请求，从请求中提取参数
    captured_params = {}

    def on_request(request):
        if 'slidesinfo' in request.url:
            # 提取 URL 参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(request.url)
            params = parse_qs(parsed.query)
            captured_params['url'] = request.url
            captured_params['params'] = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
            captured_params['headers'] = dict(request.headers)

    page.on('request', on_request)

    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    if captured_params.get('url'):
        print(f"\n捕获的 JS 请求:")
        print(f"  URL: {captured_params['url'][:200]}...")
        print(f"\n  参数:")
        for k, v in captured_params['params'].items():
            print(f"    {k}: {v[:100] if isinstance(v, str) else v}")
        print(f"\n  关键 headers:")
        h = captured_params['headers']
        for key in ['referer', 'user-agent', 'accept', 'sec-ch-ua-mobile']:
            if key in h:
                print(f"    {key}: {h[key][:100]}")

        # 提取 aweme_ids 参数
        aweme_ids = captured_params['params'].get('aweme_ids', '')
        if isinstance(aweme_ids, list):
            import re
            match = re.search(r'%5B(\d+)%5D', aweme_ids[0] if isinstance(aweme_ids, list) else aweme_ids)
            if match:
                aweme_id = match.group(1)
            else:
                aweme_id = aweme_ids[0] if isinstance(aweme_ids, list) else aweme_ids
        else:
            import re
            match = re.search(r'%5B(\d+)%5D', aweme_ids)
            if match:
                aweme_id = match.group(1)
            else:
                aweme_id = aweme_ids

        print(f"\n  aweme_id: {aweme_id}")
    else:
        print("未捕获到 slidesinfo 请求")

    browser.close()