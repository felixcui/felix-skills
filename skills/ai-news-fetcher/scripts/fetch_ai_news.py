#!/usr/bin/env python3
"""
AI 资讯获取与分类脚本（10分类新版）
从微信公众号 RSS 源获取资讯，使用 AI 进行智能分类
"""
import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from openai import OpenAI
import httpx

# ========== 加载环境变量 ==========
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
ENV_FILE = SKILL_ROOT / ".env"

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
except ImportError:
    pass

# ========== OpenAI API 配置 ==========
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'qwen-plus')

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

# 分类图标映射（10分类新版）
CATEGORY_ICONS = {
    "AI 算力": "⚡",
    "模型技术": "🧠",
    "Agent基础设施": "🏗️",
    "AI软件工程": "💻",
    "内容创作": "🎨",
    "个人生产力": "📊",
    "行业应用": "🏭",
    "智能终端": "📱",
    "其他AI相关": "📈",
    "其他": "📂"
}


def classify_news_with_ai(news_list):
    """使用 OpenAI 兼容 API 进行智能分类（10分类新版）"""
    
    if not news_list:
        return {}
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'your_api_key':
        print("⚠️ OPENAI_API_KEY 未配置，使用关键词分类")
        return classify_by_keywords(news_list)
    
    # 将新闻标题拼接成提示
    titles = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_list)])
    
    prompt = f"""请对以下 {len(news_list)} 条资讯进行智能分类。

【重要原则】
1. 所有资讯都与AI/科技相关，请优先归入前9个分类，未匹配的归入"其他"
2. "其他"用于：跨分类综合话题等未完全落入上述分类的AI相关内容
3. 当一条资讯可能属于多个分类时，选择最核心、最突出的那个
4. 索引从 1 开始，与上面的序号对应

资讯列表：
{titles}

分类规则（严格使用以下 10 个分类名称）：

**AI 算力** - 芯片、算力基础设施、训练与推理成本
- 包含：GPU、TPU、NPU等芯片、服务器、数据中心、算力租赁
- 包含：集成电路、半导体、训练成本、推理成本、算力优化
- 包含：华为昇腾、英伟达、AMD、英特尔等算力硬件

**模型技术** - 模型本身的技术进展
- 包含：新模型发布、模型架构、多模态、推理方法、训练方法
- 包含：数据集、评测、Benchmark、开源模型、技术路线
- 包含：GPT、Claude、Kimi、Qwen、Llama、DeepSeek等模型

**Agent基础设施** - Agent系统的底层框架与协议
- 包含：MCP、技能(Skill)、Hook、记忆、沙箱、安全机制
- 包含：多智能体协作、工作流编排、Agent框架、协议标准
- 包含：AIP协议、Tool Use、Function Calling底层设计

**AI软件工程** - AI在软件开发中的应用
- 包含：Coding Agent、IDE插件、代码生成、代码审查
- 包含：开发流程、测试、运维、前端与工程化
- 包含：Cursor、Claude Code、Copilot、Vibe Coding

**内容创作** - AI生成的多媒体内容
- 包含：图像生成、视频生成、音频生成、设计工具
- 包含：短剧、漫剧、游戏创作、营销内容制作
- 包含：Sora、Midjourney、Stable Diffusion、Seedance等工具

**个人生产力** - AI提升个人效率的工具
- 包含：知识库、办公自动化、学习辅助、智能搜索
- 包含：信息处理、PPT生成、个人自动化、消费级AI助手
- 包含：Notion AI、ChatGPT日常使用、AI写作助手

**行业应用** - AI在垂直行业的落地
- 包含：科学研究、金融、医疗、教育、政务
- 包含：制造、零售、文化传媒、法律等垂直场景

**智能终端** - 集成AI的硬件设备
- 包含：AI手机、AI眼镜、AI耳机、可穿戴设备
- 包含：机器人、智能汽车、智能家居设备
- 包含：Apple Intelligence、AI PC、具身智能

**其他AI相关** - AI行业的商业动态、战略与分析
- 包含：公司动态、融资并购、投资、上市
- 包含：产品战略、市场分析、行业观点、趋势预测
- 包含：深度分析、人物访谈、行业报告

**其他** - 与AI相关但未完全落入上述分类的内容，或跨分类综合话题

请以 JSON 格式输出分类结果，格式如下：
{{
  "AI 算力": [索引列表],
  "模型技术": [索引列表],
  "Agent基础设施": [索引列表],
  "AI软件工程": [索引列表],
  "内容创作": [索引列表],
  "个人生产力": [索引列表],
  "行业应用": [索引列表],
  "智能终端": [索引列表],
  "其他AI相关": [索引列表],
  "其他": [索引列表]
}}

只输出 JSON，不要输出其他内容。"""

    try:
        print(f"🤖 使用 {OPENAI_MODEL} 进行 AI 分类...")
        
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=httpx.Timeout(300.0, connect=15.0),
        )
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "你是一个专业的 AI 资讯分类助手，擅长将科技资讯准确归类。只输出 JSON，不要输出其他内容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # 提取 JSON（兼容 markdown 代码块包裹的情况）
        if response_text.startswith('```'):
            # 去掉 ```json ... ``` 包裹
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1])
        
        categories = json.loads(response_text)
        
        # 索引转换：API 返回的索引从 1 开始，内部使用从 0 开始
        converted = {}
        for cat, indices in categories.items():
            converted[cat] = [idx - 1 for idx in indices if isinstance(idx, int)]
        categories = converted
        
        # 验证分类结果：将遗漏的资讯归入"其他"
        all_indices = set()
        for cat_indices in categories.values():
            all_indices.update(cat_indices)
        
        if len(all_indices) < len(news_list):
            missing = [i for i in range(len(news_list)) if i not in all_indices]
            if "其他" not in categories:
                categories["其他"] = []
            categories["其他"].extend(missing)
        
        print(f"✅ AI 分类完成")
        return categories
        
    except Exception as e:
        print(f"❌ AI 分类失败: {str(e)}")
    
    # 如果 AI 分类失败，使用关键词分类作为后备
    print("⚠️ 使用关键词分类作为后备方案")
    return classify_by_keywords(news_list)


