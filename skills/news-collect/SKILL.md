---
name: news-collect
description: "一站式资讯收集工具 V2：抓取文章 → 生成摘要 → 推送飞书 → 上传NotebookLM → 生成多种格式。支持微信公众号、普通网页、Twitter/X，完全自动化处理。"
metadata: { "openclaw": { "emoji": "📰", "requires": { "bins": ["python3"] } } }
---

# News Collect V2 - 增强版资讯收集工具

一个脚本完成所有操作：抓取文章 → 生成摘要 → 推送飞书 → 上传NotebookLM → 生成多种格式

## 🆕 V2 新增功能

- ✅ **NotebookLM 深度集成**：自动上传到「AI 资讯」笔记本
- ✅ **多格式生成**：支持报告、思维导图、PPT、播客、Quiz
- ✅ **批量处理**：支持从文件批量处理多个URL
- ✅ **改进的微信抓取**：使用requests+BeautifulSoup，更稳定
- ✅ **智能输出控制**：灵活选择推送目标（飞书/NotebookLM/两者）
- ✅ **默认投递**：在无特殊说明时，默认同时推送到飞书、IMA 和 NotebookLM

## 功能特点

- ✅ **一站式处理**：一个命令完成抓取、摘要、推送全流程
- ✅ **多引擎摘要**：默认使用 GLM API 生成摘要，支持 Claude Code 和纯规则引擎
- ✅ **支持多源**：微信公众号、普通网页、Twitter/X 自动识别
- ✅ **自动降级**：LLM 不可用时自动使用规则生成摘要
- ✅ **自动推送**：支持飞书 webhook 推送
- ✅ **NotebookLM 集成**：直接上传并生成多种格式

## 前置要求

- Python 3.6+
- Hermes 配置文件中有 GLM API key（`~/.hermes/config.yaml`，默认摘要引擎自动读取）
- NotebookLM CLI（Python 3.14 版本，可选）
- requests、beautifulsoup4、pyyaml 库

安装依赖：
```bash
pip3 install requests beautifulsoup4 pyyaml
```

## 使用方法

### 基础用法（抓取 + 摘要 + 飞书/IMA/NotebookLM 全量分发）

```bash
python3 scripts/collect_v2.py <文章URL>
```

> 默认情况下，如无额外说明，脚本会将结果同时推送到飞书、IMA 和 NotebookLM。

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

### 选择摘要引擎

```bash
# GLM API（默认，速度快）
python3 scripts/collect_v2.py <URL> --summary-engine glm

# Claude Code（高质量，需安装 claude CLI）
python3 scripts/collect_v2.py <URL> --summary-engine claude

# 纯规则提取（无 API 调用）
python3 scripts/collect_v2.py <URL> --summary-engine rule
```

> GLM API 配置自动从 `~/.hermes/config.yaml` 读取。如果 GLM 不可用（余额不足、网络等），自动降级为规则提取。

### 调整摘要长度

```bash
python3 scripts/collect_v2.py <URL> --summary-length 150
```

### 自定义文章保存路径

```bash
python3 scripts/collect_v2.py <URL> --output-dir ~/Desktop/my_news
```
> 默认会将抓取的文章 Markdown 存储到 `~/work/github/media-conent/raw` 目录中。支持 `~/` 写法。

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
✅ 文件已保存到 /tmp/news-collect_output

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

| 来源类型 | 自动识别 | 支持内容 | NotebookLM | IMA |
|---------|---------|---------|-----------|-----|
| 微信公众号 | ✅ | 标题、作者、发布时间、正文 | ✅ | ✅ |
| 普通网页 | ✅ | 标题、正文 | ✅ | ✅ |
| Twitter/X 推文 | ✅ | 标题、作者、正文、互动数据 | ✅ | ❌ |
| X Article 长文 | ✅ | 完整长文标题、正文、作者、互动数据 | ✅ | ❌ |
| 飞书文档 | ✅ | 标题、正文 | ✅ | ✅ |

> ⚠️ IMA 无法解析 X/Twitter 页面（返回 ret_code 220001），Twitter 相关 URL 已自动跳过 IMA 导入。

## 配置

### NotebookLM 配置

默认使用 Python 3.14 版本的 NotebookLM：
```python
NOTEBOOKLM = "/opt/homebrew/bin/python3.14 -m notebooklm"
NOTEBOOK_ID = "87c6e099-77f1-4727-8d82-92ac00e29cf7"  # "AI 资讯" notebook
NOTEBOOK_NAME = "AI 资讯"
```

