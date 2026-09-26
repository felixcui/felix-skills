#!/usr/bin/env python3
"""X 监控推文总结脚本 - 对推文 JSON 生成中文摘要并格式化输出

用法：
  python3 scripts/summarize_tweets.py <json_file> [--batch]

读取 fetch_new_tweets.py 输出的 JSON 文件，调用 LLM 对每条推文生成中文总结，
输出格式化的飞书消息。

LLM 配置从技能目录 .env 读取（不依赖 Hermes config.yaml）。
降级链：主模型（OPENAI_*）→ deepseek（DEEPSEEK_*）→ 规则摘要（取原文前80字）。
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)  # x-monitor/

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
DATE_STR = NOW.strftime("%m月%d日")
TIME_STR = NOW.strftime("%H:%M")


def load_llm_config():
    """加载 LLM 配置，降级链：技能 .env 主模型（OPENAI_*）→ 技能 .env deepseek（DEEPSEEK_*）"""
    configs = []
    env_path = os.path.join(SKILL_DIR, ".env")

    values = {}
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()

    # 第1优先：Hermes 主模型
    api_key, base_url, model_name = (values.get("OPENAI_API_KEY", ""),
                                     values.get("OPENAI_BASE_URL", ""),
                                     values.get("OPENAI_MODEL", ""))
    if api_key and base_url and model_name:
        configs.append({"name": f"主模型 ({model_name})", "api_key": api_key,
                        "base_url": base_url, "model": model_name})

    # 第2优先：deepseek
    ds_key, ds_url, ds_model = (values.get("DEEPSEEK_API_KEY", ""),
                                values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                                values.get("DEEPSEEK_MODEL", "deepseek-v4-flash"))
    if ds_key and ds_url:
        configs.append({"name": f"deepseek ({ds_model})", "api_key": ds_key,
                        "base_url": ds_url, "model": ds_model})

    return configs


def call_llm(config, prompt, timeout=30, max_len=300):
    """调用 LLM API，返回文本或 None"""
    import requests
    try:
        url = config["base_url"].rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        payload = {
            "model": config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8192,
            "temperature": 0.3,
        }
        # 推理模型（如 deepseek-v4.1-flash）需关闭思考，避免思考内容泄漏进摘要
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
            json=dict(payload, enable_thinking=False),
            timeout=timeout,
        )
        if resp.status_code != 200:
            # 端点不支持 enable_thinking 时回退重试
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
        if resp.status_code == 200:
            msg = resp.json()["choices"][0]["message"]
            text = msg.get("content", "").strip() or msg.get("reasoning_content", "").strip()
            text = re.sub(r'^["\']|["\']$', '', text)
            # 清理常见前缀
            text = re.sub(r'^(摘要|总结|Summary)[:：]\s*', '', text)
            if 10 < len(text) < max_len:
                if not text.endswith(('。', '！', '？', '~')):
                    text += '。'
                return text
        return None
    except Exception:
        return None


def summarize_batch(texts, max_chars=2000):
    """批量总结：将多条推文合并为一个 LLM 调用，减少 API 次数"""
    configs = load_llm_config()
    if not configs:
        return None

    items = []
    for i, (author, text) in enumerate(texts):
        items.append({"i": i, "author": author, "text": text[:max_chars]})

    prompt = f"""请对以下 {len(texts)} 条推文分别用一句话中文总结（15-40字，概括核心内容）。必须返回 JSON 数组，每项包含 "i"（序号）和 "s"（总结）。

推文数据：
{json.dumps(items, ensure_ascii=False, indent=2)}

