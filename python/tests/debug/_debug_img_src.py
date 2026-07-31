#!/usr/bin/env python3
"""对比 DOM 中 img 标签的 src vs data-src"""
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

    print(f"访问: {url}")
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(5000)

    # 检查 DOM 中的 img 标签
    result = page.evaluate("""
        () => {
            const imgs = document.querySelectorAll('img');
            const results = [];
            for (const img of imgs) {
                const src = img.src || '';
                const dataSrc = img.getAttribute('data-src') || '';
                const dataOriginal = img.getAttribute('data-original') || '';
                const naturalWidth = img.naturalWidth || img.width;
                const naturalHeight = img.naturalHeight || img.height;

                if (naturalWidth > 200 && naturalHeight > 200 &&
                    !src.includes('avatar') && !src.includes('icon') && !src.includes('gif')) {
                    results.push({
                        src: src,
                        dataSrc: dataSrc,
                        dataOriginal: dataOriginal,
                        width: naturalWidth,
                        height: naturalHeight,
                        tag: img.outerHTML.substring(0, 300)
                    });
                }
            }
            return results;
        }
    """)

    print(f"\n找到 {len(result)} 个符合条件的 img 标签:")
    for i, img in enumerate(result[:5]):
        print(f"\n--- 第 {i+1} 张 ---")
        print(f"  src: {img['src'][:150] if img['src'] else '(空)'}")
        print(f"  data-src: {img['dataSrc'][:150] if img['dataSrc'] else '(空)'}")
        print(f"  data-original: {img['dataOriginal'][:150] if img['dataOriginal'] else '(空)'}")
        print(f"  尺寸: {img['width']}x{img['height']}")

    browser.close()