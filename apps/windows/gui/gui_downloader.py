#!/usr/bin/env python3
"""
抖音 / TikTok 批量下载器 — GUI 入口文件
本文件只包含核心下载逻辑（后台线程运行、配置读写、模块动态加载等），
不包含任何 tkinter / GUI 相关代码。
"""

import sys
import os

from pathlib import Path

# Allow running this source checkout directly without requiring an editable install.
_SOURCE_ROOT = Path(__file__).resolve().parents[3] / "python" / "src"
if _SOURCE_ROOT.is_dir() and str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

# 修复 PyInstaller 打包环境中子进程（如 Playwright 启动的浏览器）
# 因为 LD_LIBRARY_PATH 污染而崩溃的问题
if getattr(sys, 'frozen', False):
    for key in ['LD_LIBRARY_PATH', 'LIBPATH', 'DYLD_LIBRARY_PATH']:
        orig_key = key + '_ORIG'
        if orig_key in os.environ:
            os.environ[key] = os.environ[orig_key]
        else:
            os.environ.pop(key, None)

import json
import ssl
import importlib
import threading
import queue

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from playwright.sync_api import sync_playwright
from media_downloader.i18n import translate

# NOTE: We no longer disable certificate verification process-wide. If a host's
# root CA is genuinely missing in the frozen runtime, opt out per request via the
# ssl context in the relevant network helper instead of weakening every connection.

# 强制设置浏览器路径为用户的全局缓存目录，防止打包后寻找 tmp 目录而崩溃（仅在未预设时设置）
if 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser('~/.cache/ms-playwright')

# ============================================================================
# 修复 Windows 环境下子进程（如下载 Playwright 时）弹出 CMD 黑框的问题
# ============================================================================
import subprocess
if os.name == 'nt':
    _original_popen = subprocess.Popen
    def _custom_popen(*args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)
    subprocess.Popen = _custom_popen

# ============================================================================
# 国内镜像加速：Playwright 浏览器下载
# ============================================================================
if 'PLAYWRIGHT_DOWNLOAD_HOST' not in os.environ:
    os.environ['PLAYWRIGHT_DOWNLOAD_HOST'] = 'https://npmmirror.com/mirrors/playwright/'

if 'npm_config_registry' not in os.environ:
    os.environ['npm_config_registry'] = 'https://registry.npmmirror.com'

# ============================================================================
# 配置文件读写
# ============================================================================

def load_config() -> dict:
    """读取脚本/exe 所在目录的 config.json；失败或不存在时返回默认值。"""
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_path = os.path.join(exe_dir, "config.json")
        if not os.path.exists(config_path):
            return {"lang": "zh"}
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if not isinstance(cfg, dict):
                return {"lang": "zh"}
            return cfg
    except Exception:
        return {"lang": "zh"}


def save_config(cfg: dict) -> None:
    """将 dict 写回 config.json，UTF-8 编码，indent=2。失败只打印警告。"""
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_path = os.path.join(exe_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] save_config failed: {e}")


def get_lang() -> str:
    """返回当前语言设置（'zh' 或 'en'）。"""
    return load_config().get("lang", "zh")


# ============================================================================
# 工具函数
# ============================================================================

def get_default_output_dir(platform: str) -> str:
    """返回 Windows 桌面的绝对路径 + 对应子目录。
    'douyin'  -> ...\\Desktop\\douyin_downloads
    'tiktok'  -> ...\\Desktop\\tiktok_downloads
    """
    if platform == "douyin":
        subdir_name = "douyin_downloads"
    elif platform == "tiktok":
        subdir_name = "tiktok_downloads"
    else:
        subdir_name = "downloads"

    candidates = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "桌面"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return os.path.join(c, subdir_name)
    # 若桌面都不可用，回退到用户主目录/downloads
    home_downloads = os.path.join(os.path.expanduser("~"), "downloads")
    if os.path.isdir(os.path.dirname(home_downloads)):
        return os.path.join(home_downloads, subdir_name)
    return os.path.join(candidates[0], subdir_name)


