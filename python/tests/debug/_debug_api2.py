#!/usr/bin/env python3
"""调试：查看 API 响应内容"""
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

    # 调用 API
    print(f"[2] 调用 API...")
    result = page.evaluate("""
        async (awemeId) => {
            const url = `https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=${awemeId}`;
            console.log('API URL:', url);
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
                console.log('Status:', response.status);
                const text = await response.text();
                console.log('Response length:', text.length);
                console.log('Response first 300:', text.substring(0, 300));
                try {
                    return {type: 'json', data: JSON.parse(text)};
                } catch(e) {
                    return {type: 'text', status: response.status, data: text.substring(0, 500)};
                }
            } catch(e) {
                console.log('Error:', e.toString());
                return {type: 'error', error: e.toString()};
            }
        }
    """, aweme_id)

    print(f"[3] 评估结果:")
    print(f"    类型: {result.get('type')}")
    if result.get('type') == 'json':
        data = result.get('data')
        print(f"    item_list 长度: {len(data.get('item_list', [])) if data else 'N/A'}")
        if data and 'item_list' in data and data['item_list']:
            item = data['item_list'][0]
            print(f"    描述: {item.get('desc', '')[:50]}")
            print(f"    图片数量: {len(item.get('images', []))}")
    elif result.get('type') == 'text':
        print(f"    状态码: {result.get('status')}")
        print(f"    响应: {result.get('data')}")
    else:
        print(f"    错误: {result.get('error')}")

    browser.close()
