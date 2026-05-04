#!/usr/bin/env python3
"""
飞书 Wiki 内容抓取脚本
使用 OpenClaw 的 feishu_fetch_doc 工具获取内容
"""
import sys
import json
import re
import subprocess
import os

def fetch_feishu_wiki(url):
    """抓取飞书 Wiki 内容 - 通过调用 OpenClaw Gateway API"""
    try:
        # 尝试使用 openclaw 命令行工具
        # 构建一个消息让 agent 获取文档
        message = f"请使用 feishu_fetch_doc 工具获取飞书 Wiki 文档内容，doc_id: {url}"
        
        result = subprocess.run(
            ["openclaw", "agent", "--message", message, "--local", "--json", "--timeout", "60"],
            capture_output=True,
            text=True,
            timeout=90
        )
        
        if result.returncode != 0:
            return {"error": "FEISHU_WIKI_NOT_SUPPORTED"}
        
        output = result.stdout.strip()
        
        # 尝试从输出中提取标题和内容
        title = ""
        content = ""
        
        # 尝试解析 JSON
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                text_content = data.get('content', '') or data.get('text', '') or str(data)
            else:
                text_content = str(data)
        except:
            text_content = output
        
        # 提取标题
        title_match = re.search(r'标题[:：]\s*([^\n]+)', text_content) or re.search(r'#\s+(.+)', text_content)
        if title_match:
            title = title_match.group(1).strip()
        
        # 清理内容
        content = re.sub(r'<[^>]+>', '', text_content)
        content = re.sub(r'\n+', '\n', content).strip()
        
        return {
            "title": title,
            "author": "",
            "publish_time": "",
            "content": content,
            "url": url
        }
            
    except Exception as e:
        return {"error": "FEISHU_WIKI_NOT_SUPPORTED"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fetch_feishu_wiki.py <wiki_url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    result = fetch_feishu_wiki(url)
    print(json.dumps(result, ensure_ascii=False))
