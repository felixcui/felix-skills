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
import yaml
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# ============ 配置 ============
# 飞书多维表格配置
FEISHU_BASE_TOKEN = "Tn1vbRQyraNFvAstbqicUlIJnue"
FEISHU_TABLE_ID = "tblXp6DHjQPomXbv"
# +record-batch-create --json 的 fields 使用字段名
FEISHU_FIELDS = ["title", "link", "description", "source", "updatetime"]
NOTEBOOKLM_CMD = "notebooklm"
NOTEBOOK_NAME = "AI 资讯 V3"
NOTEBOOK_ID = "b08626a7-cda5-4dd2-b0e7-536eafb48274"

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
    """判断是否是 Twitter/X 链接（包括 /i/article/ 长文链接）"""
    return bool(re.match(r'https?://(x\.com|twitter\.com)/\w+/status/\d+', url)) or \
           bool(re.match(r'https?://(x\.com|twitter\.com)/i/article/\d+', url))


def is_feishu_doc(url):
    """判断是否是飞书文档链接"""
    return 'feishu.cn/docx' in url or 'feishu.cn/wiki' in url


def fetch_feishu_doc(url):
    """抓取飞书文档 - 使用 lark-cli docs +fetch (v2 API)"""
    try:
        # v2 API 接受完整 URL 或 token，直接传入即可
        result = subprocess.run(
            ['lark-cli', 'docs', '+fetch', '--doc', url,
             '--scope', 'full', '--doc-format', 'markdown',
             '--format', 'json', '--as', 'user'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            # stderr 可能包含 hint，提取实际错误
            return {"error": f"lark-cli 调用失败: {stderr}"}

        try:
            resp = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": f"lark-cli 返回非 JSON: {result.stdout[:200]}"}

        if not resp.get('ok'):
            return {"error": f"lark-cli API 错误: {resp}"}

        # v2 返回结构: data.document.content (markdown/xml 字符串)
        doc_data = resp.get('data', {}).get('document', {})
        content = doc_data.get('content', '')

        if not content or not content.strip():
            return {"error": "飞书文档内容为空（可能无权限访问）"}

        # v2 返回的 markdown 格式，content 以 <title> 开头
        # 从 content 中提取标题
        doc_title = ""
        title_match = re.match(r'<title>(.*?)</title>', content)
        if title_match:
            doc_title = title_match.group(1).strip()
            content = content[title_match.end():]

        # 如果 markdown 格式，清理飞书特殊标签
        all_markdown = content
        all_markdown = re.sub(r'<image[^/]*/>', '', all_markdown)
        all_markdown = re.sub(r'<view[^>]*>.*?</view>', '', all_markdown, flags=re.DOTALL)
        all_markdown = re.sub(r'<file[^/]*/>', '', all_markdown)
        all_markdown = re.sub(r'<mention-doc[^>]*>(.*?)</mention-doc>', r'\\1', all_markdown)
        # 清理其他飞书特殊标签
        all_markdown = re.sub(r'<whiteboard[^>]*>.*?</whiteboard>', '', all_markdown, flags=re.DOTALL)
        all_markdown = re.sub(r'<grid[^>]*>.*?</grid>', '', all_markdown, flags=re.DOTALL)
        all_markdown = re.sub(r'<column[^>]*/?>', '', all_markdown)
        # 修复 lark-cli 转义的 unicode
        all_markdown = all_markdown.replace('\\u003c', '<').replace('\\u003e', '>')
        all_markdown = all_markdown.replace('\\u0026', '&')

        # 从 markdown 中提取标题（如果 XML title 没拿到）
        if not doc_title:
            for line in all_markdown.split('\n'):
                if line.startswith('# '):
                    doc_title = line[2:].strip()
                    break
        if not doc_title:
            doc_title = "未知标题"

        return {
            "title": doc_title,
            "author": "",
            "source_name": "飞书文档",
            "publish_time": "",
            "content": all_markdown.strip(),
            "url": url
        }
    except subprocess.TimeoutExpired:
        return {"error": "lark-cli 超时"}
    except FileNotFoundError:
        return {"error": "lark-cli 未安装"}
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


def fetch_wechat_article_defuddle(url):
    """抓取微信公众号文章 - 使用 defuddle 获取 Markdown 内容"""
    try:
        result = subprocess.run(
            ['defuddle', 'parse', '-j', '--md', url],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return {"error": f"defuddle 调用失败: {result.stderr}"}
            
        data = json.loads(result.stdout.strip())
        
        # 提取公众号名称（作为 source_name）
        source_name = data.get("site_name") or ""
        if not source_name:
            # defuddle 可能返回 author，但那是文章作者而非公众号
            # 通过 fetch_wechat_account_name 从页面 HTML 补充获取
            source_name = fetch_wechat_account_name(url)
        
        return {
            "title": data.get("title") or "未知标题",
            "author": data.get("author") or "未知作者",
            "source_name": source_name,
            "publish_time": data.get("published") or "",
            "content": data.get("content") or "无法提取正文",
            "url": url
        }
    except FileNotFoundError:
        return {"error": "defuddle 未安装，请先安装 defuddle"}
    except subprocess.TimeoutExpired:
        return {"error": "defuddle 调用超时"}
    except json.JSONDecodeError:
        return {"error": "defuddle 返回格式解析失败"}
    except Exception as e:
        return {"error": f"抓取失败: {str(e)}"}


def fetch_wechat_account_name(url):
    """从微信文章页面提取公众号名称"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 方式1: og:article:tag 通常包含公众号名称
        og_tag = soup.find('meta', property='og:article:tag')
        if og_tag and og_tag.get('content'):
            return og_tag.get('content')
        
        # 方式2: 账号信息区域 nickname class
        nickname_el = soup.find('a', class_='rich_media_meta_nickname') or \
                      soup.find('span', class_='rich_media_meta_nickname') or \
                      soup.find('a', attrs={'id': 'js_name'}) or \
                      soup.find('a', attrs={'id': 'profileBt'})
        if nickname_el:
            return nickname_el.get_text(strip=True)
        
        return ""
    except Exception:
        return ""


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
        
        # 提取网站名称（域名）
        from urllib.parse import urlparse
        parsed = urlparse(url)
        site_name = parsed.netloc.replace('www.', '').split('.')[0].capitalize()
        
        return {
            "title": title,
            "author": "",
            "source_name": site_name,
            "publish_time": "",
            "content": content,
            "url": url
        }
    except Exception as e:
        return {"error": f"抓取失败: {str(e)}"}


TWITTER_CLI = "/Users/felix/.local/bin/twitter"


def _parse_twitter_timestamp(ts_str):
    """解析 twitter CLI 的时间戳（支持 ISO 格式和 Unix 时间戳）"""
    if not ts_str:
        return ""
    # ISO 格式: 2026-05-08T17:56:30+00:00
    if "T" in str(ts_str):
        try:
            from datetime import timezone
            dt = datetime.fromisoformat(str(ts_str))
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).astimezone()
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            pass
    # 回退到原始 format_timestamp
    return format_timestamp(ts_str)


def fetch_twitter_tweet(url):
    """使用 twitter CLI 获取推文内容（支持普通推文和 X Article 长文）"""
    # 如果是 /i/article/ 链接，需要先获取对应的 status URL
    fetch_url = url
    if "/i/article/" in url:
        # twitter CLI 的 tweet 子命令需要 status URL，尝试直接用 article URL
        # 如果失败，会回退到错误提示
        pass

    try:
        result = subprocess.run(
            [TWITTER_CLI, "tweet", fetch_url, "--json"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {"error": f"twitter CLI 获取失败: {result.stderr.strip() or '未知错误'}"}

        data = json.loads(result.stdout.strip())
        tweet_list = data.get("data", data)
        if isinstance(tweet_list, list) and tweet_list:
            tweet_data = tweet_list[0]
        elif isinstance(tweet_list, dict):
            tweet_data = tweet_list
        else:
            return {"error": "twitter CLI 未返回有效推文数据（可能推文不存在或不可访问）"}

        author_info = tweet_data.get("author", {})
        screen_name = author_info.get("screenName", "")
        author_name = author_info.get("name", "")

        # 判断是否为 X Article 长文
        article_title = tweet_data.get("articleTitle")
        article_text = tweet_data.get("articleText")

        if article_title and article_text:
            # Article 类型：使用完整长文内容
            title = article_title
            content = article_text
        else:
            # 普通推文：使用 text 字段
            title = f"@{screen_name} 的推文"
            content = tweet_data.get("text", "")

        # 补充 metrics 信息到 content 末尾
        metrics = tweet_data.get("metrics", {})
        likes = metrics.get("likes", 0)
        retweets = metrics.get("retweets", 0)
        views = metrics.get("views", 0)
        bookmarks = metrics.get("bookmarks", 0)
        if any([likes, retweets, views, bookmarks]):
            content += f"\n\n---\n📊 互动数据：❤️ {likes} | 🔁 {retweets} | 👁 {views} | 🔖 {bookmarks}"

        return {
            "title": title,
            "author": f"{author_name} (@{screen_name})",
            "source_name": f"X: @{screen_name}",
            "publish_time": _parse_twitter_timestamp(tweet_data.get("createdAtISO", "")),
            "content": content,
            "url": url
        }
    except FileNotFoundError:
        return {"error": f"twitter CLI 未找到: {TWITTER_CLI}"}
    except subprocess.TimeoutExpired:
        return {"error": "twitter CLI 超时（60s）"}
    except json.JSONDecodeError as e:
        return {"error": f"twitter CLI 返回无效 JSON: {str(e)}"}
    except Exception as e:
        return {"error": f"twitter CLI 错误: {str(e)}"}


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
        return fetch_wechat_article_defuddle(url)
    if is_feishu_doc(url):
        return fetch_feishu_doc(url)
    return fetch_generic_article(url)


# ============ 摘要生成 ============

def _load_hermes_config():
    """从 Hermes 配置文件加载 LLM API 配置"""
    config_paths = [
        Path.home() / ".hermes" / "config.yaml",
        Path.home() / ".hermes" / "config.yml",
    ]
    for p in config_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    return {}

def _call_llm_for_summary(api_key, base_url, model_name, prompt, max_length):
    """调用 LLM API 生成摘要的通用函数，返回摘要字符串或 None"""
    chat_url = base_url.rstrip("/")
    if not chat_url.endswith("/chat/completions"):
        chat_url = chat_url.rstrip("/") + "/chat/completions"

    resp = requests.post(
        chat_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.3,
        },
        timeout=60,
    )

    if resp.status_code == 200:
        msg = resp.json()["choices"][0]["message"]
        summary = msg.get("content", "").strip() or msg.get("reasoning_content", "").strip()
        # 清理摘要
        summary = re.sub(r'^["\']|["\']$', '', summary)
        summary = re.sub(r'^(摘要|总结)[:：]?\s*', '', summary)
        summary = re.sub(r'\.{3}', '', summary)
        summary = re.sub(r'…', '', summary)

        # 检测伪摘要：推理模型偶尔输出分析过程而非实际摘要
        if re.match(r'^[\d]+\.\s*\*{0,2}(分析|任务|长度|格式|内容|约束|要求)', summary):
            return None

        if len(summary) > 50:
            if len(summary) > max_length:
                truncated = summary[:max_length]
                last_period = truncated.rfind('。')
                if last_period > max_length * 0.6:
                    summary = truncated[:last_period+1]
                else:
                    summary = truncated.rstrip() + '。'
            if not summary.endswith('。'):
                summary = summary.rstrip('.') + '。'
            return summary
    return None


def generate_summary_with_glm(content, title="", max_length=200):
    """使用 GLM API 生成文章摘要，失败时自动降级到 hongmacc，再失败用规则"""
    if not content:
        return ""

    content = content.strip()[:2000]

    prompt = f"""请直接输出以下文章的摘要，{max_length}字以内，一段话，以句号结尾。不要输出任何分析过程、思考步骤或约束条件复述。

标题：{title}

内容：
{content}

摘要："""

    # ---- 第1优先：GLM（从 .env 读取）----
    try:
        skill_env_path = Path(__file__).resolve().parent.parent / ".env"
        api_key, base_url, model_name = "", "https://open.bigmodel.cn/api/paas/v4", "glm-5-turbo"
        if skill_env_path.exists():
            for line in skill_env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                elif line.startswith("OPENAI_BASE_URL="):
                    base_url = line.split("=", 1)[1].strip()
                elif line.startswith("OPENAI_MODEL="):
                    model_name = line.split("=", 1)[1].strip()

        if api_key:
            print(f"   使用 GLM ({model_name}) 生成摘要...")
            summary = _call_llm_for_summary(api_key, base_url, model_name, prompt, max_length)
            if summary:
                print(f"   使用 GLM 生成摘要 ({len(summary)}字)")
                return summary
            else:
                print(f"   ⚠️ GLM 返回无效内容，尝试 hongmacc...")
        else:
            print("   ⚠️ GLM API key 未配置，尝试 hongmacc...")
    except Exception as e:
        print(f"   ⚠️ GLM 不可用: {e}，尝试 hongmacc...")

    # ---- 第2优先：hongmacc (gpt-5.4-mini，从 ~/.hermes/config.yaml 读取)----
    try:
        import yaml as _yaml
        config_path = Path.home() / ".hermes" / "config.yaml"
        if config_path.exists():
            cfg = _yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            providers = cfg.get("providers", [])
            for p in providers:
                if isinstance(p, dict) and p.get("name") == "hongmacc":
                    h_key = p.get("api_key", "")
                    h_url = p.get("base_url", "https://hongmacc.com/v1")
                    h_model = p.get("model", "gpt-5.4-mini")
                    print(f"   使用 hongmacc ({h_model}) 生成摘要...")
                    summary = _call_llm_for_summary(h_key, h_url, h_model, prompt, max_length)
                    if summary:
                        print(f"   使用 hongmacc 生成摘要 ({len(summary)}字)")
                        return summary
                    else:
                        print(f"   ⚠️ hongmacc 返回无效内容，使用规则生成...")
                    break
    except Exception as e:
        print(f"   ⚠️ hongmacc 不可用: {e}")

    # ---- 最终降级：规则摘要 ----
    return generate_summary_rule_based(content, title, max_length)



def generate_summary_with_llm(content, title="", max_length=200, engine="glm"):
    """使用指定 LLM 引擎生成文章摘要

    engine: "glm" (默认) | "rule"
    """
    if engine == "rule":
        return generate_summary_rule_based(content, title, max_length)
    else:
        # 默认使用 GLM
        return generate_summary_with_glm(content, title, max_length)


def _clean_content_for_summary(content):
    """清洗正文内容，去除作者行、编辑行、格式标记等噪声"""
    if not content:
        return ""
    
    lines = content.split('\n')
    cleaned_lines = []
    
    # 需要跳过的噪声模式
    noise_patterns = [
        # 作者/编辑行：** 作者｜xxx** / **编辑｜ **xxx****（仅匹配短行，长行做行内清洗）
        # 图片链接
        r'^!\[.*?\]\(.*?\)$',
        # 空行/纯空白
        r'^\s*$',
        # 阅读器交互文本："在小说阅读器读本章" / "去阅读"
        r'^(在.*阅读器|去阅读|展开全文|阅读原文|点击阅读)',
        # 微信公众号底部交互元素
        r'^(赞|在看|分享|收藏|喜欢|打赏|投诉|举报)',
        # 纯 emoji 行
        r'^[\s]*[🦞📝🛠️💡🔥⭐✨✅❌📌🎯📊💪⚡🌟💎🎁❤️👇🎉🏆💬🔔🔗📱💻🔍📈🎁🤖]+[\s]*$',
    ]
    
    # 短元数据行模式（作者/编辑/来源行，长度<80才整行跳过）
    metadata_line_pattern = r'^[\s]*\*{0,2}\s*(作者|编辑|来源|出处)\s*[｜|:：]'
    # 纯名字行（如 "Li Yuan Li Yuan"）
    name_line_pattern = r'^[\s]*[A-Za-z]+(\s+[A-Za-z]+)+\s*$'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过匹配通用噪声模式的行
        if any(re.match(p, line) for p in noise_patterns):
            continue
        # 跳过纯名字行（如 "Li Yuan Li Yuan"）
        if re.match(name_line_pattern, line):
            continue
        # 跳过短的元数据行（纯作者/编辑/来源信息，<80字符），长行保留做行内清洗
        if re.match(metadata_line_pattern, line) and len(line) < 80:
            continue
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # 去除 markdown 加粗/格式标记
    text = re.sub(r'\*{2,}', '', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # 内联图片
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # 链接保留文字
    
    # 去除行内残留的作者/编辑标记（如 "作者｜Li Yuan 编辑｜ 郑玄"）
    text = re.sub(r'(作者|编辑|来源|出处)\s*[｜|:：]\s*[\w\s\.]+?(?=\s*(?:作者|编辑|来源|出处)|[，。！？\n]|$)', '', text)
    
    # 压缩连续空白
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()


def generate_summary_rule_based(content, title="", max_length=200):
    """基于规则生成文章摘要"""
    if not content:
        return ""
    
    # 先清洗噪声
    content = _clean_content_for_summary(content)
    
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'[🦞📝🛠️💡🔥⭐✨✅❌📌🎯📊💪⚡🌟💎🎁❤️👇📌]', '', content)
    
    # 优先从文章开头提取关键信息（通常包含核心观点）
    intro_section = content[:800] if len(content) > 800 else content
    
    # 从文章开头提取关键句子（通常包含核心观点）
    intro_sentences = re.split(r'[。！？\n]', intro_section)
    intro_sentences = [s.strip() for s in intro_sentences if len(s.strip()) > 15 and len(s.strip()) < 200]
    
    # 从全文提取句子
    sentences = re.split(r'[。！？\n]', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15 and len(s.strip()) < 200]
    
    # 过滤掉代码、命令行、URL、指令等
    filtered_sentences = []
    skip_patterns = [
        r'^```', r'^python', r'^npm', r'^\$', r'^>', r'^https?://',
        r'^/', r'^\[', r'^\d+\.', r'^[-\*\+#]',  # 过滤 markdown 格式
        r'^(请|建议|注意|提示|警告)',  # 过滤指令性文字
        r'^(作者|编辑|来源)[｜|:：]',  # 过滤残留的作者/编辑标记
    ]
    
    for sent in sentences:
        if any(re.match(p, sent) for p in skip_patterns):
            continue
        # 过滤纯数字或纯符号
        if re.match(r'^[\d\s\W]+$', sent):
            continue
        # 过滤过短的纯人名（如 "Li Yuan"）
        if re.match(r'^[A-Za-z]+(\s[A-Za-z]+)+$', sent) and len(sent) < 30:
            continue
        filtered_sentences.append(sent)
    
    # 关键句识别（优先级排序）
    key_patterns = [
        r'(本文|文章|指出|认为|表示|介绍|分享|讲解|说明|阐述)',
        r'(核心|关键|要点|重点|本质|实质)',
        r'(总结|结论|建议|启示|意义|价值)',
    ]
    
    key_sentences = []
    normal_sentences = []
    
    # 优先使用开头的句子
    for sent in intro_sentences[:8]:
        is_key = any(re.search(pattern, sent) for pattern in key_patterns)
        if is_key:
            key_sentences.append(sent)
        else:
            normal_sentences.append(sent)
    
    # 再从全文中找关键句
    for sent in filtered_sentences[:30]:
        if sent in intro_sentences[:8]:
            continue
        is_key = any(re.search(pattern, sent) for pattern in key_patterns)
        if is_key and len(sent) > 25:
            key_sentences.append(sent)
    
    # 构建摘要
    summary_parts = []
    
    # 优先使用关键句
    if key_sentences:
        summary_parts.extend(key_sentences[:3])
    
    # 补充普通句子直到接近 max_length
    if normal_sentences:
        for sent in normal_sentences[:5]:
            if len(''.join(summary_parts)) + len(sent) < max_length - 5:
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


import time


def upload_to_notebooklm(file_path, title, max_retries=3, retry_delay=3):
    """上传本地 Markdown 文件到 NotebookLM（带自动重试）。

    NotebookLM 对特殊字符文件名兼容性差，上传时自动去除特殊字符保留中文。
    """
    try:
        print(f"   上传到 NotebookLM...")

        # 去除文件名中的特殊字符（保留中文、字母、数字、下划线、连字符、点号）
        import tempfile
        original_path = Path(file_path)
        safe_name = re.sub(r'[^\w\u4e00-\u9fff.\-]', '', original_path.stem) or 'upload'
        tmp_path = Path(tempfile.gettempdir()) / f"{safe_name}.md"
        tmp_path.write_text(original_path.read_text(encoding='utf-8'), encoding='utf-8')

        for attempt in range(1, max_retries + 1):
            result = subprocess.run(
                [NOTEBOOKLM_CMD, 'source', 'add', str(tmp_path), '--title', title, '--notebook', NOTEBOOK_ID],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print(f"   ✅ 上传成功，已添加到「{NOTEBOOK_NAME}」笔记本")
                tmp_path.unlink(missing_ok=True)
                return True

            # 判断是否为可重试错误（服务端偶发抖动通常返回空错误信息）
            stderr = result.stderr.strip() if result.stderr else ''
            stdout = result.stdout.strip() if result.stdout else ''
            error_msg = stderr or stdout or '(空错误)'

            if attempt < max_retries:
                wait = retry_delay * attempt  # 递增等待：3s, 6s
                print(f"   ⚠️ 上传失败 (第{attempt}次): {error_msg}")
                print(f"   ⟳ {wait}秒后重试...")
                time.sleep(wait)
            else:
                print(f"   ⚠️ 上传失败 (已重试{max_retries-1}次): {error_msg}")
                tmp_path.unlink(missing_ok=True)
                return False
    except subprocess.TimeoutExpired:
        print(f"   ⚠️ NotebookLM 上传超时（已重试{max_retries-1}次）")
        tmp_path.unlink(missing_ok=True)
        return False
    except Exception as e:
        print(f"   ⚠️ 上传失败: {e}")
        tmp_path.unlink(missing_ok=True)
        return False


# ============ 飞书多维表格推送 ============

def push_to_feishu(url, title, summary, author="", webhook_url=None):
    """推送文章到飞书多维表格（通过 lark-cli）"""
    import subprocess
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    record_data = {
        "fields": FEISHU_FIELDS,
        "rows": [[title, url, summary, author, now]]
    }
    
    try:
        result = subprocess.run(
            [
                "lark-cli", "base", "+record-batch-create",
                "--base-token", FEISHU_BASE_TOKEN,
                "--table-id", FEISHU_TABLE_ID,
                "--as", "user",
                "--json", json.dumps(record_data, ensure_ascii=False)
            ],
            capture_output=True, text=True, timeout=30
        )
        
        resp = json.loads(result.stdout) if result.stdout else {}
        
        if resp.get("ok") or resp.get("data", {}).get("records"):
            return True, resp
        else:
            error_msg = resp.get("error", {}).get("message", result.stderr or "未知错误")
            return False, {"error": error_msg}
            
    except Exception as e:
        return False, {"error": str(e)}


# ============ IMA 知识库 ============

def add_to_ima_kb(url):
    """添加文章 URL 到 IMA 知识库（支持公众号、X/Twitter、飞书文档等公网可访问的 URL）"""
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
    text = re.sub(r'[\x00-\x1f]+', '', text)
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


def save_raw_markdown(title, markdown_content, output_dir=None):
    """将抓取到的文章 Markdown 存储到指定目录。"""
    if output_dir:
        raw_dir = Path(output_dir).expanduser()
    else:
        raw_dir = Path('~/work/github/media-conent/raw').expanduser()
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
    parser.add_argument('--no-push', action='store_true', help='不推送到飞书，仅输出结果')
    parser.add_argument('--notebook', action='store_true', default=True, help='上传到 NotebookLM（默认开启）')
    parser.add_argument('--no-notebook', action='store_true', help='不上传到 NotebookLM')
    parser.add_argument('--summary-length', type=int, default=200, help='摘要长度（默认200字）')
    parser.add_argument('--summary-engine', choices=['glm', 'rule'], default='glm', help='摘要引擎：glm(默认) | rule')
    parser.add_argument('--output-dir', help='自定义文章存储目录，支持 ~ 写法。默认: ~/work/github/media-conent/raw')
    
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
    summary = generate_summary_with_llm(data['content'], data['title'], args.summary_length, engine=args.summary_engine)
    print(f"✅ 摘要生成完成 ({len(summary)}字)")
    
    # 3. 创建 Markdown 并保存到本地
    print("\n[3/5] 创建并保存 Markdown...")
    markdown_content = create_markdown_content(
        data['title'],
        data.get('author', ''),
        args.url,
        summary,
        data['content']
    )
    raw_path = save_raw_markdown(data['title'], markdown_content, args.output_dir)
    print(f"✅ 已保存到: {raw_path}")
    
    # 4. 上传到 NotebookLM（复用本地文件）
    if args.notebook and not args.no_notebook:
        print("\n[4/5] 上传到 NotebookLM...")
        # setup_success = setup_notebooklm_notebook()
        setup_success = True 
        
        if setup_success:
            upload_success = upload_to_notebooklm(raw_path, raw_path.stem)
            
            if not upload_success:
                print("⚠️ NotebookLM 上传失败，但继续其他操作")
    
    # 5. 推送到飞书多维表格
    if not args.no_push:
        print("\n[5/5] 推送到飞书多维表格...")
        source_name = data.get('source_name', '')
        success, response = push_to_feishu(
            args.url,
            data['title'],
            summary,
            source_name
        )
        
        if success:
            print("✅ 推送成功！")
        else:
            print(f"❌ 推送失败: {response.get('error', '未知错误')}")
            sys.exit(1)
    
    # 6. 添加到 IMA 知识库（排除 X/Twitter，IMA 无法解析其页面）
    if not args.no_push and IMA_KB_ENABLED and not is_twitter_url(args.url):
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
