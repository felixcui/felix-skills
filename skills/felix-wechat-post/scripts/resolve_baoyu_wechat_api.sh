#!/usr/bin/env bash
set -euo pipefail

# Resolve baoyu-post-to-wechat's wechat-api.ts without assuming one fixed machine path.
# Priority:
# 1. Explicit skill dir: BAOYU_POST_TO_WECHAT_DIR
# 2. Default local skill roots, in order:
#    ~/.agents/skills/baoyu-post-to-wechat
#    ~/.codex/skills/baoyu-post-to-wechat
#    ~/.claude/skills/baoyu-post-to-wechat
# 3. Bounded fallback search under those roots and common user workspaces

if [[ -n "${BAOYU_POST_TO_WECHAT_DIR:-}" && -f "${BAOYU_POST_TO_WECHAT_DIR}/scripts/wechat-api.ts" ]]; then
  printf '%s\n' "${BAOYU_POST_TO_WECHAT_DIR}/scripts/wechat-api.ts"
  exit 0
fi

codex_skills_dir="${CODEX_HOME:-$HOME/.codex}/skills"

candidates=(
  "$HOME/.agents/skills/baoyu-post-to-wechat/scripts/wechat-api.ts"
  "$codex_skills_dir/baoyu-post-to-wechat/scripts/wechat-api.ts"
  "$HOME/.claude/skills/baoyu-post-to-wechat/scripts/wechat-api.ts"
  "$HOME/work/skills/baoyu-skills/skills/baoyu-post-to-wechat/scripts/wechat-api.ts"
  "$HOME/work/github/baoyu-skills/skills/baoyu-post-to-wechat/scripts/wechat-api.ts"
  "$HOME/work/github/felix-skills/skills/baoyu-post-to-wechat/scripts/wechat-api.ts"
)

for p in "${candidates[@]}"; do
  if [[ -f "$p" ]]; then
    printf '%s\n' "$p"
    exit 0
  fi
done

search_roots=(
  "$HOME/.agents/skills"
  "$codex_skills_dir"
  "$HOME/.claude/skills"
  "$HOME/work/skills"
  "$HOME/work/github"
  "$PWD"
)

for root in "${search_roots[@]}"; do
  [[ -d "$root" ]] || continue
  found=$(find "$root" -path '*/baoyu-post-to-wechat/scripts/wechat-api.ts' -type f -print -quit 2>/dev/null || true)
  if [[ -n "$found" ]]; then
    printf '%s\n' "$found"
    exit 0
  fi
done

echo "Could not find baoyu-post-to-wechat/scripts/wechat-api.ts." >&2
echo "Default lookup order: ~/.agents/skills, ~/.codex/skills, ~/.claude/skills." >&2
echo "Set BAOYU_POST_TO_WECHAT_DIR=/path/to/baoyu-post-to-wechat if it is installed elsewhere." >&2
exit 1
