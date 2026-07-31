#!/usr/bin/env python3
"""检查 page.evaluate() fetch slidesinfo API 的实际返回"""
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

    # 先访问让 cookie 设置好
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    aweme_id = "7634863186633781861"  # 从之前的调试已知这个 ID
    slides_api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/?reflow_source=reflow_page&item_ids={aweme_id}"

    print(f"当前 page.url: {page.url}")
    print(f"API URL: {slides_api_url}")

    # 测试 fetch
    result = page.evaluate("""
        async (apiUrl) => {
            try {
                const response = await fetch(apiUrl, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Referer': 'https://www.iesdouyin.com/',
                        'Accept': 'application/json, text/plain, */*'
                    },
                    credentials: 'include'
                });
                const status = response.status;
                const statusText = response.statusText;
                const headers = {};
                response.headers.forEach((val, key) => { headers[key] = val; });
                let body;
                try {
                    body = await response.json();
                } catch(e) {
                    body = await response.text();
                }
                return { status, statusText, headers, body };
            } catch(e) {
                return { error: e.toString() };
            }
        }
    """, slides_api_url)

    print(f"\nfetch 结果:")
    if 'error' in result:
        print(f"  错误: {result['error']}")
    else:
        print(f"  status: {result['status']} {result['statusText']}")
        print(f"  body 类型: {type(result['body'])}")
        if isinstance(result['body'], dict):
            print(f"  body keys: {list(result['body'].keys())}")
            ad = result['body'].get('aweme_details') or result['body'].get('item_list') or []
            print(f"  aweme_details/item_list 长度: {len(ad)}")
            if ad:
                images = ad[0].get('images', [])
                print(f"  images 数量: {len(images)}")
                if images:
                    url_list = images[0].get('url_list', [])
                    print(f"  第1张图片 url_list 长度: {len(url_list)}")
                    if url_list:
                        print(f"  第1个URL: {url_list[0][:100]}")
        else:
            print(f"  body 前200字符: {str(result['body'])[:200]}")

    browser.close()