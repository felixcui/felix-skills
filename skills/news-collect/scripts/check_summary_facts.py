#!/usr/bin/env python3
"""摘要数字回检：把「## 摘要」里出现的每个数字，拿到「## 正文」里核对一遍。

背景：摘要模型会写出「像那么回事」的精确数字（准确率从 60% 提到 90%、某个名次、
某个奖项），而原文根本没有。写回表格之前跑一次，比人工扫一眼可靠。

用法：
    python3 check_summary_facts.py <raw.md>
    python3 check_summary_facts.py <raw.md> --summary "要检查的摘要原文"

退出码：0 = 全部命中；1 = 有数字在正文里找不到（需人工删改）。
"""
import re
import sys

DIGIT_RE = re.compile(r"\d+(?:\.\d+)?")
NUM_TOKEN_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|％|倍|万亿|亿|万|千|条|个|人|名|天|周|月|年|日|小时|分钟|秒|"
    r"美元|元|块|分|台|张|门|篇|项|次|轮|GB|TB|MB|K|nm|B)"
)


def split_sections(text):
    """返回 (摘要, 正文)。没有 ## 正文 时，正文取摘要之后的全部内容。"""
    m = re.search(r"^##\s*摘要\s*$", text, re.M)
    if not m:
        return "", text
    rest = text[m.end():]
    m2 = re.search(r"^##\s*正文\s*$", rest, re.M)
    if m2:
        return rest[: m2.start()], rest[m2.end():]
    return rest.split("\n---", 1)[0], rest


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    override = None
    if "--summary" in sys.argv:
        override = sys.argv[sys.argv.index("--summary") + 1]

    text = open(path, encoding="utf-8").read()
    summary, body = split_sections(text)
    if override:
        summary = override
    if not summary.strip():
        print("没有摘要可检查")
        return 0

    body_digits = set(DIGIT_RE.findall(body))
    body_flat = re.sub(r"\s+", "", body)

    missing = []
    seen = set()
    for tok in NUM_TOKEN_RE.findall(summary):
        core = DIGIT_RE.search(tok).group(0)
        key = core
        if key in seen:
            continue
        seen.add(key)
        hit = core in body_digits or re.sub(r"\s+", "", tok) in body_flat
        if not hit:
            missing.append((tok, core))

    total = len(seen)
    if not missing:
        print(f"✅ 摘要里 {total} 个数字全部能在正文中找到")
        return 0

    print(f"⚠️ 摘要里 {total} 个数字中，{len(missing)} 个在正文找不到：")
    for tok, core in missing:
        idx = summary.find(core)
        ctx = summary[max(0, idx - 18): idx + len(tok) + 18].replace("\n", " ")
        print(f"  - {tok!r}  …{ctx}…")
    print("\n处理：删掉这些数字换成原文真实指标，或在正文里确认确有其事再保留。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
