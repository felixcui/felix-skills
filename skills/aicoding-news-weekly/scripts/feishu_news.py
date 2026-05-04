import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Optional
from collections import defaultdict

# 自动加载 skill 目录下的 .env 文件
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 未安装时，依赖系统环境变量

# Feishu Configuration
FEISHU_CONFIG = {
    "APP_ID": os.getenv("FEISHU_APP_ID"),
    "APP_SECRET": os.getenv("FEISHU_APP_SECRET"),
    "NEWS": {
        "APP_TOKEN": "Tn1vbRQyraNFvAstbqicUlIJnue",
        "TABLE_ID": "tblXp6DHjQPomXbv",
        "VIEW_ID": "vewbl6mgMC",
        "FIELDS": ["title", "link", "category", "description", "updatetime"]
    },
    "API": {
        "BASE_URL": "https://open.feishu.cn/open-apis",
        "AUTH_TOKEN": "/auth/v3/tenant_access_token/internal",
        "BITABLE": "/bitable/v1"
    }
}

class FeishuConfigError(Exception):
    """飞书凭证配置错误"""
    pass

def check_feishu_config():
    """检查飞书凭证是否已配置"""
    if not FEISHU_CONFIG["APP_ID"] or not FEISHU_CONFIG["APP_SECRET"]:
        skill_dir = Path(__file__).parent.parent
        env_path = skill_dir / ".env"
        raise FeishuConfigError(f"""❌ 飞书 API 凭证未配置！

请提供以下凭证：
  • FEISHU_APP_ID: 飞书应用的 App ID
  • FEISHU_APP_SECRET: 飞书应用的 App Secret

凭证将保存到: {env_path}

请回复凭证信息，格式如下：
  APP_ID=cli_xxxxxxxxxxxx
  APP_SECRET=xxxxxxxxxxxxxxxx""")