def classify_by_keywords(news_list):
    """加权关键词分类（按优先级匹配）"""
    if not news_list:
        return {}

    print(f"🏷️  关键词规则分类 {len(news_list)} 条资讯...")

    classified = set()
    categories = {
        "AI 算力": [],
        "模型技术": [],
        "Agent基础设施": [],
        "AI软件工程": [],
        "内容创作": [],
        "个人生产力": [],
        "行业应用": [],
        "智能终端": [],
        "其他AI相关": [],
        "其他": [],
    }

    # 非AI内容关键词（仅过滤明显与AI无关的内容）
    non_ai_keywords = [
        "招聘", "诚聘", "招贤", "简历", "招人",
        "内推", "社招", "校招", "猎头",
    ]

    # 加权规则定义：每个元组是 (分类, [(关键词, 权重), ...])
    # 权重越高越优先匹配，用于同一条匹配多个分类时决定归属
    rules = [
        # === AI 算力 ===
        ("AI 算力", [
            ("芯片", 10), ("GPU", 10), ("TPU", 10), ("NPU", 10),
            ("数据中心", 9), ("算力", 9), ("服务器", 8), ("集成电路", 9), ("半导体", 9),
            ("训练成本", 8), ("推理成本", 8), ("算力租赁", 9),
            ("昇腾", 10), ("英伟达", 8), ("NVIDIA", 8),
            ("H100", 9), ("H200", 9), ("B200", 9),
            ("推理芯片", 9), ("专用芯片", 8), ("存算", 8), ("液冷", 7), ("智算中心", 9),
            ("银河算廊", 10),
        ]),
        # === 模型技术 ===
        ("模型技术", [
            # 顶会/论文
            ("CVPR", 10), ("ICLR", 10), ("NeurIPS", 10), ("AAAI", 10), ("ICML", 10), ("顶会", 10),
            # 技术指标
            ("SOTA", 9), ("Benchmark", 9), ("技术报告", 9), ("综述", 9),
            # 模型技术关键词
            ("VLA", 8), ("具身", 7),
            ("微调", 7), ("蒸馏", 7), ("量化", 7), ("推理优化", 7), ("多模态", 7), ("Transformer", 7),
            ("模型架构", 7), ("算法", 6), ("数据集", 8),
            ("性能直逼", 8), ("模型发布", 8), ("版本更新", 8),
            ("最强模型", 7), ("新模型", 7),
            ("开源模型", 8), ("开源发布", 9),
            ("训练方法", 8), ("评测", 8), ("MoE", 8), ("长上下文", 7),
            ("RLHF", 8), ("GRPO", 8), ("DPO", 8), ("世界模型", 8),
            ("技术路线", 7), ("持续学习", 7),
        ]),
        # === Agent基础设施 ===
        ("Agent基础设施", [
            ("MCP", 10), ("技能", 8), ("Hook", 9), ("记忆", 7), ("沙箱", 8),
            ("多智能体", 9), ("工作流", 7), ("协议", 7),
            ("AIP", 9), ("Tool Use", 9), ("Function Calling", 9),
            ("Agent框架", 9), ("驾驭层", 10), ("Harness", 9), ("护栏", 9),
            ("Agent三件套", 10), ("安全治理", 8), ("智能体安全", 8),
            ("技能市场", 8),
        ]),
        # === AI软件工程 ===
        ("AI软件工程", [
            ("Claude Code", 10), ("GitHub Copilot", 10), ("Cursor", 10),
            ("Vibe Coding", 10), ("Vibe Design", 10), ("Codex", 10),
            ("代码生成", 9), ("IDE", 9), ("编程", 8),
            ("代码审查", 8), ("Code Review", 8),
            ("测试", 7), ("运维", 7), ("DevOps", 8), ("CI/CD", 8),
            ("前端", 7), ("工程化", 8), ("研发效能", 8),
            ("开源项目", 7), ("CLI", 8),
            ("一人公司", 8), ("AI员工", 9), ("AI 员工", 9),
            ("编程助手", 8), ("编码代理", 8), ("软件工程", 8),
        ]),
        # === 内容创作 ===
        ("内容创作", [
            ("Seedance", 10), ("Sora", 9), ("Midjourney", 9), ("Stable Diffusion", 9),
            ("Vidu", 9), ("LibTV", 10),
            ("短剧", 9), ("漫剧", 9), ("游戏创作", 8), ("营销内容", 7),
            ("设计工具", 8), ("AI配音", 9), ("AI音乐", 9), ("3D模型", 8),
            ("视频生成", 8), ("AI视频", 8), ("AI绘画", 8), ("AI写作", 8),
            ("图像生成", 8), ("内容创作", 8), ("内容生产", 8),
            ("做AI视频", 9), ("AI做视频", 9), ("视频制作", 7),
            ("创作工具", 7), ("生成式", 7),
            ("AI视频的进化速度", 9),
        ]),
        # === 个人生产力 ===
        ("个人生产力", [
            ("知识库", 9), ("办公", 7), ("学习", 6), ("搜索", 7),
            ("信息处理", 7), ("PPT", 9), ("个人自动化", 8), ("消费级", 7),
            ("效率工具", 8), ("笔记", 7), ("Notion AI", 10),
            ("办公自动化", 8), ("自动剪辑", 8),
            ("ChatCut", 10), ("WPS", 8), ("灵犀", 8), ("WorkBuddy", 10),
        ]),
        # === 行业应用 ===
        ("行业应用", [
            ("医疗AI", 9), ("金融AI", 9), ("教育AI", 9), ("政务AI", 9),
            ("科学智能", 9), ("AI for Science", 10),
            ("制造", 7), ("零售", 7), ("文化传媒", 7), ("法律AI", 8),
            ("农业", 7), ("制药", 8), ("药物发现", 9), ("精准医疗", 8),
            ("智慧城市", 8), ("智慧教育", 8),
        ]),
        # === 智能终端 ===
        ("智能终端", [
            ("AI手机", 10), ("AI眼镜", 10), ("智能眼镜", 10), ("AI耳机", 10),
            ("可穿戴", 8), ("机器人", 8),
            ("智能汽车", 9), ("自动驾驶", 9), ("智能家居", 8),
            ("Apple Intelligence", 10), ("AI PC", 9),
            ("AI Pin", 9), ("Rabbit", 9),
            ("端侧", 8), ("边缘计算", 7), ("具身智能", 8),
            ("人形机器人", 9), ("智能终端", 9),
        ]),
    ]

    for i, news in enumerate(news_list):
        if i in classified:
            continue

        title = news["title"]
        matched = False

        # 检查非AI内容
        for kw in non_ai_keywords:
            if kw in title:
                categories["其他"].append(i)
                classified.add(i)
                matched = True
                break
        if matched:
            continue

        # 用加权规则匹配：收集所有匹配，取权重最高的分类
        best_cat = None
        best_weight = 0

        for cat, keyword_list in rules:
            for kw, weight in keyword_list:
                if kw in title:
                    if weight > best_weight:
                        best_weight = weight
                        best_cat = cat

        if best_cat:
            categories[best_cat].append(i)
            classified.add(i)
            matched = True

        if not matched:
            # 兜底启发式
            if any(x in title for x in ["编码", "编程", "代码", "开源", "开发框架", "软件工程"]):
                categories["AI软件工程"].append(i)
            elif any(x in title for x in ["视频", "图像", "绘画", "写作", "创作", "生成", "短剧", "漫剧"]):
                categories["内容创作"].append(i)
            elif any(x in title for x in ["知识库", "办公", "笔记", "PPT", "搜索"]):
                categories["个人生产力"].append(i)
            elif any(x in title for x in ["芯片", "GPU", "算力", "服务器", "数据中心"]):
                categories["AI 算力"].append(i)
            elif any(x in title for x in ["模型", "算法", "大模型", "AI", "评测", "论文"]):
                categories["模型技术"].append(i)
            elif any(x in title for x in ["Agent", "智能体", "MCP", "记忆", "安全治理"]):
                categories["Agent基础设施"].append(i)
            elif any(x in title for x in ["融资", "投资", "收购", "上市"]):
                categories["其他AI相关"].append(i)
            elif any(x in title for x in ["手机", "眼镜", "耳机", "终端", "机器人", "汽车"]):
                categories["智能终端"].append(i)
            elif any(x in title for x in ["教育", "医疗", "金融", "政务", "制造", "科学", "法律"]):
                categories["行业应用"].append(i)
            elif any(x in title for x in ["融资", "投资", "收购", "上市", "观点", "趋势", "思考", "预测", "深度", "访谈", "战略", "动态", "发布", "发布会"]):
                categories["其他AI相关"].append(i)
            else:
                categories["其他"].append(i)
            classified.add(i)

    return categories