def _mkdir_with_fallback(path: str, log_queue=None, lang: str = "zh") -> str:
    """创建输出目录，带重试和回退机制。
    返回实际使用的路径（可能是传入值或回退值）。
    失败时抛异常（调用方负责捕获并写入日志）。
    """
    path = os.path.abspath(os.path.normpath(path))

    # 快速路径：目录已存在
    try:
        if os.path.isdir(path):
            return path
    except Exception:
        pass

    # 正常创建：带重试（应对 Windows 杀毒软件瞬态锁定）
    import time as _time
    last_err = None
    for attempt in range(3):
        try:
            os.makedirs(path, exist_ok=True)
            if os.path.isdir(path):
                return path
        except Exception as e:
            last_err = e
            if attempt < 2:
                _time.sleep(0.5 + attempt * 0.5)
            continue

    # 回退到临时目录（若主路径不可用）
    try:
        temp_root = os.environ.get("TMP") or os.environ.get("TEMP") or os.path.expanduser("~")
        basename = os.path.basename(path.rstrip(os.sep)) or "downloads"
        fallback = os.path.join(temp_root, basename)
        os.makedirs(fallback, exist_ok=True)
        if log_queue is not None:
            msg_tpl = translate("gui.run.fallback_directory", locale=lang, orig=path, fallback=fallback)
            try:
                log_queue.put(("log", "warning", msg_tpl.format(orig=path, fallback=fallback)))
            except Exception:
                pass
        return fallback
    except Exception as e:
        if last_err is not None:
            raise last_err
        raise e


from media_downloader.platforms import douyin, tiktok

def get_module(platform: str):
    """动态加载对应平台模块。未知平台抛出 ValueError。"""
    if platform == "douyin":
        return douyin
    elif platform == "tiktok":
        return tiktok
    else:
        raise ValueError(f"Unknown platform: {platform}")


def extract_unique_urls(platform_module, raw_text: str) -> list:
    """调用 platform_module.extract_urls_from_text(raw_text) 并去重（保持原顺序）。"""
    urls = platform_module.extract_urls_from_text(raw_text)
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


# ============================================================================
# 日志 / stdout 重定向：将 print 输出转为 log_queue 的 (log, level, text) 消息
# ============================================================================

class _GuiLogWriter:
    """把 stdout 写入到 log_queue，供主线程 GUI 消费。
    约定消息格式：
      ("log", "info" | "error" | "warning", text)
      ("progress", current, total)
      ("done", {"success": N, "fail": M, "cancelled": bool, "path": output_dir})
    """

    __slots__ = ("_queue", "_buffer")

    def __init__(self, log_queue):
        self._queue = log_queue
        self._buffer = []

    def write(self, text):
        if not text:
            return
        # 按行拆分，非空行入队（log / info 等级）
        for line in text.splitlines():
            stripped = line.strip()
            if stripped:
                try:
                    self._queue.put(("log", "info", stripped))
                except Exception:
                    pass

    def flush(self):
        self._buffer = []


# ============================================================================
# 文案通过 media_downloader.i18n 读取。
# ============================================================================

def _current_lang() -> str:
    try:
        return get_lang()
    except Exception:
        return "zh"


def _run_text(key: str, lang: str, **variables) -> str:
    return translate(f"gui.run.{key}", locale=lang, **variables)


# ============================================================================
# 后台线程执行的核心下载函数
# ============================================================================

def _send_log(log_queue, level: str, text: str):
    try:
        log_queue.put(("log", level, str(text)))
    except Exception:
        pass


def _send_done(log_queue, success: int, fail: int, cancelled: bool, path: str):
    try:
        log_queue.put(("done", {
            "success": int(success),
            "fail": int(fail),
            "cancelled": bool(cancelled),
            "path": str(path),
        }))
    except Exception:
        pass


def _send_progress(log_queue, current: int, total: int):
    try:
        log_queue.put(("progress", int(current), int(total)))
    except Exception:
        pass


