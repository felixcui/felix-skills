#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 资讯发布到微信公众号（使用 baoyu-markdown-to-html）

直接使用 fetch_ai_news.py 的 get_news_summary 获取 Markdown
使用 baoyu-markdown-to-html 转换为 HTML

使用：
    python3 publish_to_wechat.py [--create-draft] [--publish] [--cover-image path/to/image.jpg]
"""

import argparse
import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
import subprocess
import importlib.util
import requests

# ========== 路径定义（基于脚本位置的相对路径） ==========
# 脚本所在目录: ai-news-fetcher/scripts/
SCRIPT_DIR = Path(__file__).resolve().parent
# skill 根目录: ai-news-fetcher/
SKILL_ROOT = SCRIPT_DIR.parent
# skills 总目录: skills/
SKILLS_DIR = SKILL_ROOT.parent

# 同目录下的 fetch_ai_news.py
FETCH_SCRIPT = SCRIPT_DIR / "fetch_ai_news.py"
# 同项目下的 wechat_api_client.py（aicoding-news-weekly skill）
WECHAT_CLIENT_SCRIPT = SKILLS_DIR / "aicoding-news-weekly" / "scripts" / "wechat_api_client.py"

# ========== 加载环境变量 ==========
ENV_FILE = SKILL_ROOT / ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
except ImportError:
    pass

# 从环境变量读取配置
BAOYU_SKILL_DIR = Path(os.getenv('BAOYU_MARKDOWN_TO_HTML_DIR', '~/work/skills/baoyu-skills/skills/baoyu-markdown-to-html')).expanduser()

# 资讯 Markdown 文件输出目录（默认为 skill 目录下的 output 子目录）
NEWS_OUTPUT_DIR = Path(os.getenv('NEWS_OUTPUT_DIR', str(SKILL_ROOT / 'output'))).expanduser()

# 默认封面图素材ID
#DEFAULT_THUMB_MEDIA_ID = "qxQUqgd9fe1MaWRFFohGgo8SIofgUyArMyHRseRKpcGrV1yW3yBRRjrd_0Kj41uF"
DEFAULT_THUMB_MEDIA_ID = "-qe1bwy7r6ypdY2NjJZf6bOjFVbsw1hQuaqDpmFowfkp5C90wR73k_lCJlKP2IXe"

# 飞书群 webhook URL（推送 AI 资讯日报到飞书群）
FEISHU_NEWS_WEBHOOK = os.getenv(
    'FEISHU_NEWS_WEBHOOK',
    'https://open.feishu.cn/open-apis/bot/v2/hook/63c93d3f-aa99-482c-8de6-bb665acdce8c'
)


def _load_module(name: str, path: Path):
    """动态加载 Python 模块"""
    if not path.exists():
        raise FileNotFoundError(f"{name} 不存在: {path}")
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WeChatNewsPublisher:
    """微信公众号新闻发布器（使用 baoyu-markdown-to-html）"""
    
    def __init__(self):
        """初始化发布器"""
        # 检查 .env 文件
        if not ENV_FILE.exists():
            raise FileNotFoundError(
                f".env 文件不存在: {ENV_FILE}\n"
                f"请在 ai-news-fetcher 目录下创建 .env 文件"
            )
        
        # 读取凭证
        self.appid = os.getenv('WECHAT_APPID')
        self.appsecret = os.getenv('WECHAT_APPSECRET')
        
        if not self.appid or not self.appsecret:
            raise ValueError(
                ".env 文件中缺少 WECHAT_APPID 或 WECHAT_APPSECRET\n"
                f"请在 {ENV_FILE} 中配置这两个参数"
            )
        
        print(f"✅ 微信公众号凭证已加载")
        print(f"   AppID: {self.appid[:8]}...")
    
    def get_ai_news_markdown(self, days: int = 1, push_db: bool = True, date: str = None) -> str:
        """
        直接使用 fetch_ai_news.py 中的 get_news_summary 获取 Markdown
        
        Args:
            days: 获取最近几天的资讯
            push_db: 是否推送到 devmaster.cn 数据库
            date: 指定具体日期（YYYY-MM-DD）
        
        Returns:
            Markdown 内容
        """
        date_label = date or f"最近 {days} 天"
        print(f"📰 正在获取 {date_label} 的 AI 资讯...")
        
        try:
            fetch_module = _load_module("fetch_ai_news", FETCH_SCRIPT)
            
            # 直接调用 get_news_summary 函数
            if hasattr(fetch_module, 'get_news_summary'):
                markdown_content = fetch_module.get_news_summary(days=days, push_db=push_db, date=date)
                print(f"✅ 成功获取 Markdown")
                print(f"   Markdown 长度: {len(markdown_content)} 字节")
                return markdown_content
            else:
                raise RuntimeError("fetch_ai_news.py 中缺少 get_news_summary 函数")
                
        except Exception as e:
            raise RuntimeError(f"获取资讯失败: {e}")
    
    def convert_to_html(self, markdown_content: str) -> str:
        """
        使用 baoyu-markdown-to-html 转换 Markdown 为 HTML
        
        Args:
            markdown_content: Markdown 内容
        
        Returns:
            HTML 内容
        """
        print(f"🔄 正在使用 baoyu-markdown-to-html 转换 Markdown 为 HTML...")
        
        # 检查 baoyu-markdown-to-html 路径
        if not BAOYU_SKILL_DIR or not BAOYU_SKILL_DIR.exists():
            raise FileNotFoundError(
                f"baoyu-markdown-to-html 目录不存在: {BAOYU_SKILL_DIR}\n"
                f"请在 {ENV_FILE} 中配置 BAOYU_MARKDOWN_TO_HTML_DIR"
            )
        
        baoyu_main = BAOYU_SKILL_DIR / "scripts" / "main.ts"
        if not baoyu_main.exists():
            raise FileNotFoundError(
                f"baoyu-markdown-to-html main.ts 不存在: {baoyu_main}\n"
                f"请确保 baoyu-markdown-to-html skill 已正确安装"
            )
        
        # 保存 Markdown 到临时文件
        temp_md = Path("/tmp/ai_news_wechat_temp.md")
        temp_md.write_text(markdown_content, encoding='utf-8')
        
        try:
            # 使用 bun 调用 main.ts
            result = subprocess.run(
                [
                    "bun", str(baoyu_main),
                    str(temp_md),
                    "--theme", "default"  # 使用默认主题
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"baoyu-markdown-to-html 转换失败: {result.stderr}\n"
                    f"请检查 baoyu-markdown-to-html 是否可用"
                )
            
            # 解析 JSON 输出，获取 htmlPath
            import json
            output_data = json.loads(result.stdout)
            html_path = output_data.get("htmlPath")
            
            if not html_path or not Path(html_path).exists():
                raise RuntimeError("HTML 文件未生成")
            
            # 读取 HTML 内容
            html_content = Path(html_path).read_text(encoding='utf-8')
            
            # 提取 body 内的内容（微信只需要 body 部分）
            import re
            body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
            if body_match:
                html_content = body_match.group(1)
                print(f"✅ 已提取 body 内容")
            
            print(f"✅ HTML 转换成功")
            print(f"   HTML 长度: {len(html_content)} 字节")
            print(f"   HTML 文件: {html_path}")
            
            return html_content
            
        finally:
            # 清理临时文件
            if temp_md.exists():
                temp_md.unlink()
    
    def _get_wechat_client(self):
        """获取微信 API 客户端实例"""
        wechat_module = _load_module("wechat_api_client", WECHAT_CLIENT_SCRIPT)
        return wechat_module.WeChatAPIClient(appid=self.appid, appsecret=self.appsecret)
    
    def create_draft(self, html_content: str, cover_image: str = None, thumb_media_id: str = None, date: str = None) -> str:
        """创建草稿"""
        print(f"📝 正在创建草稿...")
        
        title_date = date or datetime.now().strftime('%Y.%m.%d')
        if date:
            # date 格式 YYYY-MM-DD，转为 YYYY.MM.DD
            title_date = date.replace('-', '.')
        title = f"AI 资讯日报-{title_date}"
        author = "AI资讯助手"
        digest = f"本期汇总了最新的 AI 相关资讯，涵盖编程工具、模型技术、产品应用和行业动态等内容。"
        content_source_url = ""
        
        try:
            client = self._get_wechat_client()
            
            # 创建草稿
            media_id = client.create_draft(
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
            
            print(f"✅ 草稿创建成功！media_id: {media_id}")
            return media_id
            
        except Exception as e:
            raise RuntimeError(f"创建草稿失败: {e}")
    
    def publish_news(self, media_id: str) -> str:
        """发布草稿"""
        print(f"🚀 正在发布文章...")
        
        try:
            client = self._get_wechat_client()
            
            # 发布草稿
            publish_id = client.publish_draft(media_id)
            
            print(f"✅ 文章发布成功！publish_id: {publish_id}")
            return publish_id
            
        except Exception as e:
            raise RuntimeError(f"发布文章失败: {e}")
    
    def _save_markdown(self, markdown_content: str, date: str = None) -> None:
        """将资讯 Markdown 保存到输出目录"""
        # 确保输出目录存在
        NEWS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # 文件名: ai-news-YYYY-MM-DD.md
        today = date or datetime.now().strftime('%Y-%m-%d')
        filename = f"ai-news-{today}.md"
        output_path = NEWS_OUTPUT_DIR / filename
        
        # 如果文件已存在，先删除
        if output_path.exists():
            output_path.unlink()
            print(f"🗑️  已删除旧文件: {output_path}")
        
        output_path.write_text(markdown_content, encoding='utf-8')
        print(f"💾 Markdown 已保存: {output_path}")

    def push_to_feishu(self, markdown_content: str) -> bool:
        """
        将资讯摘要推送到飞书群 webhook。
        
        解析 Markdown 中的分类和文章，生成飞书富文本消息格式推送。
        飞书消息不支持 markdown 表格，使用 emoji + 加粗列表格式。
        
        Args:
            markdown_content: 资讯 Markdown 内容
            
        Returns:
            是否推送成功
        """
        if not FEISHU_NEWS_WEBHOOK:
            print("⚠️ 未配置 FEISHU_NEWS_WEBHOOK，跳过飞书推送")
            return False
        
        print("📨 正在推送资讯到飞书群...")
        
        today = datetime.now().strftime('%Y.%m.%d')
        
        # 解析 Markdown：提取分类和文章
        # 格式: ## AI 资讯日报 / ### 🏷️ 分类名（N 条） / 1. [标题](url) `来源`
        lines = markdown_content.strip().split('\n')
        
        categories = []  # [(emoji_name, count, articles)]
        current_category = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 匹配分类行: ### 🏷️ 分类名（N 条）
            cat_match = re.match(r'^###\s+(.+?)[（(](\d+)\s*条[)）]$', line)
            if cat_match:
                current_category = {
                    'name': cat_match.group(1),
                    'count': int(cat_match.group(2)),
                    'articles': []
                }
                categories.append(current_category)
                continue
            
            # 匹配文章行: 1. [标题](url) `来源`
            if current_category:
                article_match = re.match(r'^\d+\.\s+\[(.+?)\]\((.+?)\)\s+`(.+?)`$', line)
                if article_match:
                    current_category['articles'].append({
                        'title': article_match.group(1),
                        'url': article_match.group(2),
                        'source': article_match.group(3)
                    })
        
        if not categories:
            print("⚠️ 未解析到任何分类，跳过飞书推送")
            return False
        
        # 统计总数
        total_articles = sum(c['count'] for c in categories)
        
        # 构建飞书富文本消息
        # 飞书消息使用 post 格式，每个分类一个卡片，文章用文本+链接
        feishu_lines = []
        feishu_lines.append(f"📰 AI 资讯日报 - {today}（共 {total_articles} 条）\n")
        
        for cat in categories:
            feishu_lines.append(f"{cat['name']}：{cat['count']} 条")
            for i, article in enumerate(cat['articles'], 1):
                feishu_lines.append(f"  {i}. <a href=\"{article['url']}\">{article['title']}</a>（{article['source']}）")
            feishu_lines.append("")  # 分类间空行
        
        content_text = '\n'.join(feishu_lines).strip()
        
        # 构建飞书 webhook payload
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": f"📰 AI 资讯日报 - {today}",
                        "content": []
                    }
                }
            }
        }
        
        # 构建内容块
        for cat in categories:
            # 分类标题行
            payload["content"]["post"]["zh_cn"]["content"].append([
                {"tag": "text", "text": f"\n{cat['name']}：{cat['count']} 条\n"}
            ])
            # 文章列表
            for i, article in enumerate(cat['articles'], 1):
                payload["content"]["post"]["zh_cn"]["content"].append([
                    {"tag": "text", "text": f"  {i}. "},
                    {"tag": "a", "text": article['title'], "href": article['url']},
                    {"tag": "text", "text": f"（{article['source']}）\n"}
                ])
        
        try:
            resp = requests.post(
                FEISHU_NEWS_WEBHOOK,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            if resp.status_code == 200:
                result = resp.json()
                if result.get('code', -1) == 0:
                    print(f"✅ 飞书群推送成功！共 {total_articles} 条资讯")
                    return True
                else:
                    print(f"⚠️ 飞书推送返回错误: {result}")
                    return False
            else:
                print(f"❌ 飞书推送 HTTP 错误: {resp.status_code} {resp.text}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ 飞书推送网络错误: {e}")
            return False
    
    def create_and_publish(self, days: int = 1, cover_image: str = None, thumb_media_id: str = None, create_only: bool = False, push_db: bool = True, date: str = None) -> str:
        """创建并发布资讯"""
        date_label = date or f"最近 {days} 天"
        print("=" * 50)
        print(f"📰 开始处理 AI 资讯（{date_label}）")
        print("=" * 50)
        
        # 获取 Markdown
        markdown_content = self.get_ai_news_markdown(days=days, push_db=push_db, date=date)
        
        # 保存 Markdown 文件到输出目录
        self._save_markdown(markdown_content, date=date)
        
        # 推送到飞书群
        self.push_to_feishu(markdown_content)
        
        # 转换为 HTML
        html_content = self.convert_to_html(markdown_content)
        
        # 创建草稿
        media_id = self.create_draft(html_content, cover_image=cover_image, thumb_media_id=thumb_media_id, date=date)
        
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
    parser = argparse.ArgumentParser(description='发布 AI 资讯到微信公众号（使用 baoyu-markdown-to-html）')
    
    parser.add_argument('--days', type=int, default=1,
                        help='获取最近几天的资讯（默认1天）')
    parser.add_argument('--date', type=str, default=None,
                        help='指定具体日期 YYYY-MM-DD，仅获取该天的资讯（优先于 --days）')
    parser.add_argument('--create-draft', action='store_true',
                        help='只创建草稿，不发布')
    parser.add_argument('--publish', action='store_true',
                        help='创建草稿并发布')
    parser.add_argument('--cover-image', type=str,
                        help='封面图片路径（本地文件）')
    parser.add_argument('--thumb-media-id', type=str,
                        help='封面图片的 media_id（使用后台已有的图片，如不指定则使用默认素材ID）')
    parser.add_argument('--no-db', action='store_true',
                        help='跳过推送到 devmaster.cn 数据库')
    
    args = parser.parse_args()
    
    # 创建发布器
    try:
        publisher = WeChatNewsPublisher()
    except Exception as e:
        print(f"❌ 初始化发布器失败: {e}")
        print(f"   请检查 ai-news-fetcher/.env 文件中的 WECHAT_APPID 和 WECHAT_APPSECRET 配置")
        sys.exit(1)
    
    # 创建草稿
    if args.create_draft or args.publish:
        cover_image = args.cover_image
        # 使用默认封面图素材ID（如果未指定）
        thumb_media_id = args.thumb_media_id if args.thumb_media_id else DEFAULT_THUMB_MEDIA_ID
        
        push_db = not args.no_db
        print(f"✅ 使用封面图素材ID: {thumb_media_id}")
        
        try:
            if args.create_draft:
                publisher.create_and_publish(days=args.days, cover_image=cover_image, thumb_media_id=thumb_media_id, create_only=True, push_db=push_db, date=args.date)
            elif args.publish:
                publisher.create_and_publish(days=args.days, cover_image=cover_image, thumb_media_id=thumb_media_id, create_only=False, push_db=push_db, date=args.date)
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            sys.exit(1)
    else:
        # 默认行为：只创建草稿，使用默认封面图
        print("⚠️  未指定操作，默认创建草稿（不发布）")
        print(f"   使用默认封面图素材ID: {DEFAULT_THUMB_MEDIA_ID}")
        print("   使用 --publish 来创建并发布")
        try:
            publisher.create_and_publish(days=args.days, thumb_media_id=DEFAULT_THUMB_MEDIA_ID, create_only=True, push_db=True, date=args.date)
        except Exception as e:
            print(f"❌ 创建草稿失败: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
