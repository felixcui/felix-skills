---
name: news-collect-v2
description: "一站式资讯收集工具 V2：抓取文章 → 生成摘要 → 推送飞书 → 上传NotebookLM → 生成多种格式。支持微信公众号、普通网页、Twitter/X，完全自动化处理。"
metadata: { "openclaw": { "emoji": "📰", "requires": { "bins": ["python3", "openclaw", "claude"] } } }
---

# News Collect V2 - 增强版资讯收集工具

一个脚本完成所有操作：抓取文章 → 生成摘要 → 推送飞书 → 上传NotebookLM → 生成多种格式

## 🆕 V2 新增功能

- ✅ **NotebookLM 深度集成**：自动上传到「AI 资讯」笔记本
- ✅ **多格式生成**：支持报告、思维导图、PPT、播客、Quiz
- ✅ **批量处理**：支持从文件批量处理多个URL
- ✅ **改进的微信抓取**：使用requests+BeautifulSoup，更稳定
- ✅ **智能输出控制**：灵活选择推送目标（飞书/NotebookLM/两者）

## 功能特点

- ✅ **一站式处理**：一个命令完成抓取、摘要、推送全流程
- ✅ **大模型摘要**：使用 Claude Code 生成高质量摘要
- ✅ **支持多源**：微信公众号、普通网页、Twitter/X 自动识别
- ✅ **自动降级**：如果大模型不可用，自动使用规则生成摘要
- ✅ **自动推送**：支持飞书 webhook 推送
- ✅ **NotebookLM 集成**：直接上传并生成多种格式

## 前置要求

- Python 3.6+
- OpenClaw CLI 或 Claude Code CLI（用于生成摘要）
- NotebookLM CLI（新增，Python 3.14 版本）
- requests 库：`pip install requests beautifulsoup4`

安装依赖：
```bash
pip install requests beautifulsoup4
```

## 使用方法

### 基础用法（抓取 + 摘要 + 飞书推送）

```bash
python3 scripts/collect_v2.py <文章URL>
```

示例：
```bash
python3 scripts/collect_v2.py "https://mp.weixin.qq.com/s/nhzMNSc_-TQefSLz9Gb08A"
```

### 上传到 NotebookLM

```bash
python3 scripts/collect_v2.py <URL> --notebook
```

### 生成 NotebookLM 格式

```bash
# 生成报告
python3 scripts/collect_v2.py <URL> --notebook --format report

# 生成思维导图
python3 scripts/collect_v2.py <URL> --notebook --format mind-map

# 生成 PPT
python3 scripts/collect_v2.py <URL> --notebook --format slide-deck

# 生成播客
python3 scripts/collect_v2.py <URL> --notebook --format audio

# 生成 Quiz
python3 scripts/collect_v2.py <URL> --notebook --format quiz
```

### 批量处理

```bash
# 创建URL文件
echo "https://mp.weixin.qq.com/s/url1" > urls.txt
echo "https://example.com/article2" >> urls.txt

# 批量处理
python3 scripts/collect_v2.py --batch urls.txt
```

### 仅抓取不推送

```bash
python3 scripts/collect_v2.py <URL> --no-push
```

### 自定义 webhook

```bash
python3 scripts/collect_v2.py <URL> --webhook "https://your-webhook-url"
```

### 调整摘要长度

```bash
python3 scripts/collect_v2.py <URL> --summary-length 150
```

## 输出示例

### 基础输出（仅飞书推送）
```
🚀 开始处理: https://mp.weixin.qq.com/s/...
============================================================

[1/5] 抓取内容...
✅ 抓取成功: 🦞 写作、排版、发布一条龙...
   作者: AI工具进化论

[2/5] 生成摘要...
   使用 Claude Code 生成摘要...
   生成摘要完成 (156字)
✅ 摘要生成完成 (156字)

[3/5] 创建 Markdown...
✅ Markdown 创建完成

[4/5] 推送到飞书...
✅ 推送成功！

[5/5] 添加到 IMA 知识库...
   ✅ 已添加到 IMA「AI资讯」知识库

============================================================
📋 处理结果:
============================================================
{
  "url": "https://mp.weixin.qq.com/s/...",
  "title": "🦞 写作、排版、发布一条龙...",
  "author": "AI工具进化论",
  "summary": "作者分享了使用OpenClaw+Claude Code+wenyan-cli搭建全自动化公众号写作系统的经验...",
  "notebooklm": false
}

✨ 完成!
```

