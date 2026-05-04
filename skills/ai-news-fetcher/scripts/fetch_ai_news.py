#!/usr/bin/env python3
"""
AI 资讯获取与分类脚本（6分类新版）
从微信公众号 RSS 源获取资讯，使用 AI 进行智能分类
"""
import requests
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from openai import OpenAI

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

# 分类图标映射（6分类新版）
CATEGORY_ICONS = {
    "AI编程与开发": "💻",
    "AI模型与技术": "🧠",
    "AI内容创作": "🎨",
    "AI产品与应用": "🚀",
    "AI行业动态": "📈",
    "观点与趋势": "💡",
    "其他": "📂"
}


def classify_news_with_ai(news_list):
    """使用 OpenAI 兼容 API 进行智能分类（6分类新版）"""
    
    if not news_list:
        return {}
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'your_api_key':
        print("⚠️ OPENAI_API_KEY 未配置，使用关键词分类")
        return classify_by_keywords(news_list)
    
    # 将新闻标题拼接成提示
    titles = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_list)])
    
    prompt = f"""请对以下 {len(news_list)} 条资讯进行智能分类。

【重要原则】
1. 所有资讯都与AI/科技相关，请优先归入前6个分类，尽量减少"其他"分类的使用
2. "其他"仅用于：与AI完全无关的内容、纯招聘信息
3. 当一条资讯可能属于多个分类时，选择最核心、最突出的那个
4. 索引从 1 开始，与上面的序号对应

资讯列表：
{titles}

分类规则（严格使用以下6个分类名称）：

**AI编程与开发** - 编程工具、软件开发、工程实践
- 包含：Cursor、Claude Code、GitHub Copilot、IDE插件
- 包含：Vibe Coding、编程技巧、实战教程、代码生成
- 包含：软件工程、研发效能、DevOps、CI/CD、架构设计、代码审查

**AI模型与技术** - 模型发布、技术突破、算法研究
- 包含：GPT、Claude、Kimi、Qwen、Llama、MiniMax等模型发布/更新
- 包含：模型架构、训练技术、算法创新、推理优化、微调量化
- 包含：多模态、Transformer、Benchmark、评测、论文、顶会

**AI内容创作** - AI生成内容、创意工具、创作应用
- 包含：AI视频生成、AI绘画、AI写作、AI音乐、AI配音
- 包含：Seedance、Sora、Midjourney、Stable Diffusion等创作工具

**AI产品与应用** - AI产品发布、平台功能、企业服务
- 包含：产品发布会、功能更新、平台上线、SaaS服务
- 包含：Agent平台、智能体、企业级AI服务、业务落地

**AI行业动态** - 商业动态、融资投资、市场竞争
- 包含：融资、投资、并购、上市、IPO、估值、财报
- 包含：人事变动、公司战略、市场竞争、行业政策

**观点与趋势** - 行业观察、深度分析、未来预测
- 包含：行业观察、趋势分析、深度报道、观点评论
- 包含：对AI发展的思考、未来预测、影响分析

**其他** - 仅当与AI完全无关时使用

请以 JSON 格式输出分类结果，格式如下：
{{
  "AI编程与开发": [索引列表],
  "AI模型与技术": [索引列表],
  "AI内容创作": [索引列表],
  "AI产品与应用": [索引列表],
  "AI行业动态": [索引列表],
  "观点与趋势": [索引列表],
  "其他": [索引列表]
}}

只输出 JSON，不要输出其他内容。"""

    try:
        print(f"🤖 使用 {OPENAI_MODEL} 进行 AI 分类...")
        
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
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
        "AI编程与开发": [],
        "AI模型与技术": [],
        "AI内容创作": [],
        "AI产品与应用": [],
        "AI行业动态": [],
        "观点与趋势": [],
        "其他": [],
    }

    # 非AI内容关键词
    non_ai_keywords = [
        "招聘", "诚聘", "招贤", "加入我们", "简历",
        "直播预告", "预告", "倒计时", "敬请期待",
    ]

    # 加权规则定义：每个元组是 (分类, [(关键词, 权重), ...])
    # 权重越高越优先匹配，用于同一条匹配多个分类时决定归属
    rules = [
        # === 第一层：强信号，几乎不会误判 ===
        ("AI模型与技术", [
            # 顶会/论文
            ("CVPR", 10), ("ICLR", 10), ("NeurIPS", 10), ("AAAI", 10), ("ICML", 10), ("顶会", 10),
            # 技术指标
            ("SOTA", 9), ("Benchmark", 9), ("技术报告", 9), ("综述", 9),
            # VLA/具身技术
            ("VLA", 8), ("具身", 7),
            # 算法/模型研究
            ("微调", 7), ("蒸馏", 7), ("量化", 7), ("推理优化", 7), ("多模态", 7), ("Transformer", 7),
            ("模型架构", 7), ("算法", 6), ("数据集", 7),
            # 模型发布/评测
            ("性能直逼", 8), ("模型发布", 8), ("版本更新", 8),
            ("高分神话", 7), ("最强模型", 7),
        ]),
        ("AI编程与开发", [
            # 编程工具（精确匹配）
            ("Claude Code", 10), ("GitHub Copilot", 10), ("Vibe Coding", 10), ("Vibe Design", 10),
            ("Cursor", 9), ("MCP", 9), ("CLI", 9), ("Copilot", 9),
            # 编程相关
            ("代码生成", 8), ("IDE插件", 8), ("智能编程", 8), ("编程助手", 8),
            ("编码代理", 8), ("AI编码", 8), ("编程代理", 8), ("编码工具", 8),
            ("软件工程", 8), ("工程规范", 8), ("工程实践", 8), ("研发效能", 8),
            ("DevOps", 8), ("CI/CD", 8), ("代码审查", 8),
            ("架构设计", 7), ("Harness", 7), ("开源项目", 7),
            # AI编程产品
            ("一句话", 9), ("AI员工", 9), ("AI 员工", 9),
            ("上线 Web 应用", 9), ("一人公司", 8),
            ("Codex", 8), ("AI Agent产品", 8), ("AI Agent 产品", 8),
            # 开发框架/平台
            ("开发平台", 7), ("Agent框架", 7), ("从零开始设计", 7),
            ("前端盘点", 7),
        ]),
        ("AI内容创作", [
            # AI视频工具（精确匹配）
            ("Seedance", 10), ("Sora", 9), ("Midjourney", 9), ("Stable Diffusion", 9),
            ("Vidu", 9), ("LibTV", 10),
            # 创作类型
            ("短剧", 8), ("漫剧", 8), ("3D模型", 8), ("视频生成", 8),
            ("AI视频", 8), ("AI绘画", 8), ("AI写作", 8), ("图像生成", 8),
            ("内容创作", 7), ("创作工具", 7), ("生成式", 7),
            ("做AI视频", 9), ("AI做视频", 9), ("视频制作", 7), ("内容生产", 7),
            # AI视频进化
            ("AI视频的进化速度", 9), ("AI视频进化", 9),
        ]),
        ("AI行业动态", [
            # 融资/收购
            ("收购", 8), ("并购", 8), ("亿美元", 8), ("亿人民币", 8), ("轮融资", 8), ("估值", 7),
            ("IPO", 8), ("上市", 7), ("裁员", 8), ("跳槽", 8), ("入职", 7), ("离职", 7),
            # 快讯/速递
            ("速递", 9), ("早知道", 9), ("快讯", 9),
            # 事件新闻
            ("遇袭", 9), ("怒火", 8), ("反AI", 8),
            # 市场数据
            ("数据 202", 8), ("GenAI网页产品数据", 9),
            # 活动
            ("黑客松", 7), ("创造营", 7), ("晚餐", 6),
            # 行业人物/公司动作
            ("创业者", 7), ("独角兽", 7),
        ]),
        ("AI产品与应用", [
            # 测评/体验
            ("实测", 9), ("一手实测", 10), ("保姆级", 9),
            ("教程", 8), ("知识库", 7), ("自动化", 6),
            ("Prompt", 7),
            # 产品发布
            ("正式发布", 8), ("开卖", 8),
            ("机器人", 7), ("AI眼镜", 9), ("智能眼镜", 9),
            # 产品体验/对比
            ("体验", 6),
            # 产品更新汇总
            ("所有更新一次性看懂", 9), ("一次性看懂", 9),
            # 产品工作流/方案
            ("工作流", 6),
        ]),
        ("观点与趋势", [
            # 明确的观点信号
            ("思考", 7), ("再思考", 9), ("重新认识", 8), ("观察", 6),
            ("趋势", 7), ("预测", 7), ("影响", 6), ("变革", 7), ("重塑", 7),
            ("暗线", 9), ("后背发凉", 9), ("神仙打架", 8),
            ("改造", 6), ("需要的不止是", 7), ("的边界", 6),
            ("感想", 7), ("随笔", 7),
            # 行业观察/现象
            ("孵化器", 7), ("洗脑", 7), ("废纸", 6),
            # 观点文章常见模式
            ("我低估了", 8), ("我看到了", 7),
            ("为什么模型永远无法", 8), ("的真相", 7),
            ("深度解析", 6), ("深度研究", 7),
            ("深度思考", 7),
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
            if any(x in title for x in ["编码", "编程", "代码", "开源", "开发框架"]):
                categories["AI编程与开发"].append(i)
            elif any(x in title for x in ["视频", "图像", "绘画", "写作", "创作", "生成"]):
                categories["AI内容创作"].append(i)
            elif any(x in title for x in ["发布", "上线", "推出", "体验"]):
                categories["AI产品与应用"].append(i)
            elif any(x in title for x in ["模型", "算法", "大模型", "AI"]):
                categories["AI模型与技术"].append(i)
            elif any(x in title for x in ["融资", "投资", "收购", "上市", "巨头"]):
                categories["AI行业动态"].append(i)
            elif any(x in title for x in ["Agent", "智能体"]):
                categories["AI产品与应用"].append(i)
            else:
                categories["观点与趋势"].append(i)
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
        "AI编程与开发",
        "AI模型与技术",
        "AI内容创作",
        "AI产品与应用",
        "AI行业动态",
        "观点与趋势",
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
