# NotebookLM 每日维护操作手册

每日维护 cron (21:00, job_id: `60bbd91f0554`) 的 NotebookLM 相关维护操作。

## 1. 比对本地文章 vs NotebookLM 已有 source

### 方法：前缀匹配

`notebooklm source list` 的标题被截断（加 `…`），无法精确匹配。使用前缀匹配：

```bash
# 获取 NotebookLM 已有 source 的日期前缀
notebooklm source list 2>&1 | grep -E 'ready|processing|error' | awk -F'│' '{print $3}' | sed 's/^ *//;s/ *$//'
# 输出如: 2026-05-14_75K…、2026-05-15_AI…

# 获取本地 raw 文件
ls /Users/felix/work/github/media-conent/raw/*.md | xargs -n1 basename | sort
# 输出如: 2026-05-14_75Kstar的SKILL爆款仓库….md
```

比对逻辑：
1. 从 `source list` 提取所有以 `2026-` 开头的标题前缀（去掉尾部的 `…`）
2. 对每个本地 raw 文件，检查是否有 NB 前缀与之匹配
3. 无匹配的 = 缺失，需要补传

### 辅助命令：`metadata`

`notebooklm metadata 2>&1` 显示完整标题和 source 总数（如 `Sources (251)`），适合验证上传结果。但标题可能跨行换行，解析较复杂。

## 2. 补传失败文章

```bash
# 中文/特殊字符文件名需先转 ASCII
cp "/Users/felix/work/github/media-conent/raw/2026-05-14_【深度拆解】OpenClawvsHermes：多Agent架构设计.md" /tmp/nb_upload.md

# 上传
notebooklm source add /tmp/nb_upload.md
# 成功输出: Added source: <uuid>

# 清理临时文件
rm /tmp/nb_upload.md
```

### 常见失败原因

| 症状 | 原因 | 处理 |
|------|------|------|
| 空 `Error:` | 瞬态连接失败 | 等几秒重试 |
| 持续空 `Error:` | Google 认证过期 | `notebooklm login` |
| 中文文件名失败 | 特殊字符 | cp 为 ASCII 名再传 |
| `status code 5 (Not found)` | 账号路由冲突 | 见下方说明 |
| `Failed to get SOURCE_ID` | Source 数量上限 | 新建笔记本 |

### 账号路由冲突（account routing mismatch）

**症状**：`notebooklm source list`、`notebooklm use <id>`、`notebooklm source add` 均返回 `RPC rLM1Ne returned null result with status code 5 (Not found)`。错误信息提到多 Google 账号登录导致请求路由到错误账号。

**关键特征**：`notebooklm doctor` 全部通过（auth、migration、config 均绿），但实际操作仍失败。`notebooklm list` 可能正常返回笔记本列表，但无法进入具体笔记本。

**诊断**：`notebooklm -vv source list` 日志显示 RPC 成功发出并获得响应，但响应中 result 为 null + status 5。

**已知 issue**：#114、#294（notebooklm CLI 仓库）。

**处理**：
1. 在浏览器中登出多余的 Google 账号，只保留一个
2. 或设置 `authuser` 参数指定正确的账号索引（如 profile 配置中设置）
3. 临时绕过：如果 `/opt/homebrew/bin/notebooklm` 遇到此问题，尝试 `/opt/homebrew/bin/python3.14 -m notebooklm`（反之亦然）

### 诊断命令

```bash
notebooklm doctor          # 检查 auth 状态
notebooklm auth check --test  # 含 token fetch 测试
notebooklm -vv source list    # 详细调试日志
```

## 3. 清理垃圾 source

`collect_v2.py` 和手动上传会产生 `notebooklm_upload_*`、`upload_b2_*`、`upload_b3_*`、`tmp*` 等残留 source。

### 删除方式

