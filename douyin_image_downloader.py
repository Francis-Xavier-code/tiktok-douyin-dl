#!/usr/bin/env python3
"""
抖音图文/视频批量下载器
用法:
  python douyin_image_downloader.py <链接/分享文本> [输出目录]
"""

import sys
import os

# 修复 PyInstaller 打包环境中子进程（如 Playwright 启动的浏览器）因为 LD_LIBRARY_PATH 污染而崩溃的问题
if getattr(sys, 'frozen', False):
    for key in ['LD_LIBRARY_PATH', 'LIBPATH', 'DYLD_LIBRARY_PATH']:
        orig_key = key + '_ORIG'
        if orig_key in os.environ:
            os.environ[key] = os.environ[orig_key]
        else:
            os.environ.pop(key, None)

import re
import time
import urllib.request
import ssl
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from i18n import get_locale, translate

# 禁用全局 SSL 证书验证，防止本地 CA 证书缺失导致网络请求失败
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# 尝试导入 Pillow
try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

# 版本控制与 GitHub 自动更新配置
VERSION = "1.6.4"
GITHUB_USER = "Xynrin"
GITHUB_REPO = "tiktok-douyin-dl"

# 强制设置浏览器路径为用户的全局缓存目录，防止打包后寻找 tmp 目录而崩溃（仅在未预设时设置）
if 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser('~/.cache/ms-playwright')

# Compatibility value for callers that inspect the selected locale. User-facing
# strings are resolved by the JSON catalogs through t().
LANG = get_locale()

# User-facing text is maintained in locales/{zh,en}.json.

def t(key, **kwargs):
    platform_key = f"cli.douyin.{key}"
    localized = translate(platform_key, locale=LANG, **kwargs)
    return localized if localized != platform_key else translate(f"cli.common.{key}", locale=LANG, **kwargs)

def parse_version(v_str):
    """解析版本字符串为数字元组，便于进行大小比较"""
    try:
        return tuple(int(x) for x in re.findall(r'\d+', v_str))
    except Exception:
        return (0,)

