#!/usr/bin/env python3
"""AI 领域每日热点推文 - 获取高互动 AI 相关推文"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(SCRIPT_DIR, "users.txt")
OUTPUT_FILE = "/tmp/x-monitor-ai-trending.json"
TWITTER_CLI = "/Users/felix/.local/bin/twitter"

# 只保留最近 2 天内的推文
MAX_AGE_DAYS = 2

QUERIES = [
    {"query": "AI OR LLM OR GPT OR Claude OR agent OR DeepSeek", "limit": 20},
    {"query": "AI agent framework", "limit": 10},
]


def tweet_id_to_timestamp(tweet_id):
    """从 createdAtISO 字段解析时间（备用：Snowflake ID）"""
    return None


def is_within_days(tweet_id, days=MAX_AGE_DAYS):
    """判断推文是否在指定天数内（通过 tweet dict 的 createdAtISO 判断，在 main 中处理）"""
    return True


def load_excluded_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE) as f:
        return {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}


def fetch_search(query, limit, timeout=60):
    try:
        result = subprocess.run(
            [TWITTER_CLI, "search", query,
             "--type", "top", "--lang", "en",
             "--max", str(limit), "--json"],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        if isinstance(data, list):
            tweets = data
        elif isinstance(data, dict):
            tweets = data.get("data", [])
        else:
            tweets = []
        return tweets
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def parse_tweet(t):
    # twitter CLI 返回嵌套结构：author 是 dict，metrics 是 dict，有 createdAtISO
    if isinstance(t, str):
        return None
    author = t.get("author", {})
    if isinstance(author, dict):
        author_name = author.get("name", "")
        author_screen = author.get("screenName", author.get("username", ""))
    else:
        author_name = ""
        author_screen = str(author)
    metrics = t.get("metrics", {})
    likes = _to_int(metrics.get("likes", 0))
    retweets = _to_int(metrics.get("retweets", 0))
    replies = _to_int(metrics.get("replies", 0))
    views = _to_int(metrics.get("views", 0))
    engagement_score = likes + retweets * 2 + replies
    # twitter CLI 直接提供时间字段
    created_at = t.get("createdAtISO", t.get("createdAt", ""))
    tweet_id = t.get("id", "")
    return {
        "id": tweet_id,
        "text": t.get("text", "").replace("\n", " ").replace("\r", " "),
        "author": author_screen,
        "author_name": author_name,
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "views": views,
        "created_at": created_at,
        "url": t.get("url", "") or (f"https://x.com/{author_screen}/status/{tweet_id}" if tweet_id else ""),
        "is_retweet": t.get("isRetweet", False) or t.get("is_retweet", False),
        "engagement_score": engagement_score,
    }


def _to_int(val):
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        try:
            return int(val.replace(",", ""))
        except (ValueError, TypeError):
            return 0
    return 0


def main():
    excluded = load_excluded_users()
    seen_ids = set()
    all_tweets = []

    for q in QUERIES:
        print(f"搜索: {q['query']}", file=sys.stderr)
        raw = fetch_search(q["query"], q["limit"])
        for t in raw:
            tid = t.get("id", "")
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            author_raw = t.get("author", "")
            if isinstance(author_raw, dict):
                author = author_raw.get("screenName", author_raw.get("username", "")).lower()
            else:
                author = str(author_raw).lower()
            if author in excluded:
                continue
            tweet = parse_tweet(t)
            if not tweet or not tweet["id"]:
                continue
            # 只保留最近 2 天内的推文（用 createdAtISO 判断）
            created_at = tweet.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
                    if dt < cutoff:
                        continue
                except (ValueError, OSError):
                    pass
            all_tweets.append(tweet)

    if not all_tweets:
        print("[]")
        with open(OUTPUT_FILE, "w") as f:
            f.write("[]")
        return

    all_tweets.sort(key=lambda x: x["engagement_score"], reverse=True)
    top = all_tweets[:10]

    output = json.dumps(top, ensure_ascii=False, indent=2)
    print(output)
    with open(OUTPUT_FILE, "w") as f:
        f.write(output)


if __name__ == "__main__":
    main()
