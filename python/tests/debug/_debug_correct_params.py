#!/usr/bin/env python3
"""用正确的 aweme_ids 参数测试 slidesinfo API"""
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
import urllib.parse

url = "https://v.douyin.com/Ya7DxSJ4oR0/"
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

    # 先访问让 cookie 设置好
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # 正确的 API URL（从拦截器获取）
    correct_url = (
        f"https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/?"
        f"reflow_source=reflow_page&"
        f"web_id=7650455054021314048&"
        f"device_id=7650455054021314048&"
        f"from_did=MS4wLjABAAAARUSfpE7Y3vfKOfVYUV__Vdc9PDt_HBKSNO7g9mzg4J61xbN0xEjtz9NXYjKkxeCW&"
        f"user_cip=111.183.128.174&"
        f"aweme_ids=%5B{aweme_id}%5D&"
        f"request_source=200"
    )

    # 测试只用 aweme_ids（不用 item_ids）的效果
    test_url = (
        f"https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/?"
        f"reflow_source=reflow_page&"
        f"aweme_ids=%5B{aweme_id}%5D"
    )

    print("测试 1: 完整参数 URL（从拦截器复制）")
    result1 = page.evaluate("""
        async (apiUrl) => {
            try {
                const resp = await fetch(apiUrl, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1',
                        'Referer': 'https://www.iesdouyin.com/share/slides/7634863186633781861/',
                        'Accept': 'application/json, text/plain, */*'
                    },
                    credentials: 'include'
                });
                const data = await resp.json();
                return { status: resp.status, ad_len: (data.aweme_details || []).length };
            } catch(e) {
                return { error: e.toString() };
            }
        }
    """, correct_url)
    print(f"  结果: {result1}")

    print("\n测试 2: 只用 aweme_ids 参数")
    result2 = page.evaluate("""
        async (apiUrl) => {
            try {
                const resp = await fetch(apiUrl, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1',
                        'Referer': 'https://www.iesdouyin.com/share/slides/7634863186633781861/',
                        'Accept': 'application/json, text/plain, */*'
                    },
                    credentials: 'include'
                });
                const data = await resp.json();
                return { status: resp.status, ad_len: (data.aweme_details || []).length };
            } catch(e) {
                return { error: e.toString() };
            }
        }
    """, test_url)
    print(f"  结果: {result2}")

    print("\n测试 3: 只用 item_ids 参数（原来的错误方式）")
    test_url3 = f"https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/?reflow_source=reflow_page&item_ids={aweme_id}"
    result3 = page.evaluate("""
        async (apiUrl) => {
            try {
                const resp = await fetch(apiUrl, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1',
                        'Referer': 'https://www.iesdouyin.com/share/slides/7634863186633781861/',
                        'Accept': 'application/json, text/plain, */*'
                    },
                    credentials: 'include'
                });
                const data = await resp.json();
                return { status: resp.status, ad_len: (data.aweme_details || []).length };
            } catch(e) {
                return { error: e.toString() };
            }
        }
    """, test_url3)
    print(f"  结果: {result3}")

    browser.close()