#!/bin/bash
# AI 资讯获取并发送脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 获取资讯
NEWS=$(python3 "${SCRIPT_DIR}/fetch_ai_news.py")

# 输出资讯内容（通过 stdout 返回，cron 会自动处理）
echo "$NEWS"

# 执行完成通知（也通过 stdout）
echo "✅ AI资讯推送任务已完成 (7:00)"
