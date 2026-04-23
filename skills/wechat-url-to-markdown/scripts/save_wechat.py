#!/usr/bin/env python3
"""
微信公众号文章保存工具
将微信公众号链接内容保存为 Markdown 格式
"""

import asyncio
import argparse
import re
import os
import sys
from urllib.parse import urlparse, unquote
from datetime import datetime
from typing import Optional

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("错误: 需要安装 playwright")
    print("请运行: pip install playwright")
    print("然后运行: playwright install chromium")
    sys.exit(1)


# 脚本目录：wechat-save/scripts/
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Skill 根目录：wechat-save/
_SKILL_DIR = os.path.dirname(_SCRIPT_DIR)
# 默认输出目录：skill 内部的 output/ 子目录
DEFAULT_OUTPUT_DIR = os.path.join(_SKILL_DIR, "output")


class WeChatSaver:
    """微信公众号文章保存器"""

    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.ensure_output_dir()

    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def sanitize_filename(self, title: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除或替换非法字符
        title = re.sub(r'[\\/*?:"<>|]', "", title)
        # 限制长度
        title = title[:100].strip()
        return title

    def extract_publish_time(self, html: str) -> Optional[str]:
        """从 HTML 中提取发布时间"""
        # 尝试多种时间格式
        patterns = [
            r'var s="(\d{4}-\d{2}-\d{2})"',
            r'var s="(\d{4}年\d{1,2}月\d{1,2}日)"',
            r'"publish_time":"(\d{4}-\d{2}-\d{2})"',
            r'(\d{4}-\d{2}-\d{2})\s+</em>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                time_str = match.group(1)
                # 统一格式化为 YYYY-MM-DD
                time_str = time_str.replace("年", "-").replace("月", "-").replace("日", "")
                return time_str
        return None

    async def fetch_article(self, url: str) -> dict:
        """抓取文章内容"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = await context.new_page()

            try:
                print(f"正在访问: {url}")
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # 等待页面加载完成
                await asyncio.sleep(2)

                # 提取标题
                title = await page.evaluate("""
                    () => {
                        const h1 = document.querySelector('#activity_name');
                        return h1 ? h1.innerText.trim() : document.title;
                    }
                """)

                # 提取作者/公众号名
                author = await page.evaluate("""
                    () => {
                        const authorEl = document.querySelector('#js_name');
                        return authorEl ? authorEl.innerText.trim() : '';
                    }
                """)

                # 提取发布时间
                html_content = await page.content()
                publish_time = self.extract_publish_time(html_content)
                if not publish_time:
                    publish_time = datetime.now().strftime("%Y-%m-%d")

                # 提取正文内容
                content = await page.evaluate("""
                    () => {
                        const contentEl = document.querySelector('#js_content');
                        if (!contentEl) return '';

                        // 处理图片，添加 alt 文本
                        const images = contentEl.querySelectorAll('img');
                        images.forEach((img, index) => {
                            const dataSrc = img.getAttribute('data-src');
                            if (dataSrc) {
                                img.setAttribute('src', dataSrc);
                            }
                            if (!img.getAttribute('alt')) {
                                img.setAttribute('alt', `图片${index + 1}`);
                            }
                        });

                        return contentEl.innerHTML;
                    }
                """)

                await browser.close()

                return {
                    "title": title,
                    "author": author,
                    "publish_time": publish_time,
                    "content": content,
                    "url": url
                }

            except Exception as e:
                await browser.close()
                raise Exception(f"抓取文章失败: {str(e)}")

    def html_to_markdown(self, html: str) -> str:
        """将 HTML 转换为 Markdown"""
        # 使用简单的正则替换进行 HTML 到 Markdown 的转换
        md = html

        # 处理标题
        md = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<h5[^>]*>(.*?)</h5>', r'##### \1\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<h6[^>]*>(.*?)</h6>', r'###### \1\n\n', md, flags=re.DOTALL)

        # 处理粗体和斜体
        md = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', md, flags=re.DOTALL)
        md = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', md, flags=re.DOTALL)
        md = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', md, flags=re.DOTALL)
        md = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', md, flags=re.DOTALL)

        # 处理段落
        md = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', md, flags=re.DOTALL)

        # 处理换行
        md = re.sub(r'<br\s*/?>', '\n', md)

        # 处理图片
        md = re.sub(
            r'<img[^>]*src=["\'](.*?)["\'][^>]*alt=["\'](.*?)["\'][^>]*>',
            r'![\2](\1)',
            md
        )
        md = re.sub(
            r'<img[^>]*alt=["\'](.*?)["\'][^>]*src=["\'](.*?)["\'][^>]*>',
            r'![\1](\2)',
            md
        )
        md = re.sub(r'<img[^>]*src=["\'](.*?)["\'][^>]*>', r'![](\1)', md)

        # 处理链接
        md = re.sub(r'<a[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>', r'[\2](\1)', md, flags=re.DOTALL)

        # 处理代码块
        md = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'```\n\1\n```\n\n', md, flags=re.DOTALL)
        md = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', md, flags=re.DOTALL)

        # 处理无序列表
        md = re.sub(r'<ul[^>]*>(.*?)</ul>', lambda m: re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', m.group(1), flags=re.DOTALL) + '\n', md, flags=re.DOTALL)

        # 处理有序列表
        def process_ol(match):
            items = re.findall(r'<li[^>]*>(.*?)</li>', match.group(1), flags=re.DOTALL)
            return '\n'.join([f"{i+1}. {item}" for i, item in enumerate(items)]) + '\n\n'
        md = re.sub(r'<ol[^>]*>(.*?)</ol>', process_ol, md, flags=re.DOTALL)

        # 处理引用
        md = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: '> ' + m.group(1).replace('\n', '\n> ') + '\n\n', md, flags=re.DOTALL)

        # 清理剩余标签
        md = re.sub(r'<[^>]+>', '', md)

        # 解码 HTML 实体
        import html
        md = html.unescape(md)

        # 清理多余空白
        md = re.sub(r'\n{3,}', '\n\n', md)

        return md.strip()

    def save_to_markdown(self, article: dict) -> str:
        """将文章保存为 Markdown 文件"""
        # 构建文件名
        safe_title = self.sanitize_filename(article['title'])
        filename = f"{article['publish_time']}_{safe_title}.md"
        filepath = os.path.join(self.output_dir, filename)

        # 转换内容为 Markdown
        content_md = self.html_to_markdown(article['content'])

        # 构建 Markdown 内容
        md_content = f"""---
title: "{article['title']}"
author: "{article['author']}"
date: "{article['publish_time']}"
source: "{article['url']}"
---

# {article['title']}

> 来源: [{article['author']}]({article['url']})
> 时间: {article['publish_time']}

---

{content_md}

---

*原文链接: [{article['url']}]({article['url']})*
"""

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return filepath


async def main():
    parser = argparse.ArgumentParser(description='保存微信公众号文章为 Markdown')
    parser.add_argument('url', help='微信公众号文章链接')
    parser.add_argument('-o', '--output', default=None,
                        help=f'输出目录 (默认: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--check', action='store_true',
                        help='检查依赖是否已安装')

    args = parser.parse_args()

    # 检查依赖
    if args.check:
        try:
            import playwright
            print("✓ playwright 已安装")
            print("请确保已运行: playwright install chromium")
        except ImportError:
            print("✗ playwright 未安装")
            print("请运行: pip install playwright")
        return

    # 验证 URL
    if not args.url.startswith('http'):
        print("错误: 请提供有效的 URL")
        return

    # 创建保存器并执行
    saver = WeChatSaver(output_dir=args.output)

    try:
        print(f"开始抓取文章...")
        article = await saver.fetch_article(args.url)

        print(f"标题: {article['title']}")
        print(f"作者: {article['author']}")
        print(f"发布时间: {article['publish_time']}")

        filepath = saver.save_to_markdown(article)
        print(f"\n✓ 文章已保存到: {filepath}")

    except Exception as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