def run_download(platform: str, raw_text: str, output_dir: str, log_queue, cancel_event=None):
    """在后台线程中执行下载。
    不使用任何 GUI / tkinter 调用，仅通过 log_queue 与主线程通信。
    """
    lang = _current_lang()
    original_stdout = sys.stdout
    success = 0
    fail = 0
    cancelled = False
    total = 0
    actual_output_dir = output_dir

    try:
        # 1. 创建输出目录（带重试和回退）
        try:
            actual_output_dir = _mkdir_with_fallback(output_dir, log_queue, lang)
        except Exception as e:
            err_msg = _run_text("error_prefix", lang) + str(e)
            _send_log(log_queue, "error", err_msg)
            _send_log(log_queue, "warning", _run_text("change_directory_hint", lang))
            _send_done(log_queue, 0, 0, False, output_dir)
            return

        # 2. 获取对应平台模块
        try:
            module = get_module(platform)
        except Exception as e:
            _send_log(log_queue, "error",
                      _run_text("error_prefix", lang) + str(e))
            _send_done(log_queue, 0, 0, False, actual_output_dir)
            return

        # 3. 重定向 stdout 到 GUI log writer，使被调用模块的 print 输出被捕获
        try:
            sys.stdout = _GuiLogWriter(log_queue)
        except Exception:
            pass

        # 4. 解析链接
        try:
            urls = extract_unique_urls(module, raw_text)
        except Exception as e:
            _send_log(log_queue, "error", _run_text("url_parse_failed", lang, error=e))
            _send_done(log_queue, 0, 0, False, actual_output_dir)
            return
        total = len(urls)

        if total == 0:
            _send_log(log_queue, "info", _run_text("no_links", lang))
            _send_log(log_queue, "warning", _run_text("no_links_hint", lang))
            _send_progress(log_queue, 0, 0)
            _send_done(log_queue, 0, 0, False, actual_output_dir)
            return

        _send_log(log_queue, "info", _run_text("found_links", lang, count=total))
        _send_log(log_queue, "info", _run_text("saved_to", lang, path=actual_output_dir))
        _send_progress(log_queue, 0, total)

        # 5. Playwright 启动 + 逐个链接下载
        # 启动前给个提示，因为浏览器下载可能比较慢
        _send_log(log_queue, "info", _run_text("browser_initializing", lang))

        browser = None
        try:
            with sync_playwright() as p:
                try:
                    module.ensure_browser_installed(p)
                except Exception as e:
                    _send_log(log_queue, "error", _run_text("browser_install_failed", lang, error=e))
                    _send_log(log_queue, "warning", _run_text("browser_install_hint", lang))
                    _send_done(log_queue, 0, 0, False, actual_output_dir)
                    return

                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as e:
                    _send_log(log_queue, "error", _run_text("browser_launch_failed", lang, error=e))
                    _send_done(log_queue, 0, 0, False, actual_output_dir)
                    return

                _send_log(log_queue, "info", _run_text("browser_ready", lang))

                for i, url in enumerate(urls, 1):
                    # 取消检测
                    if cancel_event is not None and cancel_event.is_set():
                        cancelled = True
                        _send_log(log_queue, "warning",
                                  _run_text("cancelled_summary", lang, success=success, failed=fail))
                        break

                    try:
                        result = module.process_single(url, browser, actual_output_dir, i, total)
                        if result:
                            success += 1
                        else:
                            fail += 1
                    except Exception as e:
                        fail += 1
                        _send_log(log_queue, "error", _run_text(
                            "download_error", lang, current=i, total=total, error=e))

                    _send_progress(log_queue, i, total)
        finally:
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass

        # 6. 完成日志
        summary_key = "cancelled_summary" if cancelled else "done_summary"
        _send_log(log_queue, "info",
                  _run_text(summary_key, lang, success=success, failed=fail))
        _send_log(log_queue, "info",
                  _run_text("path_info", lang, path=os.path.abspath(actual_output_dir)))

    except Exception as e:
        # 异常分支：发送错误日志
        try:
            sys.stdout = original_stdout
        except Exception:
            pass
        err_text = _run_text("error_prefix", lang) + str(e)
        _send_log(log_queue, "error", err_text)

    finally:
        # 无论是否异常，都必须恢复原 stdout
        try:
            sys.stdout = original_stdout
        except Exception:
            pass
        # 发送 done 消息（确保主线程恢复 UI 状态）
        _send_done(log_queue, success, fail, cancelled, actual_output_dir)


