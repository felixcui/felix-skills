#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Generate a deterministic WeChat article cover: solid deep-blue background + centered bold white title. Long titles auto-wrap to at most 2 lines; the font size shrinks until the title fits within --max-ratio width in ≤ 2 lines.

Usage:
  generate_wechat_cover.sh --title "文章标题" --out path/to/cover.png [options]

Options:
  --title <text>       Cover title, rendered verbatim. Required.
  --out <path>         Output PNG path. Required.
  --width <px>         Width. Default: 1200.
  --height <px>        Height. Default: 510.
  --bg <hex>           Background color. Default: #071B4D.
  --font <path>        Font path. Default: first available CJK bold font.
  --max-ratio <float>  Max text width / image width. Default: 0.82.
USAGE
}

TITLE=""
OUT=""
WIDTH=1200
HEIGHT=510
BG="#071B4D"
FONT=""
MAX_RATIO="0.82"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    --width) WIDTH="${2:-}"; shift 2 ;;
    --height) HEIGHT="${2:-}"; shift 2 ;;
    --bg) BG="${2:-}"; shift 2 ;;
    --font) FONT="${2:-}"; shift 2 ;;
    --max-ratio) MAX_RATIO="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$TITLE" || -z "$OUT" ]]; then
  usage >&2
  exit 2
fi

if ! command -v magick >/dev/null 2>&1; then
  echo "ImageMagick 'magick' is required. Install it with: brew install imagemagick" >&2
  exit 1
fi

if [[ -z "$FONT" ]]; then
  candidates=(
    "/System/Library/Fonts/STHeiti Medium.ttc"
    "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
    "/Library/Fonts/Arial Unicode.ttf"
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
  )
  for f in "${candidates[@]}"; do
    if [[ -f "$f" ]]; then FONT="$f"; break; fi
  done
fi

if [[ -z "$FONT" || ! -f "$FONT" ]]; then
  echo "No usable CJK font found. Pass --font /path/to/font.ttc" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"

MAX_WIDTH=$(python3 - <<PY
print(int($WIDTH * $MAX_RATIO))
PY
)
POINT=86
LINE_H=0
while [[ $POINT -gt 24 ]]; do
  # 单行渲染：测宽度 SW 与行高 SH
  single=$(magick -background none -fill white -font "$FONT" -pointsize "$POINT" label:"$TITLE" -format "%w %h" info:)
  read -r SW SH <<< "$single"
  LINE_H=$SH
  [[ "$SW" -le "$MAX_WIDTH" ]] && break                          # 单行即可放下
  # 限宽自动换行，测换行后所需总高度；按行高折算行数
  wrapped=$(magick -background none -fill white -font "$FONT" -pointsize "$POINT" -size "${MAX_WIDTH}x" caption:"$TITLE" -format "%w %h" info:)
  read -r _ WH <<< "$wrapped"
  rows=$(( (WH + SH / 2) / SH ))                                # 行数（按行高四舍五入）
  [[ "$rows" -le 2 ]] && break                                  # 最多两行
  POINT=$((POINT - 2))
done

# 展示文本：超长标题在最小字号仍超过两行时，逐字截断并加省略号，硬性保证 ≤ 2 行
DISPLAY="$TITLE"
final=$(magick -background none -fill white -font "$FONT" -pointsize "$POINT" -size "${MAX_WIDTH}x" caption:"$TITLE" -format "%h" info:)
rows=$(( (final + LINE_H / 2) / LINE_H ))
if [[ "$rows" -gt 2 ]]; then
  n=${#TITLE}
  for (( k=n; k>=1; k-- )); do
    cand="${TITLE:0:k}…"
    ch=$(magick -background none -fill white -font "$FONT" -pointsize "$POINT" -size "${MAX_WIDTH}x" caption:"$cand" -format "%h" info:)
    r2=$(( (ch + LINE_H / 2) / LINE_H ))
    [[ "$r2" -le 2 ]] && { DISPLAY="$cand"; break; }
  done
fi

# 背景 + caption 自动换行文本层（限宽 MAX_WIDTH，裁去透明边后严格居中合成）
magick -size "${WIDTH}x${HEIGHT}" xc:"$BG" \
  \( -background none -fill white -stroke white -strokewidth 1 \
     -font "$FONT" -pointsize "$POINT" -size "${MAX_WIDTH}x" caption:"$DISPLAY" -trim +repage \) \
  -gravity center -composite \
  "$OUT"

printf '%s\n' "$OUT"
