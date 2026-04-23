#!/usr/bin/env python3
"""
AI 资讯获取与分类脚本（优化版）
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
    """使用阿里云百炼进行智能分类（深度优化版）"""
    
    if not news_list:
        return {}
    
    # 将新闻标题拼接成提示
    titles = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_list)])
    
    prompt = f"""请对以下 {len(news_list)} 条资讯进行智能分类。

【重要原则】
1. 所有资讯都与AI/科技相关，请优先归入前4个分类，尽量减少"其他"分类的使用
2. "其他"仅用于：与AI完全无关的内容、招聘信息、纯广告、或个人日常分享
3. 当一条资讯可能属于多个分类时，选择最核心、最突出的那个

资讯列表：
{titles}

分类规则（严格使用以下分类名称）：

**AI编程** - 编程工具、开发实践、软件工程
- 包含：Cursor、Claude Code、GitHub Copilot、OpenClaw、IDE插件、代码生成、编程助手
- 包含：Vibe Coding、编程技巧、实战教程、代码审查、开发者工具
- 包含：软件工程、研发效能、DevOps、CI/CD、架构设计、测试部署
- 判断标准：标题包含编程工具名称、开发实践、代码相关、软件工程改进

**AI模型与技术** - 模型发布、技术突破、算法研究
- 包含：GPT、Claude、Kimi、Qwen、Llama、MiniMax等模型发布/更新/评测
- 包含：模型架构、训练技术、算法创新、推理优化、微调量化、多模态
- 包含：论文、顶会（CVPR、ICLR、AAAI、NeurIPS等）、研究成果、技术突破
- 包含：性能提升、Benchmark、模型能力对比
- 判断标准：标题包含模型名称+发布/更新/论文/架构/算法/性能等词

**AI产品与应用** - AI产品、工具应用、场景落地
- 包含：AI产品发布、功能更新、工具上线、SaaS服务、平台功能
- 包含：Agent、智能体、AI应用、场景解决方案、产品集成
- 包含：具体AI工具的使用案例、落地实践、业务应用
- 包含：视频生成、图像生成、内容创作工具、生产力工具
- 判断标准：标题强调产品、工具、应用、Agent、功能上线、使用案例

**AI行业动态及观察** - 商业动态、行业趋势、市场分析
- 包含：融资、投资、并购、上市、IPO、估值、财报
- 包含：人事变动（入职、离职、任命）、组织架构调整
- 包含：公司战略、市场竞争、行业政策、监管动态
- 包含：行业观察、趋势分析、市场报告、观点评论
- 包含：大型发布会、重大合作、生态布局
- 判断标准：标题包含金额、公司战略、人事、行业趋势、竞争格局

**其他** - 仅当与AI完全无关时使用
- 仅用于：纯招聘信息、与科技无关的内容、个人生活分享
- 不要用"其他"来逃避分类决策

【分类示例】
- "MiniMax M2.7重磅发布" → AI模型与技术（模型发布）
- "把MiniMax M2.7扔进真实业务" → AI产品与应用（业务落地）
- "858亿砸AI，腾讯杀入AI战争" → AI行业动态及观察（投资/战略）
- "英伟达桌面超算开卖" → AI行业动态及观察（产品发布+商业动态）
- "CVPR2026 | Streamo实时交互助手" → AI模型与技术（顶会论文）
- "钉钉彻底CLI化" → AI产品与应用（产品功能更新）
- "量子位编辑作者招聘" → 其他（纯招聘）

请以 JSON 格式输出分类结果，格式如下：
{{
  "AI编程": [索引列表],
  "AI模型与技术": [索引列表],
  "AI产品与应用": [索引列表],
  "AI行业动态及观察": [索引列表],
  "其他": [索引列表]
}}