# ============================================================================
# 便于在后台线程中触发 run_download 的便捷入口
# ============================================================================

def start_download_thread(platform: str, raw_text: str, output_dir: str,
                          log_queue, cancel_event=None):
    """启动一个后台线程来运行 run_download，返回该线程对象。"""
    thread = threading.Thread(
        target=run_download,
        args=(platform, raw_text, output_dir, log_queue, cancel_event),
        daemon=True,
        name="DownloadWorker",
    )
    thread.start()
    return thread


# ============================================================================
def _t(key: str, **variables) -> str:
    """Read a GUI string from the shared translation catalog."""
    if "err" in variables and "error" not in variables:
        variables["error"] = variables["err"]
    return translate(f"gui.ui.{key}", locale=_current_lang(), **variables)


# ============================================================================
# 免责声明对话框
# ============================================================================

class DisclaimerDialog(tk.Toplevel):
    """启动前显示的免责声明弹窗，模态。"""

    def __init__(self, master=None):
        super().__init__(master)
        self.title(_t("disclaimer_title"))
        self.resizable(False, False)
        # 居中
        self.update_idletasks()
        w, h = 640, 520
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

        self.agreed = False
        self.dont_show_again = False

        self._agree_var = tk.BooleanVar(value=False)
        self._dont_show_var = tk.BooleanVar(value=False)

        self._build_ui()

        # 模态
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

        # 居中于父窗口
        if master is not None:
            try:
                master.update_idletasks()
                mx = master.winfo_rootx()
                my = master.winfo_rooty()
                mw = master.winfo_width()
                mh = master.winfo_height()
                cx = mx + (mw - w) // 2
                cy = my + (mh - h) // 2
                self.geometry(f"{w}x{h}+{max(cx, 0)}+{max(cy, 0)}")
            except Exception:
                pass

        if master is not None:
            master.wait_window(self)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        disclaimer_text = _t("disclaimer_text")

        text_frame = ttk.Frame(self)
        text_frame.pack(fill="both", expand=True, padx=12, pady=(12, 4))

        text_widget = scrolledtext.ScrolledText(
            text_frame, wrap="word", height=18, font=("Consolas", 10)
        )
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", disclaimer_text)
        text_widget.configure(state="disabled")

        check_frame = ttk.Frame(self)
        check_frame.pack(fill="x", padx=12, pady=2)

        agree_chk = ttk.Checkbutton(
            check_frame,
            text=_t("agree_check"),
            variable=self._agree_var,
            command=self._on_agree_changed,
        )
        agree_chk.pack(anchor="w")

        dont_show_chk = ttk.Checkbutton(
            check_frame,
            text=_t("dont_show"),
            variable=self._dont_show_var,
        )
        dont_show_chk.pack(anchor="w")

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=12, pady=12)

        self._continue_btn = ttk.Button(
            btn_frame, text=_t("continue_btn"), command=self._on_continue, state="disabled"
        )
        self._continue_btn.pack(side="right", padx=4)

        exit_btn = ttk.Button(btn_frame, text=_t("exit_btn"), command=self._on_exit)
        exit_btn.pack(side="right", padx=4)

    def _on_agree_changed(self):
        if self._agree_var.get():
            self._continue_btn.configure(state="normal")
        else:
            self._continue_btn.configure(state="disabled")

    def _on_continue(self):
        if not self._agree_var.get():
            try:
                messagebox.showwarning(self.title(), _t("must_agree"))
            except Exception:
                pass
            return
        self.agreed = True
        self.dont_show_again = bool(self._dont_show_var.get())

        # 保存到 config.json
        try:
            cfg = load_config()
            cfg["disclaimer_agreed"] = self.dont_show_again
            save_config(cfg)
        except Exception:
            pass

        self.destroy()

    def _on_exit(self):
        self.agreed = False
        try:
            root = self.master
            if root is not None:
                root.destroy()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


# ============================================================================
# 主应用窗口
# ============================================================================

