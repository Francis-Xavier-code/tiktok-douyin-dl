"""Gradio WebUI adapter for NAS and server deployments."""

import os
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "python" / "src"
if SOURCE_ROOT.is_dir() and str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright")

try:
    import gradio as gr
except ImportError:
    print("请先安装 WebUI 依赖: pip install -e './python[web]'")
    raise SystemExit(1)

from media_downloader.core.download_policy import check_download_allowed
from media_downloader.platforms.douyin import download_douyin_links
from media_downloader.platforms.tiktok import download_tiktok_links

OUTPUT_DIR = os.environ.get("DOWNLOAD_DIR", "/downloads")

# 可选鉴权：设置 GRADIO_AUTH_USER / GRADIO_AUTH_PASS 后，WebUI 需要登录才能使用。
_AUTH_USER = os.environ.get("GRADIO_AUTH_USER", "")
_AUTH_PASS = os.environ.get("GRADIO_AUTH_PASS", "")
_AUTH = (("admin", _AUTH_PASS),) if _AUTH_USER == "admin" else None
if _AUTH_USER and _AUTH_USER != "admin":
    _AUTH = ((_AUTH_USER, _AUTH_PASS),)


def start_download(platform: str, text: str) -> str:
    if not text.strip():
        return "❌ 请输入链接"

    # 下载策略闸门（fail-closed，Ed25519 验签）：策略不可达/无效时拒绝下载。
    decision = check_download_allowed(silent=True)
    if decision.is_block:
        return f"❌ 下载已暂停：{decision.message}"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    links = [line.strip() for line in text.splitlines() if line.strip()]

    try:
        if platform == "Douyin (抖音)":
            download_douyin_links(links, OUTPUT_DIR)
        else:
            download_tiktok_links(links, OUTPUT_DIR)
        return f"✅ 下载完成！\n文件已保存至: {OUTPUT_DIR}"
    except Exception as error:
        return f"❌ 下载失败: {error}"


with gr.Blocks(title="MediaDownloader WebUI", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 MediaDownloader WebUI\n粘贴抖音或 TikTok 分享链接即可下载媒体。")
    platform_radio = gr.Radio(
        ["Douyin (抖音)", "TikTok"],
        label="选择平台",
        value="Douyin (抖音)",
    )
    links_input = gr.Textbox(label="分享文本或链接", lines=5)
    download_btn = gr.Button("🚀 立即提取下载", variant="primary")
    status_output = gr.Textbox(label="运行状态", interactive=False)
    download_btn.click(
        fn=start_download,
        inputs=[platform_radio, links_input],
        outputs=status_output,
    )


if __name__ == "__main__":
    print(f"[*] WebUI 下载目录: {OUTPUT_DIR}")
    if _AUTH:
        print("[*] 已启用 HTTP Basic 鉴权（GRADIO_AUTH_USER / GRADIO_AUTH_PASS）")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, auth=_AUTH)
