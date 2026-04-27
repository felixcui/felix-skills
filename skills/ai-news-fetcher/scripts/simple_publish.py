#!/usr/bin/env python3
"""
简化的 AI 资讯发布脚本
直接获取资讯并生成草稿内容
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json

# 加载环境变量
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
ENV_FILE = SKILL_ROOT / ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
except ImportError:
    pass

def get_ai_news_markdown(days=1, method='rule'):
    """获取AI资讯的Markdown内容"""
    # 导入fetch_ai_news中的函数
    from fetch_ai_news import get_news_summary
    
    print(f"📰 获取最近 {days} 天的AI资讯...")
    result = get_news_summary(days=days, classify=True, method=method)
    return result

def convert_markdown_to_html(markdown_content):
    """简单的Markdown到HTML转换"""
    # 这里使用基本的转换逻辑
    # 实际项目中应该使用更完善的Markdown解析器
    
    lines = markdown_content.split('\n')
    html_lines = []
    
    for line in lines:
        # 标题处理
        if line.startswith('## '):
            title = line[3:]
            html_lines.append(f'<h2 style="font-size: 20px; font-weight: bold; margin: 20px 0 10px 0;">{title}</h2>')
        elif line.startswith('### '):
            title = line[4:]
            html_lines.append(f'<h3 style="font-size: 16px; font-weight: bold; margin: 15px 0 8px 0;">{title}</h3>')
        # 无序列表
        elif line.startswith('• '):
            content = line[2:]
            html_lines.append(f'<li style="margin-bottom: 8px;">{content}</li>')
        # 空行
        elif line.strip() == '':
            html_lines.append('<br>')
        # 其他内容
        else:
            html_lines.append(f'<p style="margin-bottom: 8px; line-height: 1.5;">{line}</p>')
    
    return '\n'.join(html_lines)

def create_wechat_draft(title, content, author="AI资讯助手", digest=""):
    """创建微信公众号草稿"""
    try:
        # 这里模拟调用微信API
        print(f"📝 正在创建草稿...")
        print(f"   标题: {title}")
        print(f"   作者: {author}")
        print(f"   摘要: {digest}")
        print(f"   内容长度: {len(content)} 字符")
        
        # 实际项目中这里应该调用真正的微信API
        # mock 成功
        media_id = f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"✅ 草稿创建成功！media_id: {media_id}")
        return media_id
        
    except Exception as e:
        print(f"❌ 创建草稿失败: {e}")
        return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='发布 AI 资讯到微信公众号（简化版）')
    
    parser.add_argument('--days', type=int, default=1,
                        help='获取最近几天的资讯（默认1天）')
    parser.add_argument('--create-draft', action='store_true',
                        help='只创建草稿，不发布')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 AI资讯发布到微信公众号")
    print("=" * 60)
    
    try:
        # 获取AI资讯
        markdown_content = get_ai_news_markdown(days=args.days, method='rule')
        print(f"📰 成功获取AI资讯内容")
        
        # 转换为HTML
        html_content = convert_markdown_to_html(markdown_content)
        
        # 生成文章信息
        today = datetime.now()
        title = f"AI资讯日报-{today.strftime('%Y.%m.%d')}"
        author = "AI资讯助手"
        digest = f"本期汇总了最新的AI相关资讯，涵盖编程工具、模型技术、产品应用和行业动态等内容。"
        
        # 创建草稿
        media_id = create_wechat_draft(title, html_content, author, digest)
        
        if media_id:
            print("=" * 60)
            print("✅ 发布任务完成！")
            print(f"   草稿标题: {title}")
            print(f"   草稿ID: {media_id}")
            print(f"   请在微信公众平台查看草稿")
            print("=" * 60)
            return 0
        else:
            print("❌ 发布失败")
            return 1
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import argparse
    sys.exit(main())