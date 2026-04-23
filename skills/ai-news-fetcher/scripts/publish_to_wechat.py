#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 资讯发布到微信公众号（使用 baoyu-markdown-to-html）

直接使用 fetch_ai_news_v4.py 的 get_news_summary 获取 Markdown
使用 baoyu-markdown-to-html 转换为 HTML

使用：
    python3 publish_to_wechat.py [--create-draft] [--publish] [--cover-image path/to/image.jpg]
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess

# 使用 workspace 根目录作为基准
# 处理 symlink 情况，先获取脚本的实际路径
_SCRIPT_REAL_PATH = Path(__file__).resolve()
# 如果是 symlink，找到实际的 workspace 根目录
if "/work/media-conent/.claude/skills/" in str(_SCRIPT_REAL_PATH):
    # 使用硬编码的 workspace 路径
    WORKSPACE_ROOT = Path("/Users/felix/.openclaw/workspace-fs_news_claw")
else:
    WORKSPACE_ROOT = _SCRIPT_REAL_PATH.parents[3]

_AICODING_SCRIPTS = WORKSPACE_ROOT / "skills" / "aicoding-news-weekly" / "scripts"
_AICODING_ENV = WORKSPACE_ROOT / "skills" / "aicoding-news-weekly" / ".env"

# 默认封面图素材ID
DEFAULT_THUMB_MEDIA_ID = "qxQUqgd9fe1MaWRFFohGgo8SIofgUyArMyHRseRKpcGrV1yW3yBRRjrd_0Kj41uF"

# 添加 scripts 目录到 Python 路径
sys.path.insert(0, str(_AICODING_SCRIPTS))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(_AICODING_ENV)
except ImportError:
    pass