def get_raw_news(days: int = 1) -> list:
    """获取原始资讯列表"""
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
                    biz_name = item.get("biz_name", "")
                    
                    if title and link:
                        if len(title) > 200 or title.count('\n') > 1 or title.count('。') > 3:
                            continue
                        news_list.append({"title": title, "link": link, "biz_name": biz_name})
        return news_list
    except Exception as e:
        print(f"获取资讯失败: {str(e)}")
        return []


def format_news_markdown(news_list, categories, start_date, end_date, platform="feishu"):
    """将资讯格式化为 Markdown"""
    lines = []
    
    lines.append("## AI 资讯日报")
    lines.append("")
    
    ai_news_count = sum(len(indices) for indices in categories.values() if indices)
    
    if ai_news_count == 0:
        lines.append("😊 暂无AI相关资讯～")
        lines.append("")
        return "\n".join(lines)
    
    # 按顺序输出分类
    category_order = [
        "AI 算力",
        "模型技术",
        "Agent基础设施",
        "AI软件工程",
        "内容创作",
        "个人生产力",
        "行业应用",
        "智能终端",
        "其他AI相关",
    ]
    
    for category in category_order:
        if category not in categories or not categories[category]:
            continue
            
        indices = categories[category]
        icon = CATEGORY_ICONS.get(category, "")
        
        lines.append(f"### {icon} {category}（{len(indices)} 条）")
        lines.append("")
        
        for i, idx in enumerate(indices, 1):
            news = news_list[idx]
            title = news["title"]
            link = news["link"]
            biz_name = news.get("biz_name", "")
            if biz_name:
                lines.append(f"{i}. [{title}]({link}) `{biz_name}`")
            else:
                lines.append(f"{i}. [{title}]({link})")
        
        lines.append("")
    
    # 生成被过滤资讯的列表
    filtered = []
    if "其他" in categories and categories["其他"]:
        for idx in categories["其他"]:
            news = news_list[idx]
            filtered.append(f"• {news['title']}")
    
    return "\n".join(lines), filtered


