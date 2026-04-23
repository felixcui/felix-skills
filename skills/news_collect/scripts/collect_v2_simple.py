#!/usr/bin/env python3
"""
News Collect V2 简化版 - 支持上传到 NotebookLM
功能：抓取文章 → 生成摘要 → 推送飞书 → 上传NotebookLM
"""
import sys
import re
import json
import urllib.request
import urllib.parse
import argparse
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# ============ 配置 ============
WEBHOOK_URL = "https://www.feishu.cn/flow/api/trigger-webhook/4ebcdc4fd26c38187fdd74434d17a916"
NOTEBOOKLM_CMD = "notebooklm"
NOTEBOOK_NAME = "AI 资讯"

# IMA 知识库配置
IMA_KB_ENABLED = True
IMA_KB_ID = "AGoC5oEY8FP12VotR1kff00HlmJyh3RP6Do9vCGKpGQ="
IMA_CONFIG_PATH = Path.home() / ".config" / "ima"
IMA_API_BASE = "https://ima.qq.com"


# ============ 内容抓取 ============

def is_wechat_article(url):
    """判断是否是微信公众号文章"""
    return 'mp.weixin.qq.com' in url or 'weixin.qq.com' in url


def is_twitter_url(url):
    """判断是否是 Twitter/X 链接"""
    return bool(re.match(r'https?://(x\.com|twitter\.com)/\w+/status/\d+', url))


def is_feishu_doc(url):
    """判断是否是飞书文档链接"""
    return 'feishu.cn/docx' in url or 'feishu.cn/wiki' in url