class WeChatNewsPublisher:
    """微信公众号新闻发布器（使用 baoyu-markdown-to-html）"""
    
    def __init__(self):
        """初始化发布器"""
        # 检查 .env 文件
        if not _AICODING_ENV.exists():
            raise FileNotFoundError(
                f".env 文件不存在: {_AICODING_ENV}\n"
                f"请在 aicoding-news-weekly 目录下创建 .env 文件"
            )
        
        # 读取凭证
        self.appid = os.getenv('WECHAT_APPID')
        self.appsecret = os.getenv('WECHAT_APPSECRET')
        
        if not self.appid or not self.appsecret:
            raise ValueError(
                ".env 文件中缺少 WECHAT_APPID 或 WECHAT_APPSECRET\n"
                f"请在 {_AICODING_ENV} 中配置这两个参数"
            )
        
        print(f"✅ 微信公众号凭证已加载")
        print(f"   AppID: {self.appid[:8]}...")
    
    def get_ai_news_markdown(self, days: int = 1) -> str:
        """
        直接使用 fetch_ai_news_v4.py 中的 get_news_summary 获取 Markdown
        
        Args:
            days: 获取最近几天的资讯
        
        Returns:
            Markdown 内容
        """
        print(f"📰 正在获取最近 {days} 天的 AI 资讯...")
        
        # 导入 fetch_ai_news 模块
        fetch_script = WORKSPACE_ROOT / "skills" / "ai-news-fetcher" / "scripts" / "fetch_ai_news_v4.py"
        
        if not fetch_script.exists():
            raise FileNotFoundError(
                f"fetch_ai_news_v4.py 不存在: {fetch_script}\n"
                f"请确保 ai-news-fetcher skill 已正确安装"
            )
        
        try:
            # 动态导入 fetch_ai_news 模块
            import importlib.util
            spec = importlib.util.spec_from_file_location("fetch_ai_news_v4", str(fetch_script))
            fetch_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fetch_module)
            
            # 直接调用 get_news_summary 函数
            if hasattr(fetch_module, 'get_news_summary'):
                markdown_content = fetch_module.get_news_summary(days=days)
                print(f"✅ 成功获取 Markdown")
                print(f"   Markdown 长度: {len(markdown_content)} 字节")
                return markdown_content
            else:
                raise RuntimeError("fetch_ai_news_v4.py 中缺少 get_news_summary 函数")
                
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
        
        # 保存 Markdown 到临时文件
        temp_md = Path("/tmp/ai_news_wechat_temp.md")
        temp_md.write_text(markdown_content, encoding='utf-8')
        
        # baoyu-markdown-to-html 路径
        baoyu_skill_dir = WORKSPACE_ROOT / "skills" / "baoyu-markdown-to-html"
        baoyu_main = baoyu_skill_dir / "scripts" / "main.ts"
        
        if not baoyu_main.exists():
            raise FileNotFoundError(
                f"baoyu-markdown-to-html 不存在: {baoyu_main}\n"
                f"请确保 baoyu-markdown-to-html skill 已正确安装"
            )
        
        try:
            # 使用 npx bun 调用 main.ts
            result = subprocess.run(
                [
                    "npx", "-y", "bun", str(baoyu_main),
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
            
            # 清理临时文件
            if temp_md.exists():
                temp_md.unlink()
            
            return html_content
            
        except Exception as e:
            raise RuntimeError(f"HTML 转换失败: {e}")
    
    def create_draft(self, html_content: str, cover_image: str = None, thumb_media_id: str = None) -> str:
        """创建草稿"""
        print(f"📝 正在创建草稿...")
        
        today = datetime.now()
        date_str = today.strftime('%Y年%m月%d日')
        
        title = f"AI 资讯日报-{today.strftime('%Y.%m.%d')}"
        author = "AI 资讯助手"
        digest = f"本期汇总了最新的 AI 相关资讯，涵盖编程工具、模型技术、产品应用和行业动态等内容。"
        content_source_url = ""
        
        # 调用 wechat_api_client.py 创建草稿
        wechat_client_script = _AICODING_SCRIPTS / "wechat_api_client.py"
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("wechat_api_client", str(wechat_client_script))
            wechat_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(wechat_module)
            
            WeChatAPIClient = wechat_module.WeChatAPIClient
            
            # 创建客户端实例
            client = WeChatAPIClient(appid=self.appid, appsecret=self.appsecret)
            
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
        
        wechat_client_script = _AICODING_SCRIPTS / "wechat_api_client.py"
        
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("wechat_api_client", str(wechat_client_script))
            wechat_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(wechat_module)
            
            WeChatAPIClient = wechat_module.WeChatAPIClient
            
            # 创建客户端实例
            client = WeChatAPIClient(appid=self.appid, appsecret=self.appsecret)
            
            # 发布草稿
            publish_id = client.publish_draft(media_id)
            
            print(f"✅ 文章发布成功！publish_id: {publish_id}")
            return publish_id
            
        except Exception as e:
            raise RuntimeError(f"发布文章失败: {e}")
    
    def create_and_publish(self, days: int = 1, cover_image: str = None, thumb_media_id: str = None, create_only: bool = False) -> str:
        """创建并发布资讯"""
        print("=" * 50)
        print(f"📰 开始处理 AI 资讯（最近 {days} 天）")
        print("=" * 50)
        
        # 获取 Markdown
        markdown_content = self.get_ai_news_markdown(days=days)
        
        # 转换为 HTML
        html_content = self.convert_to_html(markdown_content)
        
        # 创建草稿
        media_id = self.create_draft(html_content, cover_image=cover_image, thumb_media_id=thumb_media_id)
        
        if create_only:
            print("✅ 仅创建草稿模式，不进行发布")
            # 发送完成通知到飞书
            self.send_completion_notification()
            return media_id
        
        # 发布草稿
        publish_id = self.publish_news(media_id)
        
        print("=" * 50)
        print(f"✅ 资讯发布成功！")
        print(f"   草稿 ID: {media_id}")
        print(f"   文章 ID: {publish_id}")
        print(f"   请在公众号后台查看: https://mp.weixin.qq.com/")
        print("=" * 50)
        
        # 发送完成通知到飞书
        self.send_completion_notification()
        
        return media_id

    def send_completion_notification(self):
        """发送执行完成通知到飞书"""
        print("📱 发送完成通知到飞书...")
        
        try:
            import subprocess
            result = subprocess.run([
                "/opt/homebrew/bin/openclaw", "message", "send",
                "--channel", "feishu",
                "--account", "fs_news_claw",
                "--target", "ou_5b479a8489e8ebf34df50794d2a2cb0d",
                "--message", "✅ AI资讯发布到公众号任务已完成，请在公众号后台查看草稿。"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ 飞书通知发送成功")
            else:
                print(f"⚠️  飞书通知发送失败: {result.stderr}")
        except Exception as e:
            print(f"⚠️  发送飞书通知异常: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='发布 AI 资讯到微信公众号（使用 baoyu-markdown-to-html）')
    
    parser.add_argument('--days', type=int, default=1,
                        help='获取最近几天的资讯（默认1天）')
    parser.add_argument('--create-draft', action='store_true',
                        help='只创建草稿，不发布')
    parser.add_argument('--publish', action='store_true',
                        help='创建草稿并发布')
    parser.add_argument('--cover-image', type=str,
                        help='封面图片路径（本地文件）')
    parser.add_argument('--thumb-media-id', type=str,
                        help='封面图片的 media_id（使用后台已有的图片，如不指定则使用默认素材ID）')
    
    args = parser.parse_args()
    
    # 创建发布器
    try:
        publisher = WeChatNewsPublisher()
    except Exception as e:
        print(f"❌ 初始化发布器失败: {e}")
        print(f"   请检查 aicoding-news-weekly/.env 文件中的 WECHAT_APPID 和 WECHAT_APPSECRET 配置")
        sys.exit(1)
    
    # 创建草稿
    if args.create_draft or args.publish:
        cover_image = args.cover_image
        # 使用默认封面图素材ID（如果未指定）
        thumb_media_id = args.thumb_media_id if args.thumb_media_id else DEFAULT_THUMB_MEDIA_ID
        
        print(f"✅ 使用封面图素材ID: {thumb_media_id}")
        
        try:
            if args.create_draft:
                publisher.create_and_publish(days=args.days, cover_image=cover_image, thumb_media_id=thumb_media_id, create_only=True)
            elif args.publish:
                publisher.create_and_publish(days=args.days, cover_image=cover_image, thumb_media_id=thumb_media_id, create_only=False)
        except Exception as e:
            print(f"❌ 发布失败: {e}")
            sys.exit(1)
    else:
        # 默认行为：只创建草稿，使用默认封面图
        print("⚠️  未指定操作，默认创建草稿（不发布）")
        print(f"   使用默认封面图素材ID: {DEFAULT_THUMB_MEDIA_ID}")
        print("   使用 --publish 来创建并发布")
        try:
            publisher.create_and_publish(days=args.days, thumb_media_id=DEFAULT_THUMB_MEDIA_ID, create_only=True)
        except Exception as e:
            print(f"❌ 创建草稿失败: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
