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

CURRENT_VERSION = "2.0.0"

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


# Shared machine-readable changelog: one file consumed by every client
# (CLI / Windows GUI / macOS / iOS), generated from CHANGELOG.md by
# scripts/update-changelog-json.py. Raw-file mirrors are reliable in CN,
# unlike api.github.com (rate-limited / blocked).
_CHANGELOG_SOURCES = [
    "https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/changelog.json",
    "https://gh-proxy.com/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/changelog.json",
    "https://ghproxy.net/https://raw.githubusercontent.com/Francis-Xavier-code/tiktok-douyin-dl/main/changelog.json",
    "https://fastly.jsdelivr.net/gh/Francis-Xavier-code/tiktok-douyin-dl@main/changelog.json",
]


def fetch_changelog(platform="windows", max_versions=3):
    """Fetch changelog.json and return (latest_version, notes_text).

    Entries are filtered to the given platform plus [全平台] (all) entries.
    On any failure returns (None, "") so callers stay fail-open.
    """
    data = None
    for url in _CHANGELOG_SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict):
                break
        except Exception:
            continue
    if not isinstance(data, dict):
        return None, ""

    versions = data.get("versions") or []
    latest = None
    lines = []
    for v in versions[:max_versions]:
        version = str(v.get("version", "")).lstrip("v")
        if not version:
            continue
        if latest is None:
            latest = version
        if _parse_version(version) <= _parse_version(CURRENT_VERSION):
            continue
        bucket = v.get("entries") or {}
        entries = []
        for key in (platform, "all"):
            entries.extend(bucket.get(key) or [])
        if not entries:
            continue
        header = f"v{version}"
        if v.get("date"):
            header += f" ({v['date']})"
        lines.append(header)
        for e in entries:
            for ln in str(e).splitlines():
                lines.append(f"  • {ln}")
        lines.append("")
    return latest, "\n".join(lines).strip()


def check_for_updates(root, silent=True):
    """检查更新。网络请求在后台线程执行，结果经队列回到主线程展示。"""
    import queue as _queue
    result_q = _queue.Queue()

    def _run():
        import re
        import urllib.request

        # 1. Preferred: shared changelog.json via raw-file mirrors (reliable in CN).
        latest_version, notes = fetch_changelog("windows")

        # 2. Fallback: /releases/latest HTML redirect for the version only.
        if not latest_version:
            check_urls = [
                "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest",
                "https://kgithub.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest",
            ]
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

        result_q.put((latest_version, notes))

    def _show_result(latest_version, notes):
        if not latest_version:
            if not silent:
                err_msg = "无法获取最新版本信息。\n\n这通常是因为国内网络波动或加速节点失效。\n请稍后再试或开启全局代理。"
                messagebox.showerror("网络错误", err_msg, parent=root)
            return

        if latest_version.lstrip("v") != CURRENT_VERSION:
            # 真实 Release 资产名：MediaDownloader-Windows-x64-Setup-<ver>.exe
            raw_dl_url = (
                f"https://github.com/Francis-Xavier-code/tiktok-douyin-dl"
                f"/releases/download/{latest_version}/"
                f"MediaDownloader-Windows-x64-Setup-{latest_version.lstrip('v')}.exe"
            )
            proxy_dl_url = f"https://ghproxy.net/{raw_dl_url}"

            _show_update_prompt(
                root, latest_version, notes,
                on_confirm=lambda: _start_download_and_update(root, proxy_dl_url),
            )
        else:
            if not silent:
                messagebox.showinfo(
                    "检查更新",
                    f"当前已是最新版本 v{CURRENT_VERSION}！",
                    parent=root,
                )

    def _poll():
        try:
            latest_version, notes = result_q.get_nowait()
        except Exception:
            root.after(100, _poll)  # 主线程轮询，等后台线程结果
            return
        _show_result(latest_version, notes)

    root.after(0, _poll)  # 主线程调度，可靠
    threading.Thread(target=_run, daemon=True).start()


def _show_update_prompt(root, latest_version, notes, on_confirm):
    """更新提示对话框：展示新版本号 + 按端过滤的更新日志（可滚动）。"""
    import tkinter as tk
    from tkinter import ttk

    win = tk.Toplevel(root)
    win.title("软件更新")
    win.geometry("600x500")
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()
    win.update_idletasks()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"+{max((sw - 600) // 2, 0)}+{max((sh - 500) // 2, 0)}")

    ttk.Label(win, text="✨ 发现新版本", font=("微软雅黑", 15, "bold")).pack(pady=(18, 2))
    ttk.Label(win, text=latest_version, foreground="#3d7eff",
              font=("微软雅黑", 13, "bold")).pack()
    ttk.Label(win, text=f"当前版本：v{CURRENT_VERSION}",
              foreground="#8b949e", font=("微软雅黑", 9)).pack(pady=(2, 8))
    ttk.Label(win, text="本次更新内容（已按当前客户端过滤）",
              foreground="#8b949e", font=("微软雅黑", 9)).pack()

    # 可滚动更新日志
    frame = ttk.Frame(win)
    frame.pack(fill="both", expand=True, padx=20, pady=8)
    txt = tk.Text(frame, height=14, wrap="word", relief="flat",
                  bg="#1e1f22", fg="#c9d1d9", font=("Microsoft YaHei UI", 10),
                  padx=14, pady=10, selectbackground="#3d7eff", selectforeground="#ffffff")
    scroll = ttk.Scrollbar(frame, command=txt.yview)
    txt.configure(yscrollcommand=scroll.set)
    txt.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    txt.tag_configure("header", foreground="#e6edf3", font=("Microsoft YaHei UI", 10, "bold"))
    txt.tag_configure("bullet", foreground="#3fb950")
    txt.tag_configure("body", foreground="#c9d1d9")
    txt.tag_configure("dim", foreground="#8b949e")
    txt.insert("end", "📝 更新日志\n", "header")
    if notes:
        for line in notes.splitlines():
            stripped = line.strip()
            if stripped.startswith("v") and "(" in stripped and ")" in stripped:
                txt.insert("end", "\n" + line + "\n", "header")
            elif stripped.startswith("•"):
                txt.insert("end", line + "\n", "bullet")
            elif stripped:
                txt.insert("end", line + "\n", "body")
    else:
        txt.insert("end", "暂无更新说明。\n", "dim")
    txt.configure(state="disabled")

    btns = ttk.Frame(win)
    btns.pack(pady=(10, 16))
    ttk.Button(btns, text="稍后再说", width=12, command=win.destroy).pack(side="left", padx=6)
    ttk.Button(btns, text="立即更新", width=14, style="Accent.TButton",
               command=lambda: (win.destroy(), on_confirm())).pack(side="left", padx=6)

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
