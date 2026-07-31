#!/usr/bin/env python3
"""调试脚本：通过 JS 注入获取 Slides 图片列表"""
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
import json, time

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
        cdp = context.new_cdp_session(page)
        cdp.send("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        })
    except Exception:
        pass

    page.goto(url, wait_until="domcontentloaded", timeout=30000)

    # 等待 SPA 渲染
    print("等待页面渲染...")
    time.sleep(8)  # 等待 8 秒让 React 完全加载

    # 方法 1：注入 JS 获取页面所有 img 的 src（懒加载后的）
    result = page.evaluate("""
        () => {
            const imgs = document.querySelectorAll('img');
            const pics = [];
            for (const img of imgs) {
                const src = img.src || img.getAttribute('data-src') || '';
                if (src && !src.startsWith('data:') && !src.includes('avatar') && !src.includes('icon_play')) {
                    pics.push({src: src, alt: img.alt || '', w: img.naturalWidth || img.width, h: img.naturalHeight || img.height});
                }
            }
            return pics;
        }
    """)
    print(f"\nJS 注入提取 img: {len(result)} 个")
    for i, r in enumerate(result):
        print(f"  [{i}] {r['w']}x{r['h']}: {r['src'][:150]}")

    # 方法 2：查找页面状态（Redux/React 状态）
    state_result = page.evaluate("""
        () => {
            // 尝试从 __NEXT_DATA__ 或 __PRELOADED_STATE__ 获取
            const scripts = document.querySelectorAll('script');
            const data = {};
            for (const s of scripts) {
                const t = s.innerText || s.textContent || '';
                if (t.includes('urlList') && t.includes('douyinpic')) {
                    // 找到了包含 urlList 的 script
                    // 尝试解析
                    try {
                        // 找 JSON 对象
                        const match = t.match(/\\{[^{}]*urlList[^{}]*\\}/);
                        if (match) {
                            return {found: 'inline', sample: match[0].substring(0, 300)};
                        }
                    } catch(e) {}
                }
            }

            // 尝试从 window 对象找
            for (const key of Object.keys(window)) {
                if (key.startsWith('__') && !key.includes('webpack')) {
                    try {
                        const val = window[key];
                        if (val && typeof val === 'object') {
                            const str = JSON.stringify(val);
                            if (str.includes('douyinpic') || str.includes('urlList')) {
                                return {found: key, sample: str.substring(0, 500)};
                            }
                        }
                    } catch(e) {}
                }
            }

            // 最后：直接搜索 HTML 中的 douyinpic
            const html = document.documentElement.outerHTML;
            const matches = html.match(/https?:\\/\\/[^\s"']+douyinpic[^\s"']+/g);
            return {found: 'html_search', count: matches ? matches.length : 0, samples: matches ? matches.slice(0,5) : []};
        }
    """)
    print(f"\n页面状态搜索: {json.dumps(state_result, ensure_ascii=False)[:500]}")

    # 方法 3：拦截网络请求找 API 响应
    print(f"\n尝试拦截 XHR/Fetch 请求...")

    api_data = []
    def handle_response(response):
        url = response.url
        if 'douyinpic' in url or 'aweme' in url or 'resource' in url:
            try:
                body = response.text()
                if body and len(body) > 1000 and 'urlList' in body:
                    api_data.append({'url': url[:100], 'size': len(body)})
                    print(f"  捕获到: {url[:100]}")
            except Exception:
                pass

    page.on('response', handle_response)

    # 刷新等待
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(3)
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(3)

    print(f"\n共捕获 {len(api_data)} 个相关请求")
    browser.close()
