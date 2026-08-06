#!/usr/bin/env bash
set -e

# 获取脚本所在目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JSON_PATH="$REPO_ROOT/download-policy.json"

# 优先使用项目内的虚拟环境 Python
if [[ -f "$REPO_ROOT/python/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/python/.venv/bin/python"
elif [[ -f "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
else
    PYTHON_BIN="python3"
fi

# 参数检查
STATUS=$1
MESSAGE=$2

if [[ "$STATUS" != "on" && "$STATUS" != "off" ]]; then
    echo "用法: $0 [on|off] \"提示消息\""
    exit 1
fi

ENABLED="true"
[[ "$STATUS" == "off" ]] && ENABLED="false"

echo "==> 正在切换下载功能状态为: [$STATUS]"
if [[ -n "$MESSAGE" ]]; then
    echo "==> 提示消息: $MESSAGE"
else
    MESSAGE="下载功能目前不可用。"
    [[ "$STATUS" == "on" ]] && MESSAGE="下载功能已恢复。"
fi

# 使用 Python 更新 JSON
"$PYTHON_BIN" - "$JSON_PATH" "$ENABLED" "$MESSAGE" <<'PY'
import json, sys, datetime
path, enabled_str, msg = sys.argv[1], sys.argv[2], sys.argv[3]
enabled = enabled_str.lower() == "true"
try:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if "download" not in data: data["download"] = {}
    data["download"]["enabled"] = enabled
    data["download"]["message"] = msg

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"成功更新 {path}")
except Exception as e:
    print(f"错误: {e}")
    sys.exit(1)
PY

# 如果存在签名脚本，则执行签名
SIGNER="$SCRIPT_DIR/sign-policy.py"
KEY="$REPO_ROOT/secrets/policy-private-key.pem"

if [[ -f "$SIGNER" && -f "$KEY" ]]; then
    echo "==> 检测到签名机制，正在重新签名..."
    "$PYTHON_BIN" "$SIGNER" "$JSON_PATH" --key "$KEY"
elif [[ -f "$SIGNER" ]]; then
    echo "::WARNING:: 找到签名脚本但未找到私钥 ($KEY)，App 可能会因验签失败而拦截下载！"
fi

echo ""
echo "✅ 操作完成！请执行以下命令正式生效："
echo "git add download-policy.json && git commit -m \"policy: toggle download $STATUS\" && git push origin master"
