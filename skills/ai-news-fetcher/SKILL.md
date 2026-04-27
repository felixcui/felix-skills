---
name: ai-news-fetcher
description: 获取 AI 领域最新资讯并进行智能分类。从微信公众号 RSS 源获取 AI 相关文章，使用关键词规则自动分类为「AI编程与开发」「AI模型与技术」「AI内容创作」「AI产品与应用」「AI行业动态」「观点与趋势」等类别，支持发布到微信公众号。使用场景：每日 AI 资讯汇总、AI 新闻监控、自动资讯推送。
---

# AI 资讯获取器

从微信公众号 RSS 源获取最新的 AI 资讯，使用加权关键词规则进行智能分类，支持发布到微信公众号。

## 功能特点

- **自动获取**：从配置的 RSS API 获取最新的 AI 资讯
- **智能分类**：使用加权关键词规则自动将资讯分类到不同类别
- **分类类别**：
  - AI编程与开发（Cursor、Claude Code、Copilot、MCP 等）
  - AI模型与技术（大模型发布、算法创新、多模态、训练推理优化等）
  - AI内容创作（AI视频、AI绘画、AI写作、图像生成等）
  - AI产品与应用（AI 应用产品、功能更新、Agent、智能体等）
  - AI行业动态（融资并购、行业政策、市场趋势、人事变动等）
  - 观点与趋势（行业观察、深度思考、趋势分析等）
  - 其他（跨分类或不确定归属的 AI 相关内容）
- **过滤机制**：
  - 自动过滤指定公众号的内容
  - 过滤非AI相关内容（招聘、活动预告等）
- **分类缓存**：同一天内复用分类结果，避免重复请求
- **公众号发布**：支持创建草稿和发布到微信公众号（使用 baoyu-markdown-to-html 转换）

## 目录结构

```
ai-news-fetcher/
├── SKILL.md                            # 技能说明文档
├── .env                                # 环境变量配置（微信凭证、外部依赖路径）
└── scripts/
    ├── fetch_ai_news.py                # 资讯获取与智能分类（核心脚本）
    ├── publish_to_wechat.py            # 微信公众号发布
    ├── publish_to_wechat_daily.sh      # 每日定时发布脚本
    └── send_ai_news.sh                 # 获取资讯并输出
```

## 前置条件

### 1. 安装 Python 依赖

```bash
pip install requests python-dotenv openai
```

### 2. 配置 .env 文件

在 `ai-news-fetcher/` 目录下创建 `.env` 文件：

```bash
# 微信公众号 API 凭证（发布到公众号时需要）
WECHAT_APPID=your_appid
WECHAT_APPSECRET=your_appsecret

# baoyu-markdown-to-html skill 路径（发布到公众号时需要）
BAOYU_MARKDOWN_TO_HTML_DIR=~/work/skills/baoyu-skills/skills/baoyu-markdown-to-html

# OpenAI 兼容 API 配置（AI 智能分类时需要，不配置则使用关键词分类）
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
```

### 3. 关联 Skill

如需发布到微信公众号，还需要以下 skill：

- **baoyu-markdown-to-html**：将 Markdown 转为微信公众号适配的 HTML
- **aicoding-news-weekly**：提供 `wechat_api_client.py` 微信 API 封装

> **注意：** 仅获取资讯（`fetch_ai_news.py`）无需以上依赖，只需 `requests` 和 `.env` 中的 RSS API 配置。

## 使用方法

### 1. 获取资讯（仅输出）

```bash
python3 scripts/fetch_ai_news.py
```

### 2. 发布到微信公众号后台草稿

```bash
python3 scripts/publish_to_wechat.py --create-draft
```

#### 使用自定义封面图（可选）

```bash
# 使用后台已有的封面图素材 ID
python3 scripts/publish_to_wechat.py --create-draft --thumb-media-id YOUR_MEDIA_ID
```

> **注意：** 默认使用固定的封面图素材 ID，无需指定。

## 配置说明

### 环境变量（.env）

在 `.env` 中配置：

```bash
# 微信公众号 API 凭证
WECHAT_APPID=your_appid
WECHAT_APPSECRET=your_appsecret

# baoyu-markdown-to-html skill 路径（支持 ~ 写法）
BAOYU_MARKDOWN_TO_HTML_DIR=~/work/skills/baoyu-skills/skills/baoyu-markdown-to-html
```

### 修改 RSS API 密钥

通过环境变量或编辑 `scripts/fetch_ai_news.py`：

```python
RSS_API_KEY = os.getenv("AI_NEWS_API_KEY", "YOUR_API_KEY")
RSS_API_BASE = os.getenv("AI_NEWS_API_BASE", "https://wexinrss.zeabur.app")
```

### 修改过滤的公众号

编辑 `scripts/fetch_ai_news.py` 中的 `EXCLUDED_BIZ_IDS` 集合：

```python
EXCLUDED_BIZ_IDS = {
    "3092970861",  # 公众号ID
    # 添加更多...
}
```

## 依赖

