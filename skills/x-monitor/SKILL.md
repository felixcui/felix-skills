---
name: x-monitor
description: 监控指定 X 用户的新推文 + AI 领域每日热点话题，汇总后通过飞书发送给 Felix。
---

# X (Twitter) 用户动态监控 + AI 热点话题

监控指定 X 用户的新推文，并获取 AI 领域每日高互动热点话题，汇总后通过飞书发送给 Felix。

## 监控用户列表

配置文件：`scripts/users.txt`，每行一个用户名（不含@）。

## 依赖

- **twitter**（`/Users/felix/.local/bin/twitter`）：用户监控脚本通过 `twitter user-posts <username> --max 1 --json` 获取用户最新推文
- **opencli**（`/opt/homebrew/bin/opencli`）：备用工具（需要 Chrome Browser Bridge 扩展）
- **twitter CLI**（`/Users/felix/.local/bin/twitter`）：AI 热点脚本通过 `twitter search --type top` 搜索 AI 相关热门推文（不依赖浏览器扩展，更稳定）
- ⚠️ `twitter user-posts` 命令不稳定，经常超时无响应，每次运行能成功抓取的用户数量会有波动，属于已知问题

## 执行方式

```bash
python3 scripts/fetch_new_tweets.py
```

- 无新推文时输出 `NO_NEW_TWEETS` 并退出码 1
- 有新推文时输出 JSON 到 stdout，同时写入 `/tmp/x-monitor-new-tweets.json`
- 这个脚本只负责抓取/比对/落盘，不直接发送飞书消息；飞书发送必须由外层工作流单独完成
- 一次完整运行可能需要几分钟，属于正常现象（16 个用户，`twitter user-posts` 不稳定，每次能成功抓取的数量有波动）

## 数据格式

JSON 数组，每条推文包含：
```json
{
  "id": "推文ID",
  "text": "推文全文",
  "author": "screenName",
  "author_name": "显示名称",
  "likes": 0, "retweets": 0, "replies": 0, "views": 0,
  "created_at": "2026-04-21T07:30:00Z",
  "url": "https://x.com/user/status/id",
  "is_retweet": false
}
```

## 飞书消息格式

无论有无新推文，都必须输出内容（不要用 `[SILENT]`）。

### 有新推文时

```
🐦 X 动态监控 | 4月21日 07:00
━━━━━━━━━━━━━━━━━━
共 5 条新推文

@dotey
推文正文内容...
🔗 <https://x.com/dotey/status/xxx>
👍 1.2k | 🔄 234 | 💬 56 | 👁 15k

@op7418
推文正文内容...
🔗 <https://x.com/op7418/status/xxx>
👍 890 | 🔄 123 | 💬 34 | 👁 8.9k

━━━━━━━━━━━━━━━━━━

🔥 AI 热点话题
━━━━━━━━━━━━━━━━━━
1. @author1 — 推文摘要前50字...
   🔗 <https://x.com/author1/status/xxx>
   👍 5.2k | 🔄 1.2k | 💬 456 | 👁 120k

2. @author2 — 推文摘要前50字...
   🔗 <https://x.com/author2/status/xxx>
   👍 3.1k | 🔄 890 | 💬 234 | 👁 89k

━━━━━━━━━━━━━━━━━━
```

### 无新推文时

```
🐦 X 动态监控 | 4月21日 07:00
暂无新推文

🔥 AI 热点话题
━━━━━━━━━━━━━━━━━━
（如有热点推文则展示，如无则显示）
暂无 AI 热点
━━━━━━━━━━━━━━━━━━
```

**热点话题获取失败时**：在热点区域显示「🔥 AI 热点话题获取失败，下次重试」，不影响用户动态部分。

⚠️ URL 必须用尖括号包裹：<https://x.com/user/status/id>，避免飞书截断超链接可点击区域。

规则：
- 每条推文必须包含完整正文，不要省略
- 数字格式化：≥1M 显示为 X.XM，≥1k 显示为 X.Xk
- 转发推文标注「🔄 转发自 @原作者」
- **无新推文时也要汇报**，不要使用 [SILENT]

