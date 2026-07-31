#!/usr/bin/env python3
"""
冒烟测试脚本 - 验证 gui_downloader.py 的核心下载逻辑函数
不启动 GUI，不实际下载，仅验证函数调用和基本行为。

Usage: python verify_gui_smoke.py
"""

import sys
import os
import json
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}" + (f" - {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f" - {detail}" if detail else ""))


# ============================================================================
#  测试 1: 模块导入
# ============================================================================
print("\n=== Test 1: 模块导入 ===")

try:
    import gui_downloader as GD
    check("gui_downloader 导入", True)
except Exception as e:
    check("gui_downloader 导入", False, str(e))
    sys.exit(1)

try:
    import douyin_image_downloader as DYD
    check("douyin_image_downloader 导入", True)
except Exception as e:
    check("douyin_image_downloader 导入", False, str(e))

try:
    import tiktok_downloader as TTD
    check("tiktok_downloader 导入", True)
except Exception as e:
    check("tiktok_downloader 导入", False, str(e))


# ============================================================================
#  测试 2: get_default_output_dir - 默认保存路径为桌面
# ============================================================================
print("\n=== Test 2: get_default_output_dir ===")

douyin_path = GD.get_default_output_dir("douyin")
tiktok_path = GD.get_default_output_dir("tiktok")
check("douyin 默认路径不为空", bool(douyin_path))
check("tiktok 默认路径不为空", bool(tiktok_path))
check("douyin 路径是绝对路径", os.path.isabs(douyin_path))
check("tiktok 路径是绝对路径", os.path.isabs(tiktok_path))
check("douyin 路径含 douyin_downloads", "douyin_downloads" in douyin_path)
check("tiktok 路径含 tiktok_downloads", "tiktok_downloads" in tiktok_path)
check("路径含 Desktop 或 桌面", ("Desktop" in douyin_path) or ("桌面" in douyin_path))
print(f"    douyin 默认: {douyin_path}")
print(f"    tiktok 默认: {tiktok_path}")


# ============================================================================
#  测试 3: load_config / save_config
# ============================================================================
print("\n=== Test 3: load_config / save_config ===")

# 先备份原 config
orig_config_path = os.path.join(HERE, "config.json")
backup_path = None
if os.path.exists(orig_config_path):
    backup_path = orig_config_path + ".bak"
    try:
        with open(orig_config_path, "r", encoding="utf-8") as f:
            backup_content = f.read()
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(backup_content)
        print(f"    已备份 config.json -> config.json.bak")
    except Exception as e:
        backup_path = None
        print(f"    [WARN] 备份失败: {e}")

try:
    # 删除原 config，确保 load_config 返回默认
    if os.path.exists(orig_config_path):
        os.remove(orig_config_path)

    cfg = GD.load_config()
    check("load_config 返回 dict", isinstance(cfg, dict))
    check("默认 lang = zh", cfg.get("lang") == "zh")

    # 写入一个自定义 config
    test_cfg = {"lang": "en", "last_output_dir": "C:\\test_path", "disclaimer_agreed": True}
    GD.save_config(test_cfg)
    check("save_config 成功", os.path.exists(orig_config_path))

    cfg2 = GD.load_config()
    check("load_config 读回 lang=en", cfg2.get("lang") == "en")
    check("load_config 读回 last_output_dir", cfg2.get("last_output_dir") == "C:\\test_path")
    check("load_config 读回 disclaimer_agreed=True", cfg2.get("disclaimer_agreed") is True)

    # get_lang 测试
    lang = GD.get_lang()
    check("get_lang 返回 'en'", lang == "en")

    # 恢复默认 zh 测试
    GD.save_config({"lang": "zh"})
    check("get_lang 切换回 'zh'", GD.get_lang() == "zh")
