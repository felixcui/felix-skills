# felix-skills

Felix 的个人 AI 技能集合，覆盖 AI 资讯采集、内容整理、公众号写作与发布，以及 X、小红书等平台的内容转换。

## 技能列表

### 资讯采集与整理

| 技能 | 说明 |
| --- | --- |
| [ai-news-fetcher](./skills/ai-news-fetcher/) | 从微信公众号 RSS 源获取 AI 资讯，自动分类、入库，并支持生成公众号内容和发布。 |
| [aicoding-news-weekly](./skills/aicoding-news-weekly/) | 从飞书数据生成 AICoding 每周资讯报告，输出 Markdown，并支持公众号预览与发布。 |
| [news-collect](./skills/news-collect/) | 抓取微信公众号、普通网页及 X 内容，生成摘要后推送至飞书和 IMA；可选接入 NotebookLM。 |
| [x-monitor](./skills/x-monitor/) | 监控指定 X 用户及 AI 热点话题，汇总、摘要后发送到飞书。 |

### 内容创作与发布

| 技能 | 说明 |
| --- | --- |
| [felix-wechat-writer](./skills/felix-wechat-writer/) | 将草稿或零散要点润色为逻辑清晰、简明真诚的公众号文章。 |
| [felix-wechat-post](./skills/felix-wechat-post/) | 自动生成深蓝色公众号封面，并通过 `baoyu-post-to-wechat` 完成预览或发布。 |
| [felix-x-writer](./skills/felix-x-writer/) | 将本地 Markdown 长文浓缩为 1～3 条 X 动态，并按 X 的字符权重规则校验长度。 |
| [felix-xhs-writer](./skills/felix-xhs-writer/) | 将本地 Markdown 文章转换为小红书文案、封面图要点和竖版信息图。 |

## 使用方式

本项目可作为 Claude Code 插件在本地加载：

```bash
git clone https://github.com/felixcui/felix-skills.git
claude --plugin-dir /path/to/felix-skills
```

加载后，通过 `/felix-skills:<技能名>` 调用，例如：

```text
/felix-skills:ai-news-fetcher
/felix-skills:felix-wechat-writer
/felix-skills:felix-wechat-post
/felix-skills:felix-x-writer ./article.md
/felix-skills:felix-xhs-writer ./article.md
```

也可以把需求直接告诉支持 Skill 的智能体；当任务符合技能描述时，智能体会自动选择相应技能。

## 配置与依赖

不同技能依赖的外部服务并不相同，可能包括：

- 飞书、微信公众号、IMA 或 NotebookLM 的账号与接口配置
- Python 3 及技能脚本声明的第三方依赖
- `baoyu-post-to-wechat`、`baoyu-fetch`、`twitter` 等配套工具
- 图片生成能力（用于生成小红书信息图）

具体要求、环境变量和执行步骤以各技能目录中的 `SKILL.md` 为准。请勿将 API Key、Cookie、Webhook 或其他敏感配置提交到仓库。

## 目录结构

```text
felix-skills/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── ai-news-fetcher/
│   ├── aicoding-news-weekly/
│   ├── felix-wechat-post/
│   ├── felix-wechat-writer/
│   ├── felix-x-writer/
│   ├── felix-xhs-writer/
│   ├── news-collect/
│   └── x-monitor/
└── README.md
```

每个技能以 `SKILL.md` 作为入口；需要自动化处理的技能会同时提供 `scripts/`，部分技能还包含 `references/` 或智能体配置。

## License

MIT
