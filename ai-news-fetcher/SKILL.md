---
name: ai-news-fetcher
description: 获取 AI 领域最新资讯并进行智能分类。用于从微信公众号 RSS 源获取 AI 相关文章，使用 AI 自动分类为「AI编程工具及实践」「AI模型与技术」「AI产品与应用」「AI行业动态」等类别，支持发送到飞书。使用场景：每日 AI 资讯汇总、AI 新闻监控、自动资讯推送。
---

# AI 资讯获取器

从微信公众号 RSS 源获取最新的 AI 资讯，进行智能分类，并支持发送到飞书。

## 功能特点

- **自动获取**：从配置的 RSS API 获取昨日到今日的 AI 资讯
- **智能分类**：使用 AI 模型自动将资讯分类到不同类别
- **分类类别**：
  - AI编程工具及实践（Cursor、Claude Code、Copilot 等）
  - AI模型与技术（大模型发布、算法创新、多模态等）
  - AI产品与应用（AI 应用产品、Agent、智能体等）
  - AI行业动态（融资并购、行业政策、市场趋势等）
- **过滤机制**：自动过滤指定公众号的内容
- **多格式输出**：支持纯文本、Markdown 等格式

## 使用方法

### 1. 获取资讯（仅输出）

```bash
python3 scripts/fetch_ai_news.py
```

### 2. 获取并发送到飞书

```bash
bash scripts/send_ai_news.sh
```

### 3. 在 Python 中调用

```python
import sys
sys.path.insert(0, 'scripts')
from fetch_ai_news import get_news_summary

result = get_news_summary()
print(result)
```

## 配置说明

### 修改 RSS API 密钥

编辑 `scripts/fetch_ai_news.py` 中的 API URL：

```python
url = f"https://wexinrss.zeabur.app/api/query?k=YOUR_API_KEY&content=0&before={before}&after={after}"
```

### 修改过滤的公众号

编辑 `scripts/fetch_ai_news.py` 中的 `EXCLUDED_BIZ_IDS` 集合：

```python
EXCLUDED_BIZ_IDS = {
    "3092970861",  # 公众号ID
    # 添加更多...
}
```

### 修改发送目标

编辑 `scripts/send_ai_news.sh` 中的 `--target` 参数：

```bash
--target "ou_xxxxx"  # 飞书用户 open_id 或群聊 chat_id
```

## 定时任务配置

添加到 crontab 实现每日自动推送：

```bash
# 每天早上 7:10 执行
10 7 * * * cd ~/.openclaw/skills/ai-news-fetcher && bash scripts/send_ai_news.sh >> /var/log/ai_news.log 2>&1
```

## 依赖

- Python 3.6+
- requests 库
- openclaw CLI（用于发送消息）

## 输出示例

```
📰 AI 资讯汇总（2026年03月04日 - 2026年03月05日）
共 15 条资讯

📌 AI编程工具及实践（5 条）
• [Cursor 0.45 发布，新增 Agent 模式](https://...)
• [Claude Code 使用技巧分享](https://...)

📌 AI模型与技术（4 条）
• [GPT-5 即将发布，参数规模突破](https://...)

📌 AI产品与应用（3 条）
• [OpenAI 推出新功能](https://...)

📌 AI行业动态（3 条）
• [某 AI 公司完成 B 轮融资](https://...)
```