def check_for_updates(silent=False):
    """检查 GitHub 上的最新版本并提示自动更新"""
    if "YOUR_GITHUB_" in GITHUB_USER or "YOUR_GITHUB_" in GITHUB_REPO:
        return  # 若未配置 GitHub 仓库，则跳过检查

    latest_version = None
    changelog = ""
    download_url = ""
    tag_name = ""

    # 1. 首先尝试通过 GitHub API 获取最新版本
    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
    api_success = False
    try:
        req = urllib.request.Request(
            api_url,
            headers={"User-Agent": "Mozilla/5.0 douyin-dl-updater"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            tag_name = data.get("tag_name", "").strip()
            latest_version = tag_name.lstrip('v')
            changelog = data.get("body", "").strip()
            assets = data.get("assets", [])
            for asset in assets:
                if asset.get("name") == "douyin-dl":
                    download_url = asset.get("browser_download_url")
                    break
            api_success = True
    except Exception:
        api_success = False

    # 2. 如果 API 请求失败，降级到网页重定向检查方法
    if not api_success:
        try:
            web_url = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(
                web_url,
                headers={"User-Agent": "Mozilla/5.0 douyin-dl-updater"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                final_url = resp.geturl()
                if "/releases/tag/" in final_url:
                    tag_name = final_url.split("/releases/tag/")[-1].split("?")[0].split("#")[0].strip("/")
                    latest_version = tag_name.lstrip('v')
                    download_url = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/{tag_name}/douyin-dl"
                    changelog = t("update_changelog_unavailable")
        except Exception as e:
            if not silent:
                print(t("update_failed", err=e))
            return

    # 3. 统一进行版本对比与更新提示
    if latest_version and parse_version(latest_version) > parse_version(VERSION):
        print(t("update_found", latest_version=latest_version, version=VERSION))
        
        if changelog:
            print(t("changelog_title"))
            print("─" * 50)
            print(changelog)
            print("─" * 50)
        
        if download_url:
            if getattr(sys, 'frozen', False):
                if not silent:
                    confirm = input(t("update_confirm")).strip().lower()
                    if confirm in ['y', 'yes']:
                        perform_self_update(download_url)
                else:
                    print(t("update_hint", cmd="douyin-dl"))
            else:
                if not silent:
                    print(t("source_mode_update_skipped"))

def perform_self_update(download_url):
    """下载最新版本的可执行文件并原地替换自身"""
    temp_exe = ""
    try:
        current_exe = os.path.abspath(sys.argv[0])
        temp_exe = current_exe + ".tmp"
        
        print(t("update_downloading"))
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "Mozilla/5.0 douyin-dl-updater"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            with open(temp_exe, "wb") as f:
                f.write(data)
        
        os.chmod(temp_exe, 0o755)
        os.replace(temp_exe, current_exe)
        print(t("update_success"))
        sys.exit(0)
    except Exception as e:
        print(t("update_failed_install", error=e))
        if temp_exe and os.path.exists(temp_exe):
            try:
                os.remove(temp_exe)
            except Exception:
                pass

def extract_urls_from_text(text: str) -> list:
    """提取文本中的所有抖音链接"""
    url_pattern = re.compile(r'https?://[a-zA-Z0-9][-a-zA-Z0-9\\._]*\bdouyin\.com\b[-a-zA-Z0-9@:%_\+.~#?&//=]*')
    return url_pattern.findall(text)

def extract_aweme_id(url_or_id: str) -> str:
    """提取作品 ID (支持纯数字 ID 或完整的 URL)"""
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id
    match = re.search(r'video/(\d+)', url_or_id)
    if match:
        return match.group(1)
    match_note = re.search(r'note/(\d+)', url_or_id)
    if match_note:
        return match_note.group(1)
    return ""

def format_size(bytes_size):
    """人性化文件大小格式"""
    if not bytes_size:
        return "N/A"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def get_image_urls_from_dom(page) -> list:
    """如果 JSON 提取失败，从 DOM 结构备份提取图文列表"""
    image_urls = []
    img_elements = page.query_selector_all('img')
    for el in img_elements:
        src = el.get_attribute('src')
        if src and ('tos-cn-i-' in src or 'img-s.dyimg.cn' in src):
            if src.startswith('//'):
                src = 'https:' + src
            if src not in image_urls:
                image_urls.append(src)
    return image_urls

def get_image_urls_from_page(page_content: str) -> list:
    """从页面源代码备份正则提取图文列表"""
    image_urls = []
    matches = re.findall(r'"src"\s*:\s*"([^"]+)"', page_content)
    for match in matches:
        url = match.replace('\\u002F', '/')
        if 'tos-cn-i-' in url or 'img-s.dyimg.cn' in url:
            if url.startswith('//'):
                url = 'https:' + url
            if url not in image_urls:
                image_urls.append(url)
    return image_urls

def get_video_id_from_iesdouyin(aweme_id: str) -> str:
    """通过 iesdouyin 备用 API 解析真实的无水印视频 vid"""
    api_url = f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={aweme_id}"
    try:
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            item_list = data.get("item_list", [])
            if item_list:
                return item_list[0].get("video", {}).get("play_addr", {}).get("uri", "")
    except Exception:
        pass
    return ""

def download_video(aweme_id: str, filepath: str) -> tuple:
    """下载无水印视频 (优先使用直接 API，支持多重 CDN 备用地址)"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 构造抖音官方源生无水印播放 API 链接
    api_urls = [
        f"https://aweme.snssdk.com/aweme/v1/play/?video_id={aweme_id}&ratio=1080p&line=0",
        f"https://aweme.snssdk.com/aweme/v1/playwm/?video_id={aweme_id}" # 降级方案
    ]
    
    # 如果能获取到真实的 vid，加入首选队列
    vid = get_video_id_from_iesdouyin(aweme_id)
    if vid:
        api_urls.insert(0, f"https://aweme.snssdk.com/aweme/v1/play/?video_id={vid}&ratio=1080p&line=0")
        
    last_err = None
    for url in api_urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                # 抖音 API 会进行 302 重定向到真实的 CDN 文件链接
                final_url = resp.geturl()
                
                # 开始读取数据流
                req_cdn = urllib.request.Request(final_url, headers=headers)
                with urllib.request.urlopen(req_cdn, timeout=60) as resp_cdn:
                    video_data = resp_cdn.read()
                    with open(filepath, "wb") as f:
                        f.write(video_data)
                    return len(video_data), "1080p" if "playwm" not in url else "720p (watermark)"
        except Exception as e:
            last_err = e
            continue
            
    raise last_err or Exception("All video download CDN sources failed.")

def get_next_filename(output_dir, extension):
    import os
    import re
    max_idx = 0
    if os.path.exists(output_dir):
        for fname in os.listdir(output_dir):
            m = re.match(r'^\[(\d+)\](?:image|video)\.\w+$', fname)
            if m:
                idx = int(m.group(1))
                if idx > max_idx:
                    max_idx = idx
    
    next_idx = max_idx + 1
    prefix = "image" if extension.lower() in ['jpg', 'jpeg', 'png', 'webp'] else "video"
    while True:
        candidate = f"[{next_idx}]{prefix}.{extension}"
        if not os.path.exists(os.path.join(output_dir, candidate)):
            return candidate
        next_idx += 1

def process_single(url, browser, output_base, index, total):
    """处理并下载单个抖音链接"""
    print(f"\n[{index}/{total}] {t('parsing')}")
    
    page = None
    try:
        # 使用移动端 (iPhone) 模拟，以绕过 PC 端的滑块验证码
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1",
            viewport={"width": 430, "height": 740},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True
        )
        page = context.new_page()
        
        # 引入反爬伪装，擦除 WebDriver 指纹
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(page)
        except ImportError:
            pass
            
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000) # 等待完整渲染与状态注水
        
        # 尝试提取页面中的注水数据 (兼容 PC 端的 RENDER_DATA 与移动端的 _ROUTER_DATA)
        render_data = None
        scripts = page.query_selector_all('script')
        for script in scripts:
            text = script.inner_text()
            if not text:
                continue
            if 'RENDER_DATA' in text:
                match = re.search(r'RENDER_DATA\s*=\s*(.*?)\s*;?\s*$', text, re.MULTILINE)
                if match:
                    try:
                        json_str = match.group(1).strip()
                        if json_str.endswith(';'):
                            json_str = json_str[:-1]
                        if '%' in json_str:
                            json_str = urllib.parse.unquote(json_str)
                        render_data = json.loads(json_str)
                        break
                    except Exception:
                        pass
            elif '_ROUTER_DATA' in text:
                match = re.search(r'_ROUTER_DATA\s*=\s*(.*?)\s*;?\s*$', text, re.MULTILINE)
                if match:
                    try:
                        json_str = match.group(1).strip()
                        if json_str.endswith(';'):
                            json_str = json_str[:-1]
                        if '%' in json_str:
                            json_str = urllib.parse.unquote(json_str)
                        render_data = json.loads(json_str)
                        break
                    except Exception:
                        pass
                        
        if not render_data:
            # 备用方案：尝试直接从 HTML 正则搜索
            html = page.content()
            match = re.search(r'id="RENDER_DATA"[^>]*>(.*?)</script>', html)
            if match:
                try:
                    json_str = urllib.parse.unquote(match.group(1))
                    render_data = json.loads(json_str)
                except Exception:
                    pass
            else:
                match_router = re.search(r'_ROUTER_DATA\s*=\s*(.*?)\s*;?\s*$', html, re.MULTILINE)
                if match_router:
                    try:
                        json_str = match_router.group(1).strip()
                        if json_str.endswith(';'):
                            json_str = json_str[:-1]
                        if '%' in json_str:
                            json_str = urllib.parse.unquote(json_str)
                        render_data = json.loads(json_str)
                    except Exception:
                        pass
                    
        # 若定位不到数据，尝试抛出异常走 DOM 兜底
        if not render_data:
            raise Exception("Neither RENDER_DATA nor _ROUTER_DATA JSON script tag found.")
            
        # 寻找作品数据节点
        aweme_detail = None
        # RENDER_DATA 结构经常发生微调，使用通用递归搜索找 aweme/awemeDetail/item_list
        def find_aweme_detail(obj):
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
                res = find_aweme_detail(v)
                if res:
                    return res
            return None
            
        aweme_detail = find_aweme_detail(render_data)
        
        if not aweme_detail:
            raise Exception("Aweme detail node not found in JSON data.")
            
        desc = aweme_detail.get('desc', 'douyin_media').strip()
        # 清洗文件名安全字符，去掉换行，并限制长度防止过长
        desc_clean = re.sub(r'[\\/*?:"<>|]', "", desc).replace("\n", " ").replace("\r", " ")
        desc_clean = desc_clean.strip()[:20] or "douyin_media"
        aweme_id = aweme_detail.get('awemeId') or aweme_detail.get('aweme_id')
        if not aweme_id:
            # 尝试从当前重定向后的 URL 提取 ID
            aweme_id = extract_aweme_id(page.url)
            
        if not aweme_id:
            raise Exception("Failed to parse aweme_id.")
            
        # 获取作者信息用于归档（不再创建子文件夹，仅做保留）
        author_info = aweme_detail.get('author', {})
        author_name = author_info.get('nickname') or author_info.get('sec_uid') or "Unknown_Author"
        author_clean = re.sub(r'[\\/*?:"<>|]', "", str(author_name)).strip()[:30]
            
        # 1. 优先提取图文相册
        images = aweme_detail.get('images')
        if images and isinstance(images, list):
            title_log = t("image_found", title=desc_clean, id=aweme_id, count=len(images))
            print(title_log)
            
            # 不再创建子目录，直接在 output_base
            os.makedirs(output_base, exist_ok=True)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            for i, img_obj in enumerate(images, 1):
                url_list = img_obj.get('urlList') or img_obj.get('url_list')
                if not url_list:
                    continue
                img_filename = get_next_filename(output_base, "jpg")
                img_path = os.path.join(output_base, img_filename)
                
                # 预占位防止循环内重名
                with open(img_path, "wb") as f:
                    pass
                    
                # 遍历备用链接，防止某个 CDN 节点 403
                success_img = False
                for img_url in url_list:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                        
                    try:
                        # 尝试通过 Playwright 获取
                        pw_resp = page.request.get(img_url, headers={"Referer": "https://www.douyin.com/"})
                        if pw_resp.status != 200:
                            pw_resp = page.request.get(img_url)
                            
                        if pw_resp.status == 200:
                            img_data = pw_resp.body()
                        else:
                            # 降级使用 urllib
                            req = urllib.request.Request(img_url, headers={"User-Agent": headers["User-Agent"]})
                            with urllib.request.urlopen(req) as resp:
                                img_data = resp.read()
                        
                        with open(img_path, "wb") as f:
                            f.write(img_data)
                        
                        # 尝试利用 Pillow 获取图片尺寸
                        resolution = "N/A"
                        if PILImage:
                            try:
                                with PILImage.open(img_path) as p_img:
                                    resolution = f"{p_img.width}x{p_img.height}"
                            except Exception:
                                pass
                        print(t("download_success", filename=img_filename, size=format_size(len(img_data)), resolution=resolution))
                        success_img = True
                        break  # 只要有一个链接下载成功就跳出循环
                    except Exception as e:
                        continue  # 失败则尝试下一个备用链接
                        
                if not success_img:
                    print(t("download_failed", err="All fallback URLs returned 403 or failed."))
                    
        # 2. 若不是图文，则提取视频
        else:
            title_log = t("video_found", title=desc_clean, id=aweme_id)
            print(title_log)
            
            os.makedirs(output_base, exist_ok=True)
            filename = get_next_filename(output_base, "mp4")
            filepath = os.path.join(output_base, filename)
            
            # 预占位
            with open(filepath, "wb") as f:
                pass
            
            # 尝试通过真实的无水印 API 体系下载视频
                try:
                    # 尝试从 JSON 提取视频 URI 作为 ID 传入
                    video_node = aweme_detail.get('video') or {}
                    vid = video_node.get('playAddr', [{}])[0].get('uri') or video_node.get('play_addr', {}).get('uri')
                    if not vid:
                        vid = aweme_id
                    size, res = download_video(vid, filepath)
                    print(t("download_success", filename=filename, size=format_size(size), resolution=res))
                except Exception as e:
                    import traceback
                    print(f"[DEBUG] 无水印 API 下载失败，准备降级。错误原因:\n{traceback.format_exc()}")
                    # 备用方案：尝试直接提取当前页面的 video src (常含水印，作为兜底)
                    video_element = page.query_selector('video')
                    if video_element:
                        video_src = video_element.get_attribute('src')
                        if video_src:
                            if video_src.startswith('//'):
                                video_src = 'https:' + video_src
                            headers = {
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            }
                            req = urllib.request.Request(video_src, headers=headers)
                            with urllib.request.urlopen(req) as resp:
                                video_data = resp.read()
                                with open(filepath, "wb") as f:
                                    f.write(video_data)
                            print(t("download_success", filename=filename, size=format_size(len(video_data)), resolution="N/A (Backup CDN)"))
                        else:
                            raise Exception("Fallback video element found but has no src attribute.")
                    else:
                        raise Exception(f"Video detail download failed and no backup DOM video tag found. Err: {e}")
                    
        context.close()
        return True
    except Exception as e:
        print(t("parse_failed", err=e))
        if page:
            try:
                page.context.close()
            except Exception:
                pass
        return False

def ensure_browser_installed(playwright_inst):
    """检查并自动安装缺失的 Playwright 浏览器"""
    try:
        # 尝试启动浏览器来验证其是否存在
        browser = playwright_inst.chromium.launch(headless=True)
        browser.close()
    except Exception as e:
        err_msg = str(e)
        if "Executable doesn't exist" in err_msg or "looks like Playwright was just installed" in err_msg:
            print(t("browser_not_found"))
            import sys
            import subprocess
            from playwright._impl._driver import compute_driver_executable, get_driver_env
            
            driver_executable, driver_cli = compute_driver_executable()
            env = get_driver_env()
            
            try:
                # 修复 Windows 子进程弹出 CMD 黑框
                creationflags = 0
                import os
                if os.name == 'nt':
                    creationflags = subprocess.CREATE_NO_WINDOW
                
                subprocess.run(
                    [driver_executable, driver_cli, "install", "chromium"],
                    env=env,
                    check=True,
                    creationflags=creationflags
                )
                print(t("browser_install_success"))
            except subprocess.CalledProcessError as exit_err:
                print(t("browser_install_failed", code=exit_err.returncode))
                sys.exit(1)
        else:
            raise e

def download_urls(raw_input: str, output_dir: str):
    """批量下载抖音链接"""
    urls = extract_urls_from_text(raw_input)
    if not urls:
        # 尝试将输入直接视为单个作品 ID
        clean_input = raw_input.strip()
        if clean_input.isdigit() and len(clean_input) >= 15:
            urls = [clean_input]
        else:
            print(t("no_links"))
            return False

    # 数组去重
    unique_urls = []
    seen = set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    urls = unique_urls

    total = len(urls)

    if not output_dir:
        output_dir = "douyin_downloads"
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        ensure_browser_installed(p)
        browser = p.chromium.launch(headless=True)
        success = 0
        fail = 0
        for i, url in enumerate(urls, 1):
            # 补全如果是纯数字 ID 类型的 URL 格式
            if url.isdigit():
                url = f"https://www.douyin.com/video/{url}"
            if process_single(url, browser, output_dir, i, total):
                success += 1
            else:
                fail += 1
        browser.close()

    print(t("download_done", success=success, fail=fail))
    print(t("save_dir_info", path=os.path.abspath(output_dir)))
    return True

def download_douyin_links(links, output_dir):
    """供 WebUI 调用的批量下载接口"""
    if isinstance(links, list):
        raw_input = "\n".join(links)
    else:
        raw_input = str(links)
    return download_urls(raw_input, output_dir)

DISCLAIMER = """================================================================================
                                【 免 责 声 明 】
================================================================================
 1. 本工具（以下简称“本软件”）仅限用于个人学习研究、学术交流及网页技术备份
    测试，严禁用于任何商业用途、非法抓取或网络攻击。
 2. 本软件所下载的所有音视频、图文等媒体资源，其知识产权及著作权归原作者/
    版权所有者或相关平台所有。用户下载后应于24小时内删除，且不得在未经原作者
    授权的情况下进行二次传播、修改、上传或用于任何盈利性活动。
 3. 用户在使用本软件时，必须遵守当地法律法规、目的平台用户协议及相关服务条款。
    因使用本软件导致的一切直接或间接法律纠纷、版权诉讼、经济赔偿，或因频繁请求
    导致的平台账号限制、IP风控封禁等后果，均由使用者自行承担全部责任。
 4. 本软件按“原样”（AS IS）提供，不附带任何明示或暗示的保证，包括但不限于
    对特定用途的适用性。作者在任何情况下均不对因使用或无法使用本软件而产生的
    任何直接、间接、偶然、特殊或惩罚性损害（包括法律处罚）承担任何赔偿责任。
 5. 任何复制、运行、分发或以任何方式使用本软件的行为，即视为您已完全阅读、
    理解并无条件接受本声明的所有条款。如果您不同意本声明的任何内容，请立即
    停止使用并卸载本软件。
================================================================================"""

DISCLAIMER_EN = """================================================================================
                                【 DISCLAIMER 】
================================================================================
 1. This tool (hereinafter referred to as "the software") is strictly for personal 
    learning, research, academic exchanges, and technical backup tests. Commercial 
    use, malicious scraping, or network attacks are strictly prohibited.
 2. All media resources (videos, images, etc.) downloaded belong to the original 
    creators/copyright owners. Users must delete them within 24 hours and must not 
    redistribute, modify, upload, or use them for profit without authorization.
 3. Users must comply with local laws and platform Terms of Service. The user assumes 
    full responsibility for any legal disputes, copyright lawsuits, financial damages, 
    account restrictions, or IP bans caused by using this software.
 4. This software is provided "AS IS" without warranties of any kind. Under no 
    circumstances shall the author be liable for any direct, indirect, incidental, 
    or special damages arising from the use or inability to use this software.
 5. Running, distributing, or using this software constitutes unconditional acceptance 
    of this disclaimer. If you disagree with any terms, please stop using and uninstall 
    this software immediately.
================================================================================"""

def main():
    if len(sys.argv) >= 2:
        # Command line parameter mode
        print(t("legal_warning"))
            
        check_for_updates(silent=True)
        raw_input = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "douyin_downloads"
        download_urls(raw_input, output_dir)
    else:
        # Interactive mode
        print(t("disclaimer_title"))
        print(t("disclaimer_text"))
            
        try:
            agree = input(t("disclaimer_agree")).strip().lower()
            if agree not in ['y', 'yes']:
                print(t("disclaimer_declined"))
                sys.exit(0)
        except (KeyboardInterrupt, EOFError):
            print("\n" + t("exited_safely"))
            sys.exit(0)

        print(t("title_banner"))
        check_for_updates(silent=False)

        try:
            while True:
                raw_input = input(t("input_prompt")).strip()
                if not raw_input or raw_input.lower() in ['q', 'exit']:
                    print(t("exited_safely"))
                    break

                output_dir = input(t("save_dir_prompt", default_dir="douyin_downloads")).strip()
                if not output_dir:
                    output_dir = "douyin_downloads"

                print(t("parsing"))
                download_urls(raw_input, output_dir)
        except (KeyboardInterrupt, EOFError):
            print("\n" + t("exited_safely"))

if __name__ == "__main__":
    main()
