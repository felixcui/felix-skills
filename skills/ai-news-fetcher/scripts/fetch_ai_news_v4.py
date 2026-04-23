#!/usr/bin/env python3
"""
AI 资讯获取与分类脚本 V5 - 纯关键词分类版
"""
import requests
import json
import os
from datetime import datetime, timedelta

# 需要过滤的标题关键词（直接跳过，不进入分类）
EXCLUDED_TITLE_KEYWORDS = [
    "招聘", "诚聘", "招贤", "加入我们", "简历", "猎头",
]

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


def classify_news(news_list):
    """纯关键词分类（按优先级匹配）"""
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

    # 规则定义：每个元组是 (分类, [(关键词列表, 权重), ...])
    # 权重越高越优先匹配，用于同一条匹配多个分类时决定归属
    # 高优先级规则先定义
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
            # AI编程产品（一句话建站、AI员工等）
            ("一句话", 9), ("AI员工", 9), ("AI 员工", 9),
            ("上线 Web 应用", 9), ("一人公司", 8),
            ("Codex", 8), ("AI Agent产品", 8), ("AI Agent 产品", 8),
            # 开发框架/平台
            ("开发平台", 7), ("Agent框架", 7), ("从零开始设计", 7), ("mini-OpenClaw", 10),
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
                    # 不 break，继续找更高权重的

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


# 缓存目录
_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')


def _get_cache_path(days: int) -> str:
    """获取缓存文件路径（按日期和天数命名，同一天内复用）"""
    date_str = datetime.now().strftime('%Y%m%d')
    return os.path.join(_CACHE_DIR, f'news_cache_{date_str}_d{days}.json')


def _load_cache(cache_path: str):
    """加载缓存，返回 (news_list, categories) 或 None"""
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('news_list') and data.get('categories'):
            print(f"📦 加载分类缓存: {cache_path}")
            return data['news_list'], data['categories']
    except Exception:
        pass
    return None


def _save_cache(cache_path: str, news_list: list, categories: dict):
    """保存分类结果到缓存"""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'news_list': news_list, 'categories': categories}, f, ensure_ascii=False)
        print(f"💾 分类缓存已保存: {cache_path}")
    except Exception as e:
        print(f"⚠️ 缓存保存失败: {e}")


def get_news_summary(days: int = 1, use_cache: bool = True) -> str:
    """获取并分类汇总 AI 资讯（支持缓存复用分类结果）"""
    
    today = datetime.now()
    yesterday = today - timedelta(days=days)
    after = yesterday.strftime("%Y%m%d")
    before = today.strftime("%Y%m%d")

    # 尝试加载缓存
    cache_path = _get_cache_path(days)
    cached = _load_cache(cache_path) if use_cache else None

    if cached:
        news_list, categories = cached
        print(f"📦 使用缓存的分类结果（{len(news_list)} 条资讯）")
    else:
        url = f"{RSS_API_BASE}/api/query?k={RSS_API_KEY}&content=0&before={before}&after={after}"

        try:
            response = requests.get(url, timeout=30, verify=False)
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
                            if len(title) > 200 or title.count('\\n') > 1 or title.count('。') > 3:
                                continue
                            if any(kw in title for kw in EXCLUDED_TITLE_KEYWORDS):
                                continue
                            news_list.append({
                                "title": title,
                                "link": link,
                                "biz_name": biz_name
                            })

            if not news_list:
                return f"""## AI 资讯汇总

> 📅 `{yesterday.strftime('%Y-%m-%d')}` - `{today.strftime('%Y-%m-%d')}`

😊 暂无AI相关资讯，请稍后再来查看～
"""

            print(f"📰 获取到 {len(news_list)} 条资讯，开始分类...")
            
            categories = classify_news(news_list)
            
            _save_cache(cache_path, news_list, categories)
        
        except Exception as e:
            return f"""## ❌ 获取 AI 资讯失败

> 错误信息：`{str(e)}`

请检查网络连接或 API 配置后重试。
"""

    # 统计分类结果
    total_classified = sum(len(v) for v in categories.values())
    print(f"📊 分类统计: 总计 {len(news_list)} 条, 已分类 {total_classified} 条")
    for cat, items in categories.items():
        if items:
            print(f"  - {cat}: {len(items)} 条")
    
    return format_output(news_list, categories, yesterday, today)


def format_output(news_list, categories, start_date, end_date):
    """格式化输出"""
    lines = []
    lines.append("## AI 资讯汇总")
    lines.append("")
    
    ai_news_count = sum(len(indices) for indices in categories.values())
    
    if ai_news_count == 0:
        lines.append("😊 暂无AI相关资讯～")
        lines.append("")
        return "\n".join(lines)
    
    category_order = [
        "AI编程与开发",
        "AI模型与技术",
        "AI内容创作",
        "AI产品与应用",
        "AI行业动态",
        "观点与趋势",
        "其他"
    ]
    
    for category in category_order:
        if category not in categories or not categories[category]:
            continue
            
        indices = categories[category]
        lines.append(f"### {category}（{len(indices)} 条）")
        lines.append("")
        
        for i, idx in enumerate(indices, 1):
            if idx < 0 or idx >= len(news_list):
                continue
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


if __name__ == "__main__":
    print(get_news_summary())
