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
- **opencli**（`/opt/homebrew/bin/opencli`）：AI 热点脚本通过 `opencli twitter search` 搜索 AI 相关热门推文
- ⚠️ `twitter user-posts` 命令不稳定，经常超时无响应，每次运行能成功抓取的用户数量会有波动，属于已知问题
- ⚠️ `opencli twitter search` 也可能超时，脚本已设置 60s timeout 并优雅降级

## 执行方式

```bash
python3 scripts/fetch_new_tweets.py
```

- 无新推文时输出 `NO_NEW_TWEETS` 并退出码 1
- 有新推文时输出 JSON 到 stdout，同时写入 `/tmp/x-monitor-new-tweets.json`
- 这个脚本只负责抓取/比对/落盘，不直接发送飞书消息；飞书发送必须由外层工作流单独完成
- 一次完整运行可能需要几分钟，属于正常现象（16 个用户 × 每次 opencli 调用约 20s）

## 输出格式

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

## 输出格式

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

- 使用 `opencli`（/opt/homebrew/bin/opencli）搜索 AI 相关热门推文
- 执行两次搜索：关键词搜索（20 条）+ 热门标签搜索（10 条）
- 自动排除 users.txt 中已监控用户的推文（避免重复）
- 按 engagement_score（likes + retweets×2 + replies）降序取 Top 10
- 输出 JSON 到 stdout，同时写入 `/tmp/x-monitor-ai-trending.json`
- opencli timeout 60s，失败时优雅降级输出空数组

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
- **opencli twitter search 输出格式**：返回扁平 JSON 数组，`author` 是字符串（非对象），`likes`/`views` 等可能是字符串或整数。fetch_ai_trending.py 已用 `_to_int()` 和 `isinstance` 兼容处理。如果 opencli 更新了输出格式，优先检查 parse_tweet 函数。
- **Claude Code 生成 opencli 相关代码时**：Claude Code 不了解 opencli 的实际输出格式，生成的解析代码经常假设嵌套结构（如 `t.get("metrics", {}).get("likes")`），需要人工验证并修复为扁平结构。建议让 Claude Code 先用 `opencli twitter search --limit 1 -f json` 看实际输出再写代码。

## Cron 任务

任务名：`x-users-monitor`
- 调度：每天 7:00, 11:00, 18:00
- Agent 执行步骤：
  1. 运行 `python3 scripts/fetch_new_tweets.py` 获取用户新推文
  2. 运行 `python3 scripts/fetch_ai_trending.py` 获取 AI 热点话题
  3. 格式化输出（两个模块独立运行，互不影响）
  4. 有新推文时展示用户动态，有热点时展示 AI 热点话题
  5. 始终推送（即使无新内容也要汇报）
