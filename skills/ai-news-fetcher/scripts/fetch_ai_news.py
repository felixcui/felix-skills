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

# ========== 分类模型配置（降级链：Hermes 主模型 → deepseek → 关键词规则） ==========
# 主模型（第一优先，从 skill 根目录 .env 读取）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1').strip()
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'deepseek-v4.1-flash')

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
    "3079567434", # 国网河南电力
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
    "3226161088", # 光大环境
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
    "3940248869", # 中信城开华南
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

# ========== 分类体系（唯一事实来源） ==========
# 顺序即日报展示顺序；「其他」为兜底桶，不参与内容分类（仅接收非 AI 或未覆盖条目）。
# 下方所有 category_order / CATEGORY_ICONS 均由此派生，避免多处硬编码导致漂移。
CATEGORY_ORDER = [
    "AI 算力",
    "模型技术",
    "Agent基建",
    "AI软件工程",
    "内容创作",
    "个人生产力",
    "行业应用",
    "智能终端",
    "其他AI相关",
    "其他",
]
FALLBACK_CATEGORY = "其他"
# 参与内容展示的分类（不含兜底桶）
CONTENT_CATEGORIES = [c for c in CATEGORY_ORDER if c != FALLBACK_CATEGORY]

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

_CATEGORY_RANK = {name: i for i, name in enumerate(CATEGORY_ORDER)}


def _normalize_categories(raw_categories, news_count):
    """把 LLM 返回的分类结果规整为安全、可渲染的结构。

    解决的问题（原先全部静默失效）：
    1. 索引必须是 1..news_count 的整数：过滤 0-based 返回、负数、越界值、
       bool（isinstance(True, int) 为 True 会穿过原校验）。
    2. 完整性校验不再依赖「集合大小 == 条数」——越界值和重复值都会凑数骗过它。
       改为逐条断言覆盖且唯一。
    3. 跨类重复按 CATEGORY_ORDER 优先级去重，保证下游每个出口只看到一条。
    4. 模型自创的分类名归入兜底桶并告警，不再静默整类丢失。

    返回 (categories, stats)；categories 的索引已转为 0-based。
    """
    stats = {"越界索引": 0, "非法索引": 0, "未知分类": 0, "跨类重复": 0, "补漏": 0}
    cleaned = {name: [] for name in CATEGORY_ORDER}
    owner = {}  # 0-based 索引 -> 当前归属分类，用于跨类重复时按优先级仲裁
    seen = set(owner.keys())

    for cat, indices in (raw_categories or {}).items():
        # 模型可能自创分类名，统一归入兜底桶而非整类丢弃
        if cat not in _CATEGORY_RANK:
            stats["未知分类"] += 1
            target = FALLBACK_CATEGORY
        else:
            target = cat

        if not isinstance(indices, list):
            stats["非法索引"] += len(indices) if isinstance(indices, (list, tuple, set)) else 1
            continue

        for idx in indices:
            # bool 是 int 的子类，必须显式排除
            if isinstance(idx, bool) or not isinstance(idx, int):
                stats["非法索引"] += 1
                continue
            # 契约是 1-based；先校验再去程，避免 0-based 返回产生 -1 回绕到列表末尾
            zero_based = idx - 1
            if zero_based < 0 or zero_based >= news_count:
                stats["越界索引"] += 1
                continue
            if zero_based in seen:
                # 同一条被分到多个分类：按 CATEGORY_ORDER 取更靠前者，与展示顺序一致
                stats["跨类重复"] += 1
                if _CATEGORY_RANK[target] < _CATEGORY_RANK[owner[zero_based]]:
                    cleaned[owner[zero_based]].remove(zero_based)
                    cleaned[target].append(zero_based)
                    owner[zero_based] = target
                continue
            seen.add(zero_based)
            cleaned[target].append(zero_based)
            owner[zero_based] = target

    # 逐条补漏：任何未被覆盖的下标都进兜底桶
    missing = [i for i in range(news_count) if i not in seen]
    if missing:
        cleaned[FALLBACK_CATEGORY].extend(missing)
        stats["补漏"] = len(missing)

    return cleaned, stats


def _describe_category_stats(stats):
    """把规整统计拼成一行告警，仅在有异常时输出。"""
    parts = [f"{k}{v}" for k, v in stats.items() if v]
    return "｜".join(parts) if parts else ""