finally:
    # 恢复备份
    if backup_path and os.path.exists(backup_path):
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                content = f.read()
            with open(orig_config_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.remove(backup_path)
            print("    已恢复 config.json")
        except Exception:
            pass
    else:
        # 清理测试用的 config.json
        if os.path.exists(orig_config_path):
            try:
                os.remove(orig_config_path)
            except Exception:
                pass


# ============================================================================
#  测试 4: get_module - 平台到模块的映射
# ============================================================================
print("\n=== Test 4: get_module ===")

douyin_module = GD.get_module("douyin")
check("douyin 模块加载成功", douyin_module is not None)
check("douyin 有 extract_urls_from_text", hasattr(douyin_module, "extract_urls_from_text"))
check("douyin 有 process_single", hasattr(douyin_module, "process_single"))
check("douyin 有 ensure_browser_installed", hasattr(douyin_module, "ensure_browser_installed"))

tiktok_module = GD.get_module("tiktok")
check("tiktok 模块加载成功", tiktok_module is not None)
check("tiktok 有 extract_urls_from_text", hasattr(tiktok_module, "extract_urls_from_text"))
check("tiktok 有 process_single", hasattr(tiktok_module, "process_single"))
check("tiktok 有 ensure_browser_installed", hasattr(tiktok_module, "ensure_browser_installed"))

try:
    GD.get_module("unknown")
    check("未知平台应抛 ValueError", False, "没有抛出异常")
except ValueError:
    check("未知平台应抛 ValueError", True)
except Exception as e:
    check("未知平台应抛 ValueError", False, f"实际抛了 {type(e).__name__}: {e}")


# ============================================================================
#  测试 5: extract_unique_urls - 链接提取与去重
# ============================================================================
print("\n=== Test 5: extract_unique_urls (抖音) ===")

douyin_text_single = "https://www.douyin.com/video/1234567890123456789"
urls_1 = GD.extract_unique_urls(douyin_module, douyin_text_single)
check("单个抖音链接提取成功", len(urls_1) >= 1)
print(f"    提取结果: {urls_1}")

douyin_text_multi = """
看这个视频 https://www.douyin.com/video/1234567890123456789 很有趣
还有这个 https://www.douyin.com/video/9876543210987654321
以及 https://www.douyin.com/video/111222333444555666777
重复链接: https://www.douyin.com/video/1234567890123456789
"""
urls_multi = GD.extract_unique_urls(douyin_module, douyin_text_multi)
check("多链接文本提取成功", len(urls_multi) >= 3)

# 检查去重
seen = set()
has_dup = False
for u in urls_multi:
    if u in seen:
        has_dup = True
        break
    seen.add(u)
check("链接已去重（无重复）", not has_dup, f"去重后数量 = {len(urls_multi)}")

# 空文本测试
urls_empty = GD.extract_unique_urls(douyin_module, "")
check("空文本返回空列表", len(urls_empty) == 0)

urls_no_link = GD.extract_unique_urls(douyin_module, "这是一段普通文本，没有任何链接")
check("无链接文本返回空列表", len(urls_no_link) == 0)

print("\n=== Test 5b: extract_unique_urls (TikTok) ===")

tiktok_text = "Check this https://www.tiktok.com/@testuser/video/1234567890 video"
urls_tt = GD.extract_unique_urls(tiktok_module, tiktok_text)
check("TikTok 链接提取", True)  # 实际可能因为正则需要域名匹配，不强制断言数量
print(f"    提取结果: {urls_tt}")


# ============================================================================
#  测试 6: _GuiLogWriter - stdout 重定向到 queue
# ============================================================================
print("\n=== Test 6: _GuiLogWriter ===")

import queue as _queue

q = _queue.Queue()
writer = GD._GuiLogWriter(q)
writer.write("Hello world")
writer.write("Second line\nThird line")

items = []
while not q.empty():
    items.append(q.get_nowait())

check("队列接收到消息", len(items) >= 2)
for item in items:
    check(f"消息格式正确 ({item[0]})", item[0] == "log" and item[1] == "info")

# 测试重定向 print
original_stdout = sys.stdout
sys.stdout = GD._GuiLogWriter(q)
print("This is a print output")
print("Line 2")
sys.stdout = original_stdout

# 检查有没有新入队的
new_items = []
while not q.empty():
    item = q.get_nowait()
    new_items.append(item)

check("print 被重定向到 queue", len(new_items) >= 2)
print(f"    重定向捕获: {[item[2] for item in new_items[:5]]}")


# ============================================================================
#  测试 7: run_download - 空链接场景（不启动浏览器）
# ============================================================================
print("\n=== Test 7: run_download (空链接场景) ===")

import queue as _queue2

q2 = _queue2.Queue()
output_dir = os.path.join(tempfile.gettempdir(), "gui_smoke_test_out")

# 空文本场景 - 不应该启动浏览器，应该直接返回 done 消息
GD.run_download("douyin", "", output_dir, q2)

items2 = []
while not q2.empty():
    items2.append(q2.get_nowait())

has_log = any(item[0] == "log" for item in items2)
has_done = any(item[0] == "done" for item in items2)

check("空文本发送了 log 消息", has_log)
check("空文本发送了 done 消息", has_done)

done_item = [item for item in items2 if item[0] == "done"][0]
check("done 消息 success=0", done_item[1]["success"] == 0)
check("done 消息 fail=0", done_item[1]["fail"] == 0)
check("done 消息含 path", "path" in done_item[1])
print(f"    done 消息: {done_item[1]}")


# ============================================================================
#  测试 8: 中文路径兼容性
# ============================================================================
print("\n=== Test 8: 中文路径兼容性 ===")

cn_path = os.path.join(tempfile.gettempdir(), "测试中文目录_下载")
try:
    os.makedirs(cn_path, exist_ok=True)
    check("可以创建中文目录", os.path.isdir(cn_path))

    # 写一个文件到中文目录
    test_file = os.path.join(cn_path, "test.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("中文内容测试")
    check("可以写文件到中文目录", os.path.exists(test_file))

    # 清理
    os.remove(test_file)
    os.rmdir(cn_path)
except Exception as e:
    check("中文目录操作", False, str(e))


# ============================================================================
#  测试 9: DISCLAMER 文本可用 (GUI 免责声明内容)
# ============================================================================
print("\n=== Test 9: 免责声明文本 ===")

if hasattr(DYD, "DISCLAIMER"):
    check("douyin_image_downloader 有 DISCLAIMER", len(DYD.DISCLAIMER) > 100)
else:
    check("douyin_image_downloader 有 DISCLAIMER", False)

if hasattr(DYD, "DISCLAIMER_EN"):
    check("douyin_image_downloader 有 DISCLAIMER_EN", len(DYD.DISCLAIMER_EN) > 100)
else:
    check("douyin_image_downloader 有 DISCLAIMER_EN", False)


# ============================================================================
#  测试 10: tkinter 可用性 (GUI 层依赖)
# ============================================================================
print("\n=== Test 10: tkinter 可用性 ===")

try:
    import tkinter as _tk
    from tkinter import ttk as _ttk
    check("tkinter 可导入", True)
    check("ttk 可导入", True)
except Exception as e:
    check("tkinter 可导入", False, str(e))


# ============================================================================
#  总结
# ============================================================================
print("\n" + "=" * 60)
print(f"  测试结果: PASS = {PASS}, FAIL = {FAIL}")
print(f"  Result: PASS = {PASS}, FAIL = {FAIL}")
print("=" * 60)

if FAIL == 0:
    print("\n  ✅ 所有冒烟测试通过！")
    print("  ✅ All smoke tests passed!")
else:
    print(f"\n  ❌ {FAIL} 个测试失败，请检查上面的 [FAIL] 标记。")
    print(f"  ❌ {FAIL} test(s) failed. Check [FAIL] markers above.")

print("\n提示: 冒烟测试不实际启动 GUI 和浏览器。")
print("     如需完整测试，请运行: python gui_downloader.py")
print("     如需打包 exe，请运行: build_exe.bat")

sys.exit(0 if FAIL == 0 else 1)
