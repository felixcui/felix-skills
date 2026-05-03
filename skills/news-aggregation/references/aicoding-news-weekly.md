---
name: aicoding-news-weekly
description: 生成 AICoding 基地的每周资讯报告，支持公众号预览和发布。
---

# AICoding 资讯周报生成

生成 AICoding 基地的每周资讯报告，支持自动生成 Markdown 文件并调用公众号发布工具。

## 技能结构

```
/Users/felix/.hermes/skills/felix-skills/skills/news-aggregation/
└── scripts/
    └── aicoding-news-weekly/        # 脚本目录
        ├── generate_weekly.py       # 主脚本：生成周报
        ├── feishu_news.py           # 飞书 API 调用
        ├── md_to_html.py            # 公众号发布工具
        └── wechat_api_client.py     # 微信 API 客户端
```

## 执行步骤

使用绝对路径运行（cron 任务和手动执行都用此路径）：

```bash
python /Users/felix/.hermes/skills/felix-skills/skills/news-aggregation/scripts/aicoding-news-weekly/generate_weekly.py --weixin
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
| 3      | 环境变量 `OUTPUT_DIR` | 读取 `.env` 或环境变量中配置的 `OUTPUT_DIR` |
| 4      | 默认 | skill 内部的 `output/` 目录 |

## 自定义选项

```bash
SCRIPT="/Users/felix/.hermes/skills/felix-skills/skills/news-aggregation/scripts/aicoding-news-weekly/generate_weekly.py"

# 生成本周周报（默认）
python $SCRIPT

# 生成指定日期的周报
python $SCRIPT --date 2026-01-15

# 生成指定日期范围的周报
python $SCRIPT --start 2026-01-01 --end 2026-01-07

# 自定义输出目录（文件名自动生成）
python $SCRIPT --output-dir ~/Desktop/weekly

# 自定义输出文件完整路径（优先级最高）
python $SCRIPT --output ~/Desktop/my-report.md

# 生成周报后调用公众号发布工具（复制 HTML 到剪贴板）
python $SCRIPT --publish

# 生成周报后生成公众号预览网页（在浏览器中打开）
python $SCRIPT --preview

# 生成周报后直接发布到公众号（创建草稿）
python $SCRIPT --weixin
```

## 公众号发布集成

生成周报后可自动调用公众号发布工具：

- **`--publish`**: 调用 `md_to_html.py`，将 Markdown 转换为带公众号样式的 HTML 并复制到剪贴板
- **`--preview`**: 生成公众号预览网页，自动在浏览器中打开预览效果
- **`--weixin`**: 直接发布到公众号，使用固定封面图素材 ID 创建草稿，摘要固定为"工具动态，编程实践，编程模型，业界观点"（需配置项目根目录 `.env` 文件）

## 环境配置

### 快速开始

skill 目录下提供了 `.env.example` 模板，复制并填入实际凭证即可：

```bash
cd aicoding-news-weekly
cp .env.example .env
# 编辑 .env 填入实际值
```

### 环境变量说明

所有配置统一在 skill 目录下的 `.env` 文件中管理（已加入 `.gitignore`，不会提交到仓库）：

```bash
# ---- 飞书 API 凭证（必填） ----
# 用于调用飞书多维表格 API 获取资讯数据
# 获取方式：https://open.feishu.cn/app → 创建应用 → 凭证与基础信息
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx

# ---- 微信公众号 API 凭证（可选，仅 --weixin 模式需要） ----
# 用于通过 API 创建公众号草稿
# 获取方式：https://mp.weixin.qq.com/ → 开发 → 基本配置
# 注意：需要认证的服务号，并在公众号后台设置服务器 IP 白名单
WECHAT_APPID=你的AppID
WECHAT_APPSECRET=你的AppSecret

# ---- 输出目录配置（可选） ----
# 自定义周报文件的默认输出路径
# OUTPUT_DIR=/your/custom/path/output
```

| 变量名 | 必要性 | 说明 |
|--------|--------|------|
| `FEISHU_APP_ID` | **必填** | 飞书应用的 App ID，用于获取多维表格数据 |
| `FEISHU_APP_SECRET` | **必填** | 飞书应用的 App Secret |
| `WECHAT_APPID` | 可选 | 微信公众号 AppID，仅 `--weixin` 模式需要 |
| `WECHAT_APPSECRET` | 可选 | 微信公众号 AppSecret，仅 `--weixin` 模式需要 |
| `OUTPUT_DIR` | 可选 | 自定义周报文件的默认输出目录 |

### Python 依赖

```bash
# 基础依赖（必装）
pip install requests python-dotenv

# 公众号 HTML 预览/发布功能（--publish / --preview）
pip install markdown pygments

# 剪贴板复制功能（可选）
pip install pyperclip
```

## 示例

如果今天是 2026-01-24（周五），周报应该：

- 开始日期：2026-01-18（上周日）
- 结束日期：2026-01-24（本周六）
- 默认保存路径：`aicoding-news-weekly/output/2026-01-24.md`

**日期计算规则**：周报以本周六为结束日期，上周日为开始日期（共 7 天）

## 注意事项

- **不要降级**：必须按完整流程执行（获取数据 → 生成周报 → 发布到公众号），不得简化步骤或降低质量。遇到问题直接报告，不要自行降级处理。
- **脚本路径**：实际位于 `scripts/aicoding-news-weekly/` 子目录下，不是 skill 根目录。cron 任务和手动执行都必须用绝对路径。
- **输出位置**：默认保存到 `output/` 目录（已加入 `.gitignore`），可通过 `--output-dir` 或 `--output` 自定义
- 如果周报文件已存在，脚本会自动覆盖旧文件
- 日期格式必须严格遵循 `YYYY-MM-DD` 格式
- 确保飞书 API 凭证有效
- 使用 `--preview` 需要系统支持浏览器自动打开
- 使用 `--publish` 需要安装 `markdown` 和 `pygments` 依赖包
- 使用 `--weixin` 需要认证的服务号，并开通草稿箱和发布接口权限
