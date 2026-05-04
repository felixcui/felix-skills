#!/usr/bin/env python3
"""
内容抓取脚本 - 仅抓取，不生成摘要
"""
import sys
import re
import json
import urllib.request
import subprocess
from pathlib import Path


def is_wechat_article(url):
    """判断是否是微信公众号文章"""
    return 'mp.weixin.qq.com' in url or 'weixin.qq.com' in url


def fetch_wechat_article(url):
    """
    使用 wechat-fetch skill 抓取微信文章

    Args:
        url: 微信文章 URL

    Returns:
        dict: 包含 title, content 的字典
    """
    try:
        # 获取 wechat-fetch 脚本路径
        skill_dir = Path(__file__).parent.parent.parent / "wechat-fetch"
        script_path = skill_dir / "scripts" / "fetch_wechat.py"

        if not script_path.exists():
            return {"error": "wechat-fetch skill not found"}

        # 调用 wechat-fetch 脚本
        result = subprocess.run(
            ["python3", str(script_path), url],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "title": data.get("title", ""),
                "content": data.get("content", ""),
                "author": data.get("author", ""),
                "publish_time": data.get("publish_time", "")
            }
        else:
            return {"error": f"Fetch failed: {result.stderr}"}

    except Exception as e:
        return {"error": f"Error: {str(e)}"}


def fetch_generic_article(url):
    """
    抓取普通网页内容

    Args:
        url: 网页 URL

    Returns:
        dict: 包含 title, content 的字典
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            # 尝试检测编码
            content_type = response.headers.get('Content-Type', '')
            encoding = 'utf-8'
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[1].split(';')[0].strip()

            html = response.read().decode(encoding, errors='ignore')

        # 提取标题
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""
        title = re.sub(r'\s+', ' ', title)  # 合并空白字符

        # 提取正文 - 尝试多种常见内容区域
        content_selectors = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="content"[^>]*>(.*?)</div>',
            r'<div[^>]*id="article"[^>]*>(.*?)</div>',
        ]

        content = ""
        for pattern in content_selectors:
            content_match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if content_match:
                content_html = content_match.group(1)
                # 去除 HTML 标签
                content = re.sub(r'<[^>]+>', ' ', content_html)
                content = re.sub(r'\s+', ' ', content).strip()
                if len(content) > 200:  # 找到足够长的内容就停止
                    break

        return {
            "title": title,
            "content": content,
            "author": "",
            "publish_time": ""
        }

    except Exception as e:
        return {"error": f"Error: {str(e)}"}


def main():
    if len(sys.argv) < 2:
        print("用法: python3 fetch_content.py <资讯URL>")
        sys.exit(1)

    url = sys.argv[1]

    # 抓取内容
    if is_wechat_article(url):
        data = fetch_wechat_article(url)
    else:
        data = fetch_generic_article(url)

    # 输出结果
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
