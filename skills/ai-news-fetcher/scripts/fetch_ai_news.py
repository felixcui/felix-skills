#!/usr/bin/env python3
"""
AI 资讯获取与分类脚本（6分类新版）
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
    """使用阿里云百炼进行智能分类（6分类新版）"""
    
    if not news_list:
        return {}
    
    # 将新闻标题拼接成提示
    titles = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_list)])
    
    prompt = f"""请对以下 {len(news_list)} 条资讯进行智能分类。

【重要原则】
1. 所有资讯都与AI/科技相关，请优先归入前6个分类，尽量减少"其他"分类的使用
2. "其他"仅用于：与AI完全无关的内容、纯招聘信息
3. 当一条资讯可能属于多个分类时，选择最核心、最突出的那个

资讯列表：
{titles}

分类规则（严格使用以下6个分类名称）：

**AI编程与开发** 💻 - 编程工具、软件开发、工程实践
- 包含：Cursor、Claude Code、GitHub Copilot、OpenClaw、IDE插件
- 包含：Vibe Coding、编程技巧、实战教程、代码生成
- 包含：软件工程、研发效能、DevOps、CI/CD、架构设计、代码审查
- 判断标准：开发者工具、编程实践、软件工程改进

**AI模型与技术** 🧠 - 模型发布、技术突破、算法研究
- 包含：GPT、Claude、Kimi、Qwen、Llama、MiniMax等模型发布/更新
- 包含：模型架构、训练技术、算法创新、推理优化、微调量化
- 包含：多模态、Transformer、Benchmark、评测
- 包含：论文、顶会（CVPR、ICLR、AAAI、NeurIPS等）、研究成果
- 判断标准：模型技术本身、论文、算法、架构创新

**AI内容创作** 🎨 - AI生成内容、创意工具、创作应用
- 包含：AI视频生成、AI绘画、AI写作、AI音乐、AI配音
- 包含：短剧生成、图像生成、视频剪辑、内容生产工具
- 包含：创作教程、使用攻略、玩法技巧、案例展示
- 包含：Seedance、Sora、Midjourney、Stable Diffusion等创作工具
- 判断标准：内容创作、生成式AI、创意工具、教程攻略

**AI产品与应用** 🚀 - AI产品发布、平台功能、企业服务
- 包含：产品发布会、功能更新、平台上线、SaaS服务
- 包含：Agent平台、智能体、企业级AI服务、产品集成
- 包含：飞书、钉钉、企业微信等平台的AI功能更新
- 包含：业务落地、实际应用案例、解决方案
- 判断标准：产品发布、平台功能、企业服务、业务应用

**AI行业动态** 📈 - 商业动态、融资投资、市场竞争
- 包含：融资、投资、并购、上市、IPO、估值、财报
- 包含：人事变动（入职、离职、任命）、组织架构调整
- 包含：公司战略、市场竞争、行业政策、监管动态
- 包含：大佬动态（黄仁勋、马斯克、李彦宏等）、创业故事
- 判断标准：商业层面、金额、人事、战略、竞争

**观点与趋势** 💡 - 行业观察、深度分析、未来预测
- 包含：行业观察、趋势分析、深度报道、观点评论
- 包含：对AI发展的思考、未来预测、影响分析
- 包含：技术解读、行业报告、市场分析、专家观点
- 包含：AI对社会/行业/个人的影响讨论
- 判断标准：观点性、分析性、预测性、深度思考

**其他** 📂 - 仅当与AI完全无关时使用
- 仅用于：纯招聘信息、与科技无关的内容

【分类示例】
- "鹅厂员工都Vibe Coding出了什么" → AI编程与开发
- "MiniMax M2.7重磅发布" → AI模型与技术
- "小云雀短剧Agent上线" → AI内容创作（视频/短剧生成）
- "飞书2026春季发布会" → AI产品与应用
- "858亿砸AI，腾讯杀入AI战争" → AI行业动态
- "AI都能自己做视频了，我却更想创作" → 观点与趋势
- "量子位编辑作者招聘" → 其他

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
        # 使用 openclaw 命令行工具调用 AI 模型
        env = os.environ.copy()
        env['OPENCLAW_MODEL'] = 'zai/glm-5'
        
        cmd = [
            "openclaw",
            "agent",
            "--session-id", "ai-news-classifier",
            "--json",
            "--message", prompt
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, env=env)
        
        if result.returncode == 0:
            response_text = result.stdout.decode('utf-8').strip()
            # --json 模式返回 JSON，提取 payloads[0].text
            try:
                outer = json.loads(response_text)
                inner_text = outer["result"]["payloads"][0]["text"]
                response_text = inner_text.strip()
            except (json.JSONDecodeError, KeyError, IndexError):
                pass  # 非 JSON 包装，继续用原始文本
            # 提取第一个完整的 JSON 对象
            start_idx = response_text.find('{')
            if start_idx == -1:
                print(f"AI 分类返回无JSON: {response_text[:200]}")
            else:
                # 用括号匹配找到第一个完整 JSON 对象
                depth = 0
                end_idx = start_idx
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        depth += 1
                    elif response_text[i] == '}':
                        depth -= 1
                        if depth == 0:
                            end_idx = i + 1
                            break
                json_text = response_text[start_idx:end_idx]
                categories = json.loads(json_text)
                # 验证分类结果
                all_indices = set()
                for cat_indices in categories.values():
                    all_indices.update(cat_indices)
                
                if len(all_indices) < len(news_list):
                    missing = [i for i in range(len(news_list)) if i not in all_indices]
                    if "其他" not in categories:
                        categories["其他"] = []
                    categories["其他"].extend(missing)
                
                return categories
        else:
            print(f"AI 分类返回错误码: {result.returncode}")
            if result.stderr:
                print(f"错误信息: {result.stderr.decode('utf-8')[:500]}")
        
    except Exception as e:
        print(f"AI 分类失败: {str(e)}")
    
    # 如果 AI 分类失败，使用关键词分类作为后备
    print("使用关键词分类作为后备方案")
    return classify_by_keywords(news_list)