def _classify_with_llm(news_list, api_key, base_url, model, provider_label):
    """使用指定 LLM（OpenAI 兼容 API）进行智能分类（10分类新版）
    
    成功返回 categories dict，失败返回 None（由调用方负责降级）。
    """
    
    # 将新闻标题拼接成提示
    titles = "\n".join([f"{i+1}. {item['title']}" for i, item in enumerate(news_list)])
    
    prompt = f"""请对以下 {len(news_list)} 条资讯进行智能分类。

【重要原则】
1. 先判断该资讯是否与 AI 实质性相关：若只是招聘、活动、招商、榜单、征稿、评选等非 AI 主题，归入"其他"；若确为 AI 相关，再归入最贴切的一个分类
2. "其他"用于：与 AI 无关的内容，或无法判断是否与 AI 相关的内容
3. 当一条资讯可能属于多个分类时，选择最核心、最突出的那个，且每条资讯只能归入一个分类
4. 融资/投资/并购类文章，应先看其技术主题归入对应分类（如融资做AI编程→AI软件工程），而非一律归入"其他AI相关"
5. 索引从 1 开始，与上面的序号对应；必须为 1 到 {len(news_list)} 的整数，不得重复

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

**其他** - 与 AI 无关的内容（招聘、活动、招商、榜单、征稿、评选等），或无法判断是否与 AI 相关的内容

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

    system_prompt = "你是一个专业的 AI 资讯分类助手，擅长将科技资讯准确归类。只输出 JSON，不要输出其他内容。"
    request_kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    try:
        print(f"🤖 使用 {model} 进行 AI 分类...")

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=httpx.Timeout(60.0, connect=15.0),
            )
        except Exception as e:
            # 配置类错误：API Key 缺失/非法、base_url 不合法等，无需重试
            print(f"❌ {provider_label} 客户端初始化失败（检查 API Key / BASE_URL）: {type(e).__name__}: {str(e)[:120]}")
            return None

        try:
            response = client.chat.completions.create(
                # 推理模型默认会输出思考内容，分类只需要 JSON，关闭思考
                extra_body={"enable_thinking": False},
                **request_kwargs,
            )
        except Exception as e:
            # 端点不支持 enable_thinking 时回退重试
            print(f"ℹ️ {provider_label} 不支持 enable_thinking，回退重试: {type(e).__name__}: {str(e)[:80]}")
            try:
                response = client.chat.completions.create(**request_kwargs)
            except Exception as e2:
                print(f"❌ {provider_label} 接口调用失败: {type(e2).__name__}: {str(e2)[:120]}")
                return None

        response_text = (response.choices[0].message.content or "").strip()

        # 提取 JSON（兼容 markdown 代码块包裹的情况）
        if response_text.startswith('```'):
            # 去掉 ```json ... ``` 包裹。用 find 定位真正的闭合围栏，
            # 避免「只有开头围栏」时按行盲切得到空串。
            body = response_text.split('\n', 1)[1] if '\n' in response_text else ''
            fence = body.rfind('```')
            response_text = (body[:fence] if fence != -1 else body).strip()

        if not response_text:
            print(f"❌ {provider_label} 返回内容为空（可能被内容过滤或模型未输出）")
            return None

        try:
            raw_categories = json.loads(response_text)
        except json.JSONDecodeError as e:
            # 解析类错误：模型未遵循 JSON 约定，与网络错误区分开便于定位
            print(f"❌ {provider_label} 返回非合法 JSON: {e}")
            print(f"   原始返回（前 200 字）: {response_text[:200]}")
            return None

        if not isinstance(raw_categories, dict):
            print(f"❌ {provider_label} 返回的 JSON 顶层不是对象，而是 {type(raw_categories).__name__}")
            return None

        # 规整：过滤非法/越界索引、跨类去重、逐条补漏
        categories, stats = _normalize_categories(raw_categories, len(news_list))

        detail = _describe_category_stats(stats)
        if detail:
            print(f"⚠️ {provider_label} 分类结果已规整: {detail}")

        print(f"✅ {provider_label} 分类完成")
        return categories

    except Exception as e:
        # 兜底：保留类型信息，便于区分网络/解析/未知错误
        print(f"❌ {provider_label} 分类失败（未预期错误 {type(e).__name__}）: {str(e)[:150]}")
        return None


def classify_news_with_ai(news_list):
    """三级降级分类：Hermes 主模型 → deepseek → 关键词规则（10分类新版）"""
    
    if not news_list:
        return {}
    
    # 第一优先：Hermes 主模型
    if OPENAI_API_KEY and OPENAI_API_KEY != 'your_api_key':
        categories = _classify_with_llm(news_list, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, "主模型")
        if categories is not None:
            return categories
        print("⚠️ 主模型分类失败，尝试 deepseek...")
    else:
        print("⚠️ 主模型未配置（OPENAI_API_KEY），尝试 deepseek...")
    
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
    categories = {name: [] for name in CATEGORY_ORDER}

    # 非AI内容关键词（仅过滤明显与AI无关的内容）
    non_ai_keywords = [
        "招聘", "诚聘", "招贤", "简历", "招人",
        "内推", "社招", "校招", "猎头",
        # 活动/调研/招商类（2026-10-12 补充：这类内容与 AI 技术无关，
        # 原先会掉进兜底分支被误判为「跨分类」，实际应直接过滤）
        "问卷", "调研收集", "助力举办", "外国企业", "投资推介",
        "招商", "路演", "报名参加", "开幕式", "交流会",
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
            # 厂商模型名（2026-10-12 补充：原先缺这些，导致「DeepSeek V4 震撼亮相」
            # 「GPT-5.5 来了」这类重磅新闻命不中任何关键词，被兜底分支当成「其他」丢弃）
            # 权重设为 8（低于 Claude Code/Cursor 等产品线的 9-10）：
            # 厂商名常与主题词共现（"Claude Code 架构解析"应归 AI软件工程而非模型技术），
            # 权重过高会盖过主题词，导致分类偏移。
            ("DeepSeek", 8), ("GPT", 8), ("Claude", 8), ("Gemini", 8),
            ("Qwen", 8), ("通义", 8), ("文心", 8), ("ERNIE", 8),
            ("Llama", 8), ("Mistral", 8), ("Grok", 8), ("Sonnet", 8),
            ("Opus", 8), ("豆包", 8), ("Kimi", 8), ("MiniMax", 8),
            ("智谱", 7), ("GLM", 7), ("阶跃", 7), ("LLaMA", 8),
            ("Sora", 7), ("Veo", 7), ("Midjourney", 7),
            # 版本号与上下文规格（模型发布类新闻的典型特征）
            ("百万上下文", 8), ("预览版", 7), ("正式版", 7), ("旗舰", 7),
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
            # 兜底启发式（2026-10-12 扩充：原先漏掉大量真实AI内容，
            # 导致重磅新闻掉进 else 被当作「其他」丢弃）
            if any(x in title for x in ["编码", "编程", "代码", "开源", "开发框架", "软件工程", "Skill", "skill", "插件", "IDE", "仓库", "GitHub"]):
                categories["AI软件工程"].append(i)
            elif any(x in title for x in ["视频", "图像", "绘画", "写作", "创作", "生成", "短剧", "漫剧", "音乐", "配音", "设计工具"]):
                categories["内容创作"].append(i)
            elif any(x in title for x in ["知识库", "办公", "笔记", "PPT", "搜索", "效率", "助手", "工作流"]):
                categories["个人生产力"].append(i)
            elif any(x in title for x in ["芯片", "GPU", "算力", "服务器", "数据中心", "英伟达", "TPU", "H100", "H200"]):
                categories["AI 算力"].append(i)
            elif any(x in title for x in ["模型", "算法", "大模型", "评测", "论文", "上下文", "参数", "token", "Token"]):
                categories["模型技术"].append(i)
            elif any(x in title for x in ["Agent", "agent", "智能体", "MCP", "记忆", "安全治理", "多智能体", "工具调用"]):
                categories["Agent基建"].append(i)
            elif any(x in title for x in ["融资", "投资", "收购", "上市", "估值", "IPO"]):
                categories["其他AI相关"].append(i)
            elif any(x in title for x in ["手机", "眼镜", "耳机", "终端", "机器人", "汽车", "可穿戴", "具身"]):
                categories["智能终端"].append(i)
            elif any(x in title for x in ["教育", "医疗", "金融", "政务", "制造", "科学", "法律", "能源", "交通"]):
                categories["行业应用"].append(i)
            elif any(x in title for x in ["观点", "趋势", "思考", "预测", "访谈", "战略", "动态", "发布", "发布会", "报告", "白皮书"]):
                categories["其他AI相关"].append(i)
            elif "AI" in title or "人工智能" in title:
                # 兜底：含 AI/人工智能 字样但未命中上面任何分类 → 归入「其他AI相关」。
                # **必须放在所有具体分支之后**，否则会截胡 Agent/终端/行业应用等更精确的判断。
                # （曾尝试用「开发者/用户/产品」等词做中间层，但这些词太泛 ——
                #  "开发者"会命中"纯Python 教程"、"用户"会命中"用户数增长"，
                #  都会造成非AI 内容被误纳入，故取消中间层，由本分支统一兜底。）
                categories["其他AI相关"].append(i)
            else:
                # 未命中任何 AI 特征 → 判定为非 AI 内容，会被过滤
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
    
    # 按分类顺序遍历，跳过"其他"分类（列表来自 CATEGORY_ORDER，避免重复硬编码）
    for category in CONTENT_CATEGORIES:
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


def summarize_hot_topics_with_ai(news_list):
    """用分类所使用的 LLM 服务按标题归纳热点；失败时返回空列表，不做关键词兜底。"""
    if not news_list:
        return []

    titles = "\n".join(f"{i + 1}. {item['title']}" for i, item in enumerate(news_list))
    prompt = f"""请仅根据以下 {len(news_list)} 条文章标题，归纳今天报道最集中的热点。

