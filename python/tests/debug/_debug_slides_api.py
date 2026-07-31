#!/usr/bin/env python3
"""调试 Slides 页面的数据提取"""
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

# 使用刚才成功的视频链接测试 Slides 格式
# 先找一个新的有效 Slides 链接

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

    # 尝试不同的 API 端点
    aweme_id = "7634863186633781861"

    print("=== 测试不同的 API 端点 ===\n")

    # 方法 1: 标准 API
    result1 = page.evaluate("""
        async (id) => {
            try {
                const resp = await fetch(
                    `https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=${id}`,
                    { credentials: 'include', headers: { 'Referer': 'https://www.iesdouyin.com/' } }
                );
                return { status: resp.status, ok: resp.ok, text: await resp.text().then(t => t.substring(0, 200)) };
            } catch(e) { return { error: e.message }; }
        }
    """, aweme_id)
    print(f"[API 1] iesdouyin.com/web/api/v2/aweme/iteminfo:")
    print(f"  {result1}")

    # 方法 2: m.toutiao API
    result2 = page.evaluate("""
        async (id) => {
            try {
                const resp = await fetch(
                    `https://m.toutiao.com/i${id}/info/`,
                    { credentials: 'include', headers: { 'Referer': 'https://m.toutiao.com/' } }
                );
                return { status: resp.status, ok: resp.ok, text: await resp.text().then(t => t.substring(0, 300)) };
            } catch(e) { return { error: e.message }; }
        }
    """, aweme_id)
    print(f"\n[API 2] m.toutiao.com/i{{id}}/info/:")
    print(f"  {result2}")

    # 方法 3: 直接访问 iesdouyin slides 页面，注入 JS 获取 __INITIAL_STATE__
    print(f"\n[API 3] 访问 iesdouyin.com/share/slides/{aweme_id} ...")
    page2 = context.new_page()
    try:
        page2.goto(f"https://www.iesdouyin.com/share/slides/{aweme_id}", wait_until="domcontentloaded", timeout=15000)
        page2.wait_for_timeout(3000)
        print(f"  URL: {page2.url}")
        print(f"  标题: {page2.title()}")

        # 查找 window.__INITIAL_STATE__ 或类似数据
        state_result = page2.evaluate("""
            () => {
                // 尝试多种可能的全局变量
                const candidates = [
                    window.__INITIAL_STATE__,
                    window.__SSR_RENDER_DATA__,
                    window.__PRELOADED_STATE__,
                    window.__NEXT_DATA__,
                    window.__ROUTE_DATA__
                ];
                for (const [name, val] of Object.entries({
                    __INITIAL_STATE__: window.__INITIAL_STATE__,
                    __SSR__: window.__SSR_RENDER_DATA__
                })) {
                    if (val) {
                        const str = JSON.stringify(val);
                        if (str.includes('images') || str.includes('urlList')) {
                            return { name, sample: str.substring(0, 500) };
                        }
                    }
                }

                // 从 script 标签找
                const scripts = document.querySelectorAll('script');
                for (const s of scripts) {
                    const t = s.textContent || '';
                    if (t.includes('images') && t.includes('urlList')) {
                        return { found: 'script', sample: t.substring(0, 500) };
                    }
                }

                // 找 RENDER_DATA
                const rd = document.getElementById('RENDER_DATA');
                if (rd) {
                    return { found: 'RENDER_DATA', sample: rd.textContent.substring(0, 300) };
                }

                return { found: 'nothing' };
            }
        """)
        print(f"  状态数据: {json.dumps(state_result, ensure_ascii=False)[:500]}")
    except Exception as e:
        print(f"  错误: {e}")

    browser.close()
