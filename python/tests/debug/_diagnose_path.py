#!/usr/bin/env python3
# 诊断脚本：确认桌面路径和权限
import os
import sys
import tempfile

print("=== 系统信息 ===")
print(f"os.name = {os.name}")
print(f"sys.platform = {sys.platform}")
print(f"用户主目录 = {os.path.expanduser('~')}")

home = os.path.expanduser('~')
candidates = [
    ("Desktop (英文)", os.path.join(home, "Desktop")),
    ("桌面 (中文)", os.path.join(home, "桌面")),
]

print("\n=== 桌面路径探测 ===")
desktop = None
for label, path in candidates:
    exists = os.path.exists(path)
    isdir = os.path.isdir(path)
    writable = False
    if isdir:
        try:
            testfile = os.path.join(path, ".write_test_" + str(os.getpid()))
            with open(testfile, 'w') as f:
                f.write("test")
            os.remove(testfile)
            writable = True
        except Exception as e:
            writable = False
            print(f"  写入测试失败: {e}")
    print(f"  {label}: {path}")
    print(f"    exists={exists}, isdir={isdir}, writable={writable}")
    if isdir and writable and desktop is None:
        desktop = path

# 也检查常见 Windows 特殊桌面路径
win_desktop = os.path.join(home, "Desktop")
print(f"\n  Windows 标准桌面: {win_desktop}")
print(f"    exists={os.path.exists(win_desktop)}, isdir={os.path.isdir(win_desktop)}")

# 尝试在主目录和临时目录测试
temp_dir = tempfile.gettempdir()
print(f"\n  临时目录: {temp_dir}, writable={os.access(temp_dir, os.W_OK)}")

# 测试创建目标目录
print("\n=== 目录创建测试 ===")
test_paths = [
    os.path.join(home, "Desktop", "douyin_downloads"),
    os.path.join(home, "桌面", "douyin_downloads"),
    os.path.join(tempfile.gettempdir(), "douyin_downloads"),
    os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "downloads"),
]
for p in test_paths:
    try:
        os.makedirs(p, exist_ok=True)
        print(f"  ✅ 成功创建: {p}")
    except Exception as e:
        print(f"  ❌ 失败: {p}")
        print(f"     错误: {e}")

# 查看系统已知的 Desktop 路径
print("\n=== 系统路径环境变量 ===")
for key in ['USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'LOCALAPPDATA', 'APPDATA', 'PUBLIC']:
    val = os.environ.get(key, '')
    if val:
        print(f"  {key} = {val}")
