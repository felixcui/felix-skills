# 抓取失败时的手工入库（复用 collect_v2 函数，不手写记录）

适用：`collect_v2.py <URL>` 在 `[1/5] 抓取内容` 阶段就失败——`Page too large`、`bgValues.length`、SPA 返回空正文——但**网页本身还能 curl 下来**。
目标：走完与脚本完全一致的五步（摘要 → 分类 → 本地 md → 飞书记录 → IMA），不产生字段错位的脏记录。

## 为什么复用函数而不是手写 `+record-batch-create`

手写 payload 要自己拼 `fields` 与 `rows` 的顺序（`title / link / description / source / category / updatetime`）。顺序错一位，摘要就进了 `source`，而且要事后逐条回读才发现。脚本里的 `push_to_feishu()` 已经固化了这份映射；`generate_summary_with_llm()` 还带上了纯文本清洗（`_strip_markdown_markup`）——手写路径会绕过这些保证。

## 步骤

### 1. 用 curl 落盘（不要换 UA 反复重试，也不要为此开浏览器）

```bash
curl -sL -m 60 -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" \
  "<URL>" -o ~/.hermes/cache/scratch/art.html
ls -l ~/.hermes/cache/scratch/art.html      # 6MB 级页面也能拿到
```

标题/公众号名优先从页面里取，取不到再从 `web_search` 标题原文回填：

```bash
grep -oE 'var msg_title = .{0,120}' art.html | head -2
grep -oE 'var nickname = .{0,80}'  art.html | head -2
grep -oE 'var author = .{0,60}'    art.html | head -2
```

### 2. 抽正文（公众号 `#js_content`）

```python
import re, html
raw = open(path, encoding='utf-8', errors='ignore').read()
m = re.search(r'<div class="rich_media_content[^"]*"[^>]*id="js_content"[^>]*>(.*?)</div>\s*<script', raw, re.S) \
    or re.search(r'id="js_content"[^>]*>(.*)', raw, re.S)
body = m.group(1)[:400000]
body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body, flags=re.S)
body = re.sub(r'<br\s*/?>', '\n', body)
body = re.sub(r'</p>|</section>|</div>|</h\d>|</li>', '\n', body)
body = re.sub(r'<[^>]+>', '', body)
content = '\n\n'.join(l.strip() for l in html.unescape(body).split('\n') if l.strip())
```

### 3. 串起流水线

```python
import sys
sys.path.insert(0, '/Users/felix/.hermes/skills/felix-skills/skills/news-collect/scripts')
import collect_v2 as c

summary  = c.generate_summary_with_llm(content, title, 240)   # 已是纯文本
category = c.classify_article(title, summary, content)
md_path  = c.save_raw_markdown(title, c.create_markdown_content(title, author, url, summary, content))
ok, resp = c.push_to_feishu(url, title, summary, author, category=category)
c.add_to_ima_kb(url)
```

摘要过薄就按 SKILL.md「摘要过薄」一节的判据重写，然后把**同一段文字**同时写进本地 md 的 `## 摘要` 与表格 `description`（纯文本，不带 `**`）。

### 4. 回读确认

```bash
lark-cli base +record-list --base-token "Tn1vbRQyraNFvAstbqicUlIJnue" \
  --table-id "tblXp6DHjQPomXbv" --as user \
  --sort-json '[{"field":"updatetime","desc":true}]' --limit 5
```

标题必须与本文完全一致才认；`--limit 1` 常常还是上一篇（写入传播有延迟）。

## 坑

- **别用 `execute_code` 跑 `import collect_v2`**：那个解释器没有 `pyyaml`，导入即 `ModuleNotFoundError: No module named 'yaml'`。写成 `.py` 文件用 `terminal` 的系统 `python3` 跑（脚本本身就是按这个解释器写的）。
- **`add_to_ima_kb()` 成功时返回 `None`**：成功与否看它打印的 `✅ 已添加到 IMA「AI资讯」知识库`，别拿返回值判断。
- **`+record-search` 查不到拉丁缩写**：`DSH`、`RAG` 这类词常返回 count=0（分词 + 索引延迟），去重要用 `+record-list --sort-json ... --limit 500 --format ndjson --output ./recs.ndjson` 再 `grep` 短链 id。
- **回填 `description` 时从本地 md 反抽摘要，不要在手写脚本里重新粘贴长文本**：`re.search(r'## 摘要\n\n(.*?)\n\n---', s, re.S)` 取出刚写好的那段再塞进 payload，改一处只有一处真相；重抄一遍容易漏字、被 heredoc 截断，还会出现「md 与表格两版摘要」。
- **先查重再开工**：公众号常换短链重发，同标题已在表里就只回一句「已入库过、同一篇」，不要重跑整条流水线。
