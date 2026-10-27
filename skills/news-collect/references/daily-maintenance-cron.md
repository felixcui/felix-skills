# 每日维护 Cron 任务编排手册

Cron job_id: `60bbd91f0554`，每日 21:00 执行。详细操作见下方各子参考文件。

## 维护任务（按执行顺序）

> ⚠️ 2026-10-27：用户要求删除本地 `~/wiki`（LLM Wiki 仓库，内容已全部推送到 github.com/felixcui/llm-wiki）。**「Wiki 同步」这一项已取消**，不要再复制文件到该目录、也不要重建它。

### 1. Git 提交（media-conent）
- `cd /Users/felix/work/github/media-conent` → `git add -A && git commit && git push`
- commit message: `文章同步 YYYY-MM-DD`
- 如果 working tree clean，标记为"无变更"

### 2. IMA 知识库清理
- 仅做认证检查（`import_urls` 返回 code:51 = 正常）
- API 列表端点（`list_by_wiki`、`get_wiki_info`）返回 404，无法枚举已有文章；列内容改用 `get_knowledge_list`
- 详见 → [ima-maintenance.md](ima-maintenance.md)

### 3. NotebookLM 补传
- 比对本地 raw vs NotebookLM source list，找出缺失文章
- 修复 error 状态 source（删除 + 重新上传）
- 清理垃圾 source（临时文件名残留）
- 详见 → [notebooklm-maintenance.md](notebooklm-maintenance.md)

## ⚠️ 重要：报告格式要求

最终报告通过飞书发送，**必须使用飞书友好的富文本格式**：

1. **不要输出终端命令原始输出**（禁止贴 git log、git status、curl 响应等）
2. **不要用大段代码块**包裹报告
3. 使用简洁的 emoji + 粗体标题 + 短列表
4. 每个维护项一行结果，格式：
   - ✅ **Wiki同步**: 上传 3 篇文章
   - ✅ **Git提交**: 已推送
   - ⚠️ **IMA清理**: 无异常
   - ✅ **NotebookLM补传**: 补传 1 篇
5. 全部成功时用一句总结即可，不需要展开细节

## 关键配置

| 项目 | 值 |
|------|-----|
| Notebook ID (V3) | `b08626a7-cda5-4dd2-b0e7-536eafb48274` |
| IMA KB ID | `ima_kb_e7ouOFmL`（旧 base64 串已失效，见 `references/ima-maintenance.md`） |
| ~~Wiki 仓库~~ | `~/wiki` 已于 2026-10-27 删除，勿重建 |
| Raw 目录 | `/Users/felix/work/github/media-conent/raw` |
| CLI 路径 | `/opt/homebrew/bin/python3.14 -m notebooklm` |
