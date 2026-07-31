#!/usr/bin/env python3
"""拦截所有 API 请求，找到 Slides 数据源"""
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

    api_requests = []

    def on_request(request):
        url_r = request.url
        # 只关注 API 请求
        if 'douyin.com' in url_r and ('api' in url_r.lower() or 'aweme' in url_r or 'iteminfo' in url_r):
            api_requests.append(url_r)

    def on_response(response):
        url_r = response.url
        if 'douyin.com' in url_r and ('api' in url_r.lower() or 'aweme' in url_r):
            try:
                body = response.text()
                if len(body) > 100 and ('images' in body or 'urlList' in body or 'image_list' in body):
                    print(f"[命中] {response.status} {url_r[:100]}")
                    print(f"  包含 images/urlList: 长度={len(body)}")
                    print(f"  内容前 300: {body[:300]}")
            except:
                pass

    page.on('request', on_request)
    page.on('response', on_response)

    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)  # 等待 5 秒让 SPA 完全加载

    print(f"\n所有 API 请求 ({len(api_requests)} 个):")
    for r in api_requests:
        print(f"  {r[:120]}")

    # 尝试从 JS 注入获取图片数据
    print("\n通过 JS 注入获取图片:")
    imgs = page.evaluate("""
        () => {
            const imgs = document.querySelectorAll('img');
            return Array.from(imgs).map(img => ({
                src: img.src || img.getAttribute('data-src') || '',
                w: img.naturalWidth || img.width,
                h: img.naturalHeight || img.height
            })).filter(x => x.w > 200 && x.h > 200);
        }
    """)
    print(f"  找到 {len(imgs)} 张图片")
    for img in imgs[:5]:
        print(f"  {img['w']}x{img['h']}: {img['src'][:120]}")

    browser.close()
