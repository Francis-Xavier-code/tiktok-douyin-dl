#!/usr/bin/env python3
"""检查 Slides 分享页 RENDER_DATA 是否存在"""
import sys, os, json, re

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
    print(f"DOMContentLoaded 后的 URL: {page.url}")

    # 立即提取 RENDER_DATA
    render_data = None
    scripts = page.query_selector_all('script')
    print(f"\n找到 {len(scripts)} 个 script 标签")

    for i, script in enumerate(scripts):
        text = script.inner_text()
        if not text:
            continue
        if 'RENDER_DATA' in text:
            print(f"\n  script[{i}] 包含 RENDER_DATA，长度={len(text)}")
            match = re.search(r'RENDER_DATA\s*=\s*(.*?)\s*;?\s*$', text, re.MULTILINE)
            if match:
                try:
                    json_str = match.group(1).strip()
                    if json_str.endswith(';'):
                        json_str = json_str[:-1]
                    if '%' in json_str:
                        json_str = urllib.parse.unquote(json_str)
                    render_data = json.loads(json_str)
                    print(f"  RENDER_DATA 解析成功!")
                    # 查找 aweme_detail
                    def find_aweme_detail(obj, depth=0):
                        if depth > 10:
                            return None
                        if not isinstance(obj, dict):
                            return None
                        if 'aweme' in obj and isinstance(obj['aweme'], dict):
                            return obj['aweme']
                        if 'awemeDetail' in obj and isinstance(obj['awemeDetail'], dict):
                            return obj['awemeDetail']
                        if 'detail' in obj and isinstance(obj['detail'], dict) and 'awemeId' in obj['detail']:
                            return obj['detail']
                        if 'item_list' in obj and isinstance(obj['item_list'], list) and len(obj['item_list']) > 0:
                            return obj['item_list'][0]
                        for v in obj.values():
                            res = find_aweme_detail(v, depth+1)
                            if res:
                                return res
                        return None

                    aweme_detail = find_aweme_detail(render_data)
                    if aweme_detail:
                        print(f"  找到 aweme_detail!")
                        images = aweme_detail.get('images', [])
                        print(f"  images 数量: {len(images)}")
                        if images:
                            for idx, img in enumerate(images[:3]):
                                url_list = img.get('urlList') or img.get('url_list') or []
                                print(f"    第{idx+1}张: url_list有{len(url_list)}个URL")
                                if url_list:
                                    print(f"      第一个URL: {url_list[0][:100]}")
                                    has_water = 'water' in url_list[0].lower() or 'tplv-dy-w' in url_list[0]
                                    print(f"      水印: {'有' if has_water else '无'}")
                    else:
                        print(f"  aweme_detail 未找到，打印顶层 keys: {list(render_data.keys())[:10]}")
                except Exception as e:
                    print(f"  解析失败: {e}")
        elif '_ROUTER_DATA' in text:
            print(f"\n  script[{i}] 包含 _ROUTER_DATA，长度={len(text)}")

    if not render_data:
        print("\nRENDER_DATA 未找到!")

    # 等待重定向
    print("\n等待 3 秒让 JS 完成重定向...")
    page.wait_for_timeout(3000)
    print(f"重定向后的 URL: {page.url}")

    browser.close()