只输出 JSON，不要输出其他内容。"""

    try:
        # 使用 openclaw 命令行工具调用 AI 模型
        # 通过环境变量设置模型
        env = os.environ.copy()
        env['OPENCLAW_MODEL'] = 'bailian/glm-5'
        
        cmd = [
            "openclaw",
            "agent",
            "--message", prompt
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, env=env)
        
        if result.returncode == 0:
            # 尝试解析 JSON
            response_text = result.stdout.decode('utf-8').strip()
            # 尝试提取 JSON 部分
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                categories = json.loads(json_text)
                # 验证分类结果，确保所有索引都被分类
                all_indices = set()
                for cat_indices in categories.values():
                    all_indices.update(cat_indices)
                
                # 如果有未分类的条目，归入"其他"
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
    
    # 如果 AI 分类失败，使用简单关键词分类作为后备
    print("使用关键词分类作为后备方案")
    return classify_by_keywords(news_list)


def classify_by_keywords(news_list):
    """智能关键词分类方案（优化版V2）"""
    # 使用集合来跟踪已分类的索引，避免重复
    classified_indices = set()
    categories = {
        "AI编程": [],
        "AI模型与技术": [],
        "AI产品与应用": [],
        "AI行业动态及观察": [],
        "其他": [],
    }

    # 定义分类规则（按优先级排序）
    rules = [
        # AI编程 - 高优先级关键词
        ("AI编程", [
            "Vibe Coding", "Claude Code", "Cursor", "GitHub Copilot",
            "编程助手", "代码生成", "IDE插件", "智能编程", "编程技巧",
            "软件工程", "研发效能", "DevOps", "CI/CD", "代码审查",
            "从没写过代码", "干掉了一个估算团队",  # 特定表达
        ]),
        # AI模型与技术 - 模型发布、论文、技术突破
        ("AI模型与技术", [
            "新论文", "论文", "顶会", "CVPR", "ICLR", "AAAI", "NeurIPS", "ICML",
            "模型架构", "算法", "推理优化", "微调", "蒸馏", "量化",
            "多模态", "Transformer", "Benchmark", "评测",
            "性能直逼", "模型发布", "版本更新", "能力提升",
        ]),
        # AI行业动态 - 融资、人事、战略
        ("AI行业动态及观察", [
            "融资", "投资", "万美元", "亿人民币", "估值", "IPO", "上市",
            "裁员", "入职", "离职", "人事变动", "任命", "辞职",
            "收购", "并购", "加入", "联手", "合作",
            "战争", "杀入", "砸", "亿", "战略", "布局",
            "创业者", "独角兽", "巨头", "行业趋势",
        ]),
        # AI产品与应用 - 产品发布、功能更新、落地应用
        ("AI产品与应用", [
            "发布会", "正式发布", "上线", "推出",
            "开卖", "送到", "正式", "答案", "方案",
            "落地", "实践", "业务", "应用",
            "Agent", "智能体", "SaaS", "平台",
            "实测", "体验", "试用", "评测",
        ]),
    ]

    # 非AI内容判断（用于"其他"分类）
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

        # 如果仍未分类，根据内容智能判断
        if not classified:
            # 包含模型名+技术相关 → 模型与技术
            if any(x in title for x in ["模型架构", "算法创新", "Benchmark", "论文", "顶会"]):
                categories["AI模型与技术"].append(i)
                classified_indices.add(i)
            # 包含产品发布相关 → 产品与应用
            elif any(x in title for x in ["发布", "上线", "推出", "实测", "体验"]):
                categories["AI产品与应用"].append(i)
                classified_indices.add(i)
            # 包含商业动态 → 行业动态
            elif any(x in title for x in ["融资", "投资", "收购", "上市", "亿"]):
                categories["AI行业动态及观察"].append(i)
                classified_indices.add(i)
            # 默认归入AI产品与应用（而非其他）
            else:
                categories["AI产品与应用"].append(i)
                classified_indices.add(i)

    # 返回所有分类
    return categories


def get_news_summary(days: int = 1, classify: bool = True, platform: str = "feishu") -> str:
    """
    获取并分类汇总 AI 资讯（仅保留AI相关）
    
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

        # 提取 title、link 和公众号名称，过滤指定公众号
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
                    biz_name = item.get("biz_name", "")  # 获取公众号名称
                    
                    # 过滤异常标题：标题过长（超过200字符）或包含多个换行
                    if title and link:
                        # 检查标题是否包含多个换行（可能是正文内容误放入标题字段）
                        if len(title) > 200 or title.count('\n') > 1 or title.count('。') > 3:
                            # 跳过这条异常资讯
                            continue
                        news_list.append({"title": title, "link": link, "biz_name": biz_name})

        if not news_list:
            return f"""## 📰 AI 资讯汇总

> 📅 `{yesterday.strftime('%Y-%m-%d')}` - `{today.strftime('%Y-%m-%d')}`

😊 暂无AI相关资讯，请稍后再来查看～
"""

        # 分类
        if classify:
            categories = classify_news_with_ai(news_list)
        else:
            # 不进行 AI 分类，全部归入"最新资讯"
            categories = {"AI相关": list(range(len(news_list)))}

        # 构建汇总消息（优化后的 Markdown 格式）
        return format_news_markdown(news_list, categories, yesterday, today, platform)

    except Exception as e:
        return f"""## ❌ 获取 AI 资讯失败

> 错误信息：`{str(e)}`

请检查网络连接或 API 配置后重试。
"""


def format_news_markdown(news_list, categories, start_date, end_date, platform="feishu"):
    """
    将资讯格式化为美观的 Markdown
    
    Args:
        news_list: 资讯列表
        categories: 分类字典
        start_date: 开始日期
        end_date: 结束日期
        platform: 目标平台
    """
    lines = []
    
    # 标题
    lines.append("## AI 资讯汇总")
    lines.append("")
    
    # 计算AI相关资讯数量
    ai_news_count = sum(len(indices) for indices in categories.values())
    
    if ai_news_count == 0:
        lines.append("😊 暂无AI相关资讯～")
        lines.append("")
        return "\n".join(lines)
    
    # 按顺序输出分类
    category_order = [
        "AI编程",
        "AI模型与技术", 
        "AI产品与应用",
        "AI行业动态及观察",
        "其他"
    ]
    
    category_number = 0
    for category in category_order:
        if category not in categories or not categories[category]:
            continue
            
        category_number += 1
        indices = categories[category]
        
        # 分类标题（使用 ### 层级，不带 emoji）
        lines.append(f"### {category}（{len(indices)} 条）")
        lines.append("")
        
        # 资讯列表（带编号和公众号名称）
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
                    # 获取公众号ID并检查是否需要过滤
                    biz_id = str(item.get("biz_id", ""))
                    if biz_id in EXCLUDED_BIZ_IDS:
                        continue
                    
                    title = item.get("title", "")
                    link = item.get("link", "")
                    biz_name = item.get("biz_name", "")  # 获取公众号名称
                    
                    # 过滤异常标题：标题过长（超过200字符）或包含多个换行
                    if title and link:
                        if len(title) > 200 or title.count('\n') > 1 or title.count('。') > 3:
                            continue
                        news_list.append({"title": title, "link": link, "biz_name": biz_name})
        return news_list
    except Exception as e:
        print(f"获取资讯失败: {str(e)}")
        return []

if __name__ == "__main__":
    print(get_news_summary())
