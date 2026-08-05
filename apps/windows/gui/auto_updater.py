import os
import sys
import threading
import urllib.request
import urllib.error
import json
import re
import tempfile
import subprocess
import tkinter.messagebox as messagebox

CURRENT_VERSION = "1.8.1"

# Remote version-policy enforcement (fail-open). Lets the maintainer retire old
# builds without re-shipping every binary. See version-policy.json / docs.
_POLICY_URLS = [
    "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
    "https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
    "https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/version-policy.json",
]
_POLICY_TIMEOUT = 6

# Local cache: a successful pull is persisted so a hard block still applies when
# the network is down. A build that has NEVER fetched a policy fails open.
_CACHE_DIR = os.path.join(os.getenv("LOCALAPPDATA") or os.path.expanduser("~/.cache"), "tiktok-douyin-dl")
_CACHE_PATH = os.path.join(_CACHE_DIR, "version-policy.json")


def _write_cache(policy):
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(policy, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _read_cache():
    try:
        with open(_CACHE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _parse_version(v):
    nums = re.findall(r"\d+", str(v))
    return tuple(int(x) for x in nums) if nums else (0,)


def fetch_version_policy(use_cache=True):
    """Return the policy dict, or None on any failure (fail-open).
    On a network failure, falls back to the last successful local cache so an
    offline EOL build can still be hard-blocked."""
    for url in _POLICY_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=_POLICY_TIMEOUT) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict):
                    _write_cache(data)
                    return data
        except Exception:
            continue
    if use_cache:
        return _read_cache()
    return None


def enforce_version_policy(platform, current_version):
    """Check the remote policy. Hard-block exits the process; soft shows a warning.
    Any failure (incl. offline with no prior cache) is ignored (fail-open) so the
    app always runs the first time."""
    try:
        policy = fetch_version_policy()
        if not isinstance(policy, dict):
            return
        platforms = policy.get("platforms") or {}
        entry = platforms.get(platform)
        if not isinstance(entry, dict):
            return
        min_version = entry.get("min_version") or "0.0.0"
        hard_block = bool(entry.get("hard_block", False))
        if _parse_version(current_version) >= _parse_version(min_version):
            return
        message = (policy.get("message") or "当前版本已过时，请升级到最新版本。").strip()
        update_url = policy.get("update_url") or \
            "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest"
        if hard_block:
            messagebox.showerror(
                "版本已停止支持",
                f"{message}\n\n最低支持版本：{min_version}\n请前往更新：\n{update_url}",
            )
            sys.exit(1)
        else:
            messagebox.showwarning(
                "建议升级",
                f"{message}\n\n最低支持版本：{min_version}\n更新地址：\n{update_url}",
            )
    except Exception:
        pass

def check_download_policy(platform: str = "windows") -> str:
    """Pre-download gate. Returns one of: 'allow', 'disabled', 'version', 'unreachable'.

    Tries direct GitHub first, then 9 domestic mirrors in order; the first
    source that returns valid JSON wins. If EVERY source fails, returns
    'unreachable' (fail-closed): the caller must block the download.

    Supports per-platform overrides: if download.platforms.<platform> exists,
    its values take precedence over the global download settings.
    """
    sources = [
        "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://raw.gitmirror.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://kgithub.com/Francis-Xavier-code/tiktok-douyin-dl/raw/main/download-policy.json",
        "https://mirror.ghproxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://github.moeyy.xyz/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://ghproxy.1888866.xyz/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://gh.api.99988866.xyz/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/download-policy.json",
        "https://fastly.jsdelivr.net/gh/Francis-Xavier-code/tiktok-douyin-dl@main/download-policy.json",
    ]
    policy = None
    for url in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict):
                policy = data
                break
        except Exception:
            continue

    if policy is None:
        return "unreachable"

    download = policy.get("download")
    if not isinstance(download, dict):
        return "unreachable"

    # Per-platform override takes precedence if present.
    platforms = download.get("platforms") or {}
    entry = platforms.get(platform) if isinstance(platforms, dict) else None
    if isinstance(entry, dict):
        eff_enabled = entry.get("enabled", download.get("enabled", True))
        eff_min = entry.get("min_version", download.get("min_version", "0.0.0"))
    else:
        eff_enabled = download.get("enabled", True)
        eff_min = download.get("min_version", "0.0.0")

    if not eff_enabled:
        return "disabled"
    if _parse_version(CURRENT_VERSION) < _parse_version(eff_min):
        return "version"
    return "allow"


