---
name: felix-wechat-post
description: Generate a WeChat Official Account article cover image from a given article title, then publish the article to a WeChat Official Account draft using baoyu-post-to-wechat. Use when the user asks to publish a WeChat/公众号 article and wants an auto-generated cover with centered bold white title on a pure deep-blue background, or asks for a one-step cover-and-publish workflow.
---

# Felix WeChat Post

Automate a common publishing flow:

1. Generate a deterministic WeChat cover image from the article title.
2. Publish the article through `baoyu-post-to-wechat` with theme `grace` and color `blue`.

## Defaults

- Cover size: `1200x510`.
- Cover background: pure deep blue `#071B4D`.
- Cover text: title rendered verbatim, centered, white, bold.
- Cover output: `imgs/<sanitized-title>-公众号封面.png` unless the user gives a path.
- Article theme: `grace`.
- Article color: `blue`.
- Publishing target: follow `baoyu-post-to-wechat` config/account selection; pass `--account <alias>` only when the user specifies an account.

## Workflow

### 1. Determine inputs

Resolve these values before generating the cover:

- Article file: use the current note, selected file, or explicitly mentioned Markdown/HTML file.
- Title: prefer user-provided title; else use Markdown frontmatter `title`; else first `#` heading; else ask only if no reliable title exists.
- Author: use user-provided author when present; otherwise let `baoyu-post-to-wechat` config/frontmatter decide.
- Summary: use user-provided summary when present; otherwise let `baoyu-post-to-wechat` auto-generate.
- Account: if user names a target account or alias, pass `--account`; otherwise use the configured default account.

### 2. Generate the cover image

Use the bundled script for exact text rendering instead of a generative image model. The default Chinese font is 华文黑体 / Heiti SC via `/System/Library/Fonts/STHeiti Medium.ttc` when available.

```bash
{skill_dir}/scripts/generate_wechat_cover.sh \
  --title "<exact title>" \
  --out "imgs/<sanitized-title>-公众号封面.png"
```

Rules:

- Preserve the title exactly, including spaces and capitalization.
- Use relative vault/workspace paths for generated cover files when working in the current project.
- Inspect or verify the generated image if there is any chance of clipped or missing characters.
- If the user asks for a different background, size, font, or output path, pass the corresponding script option.

### 3. Publish through baoyu-post-to-wechat

Use `baoyu-post-to-wechat` rather than reimplementing WeChat publishing. Load that skill when available and follow its setup/config rules.

Do **not** hardcode one machine-specific `baoyu-post-to-wechat` path. Resolve the publishing script in this order:

1. If the runtime skill list exposes `baoyu-post-to-wechat`, use that skill's current path.
2. Else use the default local lookup order: `~/.agents/skills/baoyu-post-to-wechat`, then `~/.codex/skills/baoyu-post-to-wechat`, then `~/.claude/skills/baoyu-post-to-wechat`.
3. Else run this skill's resolver script, which implements the lookup order above and then bounded fallback search:

```bash
WECHAT_API_TS=$({skill_dir}/scripts/resolve_baoyu_wechat_api.sh)
```

The resolver supports one override for unusual machines:

- `BAOYU_POST_TO_WECHAT_DIR=/path/to/baoyu-post-to-wechat`

Use the skill directory rather than a direct script path so the resolver can derive `scripts/wechat-api.ts` consistently.

For API publishing, the effective command pattern is:

```bash
WECHAT_API_TS=$({skill_dir}/scripts/resolve_baoyu_wechat_api.sh)

bun "$WECHAT_API_TS" \
  "<article-file>" \
  --theme grace \
  --color blue \
  --title "<exact title>" \
  --cover "<cover-path>" \
  [--author "<author>"] \
  [--summary "<summary>"] \
  [--account "<account-alias>"]
```

Important:

- Do not pre-convert Markdown to HTML; the WeChat publishing script handles conversion and image uploads.
- Always pass `--theme grace --color blue` unless the user explicitly requests another style.
- Always pass the generated cover path via `--cover`.
- Preserve user-provided author, summary, source URL, and account choices.
- Do not print secrets, AppSecret values, or full credential files in the final answer.

### 4. Report completion

After publishing, report:

- Article file.
- Cover image path.
- Theme/color used.
- Account if known.
- Draft `media_id` if returned.
- Next step: check the WeChat Official Account draft box.
