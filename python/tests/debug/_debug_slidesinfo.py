#!/usr/bin/env python3
"""调试 Slidesinfo API"""
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

    # 先访问 Slides 页面
    print(f"[1] 访问 Slides 页面...")
    page.goto(f"https://v.douyin.com/Ya7DxSJ4oR0/", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)
    print(f"    URL: {page.url}")

    # 尝试调用 slidesinfo API
    print(f"\n[2] 调用 slidesinfo API...")

    # 方法 1: 拦截到的原始格式
    result1 = page.evaluate("""
        async (id) => {
            // 尝试从 intercepted URL 看到的格式
            const url = `https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/?reflow_source=reflow_page&item_ids=${id}`;
            console.log('URL:', url);
            try {
                const resp = await fetch(url, {
                    credentials: 'include',
                    headers: {
                        'Referer': 'https://www.iesdouyin.com/',
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
                    }
                });
                const text = await resp.text();
                console.log('Status:', resp.status, 'Length:', text.length);
                if (text.length > 100) {
                    // 尝试找 images 字段
                    const match = text.match(/"images"\\s*:\\s*\\[/);
                    console.log('Has images:', !!match);
                }
                return text.substring(0, 500);
            } catch(e) {
                return 'ERROR: ' + e.message;
            }
        }
    """, aweme_id)
    print(f"  结果: {result1}")

    # 方法 2: 尝试直接用 urllib 调用
    import urllib.request
    url2 = f"https://www.iesdouyin.com/web/api/v2/aweme/slidesinfo/?reflow_source=reflow_page&item_ids={aweme_id}"
    print(f"\n[3] urllib 直接调用...")
    try:
        req = urllib.request.Request(url2, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.iesdouyin.com/'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode('utf-8')
            print(f"  状态: 成功，长度={len(data)}")
            print(f"  内容: {data[:300]}")
    except Exception as e:
        print(f"  错误: {e}")

    browser.close()
