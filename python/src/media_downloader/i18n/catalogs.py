"""Built-in translations used by source and frozen application builds."""

_ZH_DISCLAIMER = (
    "本工具仅供个人学习、研究和合法的内容备份使用。请仅下载你拥有权利或已获得授权的内容，"
    "遵守所在地法律、平台服务条款及著作权规定。严禁将本工具用于商业侵权、非法抓取、绕过访问控制或网络攻击。"
    "使用本工具产生的版权、账号和数据安全风险由使用者自行承担。"
)
_EN_DISCLAIMER = (
    "This tool is provided only for personal study, research, and lawful backups. Download only content you own or are authorized to use, "
    "and comply with applicable law, platform terms, and copyright rules. Do not use it for infringement, unauthorized scraping, access-control bypasses, or attacks. "
    "You are responsible for copyright, account, and data-security consequences arising from its use."
)


def _cli_common(disclaimer: str, english: bool) -> dict:
    if english:
        return {
            "browser_install_success": "Chromium is ready.",
            "browser_not_found": "Playwright Chromium was not found; installing it now.",
            "browser_install_failed": "Chromium installation failed (exit code {code}).",
            "changelog_title": "Release notes",
            "disclaimer_agree": "Type y to accept and continue: ",
            "disclaimer_declined": "You did not accept the disclaimer.",
            "disclaimer_text": disclaimer,
            "disclaimer_title": "Disclaimer",
            "download_done": "Finished: {success} succeeded, {fail} failed.",
            "download_failed": "Download failed: {err}",
            "download_success": "Saved {filename} ({size}, {resolution}).",
            "exited_safely": "Exited safely.",
            "input_prompt": "Paste share text or a URL: ",
            "legal_warning": "Use only for lawful, authorized downloads.",
            "no_links": "No supported links were found.",
            "parse_failed": "Could not parse the page: {err}",
            "save_dir_info": "Saving to: {path}",
            "save_dir_prompt": "Output directory [{default_dir}]: ",
            "source_mode_update_skipped": "Automatic replacement is available only in packaged builds.",
            "update_changelog_unavailable": "Release notes are unavailable.",
            "update_confirm": "Install the update now? [y/N]: ",
            "update_downloading": "Downloading update...",
            "update_failed": "Update check failed: {err}",
            "update_failed_install": "Update installation failed: {error}",
            "update_found": "Version {latest_version} is available (current: {version}).",
            "update_hint": "Run the installer again to update {cmd}.",
            "update_success": "Update installed.",
            "policy_release_url": "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest",
            "policy_block_header": "This version is no longer supported.",
            "policy_nag_header": "A newer version is recommended.",
            "policy_min_version": "Minimum supported version: {min_version}.",
            "policy_update_link": "Download the latest version: {url}",
            "policy_update_required": "Your version is out of date. Please update to the latest release.",
            "policy_issue_url": "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/issues",
            "policy_issue_hint": "If this looks wrong, please file an issue: {url}",
            "download_blocked_header": "Download is currently unavailable.",
            "download_policy_unreachable": "Could not reach the download policy server (all sources failed). Downloads are disabled until connectivity is restored.",
            "download_policy_disabled": "Downloads are temporarily disabled by the maintainer. Please check the project page for status.",
            "download_policy_min_version": "Downloads require version {min_version} or newer.",
        }
    return {
            "browser_install_success": "Chromium 浏览器已就绪。",
            "browser_not_found": "未找到 Playwright Chromium，正在安装。",
            "browser_install_failed": "Chromium 安装失败（退出代码 {code}）。",
            "changelog_title": "更新说明",
        "disclaimer_agree": "输入 y 表示同意并继续：",
        "disclaimer_declined": "你未同意免责声明。",
        "disclaimer_text": disclaimer,
        "disclaimer_title": "免责声明",
        "download_done": "处理完成：成功 {success} 个，失败 {fail} 个。",
        "download_failed": "下载失败：{err}",
        "download_success": "已保存 {filename}（{size}，{resolution}）。",
        "exited_safely": "已安全退出。",
        "input_prompt": "请粘贴分享文本或链接：",
        "legal_warning": "请仅下载合法且已获授权的内容。",
        "no_links": "未找到支持的链接。",
        "parse_failed": "页面解析失败：{err}",
        "save_dir_info": "保存目录：{path}",
        "save_dir_prompt": "输出目录 [{default_dir}]：",
        "source_mode_update_skipped": "自动替换仅适用于打包后的程序。",
        "update_changelog_unavailable": "暂无更新说明。",
        "update_confirm": "现在安装更新吗？[y/N]：",
        "update_downloading": "正在下载更新……",
        "update_failed": "检查更新失败：{err}",
        "update_failed_install": "安装更新失败：{error}",
        "update_found": "发现版本 {latest_version}（当前版本：{version}）。",
        "update_hint": "请重新运行安装器更新 {cmd}。",
        "update_success": "更新安装完成。",
            "policy_release_url": "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/releases/latest",
            "policy_block_header": "当前版本已停止支持。",
            "policy_nag_header": "建议使用更新的版本。",
            "policy_min_version": "最低支持版本：{min_version}。",
            "policy_update_link": "下载最新版本：{url}",
            "policy_update_required": "你的版本已过时，请升级到最新版本。",
            "policy_issue_url": "https://github.com/Francis-Xavier-code/tiktok-douyin-dl/issues",
            "policy_issue_hint": "若认为有误，请前往反馈：{url}",
            "download_blocked_header": "下载功能当前不可用。",
            "download_policy_unreachable": "无法连接到下载策略服务（所有源均失败）。在恢复连接前已暂停下载功能。",
            "download_policy_disabled": "维护者已临时关闭下载功能，请关注项目主页了解状态。",
            "download_policy_min_version": "下载功能需要 {min_version} 及以上版本。",
    }


