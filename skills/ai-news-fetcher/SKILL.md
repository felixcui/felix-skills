---
name: ai-news-fetcher
description: 获取微信公众号 RSS 中的 AI 资讯并生成每日分类日报，可选保存 Markdown、写入 DevMaster、创建微信公众号草稿或发布。用户需要每日 AI 资讯汇总、新闻监控或发布日报时使用。
---

# AI 资讯获取器

根据用户需要选择获取、创建草稿或发布流程。分类、热点归纳、过滤和 Markdown 排版由脚本实现；不要在本文件重复维护类别清单或算法细节。

## 常用操作

在技能目录下运行：

```bash
# 获取最近一天的资讯，输出 Markdown
python3 scripts/fetch_ai_news.py

# 仅用规则分类
python3 scripts/fetch_ai_news.py --method rule

# 创建微信公众号草稿
python3 scripts/publish_to_wechat.py --create-draft

# 创建并发布文章
python3 scripts/publish_to_wechat.py --publish

# 指定日期创建草稿
python3 scripts/publish_to_wechat.py --create-draft --date YYYY-MM-DD

# 创建草稿时跳过 DevMaster 入库
python3 scripts/publish_to_wechat.py --create-draft --no-db
```

`--days` 可指定查询天数。`--date` 仅由发布脚本支持。发布脚本负责串起获取、生成 Markdown、转换 HTML 和创建草稿，不要改为手工分步执行。`--publish` 会实际发布；预览时使用 `--create-draft`。

发布脚本将 Markdown 保存为 `ai-news-YYYY-MM-DD.md`：可用 `NEWS_OUTPUT_DIR` 指定目录，默认是技能目录下的 `output/`。单独运行获取脚本时，Markdown 输出到标准输出；若配置了 `DEVELMASTER_API_KEY`，该命令也会尝试写入 DevMaster。发布脚本可用 `--no-db` 跳过入库。

## 配置

按需在技能根目录 `.env` 中配置。获取资讯需要 RSS；AI 分类/热点、入库和公众号发布可分别配置：

```bash
AI_NEWS_API_KEY=...
AI_NEWS_API_BASE=https://wexinrss.zeabur.app

OPENAI_API_KEY=...
OPENAI_BASE_URL=...
OPENAI_MODEL=...
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

DEVELMASTER_API_KEY=...

WECHAT_APPID=...
WECHAT_APPSECRET=...
BAOYU_MARKDOWN_TO_HTML_DIR=~/work/skills/baoyu-skills/skills/baoyu-markdown-to-html
NEWS_OUTPUT_DIR=...
```

若主模型未配置或不可用，分类会尝试备用模型，再回退到脚本内置规则；热点总结只使用已配置的 AI 服务，失败时省略热点，不使用关键词兜底。RSS 地址末尾的斜杠由脚本处理。DeepSeek 密钥也可从 `~/.hermes/.env` 读取。

## 发布依赖与故障处理

- 微信发布需要 `baoyu-markdown-to-html` 和 `aicoding-news-weekly/scripts/wechat_api_client.py`。凭证、密钥等敏感信息只放在 `.env`，不要写入文档或提交到版本库。
- 微信封面素材 ID 可能过期。若草稿接口报 `40007 invalid media_id`，重新上传封面后更新发布脚本默认素材 ID，或用 `--cover-image` / `--thumb-media-id` 指定封面。
- 若微信报 `45166 invalid content hint`，检查资讯标题中的半角 `]` 是否破坏 Markdown 链接，修正后再创建草稿。
- 获取失败时先检查 RSS 服务和网络；AI 分类或热点失败时查看脚本日志中的模型降级信息。