### NotebookLM 输出
```
🚀 开始处理: https://mp.weixin.qq.com/s/...
============================================================

[1/5] 抓取内容...
✅ 抓取成功: Harness Engineering详解

[2/5] 生成摘要...
   使用 Claude Code 生成摘要...
   生成摘要完成 (156字)
✅ 摘要生成完成 (156字)

[3/5] 创建 Markdown...
✅ Markdown 创建完成

[4/5] 上传到 NotebookLM...
   创建 NotebookLM 笔记本「AI 资讯」...
   ✅ 笔记本创建成功
   上传到 NotebookLM...
   ✅ 上传成功

[5/5] 生成 NotebookLM 格式...
   生成 report...
   ✅ report 生成已启动

等待生成完成（约30秒）...
   下载 report...
   ✅ 下载成功
✅ 文件已保存到 /tmp/news_collect_output

[5/5] 推送到飞书...
✅ 推送成功！

[5/5] 添加到 IMA 知识库...
   ✅ 已添加到 IMA「AI资讯」知识库

============================================================
📋 处理结果:
============================================================
{
  "url": "https://mp.weixin.qq.com/s/...",
  "title": "Harness Engineering详解",
  "author": "Friday",
  "summary": "Ryan Lopopolo在伦敦这场演讲里，真正讲透的不是\"code is free\"...",
  "notebooklm": true
}

✨ 完成!
```

## 支持的来源

| 来源类型 | 自动识别 | 支持内容 | NotebookLM |
|---------|---------|---------|-----------|
| 微信公众号 | ✅ | 标题、作者、发布时间、正文 | ✅ |
| 普通网页 | ✅ | 标题、正文 | ✅ |
| Twitter/X | ✅ | 标题、作者、正文 | ✅ |

## 配置

### NotebookLM 配置

默认使用 Python 3.14 版本的 NotebookLM：
```python
NOTEBOOKLM = "/opt/homebrew/bin/python3.14 -m notebooklm"
NOTEBOOK_NAME = "AI 资讯"
```

首次使用前请确保已完成 NotebookLM 认证：
```bash
/opt/homebrew/bin/python3.14 -m notebooklm login
```

### 飞书 Webhook 配置

```python
WEBHOOK_URL = "https://www.feishu.cn/flow/api/trigger-webhook/4ebcdc4fd26c38187fdd74434d17a916"
```

发送字段：
- `url`: 文章链接
- `title`: 文章标题
- `summary`: 生成的摘要（由大模型生成）

### IMA 知识库配置

```python
IMA_KB_ID = "AGoC5oEY8FP12VotR1kff00HlmJyh3RP6Do9vCGKpGQ="
IMA_CONFIG_PATH = Path.home() / ".config" / "ima"
IMA_API_BASE = "https://ima.qq.com"
```

## 参数说明

| 参数 | 说明 | 默认值 |
|-----|------|-------|
| `url` | 文章URL（支持多个） | - |
| `--webhook` | 自定义飞书webhook | 内置地址 |
| `--no-push` | 不推送到飞书，仅输出结果 | False |
| `--summary-length` | 摘要最大长度 | 200 |
| `--notebook` | 上传到 NotebookLM | False |
| `--format` | NotebookLM 生成格式 | - |
| `--batch` | 批量处理URL文件 | - |

## 工作流程

### 完整流程（NotebookLM 模式）

1. **抓取内容** - 自动识别来源类型并抓取
2. **生成摘要** - 使用 Claude Code 高质量摘要
3. **创建 Markdown** - 标准化格式
4. **上传 NotebookLM** - 自动创建「AI 资讯」笔记本并上传
5. **生成格式** - 根据参数生成报告/思维导图/PPT/播客/Quiz
6. **下载文件** - 下载生成的文件到 `/tmp/news_collect_output`
7. **推送飞书** - 推送摘要到飞书 webhook
8. **添加 IMA** - 添加微信文章到 IMA 知识库

### 标准流程（仅飞书推送）

1. **抓取内容**
2. **生成摘要**
3. **创建 Markdown**
4. **推送飞书**
5. **添加 IMA**

## 文件结构

```
news_collect/
├── SKILL.md                    # 技能文档
└── scripts/
    ├── collect_v2.py            # ⭐ V2 主脚本（增强版）
    ├── collect.py                # V1 原版（保留兼容）
    ├── fetch_feishu_wiki.py     # 飞书 Wiki 抓取辅助
    └── fetch_content.py          # 旧版（保留兼容）
```

## 更新日志

### v2.0 (2026-04-20)
- ✨ 新增：NotebookLM 深度集成
- ✨ 新增：支持生成报告、思维导图、PPT、播客、Quiz
- ✨ 新增：批量处理功能
- 🔧 改进：微信文章抓取稳定性
- 🔧 改进：智能输出控制（灵活选择推送目标）
- 🔧 改进：摘要生成逻辑优化

### v1.0
- 基础功能：抓取、摘要、推送
- 支持微信公众号、网页、飞书 Wiki
- IMA 知识库集成
