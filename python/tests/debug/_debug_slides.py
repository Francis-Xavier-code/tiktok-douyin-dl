#!/usr/bin/env python3
"""调试脚本：查看抖音 Slides 页面加载后的完整内容"""
import sys
import os

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
import re

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

    # CDP 注入
    try:
        cdp_session = context.new_cdp_session(page)
        cdp_session.send("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
                window.chrome = { runtime: {} };
                delete window.cdc_adoQpoasnfa4pcohlfhok;
                delete window.$cdc_asdjflasutopfhvcZLmcfl_;
            """
        })
        print("[CDP] 注入成功")
    except Exception as e:
        print(f"[CDP] 注入失败: {e}")

    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    print(f"最终 URL: {page.url}")
    print(f"标题: {page.title()}")

    # 搜索所有可能的数据标签
    keywords = ['RENDER_DATA', '_ROUTER_DATA', 'UNIVERSAL_DATA', '__INITIAL_STATE__',
                'window.__', 'aweme_id', 'awemeId', 'item_list', 'itemStruct',
                'aweme_detail', 'awemeDetail', 'slides', 'imageList', 'images']

    scripts = page.query_selector_all('script')
    print(f"\n找到 {len(scripts)} 个 script 标签")

    found_data = False
    for i, script in enumerate(scripts):
        try:
            text = script.inner_text()
            if not text or len(text) < 10:
                continue

            matched_kw = [kw for kw in keywords if kw in text]
            if matched_kw:
                print(f"\nscript[{i}] (长度={len(text)}) 包含: {matched_kw}")
                # 显示前500字符
                print(f"  内容预览: {text[:500]}")
                found_data = True
        except Exception as e:
            print(f"  script[{i}] 读取失败: {e}")

    if not found_data:
        print("\n⚠️ 未找到任何数据标签！")
        print("\n页面 HTML 前 3000 字符:")
        print(page.content()[:3000])
    else:
        # 检查是否有图片元素
        imgs = page.query_selector_all('img')
        print(f"\n页面图片数量: {len(imgs)}")
        for j, img in enumerate(imgs[:5]):
            try:
                src = img.get_attribute('src')
                if src:
                    print(f"  img[{j}]: {src[:100]}")
            except Exception:
                pass

    browser.close()
