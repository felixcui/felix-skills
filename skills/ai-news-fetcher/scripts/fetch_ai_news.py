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

# ========== 分类模型配置（降级链：GLM → deepseek → 关键词规则） ==========
# GLM（第一优先，从 skill 根目录 .env 读取）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4').strip()
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'glm-5-turbo')

# deepseek（第二优先：优先 skill 根目录 .env，回退 ~/.hermes/.env）
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').strip()
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')

# 从 ~/.hermes/.env 回退读取 deepseek 配置（不覆盖已从 skill .env 读到的值）
if not DEEPSEEK_API_KEY:
    _hermes_env = Path.home() / ".hermes" / ".env"
    if _hermes_env.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_hermes_env)
            DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
            DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').strip()
            DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')
        except ImportError:
            pass

# 需要过滤的公众号ID列表
EXCLUDED_BIZ_IDS = {
    "2390137096",
    "2390216734",
    "2390327125",
    "2391160948",
    "2391870715",
    "2391982425",
    "2392812511",
    "2393189071",
    "2394909541",
    "2395857064",
    "2396036352",
    "2397888542",
    "2399984412",
    "3000059561",
    "3003017875",
    "3017678939",
    "3070173033",
    "3070785833",
    "3074214840",
    "3079062760",
    "3081016363",
    "3083900716",
    "3084683924",
    "3086319450",
    "3087180557",
    "3088211406",
    "3088691707",
    "3089417812",
    "3089520911",
    "3090069028",
    "3091835464",
    "3092970861",
    "3095879089",
    "3096962707",
    "3098205029",
    "3098315652",
    "3098724720",
    "3198421828",
    "3200012133",
    "3201047396",
    "3202328088",
    "3204376591",
    "3211013606",
    "3211050196",
    "3219353713",
    "3222508206",
    "3223159877",
    "3223465257",
    "3224156812",
    "3227018184",
    "3237111815",
    "3241038037",
    "3252512160",
    "3254265986",
    "3264468330",
    "3271657808",
    "3273408132",
    "3289623139",
    "3296313468",
    "3516808955",
    "3523027248",
    "3539572217",
    "3550942265",
    "3571585559",
    "3573172279",
    "3595068712",
    "3870521375",
    "3900244815",
    "3907835675",
    "3914343645",
    "3924631366",
    "3931971375",
    "3942315633",
    "3975307385",
}

# devmaster.cn API 配置（AI 资讯入库）
DEVELMASTER_API_URL = os.getenv("DEVELMASTER_API_URL", "https://devmaster.cn/api/ai-news/ingest")
DEVELMASTER_API_KEY = os.getenv("DEVELMASTER_API_KEY", "")

# RSS API 配置
RSS_API_KEY = os.getenv("AI_NEWS_API_KEY", "5O5H1c1NsT")
RSS_API_BASE = os.getenv("AI_NEWS_API_BASE", "https://wexinrss.zeabur.app")
# 修复末尾斜杠导致 404 的问题
RSS_API_BASE = RSS_API_BASE.rstrip('/')

# 分类图标映射（10分类新版）
CATEGORY_ICONS = {
    "AI 算力": "⚡",
    "模型技术": "🧠",
    "Agent基建": "🏗️",
    "AI软件工程": "💻",
    "内容创作": "🎨",
    "个人生产力": "📊",
    "行业应用": "🏭",
    "智能终端": "📱",
    "其他AI相关": "📈",
    "其他": "📂"
}


