---
name: news-aggregation
description: 一站式新闻资讯收集与分发 — 从微信公众号 RSS、飞书、普通网页多源抓取，AI 分类摘要，推送至飞书/微信公众号/NotebookLM/IMA。覆盖 ai-news-fetcher、aicoding-news-weekly、news-collect 三套工具链。
---

# News Aggregation — 资讯收集与分发

Umbrella skill for the news aggregation pipeline: fetch from multiple sources → classify/summarize → distribute to multiple channels.

## Pipeline Overview

```
                      ┌─ ai-news-fetcher ────→ WeChat Official Account
Sources ──→ Classify ─┼─ news-collect ───────→ Feishu + NotebookLM + IMA
                      └─ aicoding-news-weekly → Feishu (weekly report)
```

## Skill References

| Reference | Purpose | Data Source | Destinations | Key Scripts |
|-----------|---------|-------------|--------------|-------------|
| [ai-news-fetcher.md](references/ai-news-fetcher.md) | Daily AI news from WeChat RSS, auto-classified | WeChat RSS API | WeChat 公众号 draft | `fetch_ai_news.py`, `publish_to_wechat.py` |
| [aicoding-news-weekly.md](references/aicoding-news-weekly.md) | Weekly AICoding community report | Feishu (多维表格) | Feishu / WeChat 公众号 | `generate_weekly.py`, `wechat_api_client.py` |
| [news-collect.md](references/news-collect.md) | One-stop article fetch → summary → push | Any URL (WeChat, web, X) | Feishu + NotebookLM + IMA | `collect_v2.py` |

---

## When to Use Which

| User Request | Use |
|-------------|-----|
| "Get today's AI news" | ai-news-fetcher — fetches from WeChat RSS |
| "Generate weekly report" | aicoding-news-weekly — generates from Feishu data |
| "Summarize this article" | news-collect — fetch URL → AI summary → push |
| "Save article to NotebookLM" | news-collect with `--notebook` flag |
| "Publish news to WeChat" | ai-news-fetcher's `publish_to_wechat.py` |
| "Push to Feishu" | news-collect (default) or aicoding-news-weekly |

## Critical Rules

- **不要降级任务**：周报生成、资讯抓取等任务必须按完整流程执行，不得自行简化步骤或降低输出质量。遇到问题（API 失败、数据缺失、脚本报错等）应直接报告问题，而不是降级处理。
- **路径注意**：aicoding-news-weekly 的脚本实际位于 `scripts/aicoding-news-weekly/` 子目录下（不是 skill 根目录），完整路径见 references。

## Common Infrastructure

All three skills share:
- Python 3.6+ with `requests`, `python-dotenv`
- `.env` files for credentials
- Cron job execution (daily/weekly schedules)
- AI summarization via LLM API or rule-based fallback

## References

- `references/ai-news-fetcher.md` — Full AI news fetcher from WeChat RSS
- `references/aicoding-news-weekly.md` — Weekly report generator from Feishu (scripts at `scripts/aicoding-news-weekly/`)
- `references/news-collect.md` — One-stop article collector
