---
name: ai-news-fetcher-wechat-draft
description: Configure and run the ai-news-fetcher workflow so AI news is collected, classified, and written to a WeChat official account draft box.
---

# ai-news-fetcher WeChat draft workflow

Use this skill when the user wants the daily AI-news collection flow to publish into the WeChat official account draft box, or when you need to test-run that pipeline.

## What to remember

- The workflow needs WeChat app credentials stored locally, not pasted back into chat.
- In this environment, the working config file is:
  - `~/.config/ai-news-fetcher/config.json`
- For this environment, the skill implementation lives in `~/.hermes/skills/felix-skills/ai-news-fetcher-wechat-draft/`, not in a separate `ai-news-fetcher` skill directory.
- The config file should contain keys similar to:
  - `WECHAT_APPID`
  - `WECHAT_APPSECRET`
- If the config file is missing, create the directory first and then write the JSON file.

## Recommended setup steps

1. Check whether `~/.config/ai-news-fetcher/config.json` exists.
2. If missing, create `~/.config/ai-news-fetcher/`.
3. Write the WeChat credentials into the JSON config.
4. Run the scheduled job once as a test.
5. Confirm the job reports success and that the draft-box action completed.

## Running the job

- The cron job can be triggered with the Hermes `cronjob` tool using `action='run'`.
- If the job already exists, run it directly rather than recreating it.
- After each run, report the execution status back to the user.
- A job status of `ok` only means the cron execution completed; it does not by itself prove a WeChat draft was created.

## Troubleshooting

- If the user cannot see a draft in WeChat, verify the workflow is actually bound to the draft-writing implementation, not just the broader `ai-news-fetcher` name.
- In this environment, the visible implementation directory is `~/.hermes/skills/felix-skills/ai-news-fetcher-wechat-draft/`.
- If the job reports success but no draft appears, inspect the downstream draft API call or the workflow’s real skill binding before assuming the publish step worked.

## Pitfalls

- Do not repeat or log the full AppSecret in chat.
- If a skill named `ai-news-fetcher` is not directly viewable, inspect available skills with `skills_list` and proceed with the configured cron workflow anyway.
- A successful job trigger does not always prove WeChat draft creation succeeded; check the job status and any downstream error field if available.
