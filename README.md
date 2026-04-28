# felix-skills

Felix 的 AI 技能集合，涵盖资讯获取、内容生成、公众号发布等日常工作效率工具。

## 技能列表

| 技能 | 说明 |
|------|------|
| [ai-coding-search](./skills/ai-coding-search) | 搜索 AICoding 相关资讯，支持主题关键词查询 |
| [ai-news-fetcher](./skills/ai-news-fetcher) | 获取 AI 领域最新资讯并进行智能分类，支持发送到飞书和发布到微信公众号 |
| [aicoding-news-weekly](./skills/aicoding-news-weekly) | 生成 AICoding 基地的每周资讯报告，支持公众号预览和发布 |
| [news-collect](./skills/news-collect) | 一站式资讯收集工具：抓取文章 → 大模型生成摘要 → 推送到飞书 |
| [wechat-writer](./skills/wechat-writer) | 技术公众号文章写作助手，支持完整文章生成、爆款标题优化、结构模板选择 |
| [wechat-fetch](./skills/wechat-fetch) | 抓取微信公众号文章内容，提取标题、作者、发布时间、正文和图片 |
| [xhs-writer](./skills/xhs-writer) | 将公众号文章保存到本地并转换为小红书风格文案，同时生成封面图设计文案 |

## 安装使用

本项目是 Claude Code 插件，支持以下方式使用：

### 本地加载（开发/测试）

```bash
claude --plugin-dir /path/to/felix-skills
```

加载后可通过 `/felix-skills:<技能名>` 调用技能，例如：

```bash
/felix-skills:wechat-fetch
/felix-skills:ai-news-fetcher
```

### 目录结构

```
felix-skills/
├── .claude-plugin/
│   ├── plugin.json         # 插件元数据（Claude Code 必需）
│   └── marketplace.json    # 市场注册信息
├── skills/                 # 技能目录
│   ├── ai-coding-search/
│   ├── ai-news-fetcher/
│   ├── aicoding-news-weekly/
│   ├── news-collect/
│   ├── wechat-writer/
│   ├── xhs-writer/
└── README.md
```

## License

MIT
