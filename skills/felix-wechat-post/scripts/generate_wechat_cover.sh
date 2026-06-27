#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Generate a deterministic WeChat article cover: solid deep-blue background + centered bold white title.

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
while [[ $POINT -gt 24 ]]; do
  dims=$(magick -background none -fill white -font "$FONT" -pointsize "$POINT" label:"$TITLE" -format "%w %h" info:)
  read -r TW TH <<< "$dims"
  if [[ "$TW" -le "$MAX_WIDTH" ]]; then
    break
  fi
  POINT=$((POINT - 2))
done

magick -size "${WIDTH}x${HEIGHT}" xc:"$BG" \
  -font "$FONT" \
  -pointsize "$POINT" \
  -fill white \
  -stroke white \
  -strokewidth 1 \
  -gravity center \
  -annotate +0+0 "$TITLE" \
  "$OUT"

printf '%s\n' "$OUT"
