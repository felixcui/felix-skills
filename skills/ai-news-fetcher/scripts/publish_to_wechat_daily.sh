#!/bin/bash
# AI 资讯发布到微信公众号（每日定时任务）

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 日志文件
LOG_FILE="/tmp/ai_news_wechat_publish.log"

# 记录时间
echo "========================================" >> "$LOG_FILE"
echo "开始执行: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 发布到公众号（创建草稿并发布）
# 如果只想创建草稿，去掉 --publish 参数
python3 "${SCRIPT_DIR}/publish_to_wechat.py" \
  --publish \
  --days 1 >> "$LOG_FILE" 2>&1

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "✅ 发布成功: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
else
    echo "❌ 发布失败: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
fi

echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"