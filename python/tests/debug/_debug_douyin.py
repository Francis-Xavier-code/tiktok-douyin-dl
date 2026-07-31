#!/usr/bin/env python3
"""调试脚本：查看抖音页面加载后的内容"""
import sys
import os

# 修复 PyInstaller 环境
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

print(f"正在访问: {url}\n")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
        viewport={"width": 430, "height": 740},
        device_scale_factor=3,
        is_mobile=True,
        has_touch=True
    )

    # CDP 注入
    try:
        cdp_session = context.cdp
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
        print("[CDP] 注入完成")
    except Exception as e:
        print(f"[CDP] 注入失败: {e}")

    page = context.new_page()

    # 监听控制台消息
    def handle_console(msg):
        if msg.type in ('error', 'warning'):
            print(f"  [Console {msg.type}]: {msg.text[:200]}")
    page.on('console', handle_console)

    # 监听请求失败
    def handle_request_failed(request):
        print(f"  [请求失败] {request.url[:100]} -> {request.failure.error_text}")
    page.on('requestfailed', handle_request_failed)

    print(f"\n[Step 1] 访问: {url}")
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    print(f"  最终 URL: {page.url}")
    print(f"  状态码: {response.status if response else 'N/A'}")
    print(f"  重定向链: {response.url if response else page.url}")

    print(f"\n[Step 2] 等待 3 秒...")
    page.wait_for_timeout(3000)

    print(f"\n[Step 3] 检查页面标题: {page.title()}")

    # 查找 RENDER_DATA
    scripts = page.query_selector_all('script')
    print(f"\n[Step 4] 找到 {len(scripts)} 个 script 标签")
    has_render_data = False
    has_router_data = False
    for i, script in enumerate(scripts):
        text = script.inner_text()
        if 'RENDER_DATA' in text:
            has_render_data = True
            print(f"  script[{i}]: 包含 RENDER_DATA (长度={len(text)})")
        if '_ROUTER_DATA' in text:
            has_router_data = True
            print(f"  script[{i}]: 包含 _ROUTER_DATA (长度={len(text)})")

    if not has_render_data and not has_router_data:
        print("\n  ⚠️ 未找到 RENDER_DATA 或 _ROUTER_DATA")
        print(f"\n[Step 5] 页面 HTML 前 2000 字符:")
        html = page.content()
        print(html[:2000])

    browser.close()

print("\n" + "=" * 60)
