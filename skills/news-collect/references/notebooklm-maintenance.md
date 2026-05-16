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

- **AI 资讯** notebook: `87c6e099-77f1-4727-8d82-92ac00e29cf7`
- 始终使用完整 ID，不要用名称匹配（不可靠）

## 5. Source 数量上限

Google NotebookLM 单个 notebook 的 source 数量上限约为 **300**。当接近上限时，需要清理旧 source 或拆分 notebook。