直接返回 JSON 数组，不要 markdown 代码块标记。"""

    for config in configs:
        print(f"  使用 {config['name']} 批量总结 {len(texts)} 条推文...", file=sys.stderr)
        result = call_llm(config, prompt, timeout=120, max_len=20000)
        if result:
            # 尝试解析 JSON
            cleaned = result.strip()
            try:
                if cleaned.startswith("```"):
                    cleaned = re.sub(r'^```\w*\n?', '', cleaned)
                    cleaned = re.sub(r'\n?```$', '', cleaned)
                parsed = json.loads(cleaned)
            except (json.JSONDecodeError, TypeError):
                # 兜底：提取首个 [ 到末尾 ] 的 JSON 子串（模型可能混入额外说明文字）
                try:
                    start, end = cleaned.find("["), cleaned.rfind("]")
                    if start != -1 and end > start:
                        parsed = json.loads(cleaned[start:end + 1])
                    else:
                        parsed = None
                except (json.JSONDecodeError, TypeError):
                    parsed = None
            if isinstance(parsed, list) and len(parsed) == len(texts):
                summaries = [None] * len(texts)
                for item in parsed:
                    idx = item.get("i", -1)
                    if 0 <= idx < len(texts):
                        summaries[idx] = item.get("s", "")
                if all(summaries):
                    return summaries
                # 部分成功，补充缺失的
                return summaries
            print(f"  ⚠️ JSON 解析失败，尝试逐条...", file=sys.stderr)

    return None


def summarize_single(author, text, max_chars=2000, timeout=15):
    """单条推文总结，短超时快速降级"""
    configs = load_llm_config()
    truncated = text[:max_chars]
    prompt = f"""请用一句话中文总结以下推文的核心内容（20-50字），直接输出总结：

@{author}: {truncated}

总结："""

    for config in configs:
        try:
            print(f"  使用 {config['name']} 总结 @{author}", file=sys.stderr)
            result = call_llm(config, prompt, timeout=timeout)
            if result:
                return result
        except Exception:
            continue

    # 降级：规则摘要
    return rule_summary(text)


def rule_summary(text):
    """规则摘要：取原文前80字"""
    text = text.replace('\n', ' ').strip()
    if len(text) <= 80:
        return text
    return text[:80].rstrip() + '...'


def format_number(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def format_user_tweets(tweets):
    """格式化用户动态"""
    if not tweets:
        return None

    # 限制最多展示条数，防止 cron 输出超长
    MAX_TWEETS = 10
    truncated_count = max(0, len(tweets) - MAX_TWEETS)
    tweets = tweets[:MAX_TWEETS]

    lines = [f"🐦 X 动态监控 | {DATE_STR} {TIME_STR}", "━━━━━━━━━━━━━━━━━━", ""]

    for t in tweets:
        author = t.get("author", "")
        author_name = t.get("author_name", "")
        display = f"@{author}（{author_name}）" if author_name else f"@{author}"
        summary = t.get("summary", rule_summary(t.get("text", "")))
        # 截断过长的摘要
        if len(summary) > 100:
            summary = summary[:100].rstrip() + "…"
        url = t.get("url", "")
        is_retweet = t.get("is_retweet", False)

        if is_retweet:
            # 从 URL 提取转发原作者
            m = re.match(r'https://x\.com/([^/]+)/status/', url)
            retweet_from = m.group(1) if m else ""
            lines.append(f"🔄 转发自 @{retweet_from}")
            lines.append(f"{display}")
        else:
            lines.append(display)
        lines.append(summary)
        lines.append(f"🔗 <{url}>")
        lines.append("")

    if truncated_count > 0:
        lines.append(f"…另有 {truncated_count} 条未展示")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)



def main():
    import argparse
    parser = argparse.ArgumentParser(description="推文总结脚本")
    parser.add_argument("json_file", help="推文 JSON 文件路径")
    parser.add_argument("--batch", action="store_true", help="使用批量总结模式（多条合并为一个 API 调用）")
    args = parser.parse_args()

    if not os.path.exists(args.json_file):
        print(f"文件不存在: {args.json_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.json_file, encoding="utf-8") as f:
        tweets = json.load(f)

    if not tweets:
        print("NO_NEW_TWEETS")
        return

    # 生成总结
    if args.batch and len(tweets) > 1:
        # 批量模式：尝试 LLM，失败直接用规则摘要
        texts = [(t.get("author", ""), t.get("text", "")) for t in tweets]
        summaries = summarize_batch(texts)
        if summaries:
            for t, s in zip(tweets, summaries):
                t["summary"] = s
        else:
            # LLM 不可用，直接用规则摘要（不逐条调 LLM 避免超时）
            print("  LLM 总结不可用，使用规则摘要", file=sys.stderr)
            for t in tweets:
                t["summary"] = rule_summary(t.get("text", ""))
    else:
        for t in tweets:
            t["summary"] = summarize_single(t.get("author", ""), t.get("text", ""))

    # 格式化输出
    print(format_user_tweets(tweets))

    # 保存带摘要的 JSON
    output_file = args.json_file.replace(".json", "-summarized.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"摘要已保存到 {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
