#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分类器回放对比：新分类（主模型）vs 表内现有分类（旧规则的结果）。
用法: python3 eval_classify.py <records.md> <raw_dir> [N]
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

SCRIPT = Path.home() / ".hermes/skills/felix-skills/skills/news-collect/scripts/collect_v2.py"
spec = importlib.util.spec_from_file_location("cv2", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def parse_records_md(path):
    """解析 lark-cli 输出的 markdown 表：返回 [{title, category}]"""
    rows = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|") or line.startswith("| _record_id") or line.startswith("| ---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        rows.append({"title": cells[1], "category": cells[7]})
    return rows


def parse_md(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    title = ""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    summary = ""
    mm = re.search(r"## 摘要\s*\n+(.+?)\n+---", text, re.S)
    if mm:
        summary = re.sub(r"\s+", " ", mm.group(1)).strip()
    body = ""
    mb = re.search(r"## 正文\s*\n+(.+)$", text, re.S)
    if mb:
        body = re.sub(r"\s+", " ", mb.group(1)).strip()
    return title, summary, body


def norm(s):
    return re.sub(r"[\s。，、：:！!？?\-—_·|「」“”\"'（）()]", "", s or "").lower()


def main():
    rec_path, raw_dir = sys.argv[1], Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 24

    records = parse_records_md(rec_path)
    by_title = {norm(r["title"]): r["category"] for r in records}

    files = sorted(raw_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    out = []
    changed = 0
    for p in files:
        title, summary, body = parse_md(p)
        old = by_title.get(norm(title), "（表内无此条）")
        new = m.classify_article(title, summary, body)
        rule_only = m.classify_article_rules(title, summary)
        if new != old:
            changed += 1
        out.append({"file": p.name, "title": title, "old": old, "new": new,
                    "rule_only": rule_only, "changed": new != old})
        print(f"{'CHG' if new != old else '   '} | 旧:{old:<8} 新:{new:<8} | {title[:46]}")

    print(f"\n共 {len(out)} 篇，变化 {changed} 篇")
    dest = Path.home() / ".hermes/cache/scratch/replay_result.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"明细已存: {dest}")


if __name__ == "__main__":
    main()