# NotebookLM 每日维护操作手册

每日维护 cron (21:00) 的 NotebookLM 相关操作。

## 1. 获取 Notebook ID

⚠️ **中文名匹配失败**：`notebooklm source list --notebook "AI 资讯 V2"` 会报找不到。必须使用 UUID。

```bash
# 获取完整 notebook 列表（含完整 UUID）
notebooklm list --json

# 从 JSON 中提取目标 notebook 的 ID（例如 AI 资讯 V2）
# 输出中 id 字段就是完整 UUID，如 8c8a9ffe-89c1-4219-a6ee-cd2f9bb4f3e0
```

## 2. 比对本地文章 vs NotebookLM 已有 source

```bash
# 列出 notebook 所有 source（含标题）
notebooklm source list --notebook "<FULL_UUID>" --json > /tmp/nlm_sources.json

# ⚠️ 不能直接 pipe 到 python3（会被安全扫描拦截 pipe_to_interpreter）
# 必须 redirect 到文件，再处理

# 检查非 ready 状态的 source
grep '"status"' /tmp/nlm_sources.json | grep -v '"status": "ready"'
```

## 3. 清理残留 source

常见残留文件名模式（均需清理）：
- `nb_upload_missing.md` — 补传追踪产物，上传后应删除
- `notebooklm_upload_*` — 上传临时文件
- `upload_b2_*` / `upload_b3_*` — 批量上传残留

```bash
# 删除 source（注意：source ID 是位置参数，不是 --source-id）
notebooklm source delete --notebook "<FULL_UUID>" -y "<SOURCE_ID_PREFIX>"
```

> 💡 `notebooklm source delete` 的子命令语法：
> - `notebooklm source delete [OPTIONS] SOURCE_ID` — SOURCE_ID 是必选位置参数
> - `-y` 跳过确认
> - 支持 partial ID（如 "72ac580a" 匹配 "72ac580a-f447-..."）
> - **不是** `--source-id`，会报错

## 4. 补传今日文章

```bash
# 逐篇上传，中文文件名需先 cp 为 ASCII 临时名
for f in /Users/felix/work/github/media-conent/raw/2026-06-05_*.md; do
  ascii_name=$(basename "$f" | iconv -f utf-8 -t ascii//TRANSLIT//IGNORE | tr -d ' ')
  cp "$f" "/tmp/$ascii_name"
  notebooklm source add --notebook "<FULL_UUID>" --file "/tmp/$ascii_name"
done
```

## 5. 已知限制

- 每个 NotebookLM notebook 的 source 数量有上限（目前 122 个 source 运行正常）
- 中文文件名可能导致上传失败，需先重命名为 ASCII
- `--notebook` 参数不支持中文模糊匹配，必须用完整 UUID
