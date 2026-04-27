#!/usr/bin/env python3
"""AI 领域每日热点推文 - 获取高互动 AI 相关推文"""

import json
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(SCRIPT_DIR, "users.txt")
OUTPUT_FILE = "/tmp/x-monitor-ai-trending.json"
OPENCLI = "/opt/homebrew/bin/opencli"

QUERIES = [
    {"query": "AI OR LLM OR GPT OR Claude OR agent OR DeepSeek", "limit": 20},
    {"query": "#AI #LLM #Claude #GPT", "limit": 10},
]


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
        tweets = data.get("data", [])
        if isinstance(data, list):
            tweets = data
        return tweets
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def parse_tweet(t):
    author_info = t.get("author", {})
    author = author_info.get("screenName", "")
    likes = t.get("metrics", {}).get("likes", 0)
    retweets = t.get("metrics", {}).get("retweets", 0)
    replies = t.get("metrics", {}).get("replies", 0)
    engagement_score = likes + retweets * 2 + replies
    return {
        "id": t.get("id", ""),
        "text": t.get("text", "").replace("\n", " ").replace("\r", " "),
        "author": author,
        "author_name": author_info.get("name", ""),
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "views": t.get("metrics", {}).get("views", 0),
        "created_at": t.get("createdAtLocal", "") or t.get("createdAt", ""),
        "url": f"https://x.com/{author}/status/{t['id']}" if t.get("id") else "",
        "is_retweet": t.get("isRetweet", False),
        "engagement_score": engagement_score,
    }


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
            author = t.get("author", {}).get("screenName", "").lower()
            if author in excluded:
                continue
            tweet = parse_tweet(t)
            if tweet["id"]:
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