def get_tenant_access_token() -> str:
    """获取飞书访问令牌"""
    check_feishu_config()  # 检查凭证配置
    url = f"{FEISHU_CONFIG['API']['BASE_URL']}{FEISHU_CONFIG['API']['AUTH_TOKEN']}"
    payload = {
        "app_id": FEISHU_CONFIG["APP_ID"],
        "app_secret": FEISHU_CONFIG["APP_SECRET"]
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["tenant_access_token"]

def build_bitable_url(app_token: str, table_id: str) -> str:
    """构建飞书列表记录 API URL"""
    return f"{FEISHU_CONFIG['API']['BASE_URL']}{FEISHU_CONFIG['API']['BITABLE']}/apps/{app_token}/tables/{table_id}/records"

def build_bitable_search_url(app_token: str, table_id: str) -> str:
    """构建飞书查询记录（search）API URL，支持服务端 filter"""
    return f"{FEISHU_CONFIG['API']['BASE_URL']}{FEISHU_CONFIG['API']['BITABLE']}/apps/{app_token}/tables/{table_id}/records/search"

def get_field_text(fields: List[Dict]) -> str:
    """将飞书字段数组转换为纯文本"""
    if not isinstance(fields, list):
        return ""
    return " ".join(field.get("text", "") for field in fields).replace("\n", " ").strip()

def extract_url(field) -> str:
    """从飞书字段中提取链接"""
    # 处理列表类型（包含多行文本或富文本片段）
    if isinstance(field, list):
        if not field:
            return ""
        for item in field:
            if isinstance(item, dict):
                # 优先查找 link 字段
                if "link" in item:
                    return item["link"]
                # 其次检查 text 字段是否包含 URL
                if "text" in item and (item["text"].startswith("http://") or item["text"].startswith("https://")):
                    return item["text"]
        return ""

    if isinstance(field, dict) and "link" in field:
        return field["link"]
    if isinstance(field, str) and (field.startswith("http://") or field.startswith("https://")):
        return field
    return ""

def format_date(date_str: str) -> str:
    """格式化日期"""
    try:
        # 如果是时间戳（毫秒）
        if str(date_str).isdigit():
            timestamp = int(date_str) / 1000  # 转换为秒
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        # 如果是日期字符串
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return date.strftime("%Y-%m-%d")
    except:
        return date_str

def get_news_list(start_date: str = None, end_date: str = None, debug: bool = False, exclude_other: bool = True) -> Dict:
    """获取资讯列表
    Args:
        start_date: 开始日期 (YYYY-MM-DD)，默认为7天前
        end_date: 结束日期 (YYYY-MM-DD)，默认为今天
        debug: 是否输出调试信息
        exclude_other: 是否过滤掉分类为"其他"的资讯，默认为 True
    """
    try:
        # 确定日期范围
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # 获取访问令牌
        token = get_tenant_access_token()
        
        # 构建查询 API URL（POST /records/search，支持服务端 filter）
        url = build_bitable_search_url(
            FEISHU_CONFIG["NEWS"]["APP_TOKEN"],
            FEISHU_CONFIG["NEWS"]["TABLE_ID"]
        )
        
        # 发送请求
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 分页获取所有数据
        all_items = []
        page_token = None
        page_count = 0
        seen_record_ids = set()  # 用于检测重复记录
        max_pages = 20  # 最大页数限制，防止无限循环
        
        while page_count < max_pages:
            # 使用 POST /records/search 接口，支持服务端 filter
            # 注意：使用 filter 时 view_id 会被忽略，改用 sort 维持倒序排列
            body = {
                "page_size": 500,
                "sort": [
                    {
                        "field_name": "updatetime",
                        "desc": True
                    }
                ]
            }

            # 服务端过滤：排除分类为"其他"的资讯
            if exclude_other:
                body["filter"] = {
                    "conjunction": "and",
                    "conditions": [
                        {
                            "field_name": "category",
                            "operator": "isNot",
                            "value": ["其他"]
                        }
                    ]
                }
            
            if debug:
                print(f"[DEBUG] exclude_other={exclude_other}, filter={'已启用' if exclude_other else '已禁用'}", file=__import__('sys').stderr)

            if page_token:
                body["page_token"] = page_token

            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            feishu_data = response.json()
            
            if feishu_data["code"] != 0:
                raise Exception(f"Feishu API Error: {feishu_data['msg']}")
            
            page_count += 1
            current_items = feishu_data["data"].get("items", [])
            
            # 检测重复记录
            new_items = []
            duplicate_count = 0
            for item in current_items:
                record_id = item.get("record_id", "")
                if record_id and record_id not in seen_record_ids:
                    seen_record_ids.add(record_id)
                    new_items.append(item)
                else:
                    duplicate_count += 1
            
            all_items.extend(new_items)
            
            if debug:
                has_more = feishu_data["data"].get("has_more", False)
                next_token = feishu_data["data"].get("page_token", "None")
                total = feishu_data["data"].get("total", "N/A")
                print(f"[DEBUG] 第 {page_count} 页获取了 {len(current_items)} 条记录 (新增: {len(new_items)}, 重复: {duplicate_count}) | total={total} | has_more={has_more} | page_token={next_token[:20] if next_token else 'None'}...", file=__import__('sys').stderr)
            
            # 如果这页全是重复数据，可能出现了问题，立即停止
            if duplicate_count > 0 and len(new_items) == 0:
                if debug:
                    print(f"[DEBUG] 检测到全部重复数据，停止分页", file=__import__('sys').stderr)
                break
            
            # 早期终止：如果最后一条记录的日期早于 start_date，可以停止分页
            if new_items:
                last_item_time = new_items[-1].get("fields", {}).get("updatetime", "")
                last_item_date = format_date(last_item_time)
                if last_item_date and last_item_date < start_date:
                    if debug:
                        print(f"[DEBUG] 最后一条记录日期 {last_item_date} 早于开始日期 {start_date}，停止分页", file=__import__('sys').stderr)
                    break
            
            # 检查是否还有更多数据
            if not feishu_data["data"].get("has_more", False):
                break
            
            new_page_token = feishu_data["data"].get("page_token")
            # 防止 page_token 没有变化导致无限循环
            if not new_page_token or new_page_token == page_token:
                if debug:
                    print(f"[DEBUG] page_token 未变化或为空，停止分页", file=__import__('sys').stderr)
                break
            page_token = new_page_token
        
        if page_count >= max_pages:
            if debug:
                print(f"[DEBUG] 达到最大页数限制 {max_pages}，停止分页", file=__import__('sys').stderr)
        
        if debug:
            print(f"[DEBUG] 总共获取了 {len(all_items)} 条原始记录 (共 {page_count} 页)", file=__import__('sys').stderr)
            
        # 诊断信息：获取数据库中最新的日期，帮助排查数据源问题
        latest_db_date = "N/A"
        if all_items:
            # API 默认按时间倒序返回，第一条就是最新的
            raw_time = all_items[0].get("fields", {}).get("updatetime")
            latest_db_date = format_date(raw_time)
        
        # 处理数据
        news_items = []
        
        # 统计跳过原因
        skip_stats = {
            "no_updatetime": 0,
            "out_of_date_range": 0,
            "no_title_or_link": 0
        }
        
        for item in all_items:
            fields = item.get("fields", {})
            
            # 安全地获取 updatetime 并检查范围
            update_time = fields.get("updatetime", "")
            formatted_date = format_date(update_time)
          
            if not update_time:
                skip_stats["no_updatetime"] += 1
                continue
                
            if not (start_date <= formatted_date <= end_date):
                skip_stats["out_of_date_range"] += 1
                continue
            
            # 安全地获取 title
            title = None
            title_field = fields.get("title", [])
            if isinstance(title_field, list) and title_field:
                title = title_field[0].get("text", "")
            elif title_field:
                title = str(title_field)
            
            # 安全地获取 link
            link = extract_url(fields.get("link", ""))
            
            # 如果没有标题或链接，跳过该条目
            if not (title and link):
                skip_stats["no_title_or_link"] += 1
                if debug:
                    print(f"[DEBUG] 跳过记录 - 标题: {title}, 链接: {link}", file=__import__('sys').stderr)
                continue
                
            # 安全地获取 description
            description = None
            desc_field = fields.get("description", [])
            if isinstance(desc_field, list):
                description = get_field_text(desc_field)
            elif desc_field:
                description = str(desc_field)
            
            # 安全地获取 category
            category = "未分类"
            category_field = fields.get("category", [])
            if isinstance(category_field, list) and category_field:
                 # 假设category是单选标签，或者文本
                 # 如果是文本字段
                category = get_field_text(category_field)
                # 如果是单选/多选字段，可能结构不同，通常是 options/value
                # 尝试直接取text，如果不行可能要调整
                if not category and isinstance(category_field[0], str): #Simple string
                     category = category_field[0]
            elif isinstance(category_field, str):
                category = category_field

            
            news_items.append({
                "id": item.get("record_id", ""),
                "title": title,
                "url": link,
                "updateTime": format_date(update_time),
                "description": description,
                "category": category if category else "未分类"
            })
        
        if debug:
            print(f"[DEBUG] 跳过统计: {skip_stats}", file=__import__('sys').stderr)
            print(f"[DEBUG] 最终返回 {len(news_items)} 条记录", file=__import__('sys').stderr)
        
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "items": news_items,
                "total": len(all_items),  # 使用实际获取的总数
                "filtered_count": len(news_items),  # 过滤后的数量
                "skip_stats": skip_stats,  # 跳过统计
                "has_more": False,  # 分页后已全部获取
                "latest_db_date": latest_db_date,
                "date_range": (start_date, end_date)
            }
        }
        
    except FeishuConfigError as e:
        # 凭证配置错误，直接向 stderr 输出并返回错误
        print(str(e), file=sys.stderr)
        return {
            "code": 500,
            "msg": str(e),
            "data": {
                "items": [],
                "total": 0,
                "has_more": False
            }
        }
    except Exception as e:
        print(f"Error fetching news: {str(e)}", file=sys.stderr)
        return {
            "code": 500,
            "msg": str(e),
            "data": {
                "items": [],
                "total": 0,
                "has_more": False
            }
        }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch Feishu news and output markdown.')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--include-other', action='store_true', help='包含分类为"其他"的资讯（默认过滤掉）')
    args = parser.parse_args()

    # 获取并打印资讯列表
    result = get_news_list(
        start_date=args.start,
        end_date=args.end,
        debug=args.debug,
        exclude_other=not args.include_other
    )
    
    if result["code"] == 0:
        items = result["data"]["items"]
        start_date, end_date = result["data"].get("date_range", ("unknown", "unknown"))
        
        if not items:
            print(f"【提示】在 {start_date} 至 {end_date} 期间没有发现新的资讯。")
            print(f"数据库中最新的一条记录日期为: {result['data'].get('latest_db_date')}")
        else:
            # Group by category
            grouped_items = defaultdict(list)
            for item in items:
                grouped_items[item['category']].append(item)

      

            # Define preferred order of categories
            preferred_order = ["编程实践", "工具动态", "行业观点"]
            
            # Get all categories
            all_categories = list(grouped_items.keys())
            
            # Sort categories: preferred ones first, then others alphabetically
            sorted_categories = sorted(all_categories, key=lambda x: (
                preferred_order.index(x) if x in preferred_order else 999, x
            ))

            for idx, category in enumerate(sorted_categories):
                print(f"## {category}\n")
                
                for item in grouped_items[category]:
                    title = item['title']
                    url = item['url']
                    description = item.get('description', '') or ''
                    
                    print(f"### [{title}]({url})\n")
                    if description:
                        print(f"{description}\n")
                    else:
                        print("\n")
                
                # Add separator if it's not the last category
                #if idx < len(sorted_categories) - 1:
                #    print("---\n")

            print('---')
            print('![](https://files.mdnice.com/user/121853/1b369e9c-c1fa-490b-a10e-a9eb803177cf.png)')
            print('- [AICoding 基地: ai-coding-base.vercel.app (工具动态，编程实践，编程模型，业界观点)')
            print('- 专为开发者打造的一站式 AI 编程情报站。这里汇聚了最前沿的 AI 编程工具、编程资讯和模型动态及深度实战案例等，旨在帮助每一位开发者跨越技术周期，掌握 AI开发核心生产力，提升开发效率。')
            
            # 输出标题，格式: AI Coding资讯周报-2026.02.07
            formatted_end_date = end_date.replace('-', '.')
            #print(f"AI Coding资讯周报-{formatted_end_date}\n")
    else:
        print(f"Error: {result['msg']}", file=sys.stderr)
        sys.exit(1)