> ⚠️ **始终使用 NOTEBOOK_ID 而非 NOTEBOOK_NAME**。名称匹配经常返回 `No notebook found`，且 `notebooklm list` 输出的 ID 可能被截断导致 `account-routing mismatch` 错误。硬编码完整 ID 是最可靠的方式。

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

IMA OpenAPI 只支持 **URL 导入**（`/openapi/wiki/v1/import_urls`），不支持本地文件上传。IMA 无法解析 X/Twitter 页面（返回 ret_code 220001），代码中已自动排除 Twitter URL。支持的来源：公众号、飞书文档、通用网页等公网可访问 URL。

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
| `--summary-engine` | 摘要引擎：glm(默认) / claude / rule | glm |
| `--notebook` | 上传到 NotebookLM | False |
| `--format` | NotebookLM 生成格式 | - |
| `--batch` | 批量处理URL文件 | - |

## 工作流程

### 完整流程（NotebookLM 模式）

1. **抓取内容** - 自动识别来源类型并抓取
2. **生成摘要** - 默认使用 GLM API，支持 `--summary-engine` 切换
3. **创建 Markdown** - 标准化格式
4. **上传 NotebookLM** - 自动创建「AI 资讯」笔记本并上传
5. **生成格式** - 根据参数生成报告/思维导图/PPT/播客/Quiz
6. **下载文件** - 下载生成的文件到 `/tmp/news-collect_output`
7. **推送飞书** - 推送摘要到飞书 webhook
8. **添加 IMA** - 添加文章 URL 到 IMA 知识库（所有公网 URL 均尝试）

### 标准流程（默认全量分发）

1. **抓取内容**
2. **生成摘要**
3. **创建 Markdown**
4. **上传 NotebookLM**
5. **推送飞书**
6. **添加 IMA**（公众号 / 飞书文档 / 通用 URL；X/Twitter 自动跳过）

> ⚠️ Wiki 同步已从收集流程中移除，改为每日例行维护任务（21:00）统一批量同步。

### 摘要引擎失败与降级

GLM API 偶发返回 `None` 导致 `TypeError: object of type 'NoneType' has no len()` 错误。此时需用 `--summary-engine rule` 重跑：

```bash
python3 scripts/collect_v2.py <URL> --summary-engine rule
```

### 摘要引擎认证失败

脚本的摘要引擎动态读取 `~/.hermes/config.yaml` 中的模型配置：

```python
model.base_url   → API endpoint
model.api_key    → 鉴权密钥
model.default    → 模型名称
```

**症状及原因：**

| 错误 | 原因 | 处理 |
|------|------|------|
| `返回错误 (401)` | API key 无效/过期 | key 错误或失效，需更换 |
| `返回错误 (429)` | 速率限制/余额不足 | 充值或等待 |
| `余额不足` | 账户余额用完 | 到对应平台充值 |

**诊断：** 从 config.yaml 中提取配置并测试：

```bash
# 读取当前配置
grep -A4 '^model:' ~/.hermes/config.yaml

# 直接用 curl 测试（替换为实际值）
curl -s "$(grep 'base_url' ~/.hermes/config.yaml | head -1 | awk '{print $2}')/chat/completions" \
  -H "Authorization: Bearer $(grep 'api_key' ~/.hermes/config.yaml | head -1 | awk '{print $2}')" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$(grep 'default:' ~/.hermes/config.yaml | head -1 | awk '{print $2}')\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}"
```

**修复：**
1. 更换 `~/.hermes/config.yaml` 中 `model.api_key` 为有效的 key
2. 或切换 provider（修改 `model.provider`、`model.base_url`、`model.api_key`、`model.default`）
3. 注意：Hermes Agent 本身可能走另一条鉴权路径（如环境变量或 providers 配置），config.yaml 中的 key 失效时脚本会降级为规则摘要

## 常见问题与解决方案

### NotebookLM 上传失败后怎么办？

白天采集时 NotebookLM 上传失败（网络抖动、认证过期等）**无需手动干预**。每日 21:00 的「例行维护」cron 任务（job_id: `60bbd91f0554`）包含维护项 4「NotebookLM 补传失败文章」，会自动：
1. 对比本地 raw 文章与 NotebookLM 已上传列表
2. 补传所有遗漏文章（中文文件名自动转 ASCII 临时文件名）
3. 失败重试 2 次

