---
name: x-monitor
description: 监控指定 X 用户的新推文，汇总后通过飞书私聊发送给 Felix。
---

# X (Twitter) 用户动态监控

监控指定 X 用户的新推文，汇总后通过飞书私聊发送给 Felix。

## 监控用户列表

配置文件：`scripts/users.txt`，每行一个用户名（不含@）。

## 依赖

- **opencli**（`/opt/homebrew/bin/opencli`）：脚本通过 `opencli twitter search --query "from:username"` 获取用户最新推文
- ⚠️ 不要使用 `twitter user-posts` 命令，该命令已失效（超时无响应）

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

## 飞书消息格式

有新推文时，用以下格式发送给 Felix（飞书私聊）：

```
🐦 X 动态监控 | 4月21日 07:00
━━━━━━━━━━━━━━━━━━
共 5 条新推文

@dotey
推文正文内容...
🔗 https://x.com/dotey/status/xxx
👍 1.2k | 🔄 234 | 💬 56 | 👁 15k

@op7418
推文正文内容...
🔗 https://x.com/op7418/status/xxx
👍 890 | 🔄 123 | 💬 34 | 👁 8.9k

━━━━━━━━━━━━━━━━━━
```

⚠️ URL 必须用尖括号包裹：<https://x.com/user/status/id>，避免飞书截断超链接可点击区域。

规则：
- 每条推文必须包含完整正文，不要省略
- 数字格式化：≥1M 显示为 X.XM，≥1k 显示为 X.Xk
- 转发推文标注「🔄 转发自 @原作者」
- 无新推文时不发消息（NO_REPLY）

## 状态管理

- 每个用户的最后一条推文 ID 保存在 `tmp/x-monitor-states/{username}-last-tweet.txt`
- 每次运行时比对，相同则跳过

## 飞书发送命令

使用 `lark-cli im +messages-send` 发送，必须显式指定 `--as bot`（auto-detect 默认为 user，该命令不支持 user 身份）：

```bash
# 发送纯文本消息
lark-cli im +messages-send --as bot --user-id "ou_bd3798f4eb3ce8399677b399fa6ee0fa" --text "$MESSAGE"

# 发送 Markdown 消息（推荐，排版更好）
lark-cli im +messages-send --as bot --user-id "ou_bd3798f4eb3ce8399677b399fa6ee0fa" --markdown "$MESSAGE"
```

- Felix 的 open_id：`ou_bd3798f4eb3ce8399677b399fa6ee0fa`
- ⚠️ `--as bot` 是必须的，不加会报 `validation` 错误
- 长消息建议用 `--markdown` 而非 `--text`，飞书 Markdown 渲染效果更好
- URL 必须用尖括号包裹 `<https://...>`，避免飞书截断可点击区域

## Troubleshooting

- 如果 cron 作业显示 `ok` 但你没收到消息，先检查本次是否实际返回了 `NO_NEW_TWEETS`，因为这种情况下按规则不会发送任何飞书内容。
- 如果本次有新推文但没收到飞书，重点排查外层发送步骤，而不是抓取脚本本身。
- 状态文件会阻止重复推送同一条推文。
- `lark-cli im +messages-send` 报 `validation` 错误：检查是否缺少 `--as bot` 参数。

## Cron 任务

任务名：`x-users-monitor`
- 调度：每天 7:00, 11:00, 18:00
- Agent 执行步骤：运行脚本 → 有新推文则格式化发送