```bash
# 方式 1: delete-by-title（推荐）
notebooklm source delete-by-title "notebooklm_upload_0.md" -y

# 方式 2: 如果 delete-by-title 报 "matches 2 sources"
# 错误信息中会包含完整 UUID:
#   Error: Title 'notebooklm_upload_0.md' matches 2 sources. Delete by ID instead:
#   9b93f4fa-0bd9... not
#   cff153b6-7bce... not
# 从错误中提取完整 UUID，然后用:
notebooklm source delete "<full-uuid>"
```

### ⚠️ 注意：source list 的 ID 被截断

`source list` 输出的 ID 形如 `9b93f4f…`，不能直接用于 `source delete`（会报 `No source found`）。必须通过 `delete-by-title` 或从其错误信息中获取完整 UUID。

## 4. 关键 Notebook ID

- **AI 资讯 V2** notebook: `8c8a9ffe-89c1-4219-a6ee-cd2f9bb4f3e0`（当前使用，旧笔记本 87c6e099 已满 273 sources）
- 始终使用完整 ID，不要用名称匹配（不可靠）

## 4.1 NotebookLM CLI 路径

系统上有两个 NotebookLM CLI 入口：
- `/opt/homebrew/bin/python3.14 -m notebooklm` — Python 3.14 模块版本（`collect_v2.py` 使用此路径）
- `/opt/homebrew/bin/notebooklm` — Homebrew 安装的独立二进制

维护任务中两者均可使用，效果相同。如果其中一个遇到 account routing 问题，可尝试另一个。

## 5. 实战比对脚本（Python/execute_code）

前缀匹配在实际执行中的工作模式：

```python
from hermes_tools import terminal

# 1. 获取 NB source titles（截断格式如 "2026-05-14_75K…"）
nb_result = terminal("notebooklm source list 2>&1")
nb_prefixes = set()
for line in nb_output.split('\n'):
    if '│' in line and ('📝' in line or '❓' in line):
        parts = [p.strip() for p in line.split('│')]
        if len(parts) >= 3:
            title = parts[2].strip()
            if title and title != 'Title':
                clean = title.rstrip('…').strip()  # 去掉截断标记
                if clean:
                    nb_prefixes.add(clean)

# 2. 获取本地文件
result = terminal("ls /Users/felix/work/github/media-conent/raw/2026-*_*.md")
local_files = [line.strip().split('/')[-1] for line in result['output'].strip().split('\n') if line.strip()]

# 3. 前缀比对：检查本地文件名是否以 NB 前缀开头
missing = []
for f in local_files:
    found = any(f.startswith(p) or p.startswith(f[:len(p)])) for p in nb_prefixes)
    if not found:
        missing.append(f)
```

**注意**：NB 标题在终端中被截断到约 20 个字符（含日期前缀），所以前缀长度约为 16-20 字符。中文字符每个占更多列宽，实际可见前缀可能更短。

## 6. 飞书维护报告格式

每日维护汇总报告发送到飞书时，用户指定了严格的格式要求：

- ❌ **不要**贴终端原始输出（git log、git status 等）
- ❌ **不要**用大段代码块包裹报告
- ✅ 使用 emoji + **粗体标题** + 短列表
- ✅ 每个维护项一行结果

格式模板：
```
🔧 **每日维护巡检报告** — YYYY-MM-DD

✅ **Wiki同步**: 上传 N 篇文章 / 无新增文章
✅ **Git提交**: 已推送 / 无变更
⚠️ **IMA清理**: 清理 X 项 / 无异常
✅ **NotebookLM补传**: 补传 N 篇 / 无遗漏
📊 **总结**: 一句话概括
```

发送方式（使用 temp file 避免 shell 转义问题）：
```python
import tempfile, os
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
    f.write(report_markdown)
    tmp = f.name
terminal(f'lark-cli im +messages-send --chat-id oc_a6df6042719de06719348cc64642cb88 --markdown "$(cat {tmp})" --as bot')
os.unlink(tmp)
```

## 7. Source 数量上限

Google NotebookLM 单个 notebook 的 source 数量上限约为 **300**。当接近上限时，需要清理旧 source 或拆分 notebook。
