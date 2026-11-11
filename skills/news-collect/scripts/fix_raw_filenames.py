#!/usr/bin/env python3
"""清洗 raw 目录里已有 Markdown 文件名的非法字符。

文件名里带 \\ / : * ? " < > | 时，在 Windows、NAS、网盘同步或「另存为」时会直接
报错（"文件名或路径不能包含特殊字符"）。collect_v2.py 新写的文件已自动清洗，但
历史文件不会自己变，所以留这个脚本做一次性/定期清理。

**只动非法字符**：空格、大小写、中文标点一律保留，避免整库改名。
与 collect_v2.sanitize_filename 不同的是这里不做空格压缩（那只用于新建文件）。

用法：
    python3 scripts/fix_raw_filenames.py            # 只预览，不改动
    python3 scripts/fix_raw_filenames.py --apply    # 实际重命名
    python3 scripts/fix_raw_filenames.py --dir ~/work/github/media-conent/raw --apply
"""
import argparse
import re
from pathlib import Path

ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')
MAP = {'\\': '＼', '/': '／', ':': '：', '*': '＊', '?': '？',
       '<': '〈', '>': '〉', '|': '｜', '"': ''}
DEFAULT_DIR = Path.home() / 'work/github/media-conent/raw'


def clean_name(stem: str) -> str:
    text = ''.join(MAP[ch] if ch in MAP else ch for ch in stem)
    text = re.sub(r'[\x00-\x1f\x7f]+', '', text)
    text = text.strip(' .')
    return text or 'article'


def needs_fix(path: Path) -> bool:
    stem = path.stem
    return bool(ILLEGAL.search(stem)) or stem != stem.strip(' .')


def target_path(path: Path) -> Path:
    new_stem = clean_name(path.stem)
    candidate = path.with_name(new_stem + path.suffix)
    idx = 2
    while candidate.exists() and candidate != path:
        candidate = path.with_name(f'{new_stem}_{idx}{path.suffix}')
        idx += 1
    return candidate


def main() -> int:
    ap = argparse.ArgumentParser(description='清洗 Markdown 文件名中的非法字符')
    ap.add_argument('--dir', default=str(DEFAULT_DIR), help='目标目录（默认 media-conent/raw）')
    ap.add_argument('--apply', action='store_true', help='实际重命名；不加则只预览')
    args = ap.parse_args()

    root = Path(args.dir).expanduser()
    if not root.is_dir():
        print(f'❌ 目录不存在：{root}')
        return 1

    todo = sorted(p for p in root.glob('*.md') if needs_fix(p))
    if not todo:
        print(f'✅ {root} 下没有需要清洗的文件名')
        return 0

    for p in todo:
        dst = target_path(p)
        print(f'{"RENAME" if args.apply else "DRY"}  {p.name}  ->  {dst.name}')
        if args.apply:
            p.rename(dst)

    print(f'\n共 {len(todo)} 个文件' + ('，已重命名' if args.apply else '，加 --apply 执行'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())