#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 资讯发布到微信公众号

功能：
1. 获取 AI 资讯（从 fetch_ai_news.py）
2. 格式化为微信公众号文章格式
3. 转换 Markdown 为 HTML
4. 创建草稿并发布到微信公众号

使用：
    python3 publish_ai_news_to_wechat.py [--create-draft] [--publish] [--cover-image path/to/image.jpg]
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess

# 添加 scripts 目录到 Python 路径
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from fetch_ai_news import get_raw_news
import wechat_api_client


class WeChatNewsPublisher:
    """微信公众号新闻发布器"""
    
    def __init__(self):
        """初始化发布器"""
        try:
            self.client = wechat_api_client.WeChatAPIClient()
            print("✅ 微信公众号 API 客户端初始化成功")
        except Exception as e:
            print(f"❌ 微信公众号 API 客户端初始化失败: {e}")
            print(f"   请检查 .env 文件中的 WECHAT_APPID 和 WECHAT_APPSECRET 配置")
            sys.exit(1)
    
    def format_news_to_markdown(self, days: int = 1) -> str:
        """
        将资讯格式化为微信公众号文章格式（Markdown）
        
        Args:
            days: 获取最近几天的资讯
        
        Returns:
            Markdown 格式的文章内容
        """
        # 获取资讯汇总（不含分类，获取原始列表）
        # 使用 classify=False 来获取所有资讯
        raw_news_text = get_news_summary(days=days, classify=False, platform="wechat")
        
        # 这里需要修改 get_news_summary 返回资讯列表
        # 为了简化，我们直接调用 get_raw_news
        news_list = wechat_api_client.get_raw_news(days=days)
        
        if not news_list:
            return "# 😊 暂无新资讯\n\n今天没有新的AI相关资讯，请稍后再来查看～"
        
        # 格式化为公众号文章
        lines = []
        
        # 标题
        today = datetime.now()
        yesterday = today - __import__('datetime').timedelta(days=days)
        date_range = f"{yesterday.strftime('%m月%d日')} - {today.strftime('%m月%d日')}"
        lines.append(f"# 📰 AI 资讯汇总（{date_range}）")
        lines.append("")
        
        # 前言
        lines.append("以下是近期的 AI 资讯汇总，涵盖了编程工具、模型技术、产品应用和行业动态等多个方面。")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 资讯列表
        lines.append("## 资讯列表")
        lines.append("")
        
        for i, news in enumerate(news_list, 1):
            title = news['title']
            link = news['link']
            lines.append(f"### {i}. {title}")
            lines.append("")
            lines.append(f"🔗 [原文链接]({link})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # 结尾
        lines.append("## 关于")
        lines.append("")
        lines.append("本资讯由 AI 自动汇总生成，涵盖 AI 编程工具、大模型技术、AI 产品应用和行业动态等内容。")
        lines.append("")
        lines.append("如需了解更多资讯，请关注我们的公众号。")
        lines.append("")
        
        # 统计信息
        lines.append(f"**汇总时间：** {today.strftime('%Y年%m月%d日 %H:%M')}")
        lines.append(f"**资讯数量：** {len(news_list)} 条")
        
        return "\n".join(lines)
    
    def convert_to_html(self, markdown_content: str) -> str:
        """
        将 Markdown 转换为 HTML（使用 md_to_html.py）
        
        Args:
            markdown_content: Markdown 内容
        
        Returns:
            HTML 内容
        """
        # 保存 Markdown 到临时文件
        temp_md = Path("/tmp/ai_news_temp.md")
        temp_md.write_text(markdown_content, encoding='utf-8')
        
        # 调用 md_to_html.py 转换
        # 假设 md_to_html.py 有一个主函数或可以模块化调用
        try:
            # 这里我们直接使用 markdown 库转换
            import markdown
            from markdown.extensions import tables, fenced_code, codehilite
            
            extensions = [
                tables.TableExtension(),
                fenced_code.FencedCodeExtension(),
                codehilite.CodeHiliteExtension(linenums=False, css_class="highlight")
            ]
            
            html_content = markdown.markdown(
                markdown_content,
                extensions=extensions,
                tab_length=4
            )
            
            # 添加微信公众号样式
            wechat_style = self._get_wechat_style()
            html_content = wechat_style + html_content + "</body></html>"
            
            return html_content
            
        except Exception as e:
            print(f"❌ Markdown 转 HTML 失败: {e}")
            # 返回纯 HTML 作为后备
            return f"<html><body>{markdown_content}</body></html>"
    
    def _get_wechat_style(self) -> str:
        """
        获取微信公众号样式 CSS
        
        Returns:
            CSS 样式字符串
        """
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 资讯汇总</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 16px;
            line-height: 1.8;
            color: #333;
            max-width: 677px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f7f7f7;
        }
        
        h1 {
            font-size: 22px;
            font-weight: bold;
            color: #000;
            margin: 24px 0 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #3f51b5;
        }
        
        h2 {
            font-size: 19px;
            font-weight: bold;
            color: #000;
            margin: 20px 0 12px;
            padding-left: 8px;
            border-left: 3px solid #3f51b5;
        }
        
        h3 {
            font-size: 17px;
            font-weight: bold;
            color: #333;
            margin: 16px 0 8px;
        }
        
        p {
            margin: 12px 0;
            text-align: justify;
        }
        
        a {
            color: #3f51b5;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        blockquote {
            border-left: 4px solid #ddd;
            padding-left: 16px;
            margin: 16px 0;
            color: #666;
            background-color: #f9f9f9;
        }
        
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 14px;
        }
        
        pre {
            background-color: #f4f4f4;
            padding: 12px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 14px;
        }
        
        hr {
            border: none;
            border-top: 1px solid #e0e0e0;
            margin: 20px 0;
        }
        
        .highlight {
            background-color: #fff3cd;
            padding: 1px 3px;
            border-radius: 2px;
        }
    </style>
