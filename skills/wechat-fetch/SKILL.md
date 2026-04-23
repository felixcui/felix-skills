---
name: wechat-fetch
description: "Fetch WeChat public account article content. Use when user provides a WeChat public account article URL and wants to extract the title, author, publish time, content, and images. Handles WeChat mp.weixin.qq.com article links."
metadata: { "openclaw": { "emoji": "📰", "requires": { "bins": ["python3"] } } }
---

# WeChat Article Fetcher

Fetch content from WeChat public account articles.

## Usage

Run the fetch script with a WeChat article URL:

```bash
python3 scripts/fetch_wechat.py <wechat-article-url>
```

## Output

Returns JSON with:

- `title` - Article title
- `author` - Account name/author
- `publish_time` - Publish time
- `content` - Article text (first 5000 chars)
- `images` - Up to 5 image URLs
- `url` - Original article URL
- `error` - Error message if fetch fails

## Example

```bash
python3 scripts/fetch_wechat.py "https://mp.weixin.qq.com/s/example"
```