如连续多次失败，可能是认证过期，需手动执行 `/opt/homebrew/bin/python3.14 -m notebooklm login`。

### 飞书 Wiki 链接抓取不完整

`collect_v2.py` 对飞书 Wiki 链接（`my.feishu.cn/wiki/` 或 `waytoagi.feishu.cn/wiki/`）可能抓取不完整（需要登录态），表现为文件只有十几行、标题为"未知标题"。

**解决流程**：
1. 用 `lark-cli docs +fetch --doc "<token或URL>" --format json --limit 10000` 获取完整内容
2. 用 Python 清理飞书特殊标签（`<image>`、`<view>`、`<file>`），替换 unicode 转义
3. 手动重建 markdown 文件（带标准 frontmatter：标题、来源、摘要、正文）
4. NotebookLM 上传时，中文文件名可能导致失败，需先 `cp` 为 ASCII 文件名再上传

### 微信文章反爬（requests 抓取失败）

部分微信公众号文章会被反爬保护拦截，`requests+BeautifulSoup` 抓取后返回"未知标题"/"未知作者"，正文为页面底部交互元素（点赞、在看等）。

**诊断信号**：`collect_v2.py` 输出 `✅ 抓取成功: 未知标题`，GLM 摘要判断"无实质性文章内容"。

**修复流程**（浏览器辅助抓取）：
1. 用 `browser_navigate` 打开文章 URL
2. 用 `browser_snapshot(full=True)` 获取完整页面快照
3. 从快照中提取标题（`heading` 元素）、作者、正文（`StaticText` 节点拼接）
4. 手动构建 Markdown（含 frontmatter），保存到 `~/work/github/media-conent/raw/`
5. 用 `requests` 分别推送飞书 webhook、NotebookLM（`notebooklm source add`）、IMA（`/openapi/wiki/v1/import_urls`）

**注意**：这种情况较少见（约 5-10% 的公众号文章），大部分文章 requests 可正常抓取。无需为此改动 `collect_v2.py` 的默认抓取逻辑。

### X/Twitter 抓取

`collect_v2.py` 使用 twitter CLI（`/Users/felix/.local/bin/twitter`）抓取 X 内容，支持普通推文和 X Article 长文。

**支持的 URL 格式**：
- `https://x.com/<user>/status/<id>` — 普通推文
- `https://x.com/i/article/<id>` — X Article 长文链接

**Article 长文**：twitter CLI 返回的 JSON 中包含 `articleTitle` 和 `articleText` 字段，脚本自动检测并使用完整长文内容（可达 10000+ 字符）作为正文，标题使用 `articleTitle`。

**普通推文**：使用 `text` 字段作为正文，标题格式为 `@<screenName> 的推文`。

**附加信息**：正文末尾自动追加互动数据（❤️ likes / 🔁 retweets / 👁 views / 🔖 bookmarks）。

**作者格式**：`Name (@screenName)`。

**时间解析**：优先使用 `createdAtISO`（ISO 格式自动转本地时区），回退到 `createdAt`（Unix 时间戳）。

**已知限制**：
- twitter CLI 偶尔超时（已设 60s 超时），重跑即可
- 推文不存在或不可访问时返回明确错误
- twitter CLI 不稳定（用户要求不替换为 opencli），如超时可重试

**twitter CLI 数据结构**（供手动调试）：
```bash
/Users/felix/.local/bin/twitter tweet <URL> --json
```
关键字段：`author.screenName`、`author.name`、`text`、`createdAtISO`、`articleTitle`（可选）、`articleText`（可选）、`metrics.likes/retweets/views/bookmarks`。返回 `{"ok": true, "data": [tweet, ...]}`，第一条为主推文。

**IMA 认证调试**：IMA API 使用自定义 header `ima-openapi-clientid` 和 `ima-openapi-apikey`（非标准 `X-Api-Key` / `X-Client-Id`）。验证 API 可用性时用空 URL 列表测试：
```bash
curl -s -X POST "https://ima.qq.com/openapi/wiki/v1/import_urls" \
  -H "Content-Type: application/json" \
  -H "ima-openapi-clientid: $(cat ~/.config/ima/client_id)" \
  -H "ima-openapi-apikey: $(cat ~/.config/ima/api_key)" \
  -d '{"knowledge_base_id":"AGoC5oEY8FP12VotR1kff00HlmJyh3RP6Do9vCGKpGQ=","urls":[]}'
```
返回 `code:51`（URL 列表不能为空）= 认证正常。返回 `code:200002` = header 名错误。

