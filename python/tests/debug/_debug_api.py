#!/usr/bin/env python3
"""调试：查看 API 响应内容"""
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

aweme_id = "7634863186633781861"

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

    # 先访问分享页获取 cookies
    print(f"[1] 访问分享页...")
    page.goto(f"https://v.douyin.com/{aweme_id}/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    print(f"    URL: {page.url}")

    # 监听所有请求
    api_response = None
    def handle_response(response):
        nonlocal api_response
        if 'aweme/iteminfo' in response.url:
            print(f"[2] 捕获 API 请求: {response.url}")
            print(f"    状态码: {response.status}")
            try:
                body = response.text()
                print(f"    响应长度: {len(body)}")
                print(f"    响应前 500 字符: {body[:500]}")
                api_response = body
            except Exception as e:
                print(f"    读取响应失败: {e}")

    page.on('response', handle_response)

    # 调用 API
    print(f"[3] 调用 API...")
    result = page.evaluate("""
        async (awemeId) => {
            const url = `https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=${awemeId}`;
            try {
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
                        'Referer': 'https://www.iesdouyin.com/',
                        'Accept': 'application/json, text/plain, */*'
                    },
                    credentials: 'include'
                });
                const text = await response.text();
                console.log('API Response:', text.substring(0, 300));
                try {
                    return JSON.parse(text);
                } catch {
                    return {raw: text, status: response.status};
                }
            } catch(e) {
                return {error: e.toString()};
            }
        }
    """, aweme_id)

    print(f"[4] 评估结果:")
    print(f"    {result}")

    browser.close()