def fetch_feishu_doc(url):
    """抓取飞书文档 - 使用 feishu_fetch_doc 工具"""
    try:
        # 提取 doc_id
        if '/docx/' in url:
            doc_id = url.split('/docx/')[-1]
        elif '/wiki/' in url:
            doc_id = url.split('/wiki/')[-1]
        else:
            return {"error": "无法识别的飞书文档 URL"}
        
        # 调用 feishu_fetch_doc
        result = subprocess.run(
            ['claude', '-p', '--permission-mode', 'bypassPermissions', '--output-format', 'text', 
             f'Use the feishu_fetch_doc tool to get the content of Feishu document with ID: {doc_id}'],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            return {"error": f"feishu_fetch_doc 调用失败: {result.stderr}"}
        
        # 从结果中提取内容
        content = result.stdout.strip()
        
        # 提取标题（第一行）
        lines = content.split('\n')
        title = "未知标题"
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
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


def fetch_wechat_article(url):
    """抓取微信公众号文章"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取标题
        title = soup.find('meta', property='og:title')
        title = title.get('content', '') if title else soup.find('h1').get_text() if soup.find('h1') else '未知标题'
        
        # 提取作者
        author = soup.find('meta', property='og:article:author')
        author = author.get('content', '未知作者') if author else '未知作者'
        
        # 提取正文
        content_div = soup.find('div', id='js_content')
        if not content_div:
            content_div = soup.find('div', class_='rich_media_content')
        
        if content_div:
            content = content_div.get_text('\n')
        else:
            content = "无法提取正文"
        
        return {
            "title": title,
            "author": author,
            "publish_time": "",
            "content": content,
            "url": url
        }
    except Exception as e:
        return {"error": f"抓取失败: {str(e)}"}


def fetch_generic_article(url):
    """抓取普通网页内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
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
            r'<div[^>]*id="content"[^>]*>(.*?)</div>',
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


def fetch_twitter_tweet(url):
    """使用 twitter-cli 获取推文内容"""
    try:
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


def fetch_article(url):
    """统一抓取文章接口"""
    if is_twitter_url(url):
        return fetch_twitter_tweet(url)
    if is_wechat_article(url):
        return fetch_wechat_article(url)
    if is_feishu_doc(url):
        return fetch_feishu_doc(url)
    return fetch_generic_article(url)


# ============ 摘要生成 ============

def generate_summary_with_llm(content, title="", max_length=200):
    """使用 Claude Code 生成文章摘要"""
    if not content:
        return ""
    
    content = content.strip()[:2000]
    
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
    
    try:
        print("   使用 Claude Code 生成摘要...")
        result = subprocess.run(
            ["claude", "-p", "--permission-mode", "bypassPermissions", "--output-format", "text", prompt],
            capture_output=True,
            text=True,
            timeout=90
        )
        
        if result.returncode == 0:
            summary = result.stdout.strip()
            # 清理摘要
            summary = re.sub(r'^["\']|["\']$', '', summary)
            summary = re.sub(r'^(摘要|总结)[:：]?\s*', '', summary)
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
    
    print("   使用规则生成摘要...")
    return generate_summary_rule_based(content, title, max_length)


def generate_summary_rule_based(content, title="", max_length=200):
    """基于规则生成文章摘要"""
    if not content:
        return ""
    
    content = content.strip()
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'[🦞📝🛠️💡🔥⭐✨✅❌📌🎯📊💪⚡🌟💎🎁❤️👇📌]', '', content)
    
    # 优先从文章开头提取关键信息（通常包含核心观点）
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
        r'^/', r'^\[', r'^\d+\.', r'^[-\*\+#]',  # 过滤 markdown 格式
        r'^(请|建议|注意|提示|警告)',  # 过滤指令性文字
    ]
    
    for sent in sentences:
        if any(re.match(p, sent) for p in skip_patterns):
            continue
        # 过滤纯数字或纯符号
        if re.match(r'^[\d\s\W]+$', sent):
            continue
        filtered_sentences.append(sent)
    
    # 关键句识别（优先级排序）
    key_patterns = [
        r'(本文|文章|作者|指出|认为|表示|介绍|分享|讲解|说明|阐述)',
        r'(核心|关键|要点|重点|本质|实质)',
        r'(总结|结论|建议|启示|意义|价值)',
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
    
    # 如果还不够，补充普通句子
    if len(''.join(summary_parts)) < 100 and normal_sentences:
        for sent in normal_sentences[:2]:
            if len(''.join(summary_parts)) + len(sent) < max_length - 10:
                summary_parts.append(sent)
    
    summary = '。'.join(summary_parts)
    summary = re.sub(r'。+', '。', summary)
    summary = summary.strip('。')
    
    if len(summary) > max_length:
        truncated = summary[:max_length]
        last_period = truncated.rfind('。')
        if last_period > max_length * 0.5:
            summary = truncated[:last_period+1]
        else:
            summary = truncated.rstrip() + '。'
    
    if not summary.endswith('。'):
        summary = summary.rstrip('.') + '。'
    
    return summary


# ============ NotebookLM 集成 ============

def setup_notebooklm_notebook():
    """确保 NotebookLM 笔记本存在"""
    try:
        # 先确认 notebooklm 命令可用
        check = subprocess.run(
            [NOTEBOOKLM_CMD, '--help'],
            capture_output=True,
            text=True
        )
        if check.returncode != 0:
            print(f"   ⚠️ NotebookLM 命令不可用: {check.stderr.strip()}")
            return False

        # 查找笔记本
        result = subprocess.run(
            [NOTEBOOKLM_CMD, 'list'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and NOTEBOOK_NAME in result.stdout:
            print(f"   ✅ NotebookLM 笔记本「{NOTEBOOK_NAME}」已存在")
            return True

        # 创建笔记本
        print(f"   创建 NotebookLM 笔记本「{NOTEBOOK_NAME}」...")
        result = subprocess.run(
            [NOTEBOOKLM_CMD, 'create', NOTEBOOK_NAME],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"   ✅ 笔记本创建成功")
            return True

        stderr = (result.stderr or '').strip() or (result.stdout or '').strip() or '未知错误'
        print(f"   ⚠️ 笔记本创建失败: {stderr}")
        return False
    except FileNotFoundError:
        print("   ⚠️ NotebookLM 命令未安装，跳过上传")
        return False
    except Exception as e:
        print(f"   ⚠️ NotebookLM 设置失败: {e}")
        return False


def upload_to_notebooklm(markdown_content, title):
    """上传内容到 NotebookLM"""
    try:
        # 创建临时文件
        import tempfile
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)[:80]
        temp_file = tempfile.mktemp(suffix='.md', prefix=f'news_{safe_title}_')
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 上传到 NotebookLM
        print(f"   上传到 NotebookLM...")
        result = subprocess.run(
            [NOTEBOOKLM_CMD, 'source', 'add', temp_file, '--title', title],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"   ✅ 上传成功，已添加到「{NOTEBOOK_NAME}」笔记本")
            return True
        else:
            print(f"   ⚠️ 上传失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ⚠️ 上传失败: {e}")
        return False


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

def add_to_ima_kb(url):
    """添加微信公众号文章到 IMA 知识库"""
    client_id = ""
    api_key = ""
    
    # 从配置文件读取
    id_file = IMA_CONFIG_PATH / "client_id"
    key_file = IMA_CONFIG_PATH / "api_key"
    if id_file.exists():
        client_id = id_file.read_text().strip()
    if key_file.exists():
        api_key = key_file.read_text().strip()
    
    if not client_id or not api_key:
        print("   ⚠️ IMA 认证未配置，跳过")
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
                print(f"   ⚠️ 添加失败: {item.get('errmsg', '未知错误')}")
    else:
        print(f"   ⚠️ API 错误: {result.get('msg', '未知错误')}")


# ============ Markdown 生成 ============

def create_markdown_content(title, author, url, summary, content):
    """创建 Markdown 格式内容"""
    markdown = f"# {title}\n\n"
    if author:
        markdown += f"**作者**: {author}\n\n"
    markdown += f"**来源**: {url}\n\n"
    markdown += "---\n\n"
    markdown += "## 摘要\n\n"
    markdown += f"{summary}\n\n"
    markdown += "---\n\n"
    markdown += "## 正文\n\n"
    markdown += content
    return markdown




def sanitize_filename(text):
    """清理文件名中的特殊字符。"""
    text = re.sub(r'[\/:*?"<>|]+', '', text)
    text = re.sub(r'\s+', '', text).strip()
    text = re.sub(r'[ -]+', '', text)
    return text


def unique_raw_markdown_path(raw_dir, base_name):
    """避免文件名重复，自动追加序号。"""
    candidate = raw_dir / f"{base_name}.md"
    if not candidate.exists():
        return candidate

    idx = 2
    while True:
        candidate = raw_dir / f"{base_name}_{idx}.md"
        if not candidate.exists():
            return candidate
        idx += 1


def save_raw_markdown(title, markdown_content):
    """将抓取到的文章 Markdown 存储到 raw 目录。"""
    raw_dir = Path('/Users/felix/work/media-conent/raw')
    raw_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')
    safe_title = sanitize_filename(title)[:80] or 'article'
    base_name = f"{today}_{safe_title}"
    file_path = unique_raw_markdown_path(raw_dir, base_name)
    file_path.write_text(markdown_content, encoding='utf-8')
    return file_path

# ============ 主流程 ============

def main():
    parser = argparse.ArgumentParser(description='News Collect V2 简化版 - 支持上传到 NotebookLM')
    parser.add_argument('url', help='文章URL')
    parser.add_argument('--webhook', help='自定义飞书webhook地址')
    parser.add_argument('--no-push', action='store_true', help='不推送到飞书，仅输出结果')
    parser.add_argument('--notebook', action='store_true', default=True, help='上传到 NotebookLM（默认开启）')
    parser.add_argument('--no-notebook', action='store_true', help='不上传到 NotebookLM')
    parser.add_argument('--summary-length', type=int, default=200, help='摘要长度（默认200字）')
    
    args = parser.parse_args()
    
    print(f"🚀 开始处理: {args.url}")
    print("="*60)
    
    # 1. 抓取内容
    print("\n[1/5] 抓取内容...")
    data = fetch_article(args.url)
    
    if "error" in data:
        error_msg = data['error']
        print(f"❌ 抓取失败: {error_msg}")
        sys.exit(1)
    
    print(f"✅ 抓取成功: {data['title']}")
    if data['author']:
        print(f"   作者: {data['author']}")
    
    # 2. 生成摘要
    print("\n[2/5] 生成摘要...")
    summary = generate_summary_with_llm(data['content'], data['title'], args.summary_length)
    print(f"✅ 摘要生成完成 ({len(summary)}字)")
    
    # 3. 创建 Markdown
    print("\n[3/5] 创建 Markdown...")
    markdown_content = create_markdown_content(
        data['title'],
        data.get('author', ''),
        args.url,
        summary,
        data['content']
    )
    print("✅ Markdown 创建完成")

    # 3.1 存储原始 Markdown
    print("\n[3.1/5] 存储原始 Markdown...")
    raw_path = save_raw_markdown(data['title'], markdown_content)
    print(f"✅ 已保存到: {raw_path}")
    
    # 4. 上传到 NotebookLM
    if args.notebook and not args.no_notebook:
        print("\n[4/5] 上传到 NotebookLM...")
        setup_success = setup_notebooklm_notebook()
        
        if setup_success:
            upload_success = upload_to_notebooklm(markdown_content, data['title'])
            
            if not upload_success:
                print("⚠️ NotebookLM 上传失败，但继续其他操作")
    
    # 5. 推送到飞书
    if not args.no_push:
        print("\n[5/5] 推送到飞书...")
        success, response = push_to_feishu(
            args.url,
            data['title'],
            summary,
            args.webhook
        )
        
        if success:
            print("✅ 推送成功！")
        else:
            print(f"❌ 推送失败: {response.get('error', '未知错误')}")
            sys.exit(1)
    
    # 6. 添加到 IMA 知识库
    if not args.no_push and IMA_KB_ENABLED and is_wechat_article(args.url):
        print("\n[6/6] 添加到 IMA 知识库...")
        try:
            add_to_ima_kb(args.url)
        except Exception as e:
            print(f"⚠️ IMA 知识库添加失败: {e}")
    
    # 7. 输出结果
    print("\n" + "="*60)
    print("📋 处理结果:")
    print("="*60)
    result = {
        "url": args.url,
        "title": data['title'],
        "author": data.get('author', ''),
        "summary": summary,
        "raw_markdown_path": str(raw_path),
        "notebooklm": args.notebook
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n✨ 完成!")


if __name__ == "__main__":
    main()
