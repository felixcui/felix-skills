#!/bin/bash
# AI 资讯获取并发送脚本（修复版）

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 获取资讯
NEWS=$(python3 "${SCRIPT_DIR}/fetch_ai_news.py")

# 发送到飞书（通过环境变量或修改下方目标）
TARGET="${AI_NEWS_TARGET:-ou_a9e43b640456cfea394cb9d542df434d}"
CHANNEL="${AI_NEWS_CHANNEL:-feishu}"

echo "$NEWS" | /opt/homebrew/bin/openclaw message send \
  --channel "$CHANNEL" \
  --target "$TARGET" \
  --message "$NEWS" 2>&1
