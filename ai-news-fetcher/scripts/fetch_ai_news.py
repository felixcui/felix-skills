#!/usr/bin/env python3
"""
AI 资讯获取与分类脚本
从微信公众号 RSS 源获取资讯，使用 AI 进行智能分类
"""
import requests
import json
import subprocess
import os
from datetime import datetime, timedelta

# 需要过滤的公众号ID列表
EXCLUDED_BIZ_IDS = {
    "3092970861",
    "3975307385",
    "3870521375",
    "3573172279",
    "3087180557",
    "3271657808",
    "2397888542",
    "2390216734"
}

# RSS API 配置
RSS_API_KEY = os.getenv("AI_NEWS_API_KEY", "5O5H1c1NsT")
RSS_API_BASE = os.getenv("AI_NEWS_API_BASE", "https://wexinrss.zeabur.app")

# 分类图标映射
CATEGORY_ICONS = {
    "AI编程工具及实践": "💻",
    "AI模型与技术": "🧠",
    "AI产品与应用": "🚀",
    "AI行业动态": "📈",
    "其他": "📌",
    "最新资讯": "📰"
}


def classify_news_with_ai(news_list):
    """使用阿里云百炼进行智能分类"""
    
    if not news_list:
        return {}
    
    # 将新闻标题拼接成提示
    titles = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_list)])
    
    prompt = f"""请对以下 {len(news_list)} 条 AI 资讯进行智能分类。

资讯列表：
{titles}

分类规则：
1. 根据标题的核心主题进行分类
2. 分类选项（严格使用以下分类名称）：
   - AI编程工具及实践：AI编程工具（Cursor、Claude Code、GitHub Copilot等）、编程技巧、开发实践、代码生成、IDE插件等
   - AI模型与技术：大模型发布、模型架构、训练技术、算法创新、多模态、推理优化等
   - AI产品与应用：AI应用产品、功能更新、工具发布、Agent、智能体、SaaS产品等
   - AI行业动态：公司融资、投资并购、行业政策、市场趋势、公司财报、人事变动等
   - 其他：不属于以上分类的内容
3. 每条资讯只分到一个最相关的分类
4. 如果某分类没有资讯，则不显示该分类

请以 JSON 格式输出分类结果，格式如下：
{{
  "分类名称": [资讯索引列表],
  ...
}}

例如：
{{
  "AI编程工具及实践": [1, 5],
  "AI模型与技术": [2, 8],
  "AI产品与应用": [3],
  "AI行业动态": [4]
}}

只输出 JSON，不要输出其他内容。"""

    try:
        # 使用 openclaw 命令行工具调用阿里云百炼
        cmd = [
            "openclaw",
            "agent",
            "--message", prompt,
            "--model", "dashscope/qwen-plus"  # 使用阿里云千问 Plus 模型
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        
        if result.returncode == 0:
            # 尝试解析 JSON
            response_text = result.stdout.decode('utf-8').strip()
            # 尝试提取 JSON 部分
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                categories = json.loads(json_text)
                return categories
        
    except Exception as e:
        print(f"AI 分类失败: {str(e)}")
    
    # 如果 AI 分类失败，使用简单关键词分类作为后备
    return classify_by_keywords(news_list)


def classify_by_keywords(news_list):
    """关键词分类后备方案"""
    categories = {
        "AI编程工具及实践": [],
        "AI模型与技术": [],
        "AI产品与应用": [],
        "AI行业动态": [],
        "其他": []
    }

    # AI编程工具及实践关键词
    coding_tool_keywords = ["Cursor", "Claude Code", "Copilot", "IDE", "编程", "代码", "开发", "Vibe Coding",
                            "代码生成", "IDE插件", "编辑器", "调试", "重构", "Git", "GitHub", "GitLab",
                            "OpenClaw", "AI编程", "智能编程", "代码补全", "代码审查", "Code Review",
                            "VSCode", "IntelliJ", "PyCharm", "开发者工具", "CLI", "命令行"]

    # AI模型与技术关键词
    model_tech_keywords = ["模型", "GPT", "Claude", "Llama", "Gemini", "算法", "训练", "推理", "参数",
                           "架构", "Transformer", "大模型", "LLM", "多模态", "MoE", "强化学习", "RL",
                           "微调", "Fine-tuning", "蒸馏", "量化", "部署", "API", "Token", "上下文",
                           "幻觉", "对齐", "安全", "评测", "Benchmark"]

    # AI产品与应用关键词
    product_app_keywords = ["发布", "推出", "上线", "功能", "产品", "应用", "App", "Agent", "智能体",
                            "Bot", "助手", "Assistant", "SaaS", "平台", "服务", "集成", "插件",
                            "扩展", "新功能", "更新", "升级", "版本", "内测", "公测", "Demo"]

    # AI行业动态关键词
    industry_keywords = ["公司", "企业", "融资", "投资", "收购", "上市", "IPO", "财报", "估值",
                         "裁员", "入职", "离职", "人事", "任命", "合作", "战略", "布局",
                         "政策", "法规", "监管", "法案", "禁令", "许可", "合规",
                         "市场", "行业", "赛道", "生态", "趋势", "报告", "预测"]

    for i, news in enumerate(news_list):
        title = news["title"]
        classified = False

        # 优先检查AI编程工具及实践
        for keyword in coding_tool_keywords:
            if keyword in title:
                categories["AI编程工具及实践"].append(i)
                classified = True
                break

        if not classified:
            for keyword in model_tech_keywords:
                if keyword in title:
                    categories["AI模型与技术"].append(i)
                    classified = True
                    break

        if not classified:
            for keyword in product_app_keywords:
                if keyword in title:
                    categories["AI产品与应用"].append(i)
                    classified = True
                    break

        if not classified:
            for keyword in industry_keywords:
                if keyword in title:
                    categories["AI行业动态"].append(i)
                    classified = True
                    break

        if not classified:
            categories["其他"].append(i)

    # 移除空分类
    return {k: v for k, v in categories.items() if v}


def get_news_summary(days: int = 1, classify: bool = True, platform: str = "feishu") -> str:
    """
    获取并分类汇总 AI 资讯
    
    Args:
        days: 获取最近几天的资讯（默认1天，即昨天到今天）
        classify: 是否进行 AI 分类（默认True）
        platform: 目标平台，影响格式（feishu/wechat/discord）
    
    Returns:
        格式化后的资讯汇总字符串（Markdown 格式）
    """

    # 计算日期范围
    today = datetime.now()
    yesterday = today - timedelta(days=days)

    # 格式化日期 YYYYMMDD
    after = yesterday.strftime("%Y%m%d")
    before = today.strftime("%Y%m%d")

    # API URL
    url = f"{RSS_API_BASE}/api/query?k={RSS_API_KEY}&content=0&before={before}&after={after}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 提取 title 和 link，过滤指定公众号
        news_list = []
        excluded_count = 0
        if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
            for item in data['data']:
                if isinstance(item, dict):
                    # 获取公众号ID并检查是否需要过滤
                    biz_id = str(item.get("biz_id", ""))
                    if biz_id in EXCLUDED_BIZ_IDS:
                        excluded_count += 1
                        continue

                    title = item.get("title", "")
                    link = item.get("link", "")
                    if title and link:
                        news_list.append({"title": title, "link": link})

        if not news_list:
            return f"""## 📰 AI 资讯汇总

> 📅 `{yesterday.strftime('%Y-%m-%d')}` 至 `{today.strftime('%Y-%m-%d')}`

😊 暂无新资讯，请稍后再来查看～
"""

        # 分类
        if classify:
            categories = classify_news_with_ai(news_list)
        else:
            # 不进行 AI 分类，全部归入"最新资讯"
            categories = {"最新资讯": list(range(len(news_list)))}

        # 构建汇总消息（优化后的 Markdown 格式）
        return format_news_markdown(news_list, categories, yesterday, today, excluded_count, platform)

    except Exception as e:
        return f"""## ❌ 获取 AI 资讯失败

> 错误信息：`{str(e)}`

请检查网络连接或 API 配置后重试。
"""


def format_news_markdown(news_list, categories, start_date, end_date, excluded_count, platform="feishu"):
    """
    将资讯格式化为美观的 Markdown
    
    Args:
        news_list: 资讯列表
        categories: 分类字典
        start_date: 开始日期
        end_date: 结束日期
        excluded_count: 过滤数量
        platform: 目标平台
    """
    lines = []
    
    # 标题
    lines.append("## 📰 AI 资讯汇总")
    lines.append("")
    
    # 日期和统计信息（使用引用块）
    lines.append(f"> 📅 `{start_date.strftime('%Y-%m-%d')}` - `{end_date.strftime('%Y-%m-%d')}`")
    if excluded_count > 0:
        lines.append(f"> 📊 共 **{len(news_list)}** 条资讯（已过滤 {excluded_count} 条）")
    else:
        lines.append(f"> 📊 共 **{len(news_list)}** 条资讯")
    lines.append("")
    
    # 按顺序输出分类
    category_order = [
        "AI编程工具及实践",
        "AI模型与技术", 
        "AI产品与应用",
        "AI行业动态",
        "其他",
        "最新资讯"
    ]
    
    category_number = 0
    for category in category_order:
        if category not in categories or not categories[category]:
            continue
            
        category_number += 1
        indices = categories[category]
        icon = CATEGORY_ICONS.get(category, "📌")
        
        # 分类标题（使用 ### 层级）
        lines.append(f"### {icon} {category}（{len(indices)} 条）")
        lines.append("")
        
        # 资讯列表（带编号）
        for i, idx in enumerate(indices, 1):
            news = news_list[idx]
            title = news["title"]
            link = news["link"]
            lines.append(f"{i}. [{title}]({link})")
        
        lines.append("")
    
    return "\n".join(lines)


def get_raw_news(days: int = 1) -> list:
    """
    获取原始资讯列表（不含分类）
    
    Args:
        days: 获取最近几天的资讯
    
    Returns:
        资讯列表，每项包含 title 和 link
    """
    today = datetime.now()
    yesterday = today - timedelta(days=days)
    after = yesterday.strftime("%Y%m%d")
    before = today.strftime("%Y%m%d")
    url = f"{RSS_API_BASE}/api/query?k={RSS_API_KEY}&content=0&before={before}&after={after}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        news_list = []
        if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
            for item in data['data']:
                if isinstance(item, dict):
                    biz_id = str(item.get("biz_id", ""))
                    if biz_id in EXCLUDED_BIZ_IDS:
                        continue
                    title = item.get("title", "")
                    link = item.get("link", "")
                    if title and link:
                        news_list.append({"title": title, "link": link})
        return news_list
    except Exception as e:
        print(f"获取资讯失败: {str(e)}")
        return []


if __name__ == "__main__":
    print(get_news_summary())
