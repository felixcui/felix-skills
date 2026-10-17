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

Use the bundled Pillow script — exact text rendering, no generative model, and no external binary to install:

```bash
python3 {skill_dir}/scripts/make_wechat_cover.py \
  --title "<exact title>" \
  --out "imgs/<sanitized-title>-公众号封面.png"
```

The script prints the actual line breaks it used. Keep `generate_wechat_cover.sh` only as a fallback for hosts that have ImageMagick (`magick`): it hardcodes a large `.ttc` font path, which this machine's gateway lifecycle guard refuses to scan ("larger than the scan cap"), so prefer the Pillow script here.

Rules:

- Preserve the title exactly, including spaces and capitalization.
- Use relative vault/workspace paths for generated cover files when working in the current project.
- Inspect or verify the generated image if there is any chance of clipped or missing characters: call `vision_analyze` on the PNG and ask "标题是否完整、有没有裁切"，并和脚本打印的断行结果对照。
- If the user asks for a different background, size, font, or output path, pass the corresponding script option.

### 2.5 Where the article file lives

公众号长文放 `~/work/github/media-conent/draft/<中文标题>.md`：首行 `# 标题`，紧跟一行 `> 导语`（发布时 `--summary` 一般就用这句）。封面放同目录 `imgs/`。**文件名不要带 `:`**（macOS 在 Finder 里显示成 `/`），用 `——` 或 `：`。英文原文的翻译稿同样放这里。

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

### 3.5 发布失败/验证的两件事

- **`40164: invalid ip <x.x.x.x> ... not in whitelist`** = 该公众号开了 API IP 白名单，当前出口 IP 不在名单里 → 连 access_token 都拿不到，草稿**不会**创建（跟文章内容无关）。让用户到公众号后台 → 设置与开发 → 基本配置 → **IP 白名单**加上错误信息里那个 IP，然后原样重跑发布即可（文章与封面都已就绪，不用重做）。诊断时可用另一个 appid 比对：换个能跑通的号取 token，能拿到就证明是我们这侧 IP、不是全局故障。
- **多账号要分清 appid**：不同公众号的 token 各走自己的白名单与凭证，报错里带上 appid 再判断，别把 A 号的失败当成整条链路坏了。
- **只是改排版、文中草稿已存在时，别重跑发布**（会多出一份草稿）：用 `draft/update` 原地更新，`media_id` 沿用 `batchget` 拿到的值。要点：`batchget` 不返回封面 `thumb_media_id`（空串），需从发布脚本的默认封面素材取值补上；`update` 的 `articles` 是**对象**而非数组。完整 payload 与回读校验步骤见 `ai-news-fetcher` 的 [references/wechat-draft-refresh.md]（同为媒体流水线，流程一致）。

### 4. Report completion

**发布成功不等于记录在**：向公众号后台回读一次草稿箱，别只信发布脚本的 stdout。用当前账号的 appid/secret 取 token 后 `POST /cgi-bin/draft/batchget`（`{"offset":0,"count":20,"no_content":1}`）列出最近的草稿，按标题 + `update_time` 确认这一篇真的在。注意：**已发布的文章会从草稿箱移出**，所以「草稿箱里没有旧的日报」通常是用户发过了，别据此判定历史发布失败；`/cgi-bin/freepublish/batchget`（已发布列表）在未认证/未授权该接口的号上返回 `48001 api unauthorized`，此时发布只能手动在后台点。

After publishing, report:

- Article file.
- Cover image path.
- Theme/color used.
- Account if known.
- Draft `media_id` if returned.
- Next step: check the WeChat Official Account draft box.