def _gui(disclaimer: str, english: bool) -> dict:
    if english:
        ui = {
            "about_description": "Download Douyin and TikTok media from one desktop app.",
            "about_title": "About MediaDownloader",
            "about_version": "Version {version}",
            "agree_check": "I have read and accept the disclaimer",
            "app_title": "MediaDownloader",
            "author": "Open-source contributors",
            "browse_btn": "Browse",
            "browse_title": "Choose output directory",
            "cancel_btn": "Cancel",
            "cancel_log": "Cancellation requested...",
            "check_update": "Check for updates",
            "continue_btn": "Continue",
            "disclaimer_text": disclaimer,
            "disclaimer_title": "Disclaimer",
            "dont_show": "Do not show again",
            "empty_path": "Output path is empty: {path}",
            "exit_btn": "Exit",
            "language_button": "中文",
            "language_restart_message": "Restart the app to apply the new language.",
            "language_restart_title": "Language changed",
            "links_label": "Share text or links",
            "must_agree": "Accept the disclaimer before continuing.",
            "open_dir_btn": "Open folder",
            "open_dir_error": "Could not open the folder: {error}",
            "path_label": "Output directory",
            "platform_douyin": "Douyin",
            "platform_label": "Platform",
            "platform_tiktok": "TikTok",
            "project_home": "Project home",
            "start_btn": "Start download",
            "status_cancelled": "Cancelled",
            "status_done": "Done: {ok} succeeded, {fail} failed",
            "status_downloading": "Downloading...",
            "status_ready": "Ready",
            "update_module_missing": "The updater module is unavailable.",
        }
        run = {
            "browser_initializing": "Initializing browser...",
            "browser_install_failed": "Browser installation failed: {error}",
            "browser_install_hint": "Run: python -m playwright install chromium",
            "browser_launch_failed": "Browser launch failed: {error}",
            "browser_ready": "Browser ready.",
            "cancelled_summary": "Cancelled: {success} succeeded, {failed} failed.",
            "change_directory_hint": "Choose another writable output directory and retry.",
            "download_error": "[{current}/{total}] Download failed: {error}",
            "error_prefix": "Error",
            "fallback_directory": "Could not use {orig}; using {fallback} instead.",
            "found_links": "Found {count} link(s).",
            "no_links": "No supported links found.",
            "no_links_hint": "Paste a complete Douyin or TikTok share link.",
            "path_info": "Output: {path}",
            "saved_to": "Saved to {path}",
            "url_parse_failed": "URL parsing failed: {error}",
        }
    else:
        ui = {
            "about_description": "在一个桌面应用中下载抖音和 TikTok 媒体。",
            "about_title": "关于 MediaDownloader",
            "about_version": "版本 {version}",
            "agree_check": "我已阅读并同意免责声明",
            "app_title": "MediaDownloader",
            "author": "开源项目贡献者",
            "browse_btn": "浏览",
            "browse_title": "选择输出目录",
            "cancel_btn": "取消",
            "cancel_log": "正在取消……",
            "check_update": "检查更新",
            "continue_btn": "继续",
            "disclaimer_text": disclaimer,
            "disclaimer_title": "免责声明",
            "dont_show": "不再显示",
            "empty_path": "输出路径为空：{path}",
            "exit_btn": "退出",
            "language_button": "English",
            "language_restart_message": "重启应用后语言设置生效。",
            "language_restart_title": "语言已切换",
            "links_label": "分享文本或链接",
            "must_agree": "请先同意免责声明。",
            "open_dir_btn": "打开文件夹",
            "open_dir_error": "无法打开文件夹：{error}",
            "path_label": "输出目录",
            "platform_douyin": "抖音",
            "platform_label": "平台",
            "platform_tiktok": "TikTok",
            "project_home": "项目主页",
            "start_btn": "开始下载",
            "status_cancelled": "已取消",
            "status_done": "完成：成功 {ok} 个，失败 {fail} 个",
            "status_downloading": "下载中……",
            "status_ready": "就绪",
            "update_module_missing": "更新模块不可用。",
        }
        run = {
            "browser_initializing": "正在初始化浏览器……",
            "browser_install_failed": "浏览器安装失败：{error}",
            "browser_install_hint": "请运行：python -m playwright install chromium",
            "browser_launch_failed": "浏览器启动失败：{error}",
            "browser_ready": "浏览器已就绪。",
            "cancelled_summary": "已取消：成功 {success} 个，失败 {failed} 个。",
            "change_directory_hint": "请选择其他可写目录后重试。",
            "download_error": "[{current}/{total}] 下载失败：{error}",
            "error_prefix": "错误",
            "fallback_directory": "无法使用 {orig}，已改用 {fallback}。",
            "found_links": "找到 {count} 个链接。",
            "no_links": "未找到支持的链接。",
            "no_links_hint": "请粘贴完整的抖音或 TikTok 分享链接。",
            "path_info": "输出目录：{path}",
            "saved_to": "已保存至 {path}",
            "url_parse_failed": "链接解析失败：{error}",
        }
    return {"ui": ui, "run": run}


