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
OPENCLI = "/opt/homebrew/bin/opencli"

# X/Twitter Snowflake ID 基准时间: 2010-11-04 01:42:54 UTC (毫秒)
TWITTER_EPOCH_MS = 1288834974657

# 只保留最近 2 天内的推文
MAX_AGE_DAYS = 2

QUERIES = [
    {"query": "AI OR LLM OR GPT OR Claude OR agent OR DeepSeek", "limit": 20},
    {"query": "#AI #LLM #Claude #GPT", "limit": 10},
]


def tweet_id_to_timestamp(tweet_id):
    """从 X/Twitter Snowflake ID 提取创建时间戳"""
    try:
        snowflake = int(tweet_id)
        timestamp_ms = (snowflake >> 22) + TWITTER_EPOCH_MS
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def is_within_days(tweet_id, days=MAX_AGE_DAYS):
    """判断推文是否在指定天数内"""
    created = tweet_id_to_timestamp(tweet_id)
    if not created:
        return True  # 无法解析时间则保留
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return created >= cutoff


def load_excluded_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE) as f:
        return {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}


def fetch_search(query, limit, timeout=60):
    try:
        result = subprocess.run(
            [OPENCLI, "twitter", "search", "--query", query,
             "--limit", str(limit), "-f", "json"],
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
    # opencli 返回扁平结构：author 是字符串，likes/views 是数字或字符串
    if isinstance(t, str):
        return None
    author = t.get("author", "")
    if isinstance(author, dict):
        author_name = author.get("name", "")
        author_screen = author.get("screenName", author.get("username", ""))
    else:
        author_name = ""
        author_screen = str(author)
    likes = _to_int(t.get("likes", 0))
    retweets = _to_int(t.get("retweets", 0))
    replies = _to_int(t.get("replies", 0))
    views = _to_int(t.get("views", 0))
    engagement_score = likes + retweets * 2 + replies
    # 从 Snowflake ID 解析时间（opencli 不返回时间字段）
    created_at = ""
    tweet_id = t.get("id", "")
    if tweet_id:
        ts = tweet_id_to_timestamp(tweet_id)
        if ts:
            created_at = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
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
            # 只保留最近 2 天内的推文
            if not is_within_days(tweet["id"]):
                continue
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