class App(tk.Tk):
    """抖音 / TikTok 批量下载器主窗口。"""

    def __init__(self):
        super().__init__()

        # 版本策略远程停用检查（硬阻挡会直接退出，软提示后续弹窗；任何失败均放行）
        try:
            import auto_updater
            auto_updater.enforce_version_policy("windows", auto_updater.CURRENT_VERSION)
        except SystemExit:
            raise
        except Exception:
            pass

        self.title(_t("app_title"))
        self.minsize(900, 680)
        self.geometry("1000x720")
        
        # 注入现代化 Fluent Design 主题
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")  # 启用暗黑模式
        except ImportError:
            pass

        # 核心状态
        self.cancel_event = threading.Event()
        self.download_thread = None
        self.log_queue = queue.Queue()
        self.is_downloading = False

        # 记录输出目录是否是用户自定义的
        self._output_dir_is_custom = False

        # 控件变量
        self._platform_var = tk.StringVar(value=_t("platform_douyin"))
        self._output_dir_var = tk.StringVar(value="")

        # 控件引用
        self._platform_combo = None
        self._links_text = None
        self._output_dir_entry = None
        self._action_btn = None
        self._open_dir_btn = None
        self._progress_bar = None
        self._progress_label = None
        self._log_text = None
        self._status_label = None

        self._build_ui()
        self._init_default_path()
        
        # 启动后静默检查更新
        try:
            import auto_updater
            # 延时 2 秒检查，避免阻塞主窗口渲染
            self.after(2000, lambda: auto_updater.check_for_updates(self, silent=True))
        except Exception:
            pass

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        pad = {"padx": 12, "pady": 4}

        # 平台选择行
        row1 = ttk.Frame(self)
        row1.pack(fill="x", **pad)
        ttk.Label(row1, text=_t("platform_label"), width=14).pack(side="left")
        self._platform_combo = ttk.Combobox(
            row1,
            textvariable=self._platform_var,
            values=[_t("platform_douyin"), _t("platform_tiktok")],
            state="readonly",
            width=20,
        )
        self._platform_combo.current(0)
        self._platform_combo.pack(side="left")
        self._platform_combo.bind("<<ComboboxSelected>>", self._on_platform_changed)

        # 链接输入行
        row2 = ttk.Frame(self)
        row2.pack(fill="both", expand=True, **pad)
        ttk.Label(row2, text=_t("links_label")).pack(anchor="w")
        self._links_text = tk.Text(row2, height=10, wrap="word")
        self._links_text.pack(fill="both", expand=True, pady=(4, 0))

        # 保存路径行
        row3 = ttk.Frame(self)
        row3.pack(fill="x", **pad)
        ttk.Label(row3, text=_t("path_label"), width=14).pack(side="left")
        self._output_dir_entry = ttk.Entry(row3, textvariable=self._output_dir_var, width=60)
        self._output_dir_entry.pack(side="left", fill="x", expand=True)
        browse_btn = ttk.Button(row3, text=_t("browse_btn"), command=self._on_browse)
        browse_btn.pack(side="left", padx=(8, 0))

        # 按钮行
        row4 = ttk.Frame(self)
        row4.pack(fill="x", **pad)
        self._action_btn = ttk.Button(row4, text=_t("start_btn"), command=self._on_action_clicked)
        self._action_btn.pack(side="left")
        self._open_dir_btn = ttk.Button(row4, text=_t("open_dir_btn"), command=self._on_open_dir)
        self._open_dir_btn.pack(side="left", padx=(8, 0))
        
        self._about_btn = ttk.Button(row4, text=_t("about_title"), command=self._show_about)
        self._about_btn.pack(side="right")
        
        def _toggle_lang():
            cfg = load_config()
            new_lang = "en" if cfg.get("lang", "zh") == "zh" else "zh"
            cfg["lang"] = new_lang
            save_config(cfg)
            if messagebox.askyesno(_t("language_restart_title"), _t("language_restart_message"), parent=self):
                self.destroy()
                import os
                import sys
                os.execl(sys.executable, sys.executable, *sys.argv)
                
        self._lang_btn = ttk.Button(row4, text=_t("language_button"), command=_toggle_lang)
        self._lang_btn.pack(side="right", padx=(0, 8))

        # 进度条行
        row5 = ttk.Frame(self)
        row5.pack(fill="x", **pad)
        self._progress_bar = ttk.Progressbar(row5, mode="determinate", maximum=100, value=0)
        self._progress_bar.pack(side="left", fill="x", expand=True)
        self._progress_label = ttk.Label(row5, text="0/0", width=10, anchor="e")
        self._progress_label.pack(side="left", padx=(8, 0))

        # 日志窗口
        row6 = ttk.Frame(self)
        row6.pack(fill="both", expand=True, **pad)
        self._log_text = scrolledtext.ScrolledText(row6, state="disabled", height=20, wrap="word")
        self._log_text.tag_configure("info")  # 默认前景
        self._log_text.tag_configure("warning", foreground="orange")
        self._log_text.tag_configure("error", foreground="red")
        self._log_text.pack(fill="both", expand=True)

        # ------------------- 注册右键菜单 -------------------
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="剪切 / Cut", command=lambda: self.focus_get().event_generate("<<Cut>>"))
        self._context_menu.add_command(label="复制 / Copy", command=lambda: self.focus_get().event_generate("<<Copy>>"))
        self._context_menu.add_command(label="粘贴 / Paste", command=lambda: self.focus_get().event_generate("<<Paste>>"))
        self._context_menu.add_separator()
        self._context_menu.add_command(label="全选 / Select All", command=lambda: self.focus_get().event_generate("<<SelectAll>>"))

        def _show_context_menu(event):
            widget = event.widget
            if widget.winfo_class() in ("Entry", "TEntry", "Text", "ScrolledText"):
                widget.focus_set()
                self._context_menu.tk_popup(event.x_root, event.y_root)

        self.bind_class("Text", "<Button-3>", _show_context_menu)
        self.bind_class("Entry", "<Button-3>", _show_context_menu)
        self.bind_class("TEntry", "<Button-3>", _show_context_menu)
        self.bind_class("ScrolledText", "<Button-3>", _show_context_menu)

        # 状态栏
        self._status_label = ttk.Label(self, text=_t("status_ready"), anchor="w", relief="sunken")
        self._status_label.pack(fill="x", side="bottom")

    def _init_default_path(self):
        """根据上次保存或默认路径初始化输出目录。"""
        try:
            cfg = load_config()
            last = cfg.get("last_output_dir", "")
            if last:
                self._output_dir_var.set(last)
                self._output_dir_is_custom = True
                return
        except Exception:
            pass
        platform = self._current_platform()
        default_path = get_default_output_dir(platform)
        self._output_dir_var.set(default_path)
        self._output_dir_is_custom = False

    def _current_platform(self) -> str:
        value = self._platform_var.get()
        if value == _t("platform_tiktok"):
            return "tiktok"
        return "douyin"

    def _show_about(self):
        try:
            import auto_updater
            version = auto_updater.CURRENT_VERSION
        except ImportError:
            version = "v1.7.0"
            
        import webbrowser
        about_win = tk.Toplevel(self)
        about_win.title(_t("about_title"))
        about_win.geometry("350x280")
        about_win.resizable(False, False)
        about_win.transient(self)
        about_win.grab_set()

        # 居中
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 350) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 280) // 2
        about_win.geometry(f"+{max(0, x)}+{max(0, y)}")

        ttk.Label(about_win, text="MediaDownloader", font=("", 16, "bold")).pack(pady=(20, 5))
        ttk.Label(about_win, text=_t("about_version", version=version)).pack(pady=2)
        ttk.Label(about_win, text=_t("about_description")).pack(pady=(10, 2))

        # 仓库链接
        repo_link = ttk.Label(about_win, text=_t("project_home"), foreground="#58a6ff", cursor="hand2")
        repo_link.pack(pady=4)
        repo_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Francis-Xavier-code/tiktok-douyin-dl"))

        # 作者链接
        author_link = ttk.Label(about_win, text=_t("author"), foreground="#58a6ff", cursor="hand2")
        author_link.pack(pady=4)
        author_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Xynrin"))

        def _do_update():
            about_win.destroy()
            try:
                import auto_updater
                auto_updater.check_for_updates(self, silent=False)
            except ImportError:
                messagebox.showerror(_t("app_title"), _t("update_module_missing"), parent=self)

        ttk.Button(about_win, text=_t("check_update"), command=_do_update).pack(pady=(20, 10))

    # ------------------------------------------------------------------ 事件处理


    def _on_platform_changed(self, _event=None):
        """切换平台时，若当前输出目录为默认的则跟着切换。"""
        try:
            platform = self._current_platform()
            default_path = get_default_output_dir(platform)
            current = self._output_dir_var.get().strip()
            # 判断当前目录是否为默认目录（douyin_downloads 或 tiktok_downloads）
            is_default = False
            try:
                if current == "":
                    is_default = True
                else:
                    norm_cur = os.path.normpath(current)
                    norm_default = os.path.normpath(default_path)
                    # 如果当前目录是任一默认形式，则视为默认
                    for p in (
                        get_default_output_dir("douyin"),
                        get_default_output_dir("tiktok"),
                    ):
                        if os.path.normpath(p) == norm_cur:
                            is_default = True
                            break
                    if not is_default and not self._output_dir_is_custom:
                        is_default = True
            except Exception:
                is_default = not self._output_dir_is_custom

            if is_default:
                self._output_dir_var.set(default_path)
                self._output_dir_is_custom = False
        except Exception:
            pass

    def _on_browse(self):
        try:
            current = self._output_dir_var.get().strip()
            platform = self._current_platform()
            initial = current if current else get_default_output_dir(platform)
            try:
                if not os.path.isdir(initial):
                    initial = os.path.expanduser("~")
            except Exception:
                initial = os.path.expanduser("~")

            chosen = filedialog.askdirectory(
                title=_t("browse_title"),
                initialdir=initial,
            )
            if chosen:
                self._output_dir_var.set(chosen)
                self._output_dir_is_custom = True
                try:
                    cfg = load_config()
                    cfg["last_output_dir"] = chosen
                    save_config(cfg)
                except Exception:
                    pass
        except Exception as e:
            try:
                messagebox.showerror(_t("app_title"), str(e))
            except Exception:
                pass

    def _on_open_dir(self):
        try:
            path = self._output_dir_var.get().strip()
            if not path:
                platform = self._current_platform()
                path = get_default_output_dir(platform)
                self._log_append("warning", _t("empty_path", path=path))
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                self._log_append("error", _t("open_dir_error", error=str(e)))
                return
            if not os.path.isdir(path):
                self._log_append("error", _t("open_dir_error", error="not a directory"))
                return
            try:
                if os.name == "nt":
                    os.startfile(path)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    import subprocess
                    subprocess.Popen(["open", path])
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", path])
            except Exception as e:
                self._log_append("error", _t("open_dir_error", error=str(e)))
        except Exception as e:
            try:
                self._log_append("error", _t("open_dir_error", error=str(e)))
            except Exception:
                pass

    def _on_action_clicked(self):
        if self.is_downloading:
            # 取消下载
            try:
                self.cancel_event.set()
                self._log_append("warning", _t("cancel_log"))
                self._action_btn.configure(state="disabled")
            except Exception:
                pass
            return

        # 开始下载
        try:
            platform = self._current_platform()
            raw_text = self._links_text.get("1.0", "end-1c")
            output_dir = self._output_dir_var.get().strip()
            if not output_dir:
                output_dir = get_default_output_dir(platform)
                self._output_dir_var.set(output_dir)
                self._log_append("warning", _t("empty_path", path=output_dir))
            else:
                # 用户已修改目录，保存到配置
                try:
                    cfg = load_config()
                    cfg["last_output_dir"] = output_dir
                    save_config(cfg)
                except Exception:
                    pass

            self.cancel_event.clear()
            self._action_btn.configure(text=_t("cancel_btn"), state="normal")
            self._clear_log()
            self._progress_bar.configure(value=0, maximum=100)
            self._progress_label.configure(text="0/0")
            self._status_label.configure(text=_t("status_downloading"))
            self.is_downloading = True

            try:
                self.download_thread = start_download_thread(
                    platform, raw_text, output_dir, self.log_queue, self.cancel_event
                )
            except Exception as e:
                self._log_append("error", str(e))
                self.is_downloading = False
                self._action_btn.configure(text=_t("start_btn"), state="normal")
                self._status_label.configure(text=_t("status_ready"))
                return

            self.after(120, self._poll_queue)
        except Exception as e:
            try:
                messagebox.showerror(_t("app_title"), str(e))
            except Exception:
                pass
            self.is_downloading = False
            try:
                self._action_btn.configure(text=_t("start_btn"), state="normal")
            except Exception:
                pass

    # ------------------------------------------------------------------ 轮询 / 日志

    def _poll_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                self._handle_queue_item(item)
        except queue.Empty:
            pass
        except Exception:
            pass

        if self.is_downloading:
            try:
                self.after(120, self._poll_queue)
            except Exception:
                pass

    def _handle_queue_item(self, item):
        try:
            if not isinstance(item, (tuple, list)) or len(item) < 1:
                return
            msg_type = item[0]
            if msg_type == "log" and len(item) >= 3:
                level = item[1] if item[1] in ("info", "warning", "error") else "info"
                text = str(item[2])
                self._log_append(level, text)
            elif msg_type == "progress" and len(item) >= 3:
                current = int(item[1]) if isinstance(item[1], (int, float)) else 0
                total = int(item[2]) if isinstance(item[2], (int, float)) else 0
                try:
                    if total > 0:
                        self._progress_bar.configure(maximum=total, value=current)
                    else:
                        self._progress_bar.configure(value=0)
                except Exception:
                    pass
                try:
                    self._progress_label.configure(text=f"{current}/{total}")
                except Exception:
                    pass
            elif msg_type == "done":
                info = item[1] if len(item) > 1 and isinstance(item[1], dict) else {}
                success = int(info.get("success", 0) or 0)
                fail = int(info.get("fail", 0) or 0)
                cancelled = bool(info.get("cancelled", False))
                actual_path = info.get("path", "")
                self.is_downloading = False
                # 若实际使用的路径与界面不一致（回退到临时目录），同步更新 Entry
                try:
                    current = self._output_dir_var.get().strip()
                    if actual_path and os.path.normpath(actual_path) != os.path.normpath(current or ""):
                        self._output_dir_var.set(actual_path)
                        self._output_dir_is_custom = True
                        try:
                            cfg = load_config()
                            cfg["last_output_dir"] = actual_path
                            save_config(cfg)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    self._action_btn.configure(text=_t("start_btn"), state="normal")
                except Exception:
                    pass
                if cancelled:
                    status_text = _t("status_cancelled")
                else:
                    status_text = _t("status_done", ok=success, fail=fail)
                try:
                    self._status_label.configure(text=status_text)
                except Exception:
                    pass
                try:
                    self._log_append("info", status_text)
                except Exception:
                    pass
        except Exception:
            pass

    def _log_append(self, level: str, text: str):
        try:
            if not self._log_text:
                return
            self._log_text.configure(state="normal")
            self._log_text.insert("end", text + "\n", level)
            self._log_text.configure(state="disabled")
            self._log_text.see("end")
        except Exception:
            pass

    def _clear_log(self):
        try:
            if not self._log_text:
                return
            self._log_text.configure(state="normal")
            self._log_text.delete("1.0", "end")
            self._log_text.configure(state="disabled")
        except Exception:
            pass


# ============================================================================
# 启动入口
# ============================================================================

if __name__ == "__main__":
    try:
        app = App()
    except Exception as e:
        try:
            messagebox.showerror("Error", str(e))
        except Exception:
            print(f"[ERROR] Failed to start GUI: {e}")
        sys.exit(1)

    try:
        cfg = load_config()
        already_agreed = bool(cfg.get("disclaimer_agreed", False))
    except Exception:
        already_agreed = False

    if not already_agreed:
        try:
            dialog = DisclaimerDialog(app)
            if not dialog.agreed:
                try:
                    app.destroy()
                except Exception:
                    pass
                sys.exit(0)
        except SystemExit:
            raise
        except Exception as e:
            try:
                messagebox.showerror(_t("app_title"), str(e))
            except Exception:
                pass
            try:
                app.destroy()
            except Exception:
                pass
            sys.exit(1)

    try:
        app.mainloop()
    except Exception as e:
        try:
            messagebox.showerror(_t("app_title"), str(e))
        except Exception:
            print(f"[ERROR] {e}")