def _catalog(disclaimer: str, english: bool) -> dict:
    common = _cli_common(disclaimer, english)
    if english:
        douyin = {
            "browser_install_failed": "Chromium installation failed (exit code {code}).",
            "image_found": "Found {count} image(s): {title} ({id}).",
            "parsing": "Parsing Douyin page...",
            "title_banner": "Douyin media downloader",
            "video_found": "Found video: {title} ({id}).",
        }
        tiktok = {
            "image_found": "Found {count} image(s): {title} ({id}).",
            "parsing": "Parsing TikTok page...",
            "title_banner": "TikTok media downloader",
            "video_found": "Found video: {title} ({id}).",
        }
    else:
        douyin = {
            "browser_install_failed": "Chromium 安装失败（退出代码 {code}）。",
            "image_found": "发现 {count} 张图片：{title}（{id}）。",
            "parsing": "正在解析抖音页面……",
            "title_banner": "抖音媒体下载器",
            "video_found": "发现视频：{title}（{id}）。",
        }
        tiktok = {
            "image_found": "发现 {count} 张图片：{title}（{id}）。",
            "parsing": "正在解析 TikTok 页面……",
            "title_banner": "TikTok 媒体下载器",
            "video_found": "发现视频：{title}（{id}）。",
        }
    return {"cli": {"common": common, "douyin": douyin, "tiktok": tiktok}, "gui": _gui(disclaimer, english)}


CATALOGS = {
    "zh": _catalog(_ZH_DISCLAIMER, False),
    "en": _catalog(_EN_DISCLAIMER, True),
}
