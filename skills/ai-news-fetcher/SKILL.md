---
name: ai-news-fetcher
description: 获取 AI 领域最新资讯并进行智能分类。用于从微信公众号 RSS 源获取 AI 相关文章，使用 AI 自动分类为「AI编程工具及实践」「AI模型与技术」「AI产品与应用」「AI行业动态」等类别，支持发送到飞书和发布到微信公众号。使用场景：每日 AI 资讯汇总、AI 新闻监控、自动资讯推送。
---

# AI 资讯获取器

从微信公众号 RSS 源获取最新的 AI 资讯，进行智能分类，并支持发送到飞书和发布到微信公众号。

## 功能特点

- **自动获取**：从配置的 RSS API 获取昨日到今日的 AI 资讯
- **智能分类**：使用 AI 模型（GLM-5）自动将资讯分类到不同类别
- **分类类别**：
  - AI编程工具及实践（Cursor、Claude Code、Copilot、OpenClaw 等）
  - AI模型与技术（大模型发布、算法创新、多模态、训练推理优化等）
  - AI产品与应用（AI 应用产品、功能更新、Agent、智能体、SaaS产品等）
  - AI行业动态及观察（融资并购、行业政策、市场趋势、人事变动、行业观察等）
  - 其他（AI相关但跨分类或不确定归属的内容）
- **过滤机制**：
  - 自动过滤指定公众号的内容
  - 谨慎过滤非AI相关内容（招聘、活动、时政、汽车、房产、游戏、娱乐、音乐、体育等）
- **公众号过滤**：可配置需要排除的公众号 ID 列表
- **多格式输出**：支持纯文本、Markdown 等格式
- **公众号发布**：支持创建草稿和发布到微信公众号

## 使用方法

### 1. 获取资讯（仅输出）

```bash
python3 scripts/fetch_ai_news.py
```

### 2. 获取并发送到飞书

```bash
bash scripts/send_ai_news.sh
```

### 微信公众号发布（新增）

#### 方式一：创建草稿（推荐先测试）

```bash
python3 scripts/publish_to_wechat.py --create-draft
```

#### 方式二：创建草稿并发布

```bash
python3 scripts/publish_to_wechat.py --publish
```

#### 方式三：指定天数

```bash
# 获取最近 3 天的资讯并创建草稿
python3 scripts/publish_to_wechat.py --days 3 --create-draft
```

#### 方式四：使用自定义封面图（可选）

```bash
# 使用后台已有的封面图素材 ID（推荐）
python3 scripts/publish_to_wechat.py --create-draft --thumb-media-id qxQUqgd9fe1MaWRFFohGgo8SIofgUyArMyHRseRKpcGrV1yW3yBRRjrd_0Kj41uF
```

**注意：** 默认使用固定的封面图素材 ID，无需指定封面图路径。

## 配置说明

### 修改 RSS API 密钥

编辑 `scripts/fetch_ai_news.py` 中的 API URL：

```python
url = f"https://wexinrss.zeabur.app/api/query?k=YOUR_API_KEY&content=0&before={before}&after={after}"
```

### 修改过滤的公众号

编辑 `scripts/fetch_ai_news.py` 中的 `EXCLUDED_BIZ_IDS` 集合：

```python
EXCLUDED_BIZ_IDS = {
    "3092970861",  # 公众号ID
    # 添加更多...
}
```

### 修改发送目标（飞书）

编辑 `scripts/send_ai_news.sh` 中的 `--target` 参数：

```bash
--target "ou_xxxxx"  # 飞书用户 open_id 或群聊 chat_id
```

### 配置微信公众号凭证

在 `aicoding-news-weekly/.env` 文件中配置（已在 skill 目录下）：

```bash
WECHAT_APPID=wx0f68874c718318bf
WECHAT_APPSECRET=4719e11ebae2e75231484b7a5eb79802
```

## 定时任务配置

### 飞书推送（已配置）

添加到 crontab 实现每日自动推送：

```bash
# 每天早上 7:10 执行
10 7 * * * cd ~/.openclaw/workspace-fs_news_claw && bash skills/ai-news-fetcher/scripts/send_ai_news.sh >> /var/log/ai_news.log 2>&1
```

### 微信公众号发布（可选）

如果需要自动发布到公众号，可以添加到 crontab：

```bash
# 每天早上 7:30 创建草稿
30 7 * * * cd ~/.openclaw/workspace-fs_news_claw && python3 skills/ai-news-fetcher/scripts/publish_to_wechat.py --create-draft >> /var/log/wechat_publish.log 2>&1

# 每天早上 8:00 发布文章
0 8 * * * cd ~/.openclaw/workspace-fs_news_claw && python3 skills/ai-news-fetcher/scripts/publish_to_wechat.py --publish >> /var/log/wechat_publish.log 2>&1
```