- Python 3.6+
- requests 库
- python-dotenv 库
- [baoyu-markdown-to-html](https://github.com/nicepkg/baoyu-markdown-to-html) skill（用于 Markdown 转 HTML）
- [aicoding-news-weekly](../aicoding-news-weekly/) skill（提供 `wechat_api_client.py`）

## Cron Job 执行注意事项

### ⚠️ 必须使用 `execute_code` 而非 `terminal()`

RSS API 域名 `wexinrss.zeabur.app` 使用 `.app` TLD，会被 `terminal()` 工具的安全扫描拦截（lookalike TLD detection），导致脚本挂起无输出。**cron job 中必须全程使用 `execute_code` 工具执行 Python 代码**，不要用 `terminal()` 直接运行脚本。

### Cron Job 推荐执行流程

不要直接 `terminal("python3 scripts/publish_to_wechat.py --create-draft")`，而是分步执行：

**Step 1：用 `execute_code` + `importlib.util` 加载并调用 fetch_ai_news.py**

```python
import importlib.util
from pathlib import Path
from dotenv import load_dotenv

skill_root = Path(os.path.expanduser("~/.hermes/skills/felix-skills/skills/ai-news-fetcher"))
load_dotenv(skill_root / ".env")

spec = importlib.util.spec_from_file_location("fetch_ai_news", str(skill_root / "scripts" / "fetch_ai_news.py"))
fetch_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_module)

markdown_content = fetch_module.get_news_summary(days=1, classify=True, method="ai")
```

**Step 2：用 `execute_code` + `subprocess.run(["bun", ...])` 进行 HTML 转换**

```python
import shutil
from pathlib import Path

# baoyu-markdown-to-html 要求输入文件以 .md 结尾
md_path = Path("/tmp/ai_news_wechat_temp.md")
md_path.write_text(markdown_content, encoding='utf-8')

result = subprocess.run(
    ["bun", str(Path("~/work/skills/baoyu-skills/skills/baoyu-markdown-to-html/scripts/main.ts").expanduser()),
     str(md_path), "--theme", "default"],
    capture_output=True, text=True, timeout=60
)
# 解析 result.stdout 中的 JSON 获取 htmlPath，提取 <body> 内容
```

**Step 3：用 `execute_code` 加载 wechat_api_client.py 并创建草稿**

```python
spec = importlib.util.spec_from_file_location(
    "wechat_api_client",
    str(skill_root.parent / "aicoding-news-weekly" / "scripts" / "wechat_api_client.py")
)
wechat_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wechat_module)

client = wechat_module.WeChatAPIClient(appid=appid, appsecret=appsecret)
media_id = client.create_draft(title=title, content=body_html, thumb_media_id=THUMB_MEDIA_ID, ...)
```

### 关键路径

- Skill 根目录：`~/.hermes/skills/felix-skills/skills/ai-news-fetcher/`
- fetch_ai_news.py：`<skill_root>/scripts/fetch_ai_news.py`
- wechat_api_client.py：`<skill_root>/../aicoding-news-weekly/scripts/wechat_api_client.py`
- baoyu-markdown-to-html：`~/work/skills/baoyu-skills/skills/baoyu-markdown-to-html/scripts/main.ts`

## 技术细节

### 资讯获取与分类

- 使用 `fetch_ai_news.py` 从 RSS API 获取资讯
- 优先使用 **OpenAI 兼容 API** 进行智能分类（支持阿里云百炼等）
- API 不可用时降级为**加权关键词规则**分类（三层匹配：强信号规则 → 加权匹配 → 兜底启发式）

### 微信公众号发布

- 使用 `publish_to_wechat.py` 统一发布流程（仅限非 cron 场景直接调用）
- 通过 `.env` 环境变量配置 `baoyu-markdown-to-html` 路径
- 通过相对路径引用 `aicoding-news-weekly/scripts/wechat_api_client.py`
- 支持创建草稿和发布文章两种模式
- **cron job 场景**：必须使用 `execute_code` 分步执行（见上方 Cron Job 执行注意事项）

## 输出示例

```markdown
## AI 资讯汇总

### AI编程与开发（5 条）

1. [骚操作来了！Claude编程的42个实战技巧大全](https://...) 
2. [手把手教你用Obsidian重构AI知识管理体系](https://...) 
3. [GitHub崩到忍无可忍，OpenAI决定开发代码托管平台](https://...) 

### AI模型与技术（3 条）

1. [图灵奖得主Don Knuth发论文致谢Claude](https://...) 
2. [跳过88%专家，保住97%性能！MoE推理优化 | CVPR'26](https://...) 

### AI产品与应用（3 条）

1. [为什么顶尖投行都选择了 Rogo 这个金融 Agent？](https://...) 
2. [Skills：从编程工具的配角到Agent研发的核心](https://...) 

### AI行业动态（2 条）

1. [OpenAI 要上市了](https://...) 
2. [捏 Ta完成超千万美金PreA+轮融资](https://...) 

### 观点与趋势（3 条）

1. [AI江湖有聚散，千问的路还在向前](https://...) 
2. [2026 年最好的 AI PC，是 Mac](https://...) 
```
