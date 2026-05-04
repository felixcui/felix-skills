#!/usr/bin/env python3
"""X 用户动态监控 - 获取新推文"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
STATE_DIR = os.path.join(WORKSPACE, "tmp", "x-monitor-states")
OUTPUT_FILE = "/tmp/x-monitor-new-tweets.json"
USERS_FILE = os.path.join(SCRIPT_DIR, "users.txt")

CST = timezone(timedelta(hours=8))


def format_number(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def load_users():
    with open(USERS_FILE) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def fetch_latest_tweet(username, timeout=30):
    try:
        result = subprocess.run(
            ["twitter", "user-posts", username, "--max", "1", "--json"],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        data = json.loads(result.stdout)
        tweets = data.get("data", [])
        if not tweets:
            return None
        t = tweets[0]
        author_info = t.get("author", {})
        author = author_info.get("screenName", username)
        is_retweet = t.get("isRetweet", False)
        url = f"https://x.com/{author}/status/{t['id']}"
        if is_retweet:
            url = f"https://x.com/{username}/status/{t['id']}"
        return {
            "id": t["id"],
            "text": t.get("text", "").replace("\n", " ").replace("\r", " "),
            "author": author,
            "author_name": author_info.get("name", ""),
            "likes": t.get("metrics", {}).get("likes", 0),
            "retweets": t.get("metrics", {}).get("retweets", 0),
            "replies": t.get("metrics", {}).get("replies", 0),
            "views": t.get("metrics", {}).get("views", 0),
            "created_at": t.get("createdAtLocal", "") or t.get("createdAt", ""),
            "url": url,
            "is_retweet": is_retweet,
        }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        return None


def main():
    os.makedirs(STATE_DIR, exist_ok=True)
    users = load_users()
    new_tweets = []

    for user in users:
        print(f"检查: {user}", file=sys.stderr)
        tweet = fetch_latest_tweet(user)
        if not tweet:
            continue

        state_file = os.path.join(STATE_DIR, f"{user}-last-tweet.txt")
        last_id = ""
        if os.path.exists(state_file):
            with open(state_file) as f:
                last_id = f.read().strip()

        if last_id == tweet["id"]:
            print(f"  无新推文", file=sys.stderr)
            continue

        with open(state_file, "w") as f:
            f.write(tweet["id"])

        new_tweets.append(tweet)
        print(f"  ✅ 新推文", file=sys.stderr)

    if not new_tweets:
        print("NO_NEW_TWEETS")
        sys.exit(1)

    # 输出 JSON
    print(json.dumps(new_tweets, ensure_ascii=False, indent=2))
    with open(OUTPUT_FILE, "w") as f:
        json.dump(new_tweets, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
