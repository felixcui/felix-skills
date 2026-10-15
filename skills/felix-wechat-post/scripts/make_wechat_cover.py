#!/usr/bin/env python3
"""Deterministic WeChat article cover: solid deep-blue background + centered white title.

Port of generate_wechat_cover.sh onto Pillow, so it needs no ImageMagick and embeds no
large font path (which trips the gateway lifecycle guard's scan cap on macOS).

Usage:
  python3 make_wechat_cover.py --title "文章标题" --out imgs/封面.png
                               [--width 1200] [--height 510] [--bg 071B4D]
                               [--font /path/to/font.ttc] [--max-ratio 0.82]

Behavior: title rendered verbatim; font size shrinks from 86 until the title fits the
max-ratio width in <= 2 lines; if it still needs more than 2 lines the title is truncated
with an ellipsis (hard cap, so the cover never overflows).
"""
import argparse
import glob
import os

from PIL import Image, ImageDraw, ImageFont

# Runtime font lookup, cheapest-first. Do NOT hardcode a single .ttc path: the file is
# tens of MB and a literal path in a script can be refused by the runtime's scan cap.
FONT_GLOBS = (
    "*STHeiti*Medium*.ttc",
    "*STHeiti*.ttc",
    "*Hiragino*W7*.ttc",
    "*Hiragino*W8*.ttc",
    "*Arial Unicode*.ttf",
)
FONT_DIRS = (
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
)


def resolve_font() -> str:
    for directory in FONT_DIRS:
        for pattern in FONT_GLOBS:
            for path in sorted(glob.glob(os.path.join(directory, pattern))):
                if os.path.isfile(path):
                    return path
    raise SystemExit("找不到中文字体，用 --font /path/to/font.ttc 指定")


def wrap(text, font, max_w):
    """Greedy wrap; returns the list of rendered lines."""
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if font.getlength(cur + ch) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def fit(title, font_path, max_w, start=86, floor=24):
    size = start
    while size > floor:
        font = ImageFont.truetype(font_path, size)
        lines = wrap(title, font, max_w)
        if len(lines) <= 2:
            return size, font, lines
        size -= 2
    font = ImageFont.truetype(font_path, floor)
    keep = title
    while len(wrap(keep + "…", font, max_w)) > 2 and len(keep) > 1:
        keep = keep[:-1]
    return floor, font, wrap(keep + "…", font, max_w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=510)
    ap.add_argument("--bg", default="071B4D")
    ap.add_argument("--font", default=None)
    ap.add_argument("--max-ratio", type=float, default=0.82)
    a = ap.parse_args()

    font_path = a.font or resolve_font()
    bg = tuple(int(a.bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    max_w = int(a.width * a.max_ratio)
    size, font, lines = fit(a.title, font_path, max_w)

    img = Image.new("RGB", (a.width, a.height), bg)
    draw = ImageDraw.Draw(img)
    line_h = int(size * 1.35)
    y = (a.height - line_h * len(lines)) // 2
    for line in lines:
        draw.text(((a.width - draw.textlength(line, font=font)) / 2, y), line,
                  font=font, fill=(255, 255, 255))
        y += line_h

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    img.save(a.out)
    print(f"saved {a.out} | {a.width}x{a.height} | font={os.path.basename(font_path)} "
          f"| fontsize={size} | lines={len(lines)}")
    for line in lines:
        print("   ", line)


if __name__ == "__main__":
    main()