def classify_by_keywords(news_list):
    """智能关键词分类方案（6分类新版）"""
    classified_indices = set()
    categories = {
        "AI编程与开发": [],
        "AI模型与技术": [],
        "AI内容创作": [],
        "AI产品与应用": [],
        "AI行业动态": [],
        "观点与趋势": [],
        "其他": [],
    }

    # 定义分类规则（按优先级排序）
    rules = [
        # AI编程与开发
        ("AI编程与开发", [
            "Vibe Coding", "Claude Code", "Cursor", "GitHub Copilot",
            "编程助手", "代码生成", "IDE插件", "智能编程", "编程技巧",
            "软件工程", "研发效能", "DevOps", "CI/CD", "代码审查",
            "从没写过代码", "干掉了一个估算团队",
            "AI Coding", "AICoding", "AI编程", "编程工具",
            "Coding", "coding", "Code",
        ]),
        # AI模型与技术
        ("AI模型与技术", [
            "新论文", "论文", "顶会", "CVPR", "ICLR", "AAAI", "NeurIPS", "ICML",
            "模型架构", "算法", "推理优化", "微调", "蒸馏", "量化",
            "多模态", "Transformer", "Benchmark", "评测",
            "性能直逼", "模型发布", "版本更新", "能力提升",
        ]),
        # AI内容创作
        ("AI内容创作", [
            "短剧", "视频生成", "AI视频", "AI绘画", "AI写作",
            "图像生成", "内容创作", "创作工具", "生成式",
            "Seedance", "Sora", "Midjourney", "Stable Diffusion",
            "做AI视频", "AI做视频", "视频制作", "内容生产",
        ]),
        # AI行业动态
        ("AI行业动态", [
            "融资", "投资", "万美元", "亿人民币", "估值", "IPO", "上市",
            "裁员", "入职", "离职", "人事变动", "任命", "辞职",
            "收购", "并购", "加入", "联手", "合作",
            "战争", "杀入", "砸", "亿", "战略", "布局",
            "创业者", "独角兽", "巨头",
        ]),
        # 观点与趋势
        ("观点与趋势", [
            "观点", "趋势", "观察", "思考", "分析",
            "未来", "预测", "影响", "变革", "重塑",
            "我却", "想要", "感想", "随笔",
            "改造", "需要的不止是", "的边界",
        ]),
        # AI产品与应用
        ("AI产品与应用", [
            "发布会", "正式发布", "上线", "推出",
            "开卖", "送到", "正式", "答案", "方案",
            "落地", "实践", "业务", "应用",
            "Agent", "智能体", "SaaS", "平台",
            "体验", "试用", "评测",
        ]),
    ]

    # 非AI内容判断
    non_ai_keywords = [
        "招聘", "诚聘", "招贤", "加入我们", "简历",
        "直播预告", "预告", "倒计时", "敬请期待",
    ]

    for i, news in enumerate(news_list):
        if i in classified_indices:
            continue
            
        title = news["title"]
        classified = False

        # 先检查是否明显非AI内容
        for keyword in non_ai_keywords:
            if keyword in title:
                categories["其他"].append(i)
                classified_indices.add(i)
                classified = True
                break
        
        if classified:
            continue

        # 按优先级检查各分类
        for category, keywords in rules:
            for keyword in keywords:
                if keyword in title:
                    categories[category].append(i)
                    classified_indices.add(i)
                    classified = True
                    break
            if classified:
                break

        # 如果仍未分类，智能判断
        if not classified:
            # 包含模型技术相关 → 模型与技术
            if any(x in title for x in ["模型架构", "算法创新", "Benchmark", "论文", "顶会"]):
                categories["AI模型与技术"].append(i)
                classified_indices.add(i)
            # 包含产品发布相关 → 产品与应用
            elif any(x in title for x in ["发布", "上线", "推出", "实测", "体验"]):
                categories["AI产品与应用"].append(i)
                classified_indices.add(i)
            # 包含内容创作相关 → 内容创作
            elif any(x in title for x in ["视频", "图像", "绘画", "写作", "创作", "生成"]):
                categories["AI内容创作"].append(i)
                classified_indices.add(i)
            # 包含商业动态 → 行业动态
            elif any(x in title for x in ["融资", "投资", "收购", "上市", "亿"]):
                categories["AI行业动态"].append(i)
                classified_indices.add(i)
            # 默认归入AI产品与应用
            else:
                categories["AI产品与应用"].append(i)
                classified_indices.add(i)

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


def get_news_summary(days: int = 1, classify: bool = True, platform: str = "feishu") -> str:
    """获取并分类汇总 AI 资讯"""
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
    print(get_news_summary())
