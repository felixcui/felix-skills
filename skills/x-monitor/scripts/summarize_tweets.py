#!/usr/bin/env python3
"""X 监控推文总结脚本 - 对推文 JSON 生成中文摘要并格式化输出

用法：
  python3 scripts/summarize_tweets.py <json_file> [--type user|trending] [--max 100]

读取 JSON 文件（fetch_new_tweets.py 或 fetch_ai_trending.py 的输出），
调用 LLM 对每条推文生成中文总结，输出格式化的飞书消息。

支持从 .env 或 ~/.hermes/config.yaml 自动读取 GLM API 配置。
降级链：GLM → hongmacc → 规则摘要（直接取原文前80字）。
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
    """加载 LLM 配置，从技能自带的 .env 文件读取"""
    configs = []
    env_path = os.path.join(SKILL_DIR, ".env")

    api_key, base_url, model_name = "", "", ""
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if line.startswith("#"):
                continue
            if line.startswith("OPENAI_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
            elif line.startswith("OPENAI_BASE_URL="):
                base_url = line.split("=", 1)[1].strip()
            elif line.startswith("OPENAI_MODEL="):
                model_name = line.split("=", 1)[1].strip()
    if api_key and base_url and model_name:
        configs.append({"name": f"GLM ({model_name})", "api_key": api_key, "base_url": base_url, "model": model_name})

    return configs


def call_llm(config, prompt, timeout=30):
    """调用 LLM API，返回文本或 None"""
    import requests
    try:
        url = config["base_url"].rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
            json={
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.3,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            msg = resp.json()["choices"][0]["message"]
            text = msg.get("content", "").strip() or msg.get("reasoning_content", "").strip()
            text = re.sub(r'^["\']|["\']$', '', text)
            # 清理常见前缀
            text = re.sub(r'^(摘要|总结|Summary)[:：]\s*', '', text)
            if 10 < len(text) < 300:
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
        result = call_llm(config, prompt, timeout=60)
        if result:
            # 尝试解析 JSON
            try:
                # 清理可能的 markdown 代码块
                cleaned = result.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r'^```\w*\n?', '', cleaned)
                    cleaned = re.sub(r'\n?```$', '', cleaned)
                parsed = json.loads(cleaned)
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
            except (json.JSONDecodeError, TypeError):
                pass
            print(f"  ⚠️ JSON 解析失败，尝试逐条...", file=sys.stderr)

    return None


def summarize_single(author, text, max_chars=2000):
    """单条推文总结"""
    configs = load_llm_config()
    truncated = text[:max_chars]
    prompt = f"""请用一句话中文总结以下推文的核心内容（20-50字），直接输出总结：

@{author}: {truncated}

总结："""

    for config in configs:
        print(f"  使用 {config['name']} 总结 @{author}", file=sys.stderr)
        result = call_llm(config, prompt, timeout=30)
        if result:
            return result

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

    lines = [f"🐦 X 动态监控 | {DATE_STR} {TIME_STR}", "━━━━━━━━━━━━━━━━━━", ""]

    for t in tweets:
        author = t.get("author", "")
        author_name = t.get("author_name", "")
        display = f"@{author}（{author_name}）" if author_name else f"@{author}"
        summary = t.get("summary", rule_summary(t.get("text", "")))
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

    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def format_trending_tweets(tweets):
    """格式化 AI 热点话题"""
    if not tweets:
        return "🔥 暂无 AI 热点"

    lines = ["🔥 AI 热点话题", "━━━━━━━━━━━━━━━━━━"]

    for i, t in enumerate(tweets, 1):
        author = t.get("author", "")
        author_name = t.get("author_name", "")
        display = f"@{author}（{author_name}）" if author_name else f"@{author}"
        summary = t.get("summary", rule_summary(t.get("text", "")))
        url = t.get("url", "")

        lines.append(f"{i}. {display} — {summary}")
        lines.append(f"   🔗 <{url}>")

    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="推文总结脚本")
    parser.add_argument("json_file", help="推文 JSON 文件路径")
    parser.add_argument("--type", choices=["user", "trending"], default="user", help="推文类型")
    parser.add_argument("--batch", action="store_true", help="使用批量总结模式（多条合并为一个 API 调用）")
    args = parser.parse_args()

    if not os.path.exists(args.json_file):
        print(f"文件不存在: {args.json_file}", file=sys.stderr)
        sys.exit(1)

    with open(args.json_file, encoding="utf-8") as f:
        tweets = json.load(f)

    if not tweets:
        if args.type == "trending":
            print(format_trending_tweets([]))
        else:
            print("NO_NEW_TWEETS")
        return

    # 生成总结
    if args.batch and len(tweets) > 1:
        # 批量模式
        texts = [(t.get("author", ""), t.get("text", "")) for t in tweets]
        summaries = summarize_batch(texts)
        if summaries:
            for t, s in zip(tweets, summaries):
                t["summary"] = s
        else:
            # 批量失败，逐条降级
            print("  批量总结失败，逐条处理...", file=sys.stderr)
            for t in tweets:
                t["summary"] = summarize_single(t.get("author", ""), t.get("text", ""))
    else:
        for t in tweets:
            t["summary"] = summarize_single(t.get("author", ""), t.get("text", ""))

    # 格式化输出
    if args.type == "user":
        output = format_user_tweets(tweets)
    else:
        output = format_trending_tweets(tweets)

    print(output)

    # 保存带摘要的 JSON
    output_file = args.json_file.replace(".json", "-summarized.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"摘要已保存到 {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