def get_news_summary(days: int = 1, classify: bool = True, platform: str = "feishu", method: str = "ai") -> str:
    """获取并分类汇总 AI 资讯
    
    Args:
        days: 获取几天内的资讯
        classify: 是否进行分类
        platform: 输出平台类型
        method: 分类方法，'ai' (AI分类+规则兜底) 或 'rule' (仅规则分类)
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
                    biz_name = item.get("biz_name", "")
                    
                    if title and link:
                        if len(title) > 200 or title.count('\n') > 1 or title.count('。') > 3:
                            continue
                        news_list.append({"title": title, "link": link, "biz_name": biz_name})

        if not news_list:
            return f"""## 📰 AI 资讯日报

> 📅 `{yesterday.strftime('%Y-%m-%d')}` - `{today.strftime('%Y-%m-%d')}`

😊 暂无AI相关资讯，请稍后再来查看～
"""

        if classify:
            if method == "rule":
                categories = classify_by_keywords(news_list)
            else:
                categories = classify_news_with_ai(news_list)
        else:
            categories = {"AI相关": list(range(len(news_list)))}

        result, filtered = format_news_markdown(news_list, categories, yesterday, today, platform)
        
        # 输出过滤的资讯到 stderr，方便 cron agent 通知用户
        if filtered:
            import sys
            print(f"\n🚫 以下 {len(filtered)} 条资讯已被过滤（非AI相关）：", file=sys.stderr)
            for item in filtered:
                print(f"  {item}", file=sys.stderr)
        
        return result

    except Exception as e:
        return f"""## ❌ 获取 AI 资讯日报失败

> 错误信息：`{str(e)}`

请检查网络连接或 API 配置后重试。
"""


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="获取并分类 AI 资讯")
    parser.add_argument("--days", type=int, default=1, help="获取过去几天的资讯，默认为 1")
    parser.add_argument("--method", type=str, choices=["ai", "rule"], default="ai",
                        help="分类方法: ai (AI分类+规则兜底), rule (仅规则分类)")
    
    args = parser.parse_args()
    
    classify = args.method != "none"
    print(get_news_summary(days=args.days, classify=classify, method=args.method))
