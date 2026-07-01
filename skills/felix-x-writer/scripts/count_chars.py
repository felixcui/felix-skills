#!/usr/bin/env python3
"""
按 X (Twitter) 规则计算推文字符权重，校验是否在 280 上限内。

权重规则（与 X 官方一致）：
- ASCII 可打印字符（英文字母、数字、英文标点、空格）：权重 1
- 中文、日文、韩文、emoji、全角符号等：权重 2
- 短链接（http://https. 开头）：统一按 23 计（X 会用 t.co 包装，无论原 URL 多长）
- 单条上限：280 权重

中文容量参考：
- 纯中文单条上限 ≈ 140 字
- 带 1 个链接 ≈ 128 字（链接占 23，再加一个空格）
- thread 里每条都独立按 280 计算

用法：
    python3 count_chars.py "推文内容"          # 校验单条
    python3 count_chars.py -f thread.md        # 校验文件（空行分隔成多条，逐条统计）
    echo "推文" | python3 count_chars.py       # 从 stdin 读单条

退出码：全部通过返回 0，存在超限条目返回 1。
"""
import re
import sys

LIMIT = 280
URL_WEIGHT = 23
URL_RE = re.compile(r'https?://\S+', re.IGNORECASE)

# emoji 与常见符号区间（补充 east_asian_width 在部分环境下对 emoji 判定不一致的情况）
EMOJI_RANGES = [
    (0x1F000, 0x1FAFF),  # Emoji 及补充符号
    (0x2600, 0x27BF),    # 杂项符号、Dingbats
    (0x2190, 0x21FF),    # 箭头
    (0x2B00, 0x2BFF),    # 杂项符号与箭头
]


def char_weight(ch):
    """单个字符的权重：ASCII 可打印为 1，其余（含全部 CJK、emoji、全角）为 2。"""
    cp = ord(ch)
    if 0x20 <= cp <= 0x7E:  # 空格到 ~，覆盖基本 ASCII 可打印
        return 1
    for lo, hi in EMOJI_RANGES:
        if lo <= cp <= hi:
            return 2
    return 2


def count(text):
    """计算一段文本的 X 权重字符数。URL 统一按 23 计。"""
    # 把每个 URL 替换成 23 个半角字符（每个权重 1，合计 23），再逐字符加权
    normalized = URL_RE.sub('a' * URL_WEIGHT, text)
    return sum(char_weight(ch) for ch in normalized)


def split_blocks(text):
    """按空行分隔成多条（thread），去掉仅含空白/序号的占位。"""
    blocks = re.split(r'\n\s*\n', text.strip())
    return [b.strip() for b in blocks if b.strip()]


def render(n, label=None):
    over = n > LIMIT
    head = f"[{label}] " if label else ""
    if over:
        return f"{head}❌ 超出：{n} / {LIMIT}（超 {n - LIMIT}，需再砍 {(n - LIMIT + 1) // 2} 个中文字）"
    if n > LIMIT - 20:
        return f"{head}⚠️  接近上限：{n} / {LIMIT}（还能写约 {(LIMIT - n) // 2} 个中文字）"
    return f"{head}✅ 通过：{n} / {LIMIT}（还能写约 {(LIMIT - n) // 2} 个中文字）"


def main():
    args = sys.argv[1:]
    text = None
    multi = False

    if args and args[0] in ('-f', '--file'):
        if len(args) < 2:
            print("用法: count_chars.py -f <文件路径>", file=sys.stderr)
            sys.exit(2)
        with open(args[1], encoding='utf-8') as f:
            text = f.read()
        multi = True
    elif args:
        text = args[0]
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("（空内容）", file=sys.stderr)
        sys.exit(2)

    if not multi:
        print(render(count(text)))
        sys.exit(0 if count(text) <= LIMIT else 1)

    blocks = split_blocks(text)
    any_over = False
    print(f"共 {len(blocks)} 条动态")
    print("─" * 30)
    for i, b in enumerate(blocks, 1):
        # 去掉行首的 "1/3" 之类序号标记再统计正文（序号本身也占权重，但为贴近真实发送场景保留）
        n = count(b)
        print(render(n, label=f"第{i}条"))
        any_over = any_over or n > LIMIT
    sys.exit(1 if any_over else 0)


if __name__ == '__main__':
    main()