</head>
<body>
"""
    
    def create_draft(self, markdown_content: str, cover_image: str = None, thumb_media_id: str = None) -> str:
        """
        创建草稿
        
        Args:
            markdown_content: Markdown 内容
            cover_image: 封面图片路径
            thumb_media_id: 封面图片的 media_id（已有）
        
        Returns:
            草稿的 media_id
        """
        print("📝 正在格式化资讯为公众号文章...")
        
        # 生成标题
        today = datetime.now()
        yesterday = today - __import__('datetime').timedelta(days=1)
        date_str = yesterday.strftime('%Y年%m月%d日')
        
        title = f"📰 AI 资讯汇总 - {date_str}"
        author = "AI 资讯助手"
        
        # 转换为 HTML
        html_content = self.convert_to_html(markdown_content)
        
        # 摘要（文章描述）
        digest = f"本期汇总了最新的AI相关资讯，涵盖编程工具、模型技术、产品应用和行业动态等内容。"
        
        # 内容来源 URL（可以为空）
        content_source_url = ""
        
        # 创建草稿
        print(f"📝 标题: {title}")
        print(f"📝 作者: {author}")
        print(f"📝 摘要: {digest}")
        print(f"📝 内容长度: {len(html_content)} 字节")
        
        try:
            media_id = self.client.create_draft(
                title=title,
                author=author,
                digest=digest,
                content=html_content,
                content_source_url=content_source_url,
                cover_image_path=cover_image,
                thumb_media_id=thumb_media_id,
                need_open_comment=1,
                only_fans_can_comment=0
            )
            return media_id
        except Exception as e:
            print(f"❌ 创建草稿失败: {e}")
            raise
    
    def publish_news(self, media_id: str) -> str:
        """
        发布草稿
        
        Args:
            media_id: 草稿的 media_id
        
        Returns:
            发布的文章 ID (publish_id)
        """
        print(f"🚀 正在发布文章...")
        
        try:
            publish_id = self.client.publish_draft(media_id)
            return publish_id
        except Exception as e:
            print(f"❌ 发布文章失败: {e}")
            raise
    
    def create_and_publish(self, days: int = 1, cover_image: str = None, create_only: bool = False) -> str:
        """
        创建并发布资讯
        
        Args:
            days: 获取最近几天的资讯
            cover_image: 封面图片路径
            create_only: 是否只创建草稿不发布
        
        Returns:
            草稿或文章的 media_id
        """
        print("=" * 50)
        print(f"📰 开始处理 AI 资讯（最近 {days} 天）")
        print("=" * 50)
        
        # 格式化为 Markdown
        markdown_content = self.format_news_to_markdown(days=days)
        
        # 创建草稿
        media_id = self.create_draft(markdown_content, cover_image=cover_image)
        
        if create_only:
            print("✅ 仅创建草稿模式，不进行发布")
            return media_id
        
        # 发布草稿
        publish_id = self.publish_news(media_id)
        
        print("=" * 50)
        print(f"✅ 资讯发布成功！")
        print(f"   草稿 ID: {media_id}")
        print(f"   文章 ID: {publish_id}")
        print(f"   请在公众号后台查看: https://mp.weixin.qq.com/")
        print("=" * 50)
        
        return media_id


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='发布 AI 资讯到微信公众号')
    
    parser.add_argument('--days', type=int, default=1,
                        help='获取最近几天的资讯（默认1天）')
    parser.add_argument('--create-draft', action='store_true',
                        help='只创建草稿，不发布')
    parser.add_argument('--publish', action='store_true',
                        help='创建草稿并发布')
    parser.add_argument('--cover-image', type=str,
                        help='封面图片路径（本地文件）')
    parser.add_argument('--thumb-media-id', type=str,
                        help='封面图片的 media_id（使用后台已有的图片）')
    parser.add_argument('--save-md', type=str,
                        help='保存 Markdown 到指定文件')
    
    args = parser.parse_args()
    
    # 创建发布器
    publisher = WeChatNewsPublisher()
    
    # 处理保存 Markdown
    if args.save_md:
        markdown_content = publisher.format_news_to_markdown(days=args.days)
        output_path = Path(args.save_md)
        output_path.write_text(markdown_content, encoding='utf-8')
        print(f"✅ Markdown 已保存到: {output_path}")
    
    # 创建草稿
    if args.create_draft or args.publish:
        cover_image = args.cover_image
        thumb_media_id = args.thumb_media_id
        
        if args.create_draft:
            publisher.create_and_publish(days=args.days, cover_image=cover_image, create_only=True)
        elif args.publish:
            publisher.create_and_publish(days=args.days, cover_image=cover_image, create_only=False)
    else:
        # 默认行为：只创建草稿
        print("⚠️  未指定操作，默认创建草稿（不发布）")
        print("   使用 --publish 来创建并发布")
        publisher.create_and_publish(days=args.days, create_only=True)


if __name__ == "__main__":
    main()
