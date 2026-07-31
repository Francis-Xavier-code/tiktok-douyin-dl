#!/usr/bin/env python3
"""调试：监听导航过程中的所有请求和响应"""
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

    slides_requests = []
    
    # 监听请求
    def on_request(request):
        url_r = request.url
        if '/slides/' in url_r or '/note/' in url_r or 'is_slides' in url_r:
            slides_requests.append(f"REQUEST: {url_r[:100]}")
            print(f"[Request] {url_r[:120]}")
    
    # 监听响应
    def on_response(response):
        url_r = response.url
        if '/slides/' in url_r or '/note/' in url_r or 'is_slides' in url_r:
            slides_requests.append(f"RESPONSE: {url_r[:100]}")
            print(f"[Response] {response.status} {url_r[:120]}")
            try:
                body = response.text()
                if 'RENDER_DATA' in body:
                    print(f"  -> 包含 RENDER_DATA!")
                if 'images' in body:
                    print(f"  -> 包含 images!")
            except:
                pass
    
    page.on('request', on_request)
    page.on('response', on_response)
    
    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    
    print(f"\n最终 URL: {page.url}")
    print(f"捕获到 Slides 相关请求: {len(slides_requests)} 个")
    
    # 尝试从 response headers 找 Location 重定向
    for req in slides_requests:
        print(f"  {req}")
    
    browser.close()
