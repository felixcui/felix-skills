#!/usr/bin/env python3
"""
News Collect - 一站式资讯收集工具
功能：抓取文章 → 使用 OpenClaw 大模型生成摘要 → 推送到飞书
"""
import sys
import re
import json
import urllib.request
import urllib.parse
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
WEBHOOK_URL = "https://www.feishu.cn/flow/api/trigger-webhook/4ebcdc4fd26c38187fdd74434d17a916"
OPENCLAW_AGENT = "fs_news_claw"  # agent ID

# IMA 知识库配置
IMA_KB_ENABLED = True
IMA_KB_ID = "AGoC5oEY8FP12VotR1kff00HlmJyh3RP6Do9vCGKpGQ="  # AI资讯知识库
IMA_CONFIG_PATH = Path.home() / ".config" / "ima"
IMA_API_BASE = "https://ima.qq.com"


# ============ 内容抓取 ============

def is_wechat_article(url):
    """判断是否是微信公众号文章"""
    return 'mp.weixin.qq.com' in url or 'weixin.qq.com' in url


def is_twitter_url(url):
    """判断是否是 Twitter/X 链接"""
    return bool(re.match(r'https?://(x\.com|twitter\.com)/\w+/status/\d+', url))


def is_feishu_wiki(url):
    """判断是否是飞书 Wiki 链接"""
    return 'feishu.cn/wiki' in url or 'larkoffice.com/wiki' in url


def format_timestamp(timestamp_str):
    """将时间戳转换为可读格式"""
    try:
        timestamp = int(timestamp_str)
        if timestamp > 1000000000000:  # 毫秒级
            dt = datetime.fromtimestamp(timestamp / 1000)
        else:  # 秒级
            dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        return timestamp_str


def fetch_wechat_article(url):
    """抓取微信公众号文章内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')

        # 提取标题
        title_match = re.search(r'<h1[^>]*class="rich_media_title[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        title = re.sub(r'<[^>]+>', '', title)

        # 提取作者
        author_match = re.search(r'<span[^>]*id="profileBt"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL)
        if not author_match:
            author_match = re.search(r'<a[^>]*id="js_name"[^>]*>(.*?)</a>', html, re.DOTALL)
        author = author_match.group(1).strip() if author_match else ""
        author = re.sub(r'<[^>]+>', '', author)

        # 提取发布时间
        publish_time = ""
        time_patterns = [
            r'<em[^>]*id="publish_time"[^>]*>(.*?)</em>',
            r'var\s+ct\s*=\s*["\']([^"\']+)["\']',
            r'<meta[^>]*property="article:published_time"[^>]*content="([^"]+)"',
            r'<span[^>]*class="rich_media_meta_text[^"]*"[^>]*>(\d{4}-\d{2}-\d{2})</span>',
        ]
        for pattern in time_patterns:
            match = re.search(pattern, html)
            if match:
                publish_time = match.group(1).strip()
                break
        publish_time = format_timestamp(publish_time)

        # 提取正文
        content_match = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*</div>\s*<script', html, re.DOTALL)
        if content_match:
            content = re.sub(r'<[^>]+>', '', content_match.group(1))
            content = re.sub(r'\n+', '\n', content).strip()
        else:
            content = ""

        return {
            "title": title,
            "author": author,
            "publish_time": publish_time,
            "content": content,
            "url": url
        }

    except Exception as e:
        return {"error": f"抓取失败: {str(e)}"}


def fetch_generic_article(url):
    """抓取普通网页内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content_type = response.headers.get('Content-Type', '')
            encoding = 'utf-8'
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[1].split(';')[0].strip()
            html = response.read().decode(encoding, errors='ignore')

        # 提取标题
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title_match.group(1).strip()) if title_match else ""

        # 提取正文
        content_selectors = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="content"[^>]*>(.*?)</div>',
            r'<div[^>]*id="article"[^>]*>(.*?)</div>',
        ]
        
        content = ""
        for pattern in content_selectors:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                content = re.sub(r'<[^>]+>', ' ', match.group(1))
                content = re.sub(r'\s+', ' ', content).strip()
                if len(content) > 200:
                    break

        return {
            "title": title,
            "author": "",
            "publish_time": "",
            "content": content,
            "url": url
        }

    except Exception as e:
        return {"error": f"抓取失败: {str(e)}"}