def _classify_with_llm(news_list, api_key, base_url, model, provider_label):
    """使用指定 LLM（OpenAI 兼容 API）进行智能分类（10分类新版）
    
    成功返回 categories dict，失败返回 None（由调用方负责降级）。
    """
    
    # 将新闻标题拼接成提示
    titles = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_list)])
    
    prompt = f"""请对以下 {len(news_list)} 条资讯进行智能分类。

【重要原则】
1. 所有资讯都与AI/科技相关，请优先归入前9个分类，未匹配的归入"其他"
2. "其他"用于：跨分类综合话题等未完全落入上述分类的AI相关内容
3. 当一条资讯可能属于多个分类时，选择最核心、最突出的那个
5. 融资/投资/并购类文章，应先看其技术主题归入对应分类（如融资做AI编程→AI软件工程），而非一律归入"其他AI相关"
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

**Agent基建** - Agent系统的底层框架与协议
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
  "Agent基建": [索引列表],
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
        print(f"🤖 使用 {model} 进行 AI 分类...")
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=httpx.Timeout(60.0, connect=15.0),
        )
        
        response = client.chat.completions.create(
            model=model,
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
        
        print(f"✅ {provider_label} 分类完成")
        return categories
        
    except Exception as e:
        print(f"❌ {provider_label} 分类失败: {str(e)}")
        return None


def classify_news_with_ai(news_list):
    """三级降级分类：GLM → deepseek → 关键词规则（10分类新版）"""
    
    if not news_list:
        return {}
    
    # 第一优先：GLM
    if OPENAI_API_KEY and OPENAI_API_KEY != 'your_api_key':
        categories = _classify_with_llm(news_list, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, "GLM")
        if categories is not None:
            return categories
        print("⚠️ GLM 分类失败，尝试 deepseek...")
    else:
        print("⚠️ GLM 未配置（OPENAI_API_KEY），尝试 deepseek...")
    
    # 第二优先：deepseek
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != 'your_api_key':
        categories = _classify_with_llm(news_list, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, "deepseek")
        if categories is not None:
            return categories
        print("⚠️ deepseek 分类失败，使用关键词分类...")
    else:
        print("⚠️ DEEPSEEK_API_KEY 未配置，跳过 deepseek")
    
    # 兜底：关键词规则分类
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
        "Agent基建": [],
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
        # === Agent基建 ===
        ("Agent基建", [
            ("MCP", 10), ("技能", 8), ("Hook", 9), ("记忆", 7), ("沙箱", 8),
            ("多智能体", 9), ("工作流", 7), ("协议", 7),
            ("AIP", 9), ("Tool Use", 9), ("Function Calling", 9),
            ("Agent框架", 9), ("驾驭层", 10), ("Harness", 9), ("护栏", 9),
            ("Agent三件套", 10), ("安全治理", 8), ("智能体安全", 8),
            ("技能市场", 8),
            ("Sif", 9), ("电商Agent", 8), ("业务监控", 8), ("Skill", 8),
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
            ("AI Native", 9), ("研发范式", 8), ("核心系统", 7),
            ("AI基础设施", 9), ("研发全链路", 9), ("结果即服务", 8),
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
                categories["Agent基建"].append(i)
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


def push_to_develmaster(news_list, categories):
    """将分类后的资讯批量推送到 devmaster.cn API
    
    Args:
        news_list: 资讯列表 [{"title", "link", "biz_name"}, ...]
        categories: 分类结果 {"分类名": [索引列表], ...}
    
    Returns:
        bool: 是否推送成功
    """
    if not DEVELMASTER_API_KEY:
        print("⚠️ DEVELMASTER_API_KEY 未配置，跳过推送")
        return False
    
    if not news_list:
        print("⚠️ 无资讯可推送")
        return False
    
    today = datetime.now().strftime("%Y-%m-%d")
    items = []
    seen_indices = set()
    
    # 按分类顺序遍历，跳过"其他"分类
    category_order = [
        "AI 算力", "模型技术", "Agent基建", "AI软件工程",
        "内容创作", "个人生产力", "行业应用", "智能终端", "其他AI相关",
    ]
    
    for category in category_order:
        if category not in categories:
            continue
        api_category = category  # 直接使用原始分类名（API 接受带空格的格式）
        for idx in categories[category]:
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            news = news_list[idx]
            items.append({
                "title": news["title"],
                "url": news["link"],
                "source": news.get("biz_name", ""),
                "category": api_category,
            })
    
    if not items:
        print("⚠️ 无有效资讯可推送")
        return False
    
    payload = {
        "publishedDate": today,
        "items": items,
    }
    
    try:
        print(f"📤 推送 {len(items)} 条资讯到 devmaster.cn...")
        resp = requests.post(
            DEVELMASTER_API_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEVELMASTER_API_KEY}",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        print(f"✅ devmaster.cn 推送成功: {json.dumps(result, ensure_ascii=False)[:200]}")
        return True
    except Exception as e:
        print(f"❌ devmaster.cn 推送失败: {str(e)}")
        return False


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
        "Agent基建",
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


def get_news_summary(days: int = 1, classify: bool = True, platform: str = "feishu", method: str = "ai", push_db: bool = True, date: str = None) -> str:
    """获取并分类汇总 AI 资讯
    
    Args:
        days: 获取几天内的资讯
        classify: 是否进行分类
        platform: 输出平台类型
        method: 分类方法，'ai' (AI分类+规则兜底) 或 'rule' (仅规则分类)
        push_db: 是否推送到 devmaster.cn 数据库（默认 True）
        date: 指定具体日期（YYYY-MM-DD），仅获取该天的资讯
    """
    today = datetime.now()
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        yesterday = target_date
        today = target_date + timedelta(days=1)
    else:
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
        
        # 推送到 devmaster.cn 数据库
        if push_db:
            push_to_develmaster(news_list, categories)
        
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