## 状态管理

- 每个用户的最后一条推文 ID 保存在 `tmp/x-monitor-states/{username}-last-tweet.txt`
- 每次运行时比对，相同则跳过

## AI 热点话题

### 执行方式

```bash
python3 scripts/fetch_ai_trending.py
```

- 使用 `twitter` CLI（`/Users/felix/.local/bin/twitter`）搜索 AI 相关热门推文，不依赖浏览器扩展
- 搜索命令：`twitter search "<query>" --type top --lang en --max N --json`
- 执行两次搜索：关键词搜索 `"AI OR LLM OR GPT OR Claude OR agent OR DeepSeek"`（20 条）+ `"AI agent framework"`（10 条）
- twitter CLI 返回嵌套结构：`author` 是 dict（`screenName`/`name`），`metrics` 是 dict（`likes`/`retweets`/`views`），有 `createdAtISO` 时间字段
- 自动排除 users.txt 中已监控用户的推文（避免重复）
- 只保留最近 2 天内的推文（用 `createdAtISO` 字段判断）
- 按 engagement_score（likes + retweets×2 + replies）降序取 Top 10
- 输出 JSON 到 stdout，同时写入 `/tmp/x-monitor-ai-trending.json`
- timeout 60s，失败时优雅降级输出空数组

### 输出格式

JSON 数组，每条推文在原有字段基础上增加 `engagement_score` 字段。

### 与用户监控的区别

| | 用户监控 (fetch_new_tweets.py) | AI 热点 (fetch_ai_trending.py) |
|---|---|---|
| 数据源 | 指定用户最新推文 | AI 关键词搜索热门推文 |
| 去重 | 基于状态文件（增量） | 每次全量获取，按热度排序 |
| 输出 | 新推文或 NO_NEW_TWEETS | 始终输出 JSON（可能为空） |

## Cron 任务投递方式

**使用 `deliver: origin`**，让系统自动投递到当前会话，不要用 lark-cli 手动发送。

```yaml
deliver: origin
```

- ❌ 不要使用 `lark-cli im +messages-send`（会造成重复发送、且消息到私聊而非当前会话）
- ❌ 不要输出 `[SILENT]`（用户要求无新推文时也要汇报）
- ✅ 直接将格式化好的内容作为最终输出，系统会自动投递

## Troubleshooting

- 如果 cron 作业显示 `ok` 但你没收到消息，先检查本次是否实际返回了 `NO_NEW_TWEETS`，因为这种情况下按规则不会发送任何飞书内容。
- 如果本次有新推文但没收到飞书，重点排查外层发送步骤，而不是抓取脚本本身。
- 状态文件会阻止重复推送同一条推文。
- `lark-cli im +messages-send` 报 `validation` 错误：检查是否缺少 `--as bot` 参数。
- **twitter CLI 返回嵌套结构**：`author` 是 dict（含 `screenName`/`name`），`metrics` 是 dict（含 `likes`/`retweets`/`views`/`bookmarks`），有 `createdAtISO` 时间字段。`parse_tweet()` 已适配此结构。如果 twitter CLI 更新了输出格式，优先检查 `parse_tweet` 函数。
- **opencli 已弃用（AI 热点）**：fetch_ai_trending.py 已从 opencli 切换到 twitter CLI。opencli 仍作为备用工具保留，但不再用于 AI 热点获取。opencli 的 Browser Bridge 扩展经常断连（`opencli doctor` 显示 `[MISSING] Extension`），导致 AI 热点连续多天失败，这是切换的主要原因。

## Cron 任务

任务名：`x-users-monitor`
- 调度：每天 7:00, 11:00, 18:00
- Agent 执行步骤：
  1. 运行 `python3 scripts/fetch_new_tweets.py` 获取用户新推文
  2. 运行 `python3 scripts/fetch_ai_trending.py` 获取 AI 热点话题
  3. 格式化输出（两个模块独立运行，互不影响）
  4. 有新推文时展示用户动态，有热点时展示 AI 热点话题
  5. 始终推送（即使无新内容也要汇报）
