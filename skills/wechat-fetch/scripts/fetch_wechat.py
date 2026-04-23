#!/usr/bin/env python3
"""
抓取微信公众号文章内容
"""
import sys
import re
import json
import urllib.request
from urllib.parse import urlparse
from datetime import datetime
import html as html_module


def format_timestamp(timestamp_str):
    """
    将时间戳转换为可读格式
    
    Args:
        timestamp_str: 时间戳字符串（秒或毫秒）
    
    Returns:
        str: 格式化后的时间字符串，如果转换失败返回原字符串
    """
    try:
        timestamp = int(timestamp_str)
        
        # 判断是秒还是毫秒
        if timestamp > 1000000000000:  # 毫秒级
            dt = datetime.fromtimestamp(timestamp / 1000)
        else:  # 秒级
            dt = datetime.fromtimestamp(timestamp)
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return timestamp_str


def html_to_markdown(html_str):
    """
    将 HTML 转换为 Markdown 格式（纯正则实现，无外部依赖）

    Args:
        html_str: HTML 字符串

    Returns:
        str: Markdown 格式的文本
    """
    text = html_str

    # 移除 style / script / img 标签及其内容
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<img[^>]*/?>', '', text, flags=re.IGNORECASE)

    # 标题 h1-h6
    for i in range(1, 7):
        prefix = '#' * i
        text = re.sub(
            rf'<h{i}[^>]*>(.*?)</h{i}>',
            lambda m, p=prefix: f'\n\n{p} {re.sub(r"<[^>]+>", "", m.group(1)).strip()}\n\n',
            text, flags=re.DOTALL | re.IGNORECASE
        )

    # 引用块 blockquote
    def convert_blockquote(m):
        inner = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        lines = inner.split('\n')
        return '\n' + '\n'.join('> ' + line.strip() for line in lines if line.strip()) + '\n'
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', convert_blockquote, text, flags=re.DOTALL | re.IGNORECASE)

    # 有序列表项 <ol> 内的 <li>
    def convert_ol(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), flags=re.DOTALL | re.IGNORECASE)
        result = '\n'
        for idx, item in enumerate(items, 1):
            item_text = re.sub(r'<[^>]+>', '', item).strip()
            result += f'{idx}. {item_text}\n'
        return result + '\n'
    text = re.sub(r'<ol[^>]*>(.*?)</ol>', convert_ol, text, flags=re.DOTALL | re.IGNORECASE)

    # 无序列表项 <ul> 内的 <li>
    def convert_ul(m):
        items = re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), flags=re.DOTALL | re.IGNORECASE)
        result = '\n'
        for item in items:
            item_text = re.sub(r'<[^>]+>', '', item).strip()
            result += f'- {item_text}\n'
        return result + '\n'
    text = re.sub(r'<ul[^>]*>(.*?)</ul>', convert_ul, text, flags=re.DOTALL | re.IGNORECASE)

    # 散落的 <li>（不在 ol/ul 内的）
    text = re.sub(r'<li[^>]*>(.*?)</li>', lambda m: '- ' + re.sub(r'<[^>]+>', '', m.group(1)).strip() + '\n', text, flags=re.DOTALL | re.IGNORECASE)

    # 加粗 <strong> / <b>
    text = re.sub(r'<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>', r'**\1**', text, flags=re.DOTALL | re.IGNORECASE)

    # 斜体 <em> / <i>（排除已处理的 publish_time em）
    text = re.sub(r'<(?:em|i)[^>]*>(.*?)</(?:em|i)>', r'*\1*', text, flags=re.DOTALL | re.IGNORECASE)

    # 链接 <a href="url">text</a>
    text = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)

    # 代码块 <pre><code>
    text = re.sub(r'<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>', r'\n```\n\1\n```\n', text, flags=re.DOTALL | re.IGNORECASE)
    # 行内代码 <code>
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL | re.IGNORECASE)

    # <br> → 换行
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # <p> → 段落分隔
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '', text, flags=re.IGNORECASE)

    # <hr> → 分隔线
    text = re.sub(r'<hr[^>]*/?>', '\n\n---\n\n', text, flags=re.IGNORECASE)

    # 去除剩余 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)

    # 解码 HTML 实体
    text = html_module.unescape(text)

    # 清理多余空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    # 清理每行首尾空白
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def fetch_wechat_article(url):
    """
    抓取微信公众号文章内容

    Args:
        url: 微信公众号文章链接

    Returns:
        dict: 包含 title, content, author, publish_time 的字典
    """
    try:
        # 设置请求头模拟浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')

        # 提取标题
        title_match = re.search(r'<h1[^>]*class="rich_media_title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        title = re.sub(r'<[^>]+>', '', title)  # 去除 HTML 标签

        # 提取作者
        author_match = re.search(r'<span[^>]*id="profileBt"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL)
        if not author_match:
            author_match = re.search(r'<a[^>]*id="js_name"[^>]*>(.*?)</a>', html, re.DOTALL)
        author = author_match.group(1).strip() if author_match else ""
        author = re.sub(r'<[^>]+>', '', author)

        # 提取发布时间 - 多种规则尝试
        publish_time = ""
        
        # 规则1: <em id="publish_time">
        time_match = re.search(r'<em[^>]*id="publish_time"[^>]*>(.*?)</em>', html)
        if time_match:
            publish_time = time_match.group(1).strip()
        
        # 规则2: JavaScript 变量 ct
        if not publish_time:
            time_match = re.search(r'var\s+ct\s*=\s*["\']([^"\']+)["\']', html)
            if time_match:
                publish_time = time_match.group(1)
        
        # 规则3: meta 标签
        if not publish_time:
            time_match = re.search(r'<meta[^>]*property="article:published_time"[^>]*content="([^"]+)"', html)
            if time_match:
                publish_time = time_match.group(1)
        
        # 规则4: rich_media_meta_text class
        if not publish_time:
            time_match = re.search(r'<span[^>]*class="rich_media_meta_text[^"]*"[^>]*>(\d{4}-\d{2}-\d{2})</span>', html)
            if time_match:
                publish_time = time_match.group(1)

        # 提取正文内容并转换为 Markdown
        content_match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*</div>\s*<script', html, re.DOTALL)
        if content_match:
            content = html_to_markdown(content_match.group(1))
        else:
            content = ""

        # 格式化时间戳
        if publish_time:
            publish_time = format_timestamp(publish_time)

        return {
            "title": title,
            "author": author,
            "publish_time": publish_time,
            "content": content,
            "url": url
        }

    except Exception as e:
        return {"error": f"抓取失败: {str(e)}"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 fetch_wechat.py <微信文章URL>")
        sys.exit(1)

    url = sys.argv[1]
    result = fetch_wechat_article(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