## 依赖

- Python 3.6+
- requests 库
- markdown 库
- pygments 库（代码高亮）
- openclaw CLI（用于发送消息）

## 输出示例

### 飞书格式（最新）

```
📰 AI 资讯汇总

> 📅 `2026-03-05` - `2026-03-06`
> 📊 共 **31** 条资讯（已过滤非AI内容）

💻 AI编程工具及实践（5 条）
1. [骚操作来了！Claude编程的42个实战技巧大全](https://...)
2. [手把手教你用Obsidian + OpenClaw重构AI知识管理体系](https://...)
3. [tmux，Vibe Coding时代的最佳跨平台终端基建](https://...)
4. [GitHub崩到忍无可忍，OpenAI决定开发代码托管平台](https://...)
5. [刚刚，Claude Code 上线语音模式！「用嘴编程」的时代，来了](https://...)

🧠 AI模型与技术（13 条）
1. [图灵奖得主Don Knuth发论文致谢Claude](https://...)
2. [跳过88%专家，保住97%性能！MoE推理的正确玩法| CVPR'26](https://...)
3. [刚刚，GPT-5.4核心内幕炸裂剧透！或拥有永久记忆，极限推理狂飙](https://...)
...

🚀 AI产品与应用（3 条）
1. [为什么顶尖投行都选择了 Rogo 这个金融 Agent？](https://...)
2. [智能体工程火爆中美！猎豹CEO亲自开播春节"养龙虾"经历！X疯传：如何成为世界级 Agent 工程师](https://...)
3. [Skills：从编程工具的配角到Agent研发的核心](https://...)

📈 AI行业动态及观察（5 条）
1. [通过"Session 0"利用多样性打造高影响力团队](https://...)
2. [刚刚，阿里批准林俊旸辞职：昨天还在挽留，否认停止开源](https://...)
3. [OpenAI 要上市了](https://...)
4. [速递｜捏 Ta完成超千万美金PreA+轮融资，定义AI时代世界创作的基础设施](https://...)
5. [阿里高层紧急回应林俊旸离职：无关任何斗争/MacBook Neo发布，不到4000能拿下/Seedance2.0价格公布：1元1秒](https://...)

📂 其他（5 条）
1. [AI 眼镜，不该只有一个「大脑」](https://...)
2. [AI江湖有聚散，千问的路还在向前](https://...)
3. [2026 年最好的 AI PC，是 Mac](https://...)
4. [OpenAI发布Symphony：AI时代的敏捷看板](https://...)
5. [我被大模型这薪资惊到了！](https://...)

---
✅ AI资讯推送任务已完成 (7:00)
```

### 微信公众号格式

标题：📰 AI 资讯汇总 - 2026年03月06日
摘要：本期汇总了最新的 AI 相关资讯，涵盖编程工具、模型技术、产品应用和行业动态等内容。
内容：HTML 格式的公众号文章（使用 baoyu-markdown-to-html 转换，支持代码高亮、数学公式等）

## 技术细节

### AI 资讯获取和分类

- 使用 `fetch_ai_news.py` 从 RSS API 获取资讯
- 使用阿里云百炼 GLM-5 模型进行智能分类（通过 OpenClaw 调用）
- 关键词分类作为后备方案
- 自动过滤非AI相关内容（谨慎过滤，包括招聘、活动、时政、汽车、房产、游戏、娱乐等）

### 微信公众号发布

- 使用 `publish_to_wechat.py` 统一发布流程
- 使用 `baoyu-markdown-to-html` 转换 Markdown 为 HTML
- 依赖 `aicoding-news-weekly/skills/wechat_api_client.py` 调用微信 API
- 支持创建草稿和发布文章两种模式

### 分类优化说明

- ✅ 分类名称更新：AI行业动态 → AI行业动态及观察
- ✅ 增加"其他"分类：收录不确定归属的AI相关内容
- ✅ 优化分类提示词：增加明确的判断标准和示例
- ✅ 模型更新：dashscope/qwen-plus → bailian/glm-5
- ✅ 谨慎过滤非AI内容：避免过度过滤
- ✅ 修复 open_id 跨应用问题
- ✅ 使用专业的 Markdown 转 HTML 工具

### 定时任务配置（OpenClaw Cron）

已配置的定时任务（使用 `openclaw cron`）：

| 任务 | 时间 | 频率 | 说明 |
|------|------|------|------|
| AI News - Send to Feishu | 每天 7:00 | 每日 | 自动获取并发送 AI 资讯到飞书 |
| AI News - Publish to WeChat | 每天 7:10 | 每日 | 自动创建草稿到微信公众号 |

任务会自动发送执行完成通知到飞书。