def check_for_updates(root, silent=True):
    def _run():
        import re
        import urllib.request
        
        # 使用加速镜像站的 /releases/latest 页面（非 API）来绕过 403 限制和 GFW
        check_urls = [
            "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest",
            "https://kgithub.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest",
        ]
        
        latest_version = None
        for url in check_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="HEAD")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    final_url = resp.geturl()
                    # 从重定向后的 URL 提取版本号，例如 .../releases/tag/v1.4.1
                    match = re.search(r'/tag/(v\d+\.\d+\.\d+)', final_url)
                    if match:
                        latest_version = match.group(1)
                        break
            except Exception:
                continue
                
        if not latest_version:
            if not silent:
                err_msg = "无法获取最新版本信息。\n\n这通常是因为国内网络波动或加速节点失效。\n请稍后再试或开启全局代理。"
                root.after(0, lambda: messagebox.showerror("网络错误", err_msg, parent=root))
            return
            
        if latest_version.lstrip("v") != CURRENT_VERSION:
            release_notes = ""
            try:
                # 尝试获取更新日志
                api_url = f"https://api.github.com/repos/Francis-Xavier-code/tiktok-douyin-dl/releases/tags/{latest_version}"
                req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    body = data.get("body", "").strip()
                    if body:
                        # 限制日志长度
                        if len(body) > 300:
                            body = body[:300] + "...\n(查看更多请前往 Github)"
                        release_notes = f"\n\n【更新日志】\n{body}"
            except Exception:
                pass
                
            msg = f"发现新版本 {latest_version}！\n\n您当前版本为 {CURRENT_VERSION}。{release_notes}\n\n是否立即下载并覆盖更新？\n(国内网络将自动启用加速节点下载)"
            def _show_prompt():
                if messagebox.askyesno("软件更新", msg, parent=root):
                    # 真实 Release 资产名：MediaDownloader-Windows-x64-Setup-<ver>.exe
                    # 直接用 ghproxy 加速下载，下载后静默运行安装包完成覆盖更新。
                    raw_dl_url = (
                        f"https://github.com/Francis-Xavier-code/tiktok-douyin-dl"
                        f"/releases/download/{latest_version}/"
                        f"MediaDownloader-Windows-x64-Setup-{latest_version.lstrip('v')}.exe"
                    )
                    proxy_dl_url = f"https://ghproxy.net/{raw_dl_url}"
                    _start_download_and_update(root, proxy_dl_url)
            root.after(0, _show_prompt)
        else:
            if not silent:
                root.after(0, lambda: messagebox.showinfo("检查更新", "当前已经是最新版本！", parent=root))

    threading.Thread(target=_run, daemon=True).start()

def _start_download_and_update(root, download_url):
    import tkinter as tk
    from tkinter import ttk

    progress_win = tk.Toplevel(root)
    progress_win.title("软件更新中")
    progress_win.geometry("350x150")
    progress_win.resizable(False, False)
    progress_win.transient(root)
    progress_win.grab_set()

    tk.Label(progress_win, text="正在下载最新安装包，请耐心等待...", font=("微软雅黑", 10)).pack(pady=15)
    progress_bar = ttk.Progressbar(progress_win, length=280, mode='determinate')
    progress_bar.pack(pady=5)
    lbl_progress = tk.Label(progress_win, text="0 MB / 0 MB", font=("微软雅黑", 9))
    lbl_progress.pack(pady=5)

    def _download():
        try:
            temp_dir = tempfile.gettempdir()
            # 直接下载安装包 exe（与 Release 资产同名），不再走 zip 解压。
            setup_path = os.path.join(temp_dir, "MediaDownloader_Update.exe")

            # 尝试多个下载节点（download_url 已可带镜像前缀，这里再补几个兜底）。
            raw_url = download_url.replace("https://ghproxy.net/", "").replace("https://gh-proxy.com/", "")
            urls_to_try = [
                download_url,
                f"https://gh-proxy.com/{raw_url}",
                f"https://ghproxy.net/{raw_url}",
                raw_url,
            ]

            success = False
            last_err = None

            for d_url in urls_to_try:
                try:
                    req = urllib.request.Request(d_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        total_size = int(resp.getheader('Content-Length', 0))
                        downloaded = 0
                        chunk_size = 8192
                        with open(setup_path, 'wb') as f:
                            while True:
                                chunk = resp.read(chunk_size)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    def _update_ui(p=progress, d=downloaded, t=total_size):
                                        progress_bar['value'] = p
                                        lbl_progress.config(text=f"{d/1024/1024:.1f} MB / {t/1024/1024:.1f} MB")
                                    root.after(0, _update_ui)
                    success = True
                    break
                except Exception as e:
                    last_err = e
                    continue

            if not success:
                raise Exception(f"所有下载节点均失败，最后错误: {last_err}")

            root.after(0, lambda: lbl_progress.config(text="即将启动安装程序..."))

            # 准备静默安装 bat 脚本：先等主程序退出，再静默运行新安装包覆盖。
            bat_path = os.path.join(temp_dir, "update_app.bat")
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write("timeout /t 2 /nobreak >nul\n")  # 等待主程序关闭
                f.write(f'start "" "{setup_path}" /SILENT\n')  # 启动静默安装

            def _apply():
                messagebox.showinfo("更新准备完毕", "更新包已下载完毕！点击确定后软件将重启以完成更新。", parent=root)
                subprocess.Popen(bat_path, shell=True)
                sys.exit(0)

            root.after(0, _apply)

        except Exception as e:
            err_msg = str(e)
            def _err(msg=err_msg):
                try:
                    progress_win.destroy()
                except:
                    pass
                messagebox.showerror("更新失败", f"下载更新包失败：{msg}", parent=root)
            root.after(0, _err)
            
    threading.Thread(target=_download, daemon=True).start()
