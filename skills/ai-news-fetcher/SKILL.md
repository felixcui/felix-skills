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

## 汇总一段时间的热点（周报 / 月报）

用户要「基于早报和收藏的内容，总结上周 / 最近 N 天的热点」时，从早报存档 + 收藏库取数再汇总；取数正则、组织顺序与坑点见 [references/weekly-rollup.md](references/weekly-rollup.md)。

## 日报内容口径（用户明确要求，改前先确认）

- **今日热点每条一句话**：直接讲事实——发生了什么、谁做了什么、有什么关键数字或影响。不要「主题：说明」两截式，不要用冒号把一句话切成前后两半；热点 JSON 只出 `topic` 一个字段，不出 `summary`。
- **禁止元叙述**：不写「多篇文章报道」「多篇文章围绕」「集中报道」「篇文章」「标题」「篇数」这类描述报道行为的措辞——读者只关心事情本身，不关心有几篇报道。
- **热点条目不设加粗**：正文里的 `<strong>` 是全文唯一的加粗正文，观感与其它章节（普通字重）不一致；热点条目与分类条目保持同一字重。
- **`###` 小标题保持加粗**：调整正文样式时不要连带改标题。
- **公众号与飞书同一口径**：两端共用同一份 markdown，不要按平台分叉（`format_news_markdown` 的 `platform` 参数是历史遗留，函数里并未使用）。
- **排除活动/招募类主题**：活动、会议、沙龙、嘉年华、报名、征集、招聘、课程招生、比赛报名及其回顾稿/宣传稿，不参与热点归纳（正文里这类标题本就被过滤，热点再捞回来等于绕过过滤器）。这条要写成提示词的**第 1 条**「先剔除再归纳」，并明写「即使条数最多、占比最高也不能成为热点」——放末尾当补充规则会被同一批要求里的「按涉及文章数排序」压过（实测注入 4 条同类标题时模型照样把它排成热点）。
- 上述任一条要改，必须同时改三处：`summarize_hot_topics_with_ai` 的提示词、`valid_topics` 的字段校验、`format_news_markdown` 的条目拼装。只改一处会出现「模型输出两句、排版只拼一句」的错位。
- 改完要实跑验证：热点提示词改动直接跑 `python3 scripts/verify_hot_topics.py`（真实 feed 跑一遍 + 注入 4 条活动/招募标题再跑一遍，断言热点不含活动词、不含报道腔、每条一句话；退出码 1 = 有失败项）；排版改动渲染后数 `<strong>`。改完按 [references/wechat-draft-refresh.md](references/wechat-draft-refresh.md) 原地刷新当天草稿。

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
- **模型报 400 / 429 时先探端点，不要改脚本里的模型名**：`.env` 的 `OPENAI_*` 才是分类与热点实际使用的模型（与 Hermes 运行时模型解耦，Hermes 切了模型这里不会自动跟着变）。看到 `HTTP 400 … supported API model names are …` 或 `429 … quota has been exhausted`，用一条最小 `/chat/completions` 请求分别打 `OPENAI_BASE_URL` 和 `DEEPSEEK_BASE_URL`，把 `OPENAI_*` 指到真正回话的端点（模型名与 Hermes 主模型一致；DeepSeek 官方端点接受 `enable_thinking:false`），探针通过后再跑发布脚本。
- **补跑当天日报前先查两处，别直接重跑**：① `sqlite3 ~/.hermes/cron/executions.db "select scheduled_instant,started_at,status,error from executions where job_id='8935b4b3eda1' order by started_at desc limit 3;"` 拿失败原文（比翻 cron 输出准确）；② `draft/batchget` 确认当天草稿是否已存在——已存在就按 [references/wechat-draft-refresh.md](references/wechat-draft-refresh.md) 用 `draft/update` 原地刷新，重跑 `--create-draft` 会多出一份同标题草稿。
- **`48001 api unauthorized`（freepublish / 已发布列表）是预期结果，不要修**：该号未授权群发接口，日报的终点就是微信公众号**草稿箱**，群发由用户在后台手动点；发布脚本天然只建草稿，不要为绕开它改造发布链路。
- 获取失败时先检查 RSS 服务和网络；AI 分类或热点失败时查看脚本日志中的模型降级信息。