def fetch_feishu_wiki_direct(url):
    """直接使用 feishu_fetch_doc 工具获取飞书 Wiki 内容"""
    # 由于 feishu_fetch_doc 需要当前会话的授权
    # 在独立脚本中无法直接调用
    # 返回特殊标记，让主流程提示用户
    
    return {
        "error": "FEISHU_WIKI_REQUIRES_SESSION",
        "url": url,
        "message": "飞书 Wiki 需要在当前 OpenClaw 会话中处理，请直接发送链接给我，我会自动获取内容并推送"
    }


def fetch_feishu_wiki(url):
    """抓取飞书 Wiki 内容 - 使用直接调用方式"""
    return fetch_feishu_wiki_direct(url)


def fetch_twitter_tweet(url):
    """使用 twitter-cli 获取推文内容"""
    try:
        # 使用 -c compact 模式减少 token 消耗
        result = subprocess.run(
            ["twitter", "tweet", url, "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            tweet_list = data.get("data", data)
            if isinstance(tweet_list, list) and tweet_list:
                tweet_data = tweet_list[0]
            else:
                tweet_data = tweet_list
            return {
                "title": f"@{tweet_data.get('author', {}).get('username', '')} 的推文",
                "author": tweet_data.get("author", {}).get("name", ""),
                "publish_time": format_timestamp(tweet_data.get("createdAt", "")) if tweet_data.get("createdAt") else "",
                "content": tweet_data.get("text", ""),
                "url": url
            }
        else:
            return {"error": f"twitter-cli 获取失败: {result.stderr.strip() or '未知错误'}"}
    except FileNotFoundError:
        return {"error": "twitter-cli 未安装，请运行: uv tool install twitter-cli"}
    except subprocess.TimeoutExpired:
        return {"error": "twitter-cli 超时"}
    except Exception as e:
        return {"error": f"twitter-cli 错误: {str(e)}"}


def fetch_article(url):
    """统一抓取文章接口"""
    if is_twitter_url(url):
        return fetch_twitter_tweet(url)
    if is_wechat_article(url):
        return fetch_wechat_article(url)
    elif is_feishu_wiki(url):
        return fetch_feishu_wiki(url)
    return fetch_generic_article(url)


# ============ 摘要生成（使用 OpenClaw agent） ============

def generate_summary_with_llm(content, title="", max_length=200):
    """
    使用 Claude Code 生成文章摘要
    """
    if not content:
        return ""

    # 清理内容，限制长度 - 减少内容长度以加快处理速度
    content = content.strip()[:2000]  # 从3000减少到2000

    # 构建更简洁的 prompt
    prompt = f"""请用{max_length}字以内总结这篇文章的核心观点，要求：
1. 一段完整的话，以句号结尾
2. 不要省略号
3. 突出关键信息
4. 不要代码和命令行
5. 直接输出摘要，不要标题

标题：{title}

内容：
{content}
"""

    # 使用 Claude Code 生成摘要 - 增加超时时间到90秒
    try:
        print("   使用 Claude Code 生成摘要...")
        result = subprocess.run(
            ["claude", "-p", "--permission-mode", "bypassPermissions", "--output-format", "text", prompt],
            capture_output=True,
            text=True,
            timeout=90  # 从60增加到90秒
        )
        
        if result.returncode == 0:
            summary = result.stdout.strip()
            # 清理摘要
            summary = re.sub(r'^["\']|["\']$', '', summary)
            summary = re.sub(r'^(摘要|总结)[:：]?\s*', '', summary)
            # 移除省略号，确保完整性
            summary = re.sub(r'\.\.\.', '', summary)
            summary = re.sub(r'…', '', summary)

            if len(summary) > 50:
                # 如果超过长度限制，智能截断到完整句子
                if len(summary) > max_length:
                    truncated = summary[:max_length]
                    # 找到最后一个句号的位置
                    last_period = truncated.rfind('。')
                    if last_period > max_length * 0.6:  # 确保至少保留60%内容
                        summary = truncated[:last_period+1]
                    else:
                        # 如果找不到合适的句号，直接截断并添加句号
                        summary = truncated.rstrip() + '。'
                # 确保摘要以句号结尾
                if not summary.endswith('。'):
                    summary = summary.rstrip('.') + '。'
                print(f"   使用 Claude Code 生成摘要 ({len(summary)}字)")
                return summary
    except subprocess.TimeoutExpired:
        print("   Claude Code 超时，使用规则生成摘要...")
        return generate_summary_rule_based(content, title, max_length)
    except Exception as e:
        print(f"   Claude Code 不可用: {e}")
    
    # Fallback: 使用规则生成摘要
    print("   使用规则生成摘要...")
    return generate_summary_rule_based(content, title, max_length)


def generate_summary_rule_based(content, title="", max_length=200):
    """基于规则生成文章摘要 - 改进版"""
    if not content:
        return ""
    
    content = content.strip()
    
    # 清理内容：去除多余空白、特殊字符、emoji
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'[🦞📝🛠️💡🔥⭐✨✅❌📌📎🎯📊💪⚡🌟💎🚀📝✅💡🎁❤️👇📌]', '', content)
    
    # 优先从文章开头提取关键信息（通常包含核心观点）
    # 提取前500字作为重点分析区域
    intro_section = content[:500] if len(content) > 500 else content
    
    # 从文章开头提取关键句子（通常包含核心观点）
    intro_sentences = re.split(r'[。！？\n]', intro_section)
    intro_sentences = [s.strip() for s in intro_sentences if len(s.strip()) > 20 and len(s.strip()) < 150]
    
    # 从全文提取句子
    sentences = re.split(r'[。！？\n]', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20 and len(s.strip()) < 150]
    
    # 过滤掉代码、命令行、URL、指令等
    filtered_sentences = []
    skip_patterns = [
        r'^```', r'^python', r'^npm', r'^\$', r'^>', r'^https?://',
        r'^/', r'^\[', r'^\d+\.', r'^[\-\*\+#]',  # 跳过markdown格式
        r'^(请|建议|注意|提示|警告)',  # 跳过指令性文字
    ]
    
    for sent in sentences:
        if any(re.match(p, sent) for p in skip_patterns):
            continue
        # 跳过纯数字或纯符号
        if re.match(r'^[\d\s\W]+$', sent):
            continue
        filtered_sentences.append(sent)
    
    # 关键句识别（优先级排序）- 更精准的模式
    key_patterns = [
        r'(本文|文章|作者|指出|认为|表示|介绍|分享|讲解|说明|阐述)',
        r'(核心|关键|要点|重点|本质|实质)',
        r'(总结|结论|建议|启示|意义|价值)',
        r'(通过|使用|采用|利用|基于).{5,30}(实现|达成|完成|做到)',
        r'(解决|应对|处理).{5,30}(问题|挑战|痛点|难题)',
    ]
    
    key_sentences = []
    normal_sentences = []
    
    # 优先使用开头的句子
    for sent in intro_sentences[:5]:
        is_key = any(re.search(pattern, sent) for pattern in key_patterns)
        if is_key:
            key_sentences.append(sent)
        else:
            normal_sentences.append(sent)
    
    # 再从全文中找关键句
    for sent in filtered_sentences[:20]:
        if sent in intro_sentences[:5]:
            continue
        is_key = any(re.search(pattern, sent) for pattern in key_patterns)
        if is_key and len(sent) > 30:
            key_sentences.append(sent)
    
    # 构建摘要
    summary_parts = []
    
    # 优先使用关键句
    if key_sentences:
        summary_parts.extend(key_sentences[:3])
    
    # 如果关键句不够，补充普通句
    if len(''.join(summary_parts)) < 100 and normal_sentences:
        for sent in normal_sentences[:2]:
            if len(''.join(summary_parts)) + len(sent) < max_length - 10:
                summary_parts.append(sent)
    
    # 合并并清理
    summary = '。'.join(summary_parts)
    summary = re.sub(r'。+', '。', summary)
    summary = summary.strip('。')
    
    # 控制长度 - 确保完整句子，不出现省略号
    if len(summary) > max_length:
        truncated = summary[:max_length]
        last_period = truncated.rfind('。')
        if last_period > max_length * 0.5:  # 确保至少保留50%内容
            summary = truncated[:last_period+1]
        else:
            # 如果找不到合适的句号，直接截断并添加句号
            summary = truncated.rstrip() + '。'
    
    # 确保摘要以句号结尾
    if not summary.endswith('。'):
        summary = summary.rstrip('.') + '。'
    
    return summary


# ============ 飞书推送 ============

def push_to_feishu(url, title, summary, webhook_url=None):
    """推送文章到飞书 webhook"""
    webhook = webhook_url or WEBHOOK_URL
    
    data = {
        "url": url,
        "title": title,
        "summary": summary
    }
    
    try:
        req = urllib.request.Request(
            webhook,
            data=json.dumps(data, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("code") == 0, result
            
    except Exception as e:
        return False, {"error": str(e)}


# ============ IMA 知识库 ============

def load_ima_credentials():
    """加载 IMA 凭证"""
    client_id = ""
    api_key = ""
    
    # 从配置文件读取
    id_file = IMA_CONFIG_PATH / "client_id"
    key_file = IMA_CONFIG_PATH / "api_key"
    if id_file.exists():
        client_id = id_file.read_text().strip()
    if key_file.exists():
        api_key = key_file.read_text().strip()
    
    return client_id, api_key


def add_to_ima_kb(url):
    """添加微信公众号文章到 IMA 知识库"""
    client_id, api_key = load_ima_credentials()
    
    if not client_id or not api_key:
        print("   ⚠️  IMA 凭证未配置，跳过")
        return
    
    payload = json.dumps({
        "knowledge_base_id": IMA_KB_ID,
        "urls": [url]
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{IMA_API_BASE}/openapi/wiki/v1/import_urls",
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'ima-openapi-clientid': client_id,
            'ima-openapi-apikey': api_key,
        },
        method='POST'
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode('utf-8'))
    
    if result.get('code') == 0:
        results = result.get('data', {}).get('results', {})
        for item in results.values():
            if item.get('ret_code') == 0:
                print("   ✅ 已添加到 IMA「AI资讯」知识库")
            else:
                print(f"   ⚠️  添加失败: {item.get('errmsg', '未知错误')}")
    else:
        print(f"   ⚠️  API 错误: {result.get('msg', '未知错误')}")


# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description='News Collect - 资讯收集工具')
    parser.add_argument('url', help='文章URL')
    parser.add_argument('--webhook', help='自定义飞书webhook地址')
    parser.add_argument('--no-push', action='store_true', help='不推送到飞书，仅输出结果')
    parser.add_argument('--summary-length', type=int, default=200, help='摘要长度（默认200字）')
    
    args = parser.parse_args()
    
    print(f"🚀 开始抓取: {args.url}")
    
    # 1. 抓取内容
    data = fetch_article(args.url)
    
    if "error" in data:
        error_msg = data['error']
        # 特殊处理飞书 Wiki
        if error_msg == "FEISHU_WIKI_REQUIRES_SESSION":
            print(f"⚠️  飞书 Wiki 链接检测")
            print(f"   {data.get('message', '请直接在当前对话中发送链接，我会自动处理')}")
            print(f"\n   URL: {args.url}")
            sys.exit(0)
        print(f"❌ 抓取失败: {error_msg}")
        sys.exit(1)
    
    print(f"✅ 抓取成功: {data['title']}")
    if data['author']:
        print(f"   作者: {data['author']}")
    
    # 2. 生成摘要
    print("📝 生成摘要...")
    summary = generate_summary_with_llm(data['content'], data['title'], args.summary_length)
    print(f"✅ 摘要生成完成 ({len(summary)}字)")
    
    # 3. 输出结果
    result = {
        "url": args.url,
        "title": data['title'],
        "author": data['author'],
        "publish_time": data['publish_time'],
        "summary": summary
    }
    
    print("\n" + "="*50)
    print("📋 收集结果:")
    print("="*50)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 4. 推送到飞书
    if not args.no_push:
        print("\n📤 推送到飞书...")
        success, response = push_to_feishu(
            args.url, 
            data['title'], 
            summary, 
            args.webhook
        )
        
        if success:
            print("✅ 推送成功！")
        else:
            print(f"❌ 推送失败: {response}")
            sys.exit(1)
    
    # 5. 添加到 IMA 知识库
    if IMA_KB_ENABLED and not args.no_push and is_wechat_article(args.url):
        print("\n📚 添加到 IMA 知识库...")
        try:
            add_to_ima_kb(args.url)
        except Exception as e:
            print(f"⚠️  IMA 知识库添加失败: {e}")
    
    print("\n✨ 完成!")


if __name__ == "__main__":
    main()