要求：
1. 按同一事件、产品发布、公司动作或明确议题合并标题；不要把共同出现的泛词当作热点。
2. 最多输出 5 个热点，只保留至少涉及 2 篇文章的主题；按涉及文章数从多到少排序。
3. 每个热点用具体、易懂的一句话概括主题，并给出简短摘要，说明多篇文章共同报道了什么。
4. articles 必须填写对应标题的序号，不能虚构或重复序号；篇数由这些序号决定。
5. 标题不足以确认同一主题时不要合并；没有符合条件的热点则返回空数组。

标题列表：
{titles}

只输出 JSON，格式：
{{"topics":[{{"topic":"具体热点标题","summary":"一句话摘要","articles":[1,2]}}]}}"""

    providers = []
    if OPENAI_API_KEY and OPENAI_API_KEY != 'your_api_key':
        providers.append((OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, "主模型"))
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != 'your_api_key':
        providers.append((DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, "deepseek"))

    for api_key, base_url, model, label in providers:
        try:
            print(f"🤖 使用 {model} 总结今日热点...")
            client = OpenAI(api_key=api_key, base_url=base_url,
                            timeout=httpx.Timeout(60.0, connect=15.0))
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是 AI 资讯编辑，擅长根据标题识别多篇文章共同报道的具体事件和主题。只输出 JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    extra_body={"enable_thinking": False},
                )
            except Exception:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是 AI 资讯编辑，擅长根据标题识别多篇文章共同报道的具体事件和主题。只输出 JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = "\n".join(content.splitlines()[1:-1])
            topics = json.loads(content).get("topics", [])
            valid_topics = []
            for topic in topics:
                if not isinstance(topic, dict):
                    continue
                indices = topic.get("articles", [])
                if not isinstance(indices, list):
                    continue
                indices = sorted({i for i in indices if isinstance(i, int) and 1 <= i <= len(news_list)})
                title = str(topic.get("topic", "")).strip()
                summary = str(topic.get("summary", "")).strip()
                if title and summary and len(indices) >= 2:
                    valid_topics.append({"topic": title, "summary": summary, "count": len(indices)})
            valid_topics.sort(key=lambda item: item["count"], reverse=True)
            print(f"✅ {label} 热点总结完成")
            return valid_topics[:5]
        except Exception as e:
            print(f"⚠️ {label} 热点总结失败: {str(e)}")
    print("⚠️ AI 服务不可用，跳过热点板块")
    return []


def format_news_markdown(news_list, categories, start_date, end_date, platform="feishu", hot_topics=None):
    """将资讯格式化为 Markdown"""
    lines = []
    
    lines.append("## AI 资讯日报")
    lines.append("")

    hot_topics = hot_topics or []
    if hot_topics:
        lines.append("### 🔥 今日热点")
        lines.append("")
        for index, topic in enumerate(hot_topics, 1):
            # 不加粗：与其它章节条目（普通字重）保持一致的排版观感
            lines.append(f"{index}. {topic['topic']}：{topic['summary']}")
        lines.append("")
    
    ai_news_count = sum(len(indices) for indices in categories.values() if indices)
    
    if ai_news_count == 0:
        lines.append("😊 暂无AI相关资讯～")
        lines.append("")
        # 早退分支也必须返回 tuple：调用方无条件解包 (result, filtered)，
        # 原先此处返回 str，会在「全部条目被归入其他」时抛 TypeError。
        return "\n".join(lines), []

    # 按顺序输出分类（列表来自 CATEGORY_ORDER，避免重复硬编码）
    for category in CONTENT_CATEGORIES:
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
    
    # 生成被过滤资讯的列表（兜底桶 = 非 AI 内容，不进日报正文，仅输出到 stderr）
    filtered = []
    if categories.get(FALLBACK_CATEGORY):
        for idx in categories[FALLBACK_CATEGORY]:
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

        hot_topics = summarize_hot_topics_with_ai(news_list)
        result, filtered = format_news_markdown(news_list, categories, yesterday, today, platform, hot_topics)
        
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