### NotebookLM `--notebook` 名称匹配失败

`notebooklm source add --notebook "AI 资讯"` 或 `notebooklm source list --notebook "AI 资讯"` 可能返回 `No notebook found starting with 'AI 资讯'`，即使笔记本确实存在。

**解决**：使用完整 notebook ID 而非名称。ID 为 `87c6e099-77f1-4727-8d82-92ac00e29cf7`。

```bash
# ❌ 不可靠 — 经常失败
notebooklm source list --notebook "AI 资讯"

# ✅ 可靠 — 始终使用完整 ID
notebooklm source list --notebook "87c6e099-77f1-4727-8d82-92ac00e29cf7"
```

**注意**：`notebooklm list` 输出的 ID 可能被终端截断（如 `87c6e099-77f1-4727-8d82`），使用截断 ID 会导致 `account-routing mismatch` RPC 错误。

### 微信公众号反爬导致抓取失败（"未知标题"）

部分微信公众号文章使用反爬机制，requests+BeautifulSoup 抓取时返回"未知标题"/"未知作者"，GLM 摘要判断为"无实质性文章内容"。此时需要浏览器辅助抓取：

**诊断**：脚本输出 `✅ 抓取成功: 未知标题` 或 GLM 摘要说"只是社交平台界面交互提示语"。

**修复流程**：
1. 用 `browser_navigate` 打开 URL，获取完整页面快照
2. 从快照中提取标题、作者、正文内容
3. 手动构建 Markdown 文件（含 frontmatter）
4. 用 `requests.post` 推送飞书 webhook、`terminal()` 调 NotebookLM CLI、`requests.post` 调 IMA API

**注意**：这不是所有微信文章都会触发，只有部分有反爬保护的文章。大多数情况下 `collect_v2.py` 能正常抓取。

### NotebookLM 上传失败（综合）

NotebookLM 上传有约 20-30% 的偶发失败率（空错误信息），脚本已内置自动重试（3次，递增等待 3s/6s）。即使重试后仍失败的文章，**不需要立即手动补传**——每日 21:00 例行维护 cron 任务（job_id: 60bbd91f0554）的「维护项 4：NotebookLM 补传失败文章」会自动检测并补传当日遗漏。

**原因1：Google 认证过期**（最常见）

症状：`notebooklm list` 或 `source add` 返回空 `Error:`，`-vv` 日志显示 CSRF token 获取失败。

诊断：`/opt/homebrew/bin/python3.14 -m notebooklm doctor` 确认 auth 状态。

修复：`/opt/homebrew/bin/python3.14 -m notebooklm login`（需浏览器交互）。

**原因2：中文文件名 + 特殊字符**

**原因2：中文文件名**

含括号等特殊字符可能导致 `Error:`。解决：先复制为 ASCII 文件名再上传。

```bash
cp "中文文件名.md" /tmp/english-name.md
/opt/homebrew/bin/python3.14 -m notebooklm source add /tmp/english-name.md
```

## 文件结构

```
news-collect/
├── SKILL.md                    # 技能文档
└── scripts/
    ├── collect_v2.py            # ⭐ V2 主脚本（增强版）
    ├── collect.py                # V1 原版（保留兼容）
    ├── fetch_feishu_wiki.py     # 飞书 Wiki 抓取辅助
    └── fetch_content.py          # 旧版（保留兼容）
```

## 更新日志

### v2.1 (2026-05-09)
- 🔧 改进：X/Twitter 抓取全面优化 — 使用完整路径 `/Users/felix/.local/bin/twitter`，支持 X Article 长文（`articleTitle`/`articleText`），修正字段名（`screenName`），使用 `createdAtISO` 时间解析，附加互动数据
- 🆕 新增：`is_twitter_url` 支持 `/i/article/` 长文链接匹配
- 🔧 改进：超时从 30s 增加到 60s，增加空列表保护和 JSON 解析错误捕获
- 🔧 改进：IMA 知识库移除公众号限制（公众号、飞书文档、通用 URL 均可导入），但排除 X/Twitter（IMA 无法解析其页面）

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
