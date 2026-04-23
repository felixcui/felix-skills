---
name: aicoding-news-weekly
description: 生成 AICoding 基地的每周资讯报告，支持公众号预览和发布。
---

# AICoding 资讯周报生成

生成 AICoding 基地的每周资讯报告，支持自动生成 Markdown 文件并调用公众号发布工具。

## 技能结构

```
<放置目录>/
└── aicoding-news-weekly/           # 技能目录（可放置在任意位置）
    ├── SKILL.md                   # 本文档
    ├── .env                       # 微信公众号凭证（可选）
    ├── scripts/                   # 周报生成脚本
    │   ├── generate_weekly.py     # 主脚本：生成周报
    │   ├── feishu_news.py         # 飞书 API 调用
    │   ├── md_to_html.py          # 公众号发布工具
    │   └── wechat_api_client.py   # 微信 API 客户端
    └── output/                    # 默认输出目录（自动创建，建议加入 .gitignore）
        └── 2026-01-24.md          # 生成的周报文件
```

## 执行步骤

直接运行周报生成脚本（可在任意目录执行，路径相对于 skill 所在位置）：

```bash
python aicoding-news-weekly/scripts/generate_weekly.py --preview
```

该脚本会自动：

1. 计算本周的日期范围（以本周六为结束日期，上周日为开始日期，共 7 天）
2. 调用飞书 API 获取本周资讯
3. 保存到输出目录（默认为 `aicoding-news-weekly/output/<结束日期>.md`）
4. （可选）调用 `md_to_html.py` 处理 markdown 文件

## 输出目录说明

输出目录按以下优先级确定（从高到低）：

| 优先级 | 方式 | 说明 |
|--------|------|------|
| 1      | `--output path/to/report.md` | 直接指定完整输出文件路径 |
| 2      | `--output-dir path/to/dir` | 指定输出目录，文件名自动生成为 `<结束日期>.md` |
| 3      | 默认 | skill 内部的 `output/` 目录 |

## 自定义选项

```bash
# 生成本周周报（默认，输出到 aicoding-news-weekly/output/<日期>.md）
python scripts/generate_weekly.py

# 生成指定日期的周报
python scripts/generate_weekly.py --date 2026-01-15

# 生成指定日期范围的周报
python scripts/generate_weekly.py --start 2026-01-01 --end 2026-01-07

# 自定义输出目录（文件名自动生成）
python scripts/generate_weekly.py --output-dir ~/Desktop/weekly

# 自定义输出文件完整路径（优先级最高）
python scripts/generate_weekly.py --output ~/Desktop/my-report.md

# 生成周报后调用公众号发布工具（复制 HTML 到剪贴板）
python scripts/generate_weekly.py --publish

# 生成周报后生成公众号预览网页（在浏览器中打开）
python scripts/generate_weekly.py --preview

# 生成周报后直接发布到公众号（创建草稿）
python scripts/generate_weekly.py --weixin
```

## 公众号发布集成

生成周报后可自动调用公众号发布工具：

- **`--publish`**: 调用 `md_to_html.py`，将 Markdown 转换为带公众号样式的 HTML 并复制到剪贴板
- **`--preview`**: 生成公众号预览网页，自动在浏览器中打开预览效果
- **`--weixin`**: 直接发布到公众号，使用固定封面图素材 ID 创建草稿，摘要固定为"工具动态，编程实践，编程模型，业界观点"（需配置项目根目录 `.env` 文件）

## 环境配置

### 飞书 API 配置

飞书 API 凭证已硬编码在 `scripts/feishu_news.py` 中，无需额外配置。

### 微信公众号 API 配置（可选）

使用 `--weixin` 功能前，在 **skill 目录**（`aicoding-news-weekly/`）下创建 `.env` 文件：

```bash
# 在 skill 目录下创建 .env
cat > aicoding-news-weekly/.env << 'EOF'
WECHAT_APPID=你的AppID
WECHAT_APPSECRET=你的AppSecret
EOF
```

或直接创建 `aicoding-news-weekly/.env` 文件，内容为：

```
WECHAT_APPID=你的AppID
WECHAT_APPSECRET=你的AppSecret
```

在公众号后台设置服务器 IP 白名单。

## 示例

如果今天是 2026-01-24（周五），周报应该：

- 开始日期：2026-01-18（上周日）
- 结束日期：2026-01-24（本周六）
- 默认保存路径：`aicoding-news-weekly/output/2026-01-24.md`

**日期计算规则**：周报以本周六为结束日期，上周日为开始日期（共 7 天）

## 注意事项

- **输出位置**：默认保存到 skill 内部的 `output/` 目录（建议加入 `.gitignore`），可通过 `--output-dir` 或 `--output` 自定义
- 如果周报文件已存在，脚本会自动覆盖旧文件
- 日期格式必须严格遵循 `YYYY-MM-DD` 格式
- 确保飞书 API 凭证有效
- 使用 `--preview` 需要系统支持浏览器自动打开
- 使用 `--publish` 需要安装 `markdown` 和 `pygments` 依赖包
- 使用 `--weixin` 需要认证的服务号，并开通草稿箱和发布接口权限
