---
name: xhs-writer
description: 将公众号文章保存到本地并转换为小红书风格文案，同时生成封面图设计文案
---

# 公众号文章转小红书文案

将公众号文章保存到输出目录，然后转换为小红书风格文案，并生成封面图设计文案，所有文件存储到同一目录，保持内容精华的同时适配小红书的内容呈现方式。

## 参数

- `$ARGUMENTS`: 公众号文章的 URL **或** 本地 Markdown 文件路径（必填），以及可选的输出目录路径

## 输出目录

输出目录按以下优先级确定（从高到低）：

| 优先级 | 方式 | 示例 |
|--------|------|------|
| 1 | 用户在参数中明确指定目录 | `/xhs-writer <URL或文件> --output-dir ~/Desktop/xhs` |
| 2 | 默认：skill 内部的 `output/` 子目录 | `xhs-writer/output/` |

> 执行前，先向用户确认使用何种输出目录，若用户未特别说明则使用默认目录。

## 执行步骤

### 步骤 0：确定输出目录

根据上方优先级规则确定 `$OUTPUT_DIR`：
- 若用户指定了目录，使用用户指定的路径（支持 `~` 和相对路径）
- 否则默认为：`<本 SKILL.md 所在目录>/output/`（即 `xhs-writer/output/`）

确保目录存在：
```bash
mkdir -p "$OUTPUT_DIR"
```

### 步骤 1：获取并准备文章内容

判断 `$ARGUMENTS` 中的输入是 URL 还是本地文件。

#### 1.1 若输入为 URL（抓取模式）

使用 `defuddle` 命令抓取并提取文章内容，转换为 Markdown 格式。

```bash
# 获取当前日期（YYYY-MM-DD 格式）
CURRENT_DATE=$(date +%Y-%m-%d)

# 使用 defuddle 获取文章 JSON 数据（包含元数据和 Markdown 正文）
# 确保系统已安装 defuddle
ARTICLE_JSON=$(defuddle parse -j --md "$ARTICLE_URL")

# 使用 jq 解析元数据（需确保系统已安装 jq）
ARTICLE_TITLE=$(echo "$ARTICLE_JSON" | jq -r '.title // "未知标题"')
ARTICLE_AUTHOR=$(echo "$ARTICLE_JSON" | jq -r '.author // "未知作者"')
ARTICLE_PUB=$(echo "$ARTICLE_JSON" | jq -r '.published // ""')
ARTICLE_DESC=$(echo "$ARTICLE_JSON" | jq -r '.description // ""')

# 清理标题中的非法字符（用于文件名）
CLEAN_TITLE=$(echo "$ARTICLE_TITLE" | sed 's/[\/\\:*?"<>|]//g')

# 最终文件路径
SAVED_MD="$OUTPUT_DIR/${CURRENT_DATE}_${CLEAN_TITLE}.md"

# 提取 Markdown 正文
ARTICLE_CONTENT=$(echo "$ARTICLE_JSON" | jq -r '.content // ""')

# 将元数据和正文写入 Markdown 文件
cat > "$SAVED_MD" << EOF
---
title: "$ARTICLE_TITLE"
author: "$ARTICLE_AUTHOR"
date: "$ARTICLE_PUB"
description: "$ARTICLE_DESC"
---

$ARTICLE_CONTENT
EOF
```

#### 1.2 若输入为本地文件（本地模式）

将直接使用传入的本地 Markdown 文件，**不进行复制**。

```bash
# 目标读取路径即为输入路径
SAVED_MD="$INPUT_FILE"
```

### 步骤 2：读取待处理的文章

读取 Markdown 文件（抓取保存的文件或输入的本地文件），提取内容用于转换。

```bash
# 使用步骤 1 中最终确定的文件路径 SAVED_MD
```

读取该文件内容，从 YAML front matter 中提取 `title`、`author`、`description` 等元信息。

### 步骤 3：分析文章结构

提取文章的核心要素：
- **标题**: 吸引眼球的亮点
- **痛点**: 问题或需求
- **核心内容**: 3-5 个关键要点
- **价值**: 读者能获得什么

### 步骤 4：转换文案风格

按照小红书内容特点进行转换：

#### 结构模板

```markdown
# 🔥 吸引眼球的标题（使用emoji）

✨ 开头钩子（引起共鸣）
✨ 提出问题
✨ 引出下文

---

## 🎯 核心内容

### 1️⃣ 要点一
- 关键信息
- 实用技巧

### 2️⃣ 要点二
- 关键信息
- 实用技巧

### 3️⃣ 要点三
- 关键信息
- 实用技巧

---

## 💡 实用总结/行动建议

#话题标签1 #话题标签2 #话题标签3
```

#### 文案风格要求

1. **标题**: 🔥 emoji + 痛点/亮点 + 情绪词
2. **开头**: 3-5 个钩子句，使用 ✨ emoji
3. **正文**:
   - 分点阐述，每点使用 emoji 数字标记
   - 简洁有力，避免冗长
   - 重点内容加粗或使用特殊符号
4. **结尾**: 简洁总结 + 话题标签

### 步骤 5：保存小红书文案

将生成的小红书文案保存到 `$OUTPUT_DIR` 目录中。

**文件名格式**: `YYYY-MM-DD_{文章标题}_xhs.md`（基于原文件名生成）

**文件内容结构**:
```markdown
# 小红书文案标题

[文案内容...]
```

> 注意：不添加 YAML frontmatter 元信息

**保存操作**:
```bash
# 提取原文件名（不含扩展名和路径）
BASENAME=$(basename "${SAVED_MD%.md}")

# 统一在 OUTPUT_DIR 目录下生成小红书文案
XHS_FILE="$OUTPUT_DIR/${BASENAME}_xhs.md"

# 写入文件
cat > "$XHS_FILE" << 'EOF'
$XHS_CONTENT
EOF
```

### 步骤 6：生成封面图设计文案

从小红书文案中提取核心要点，生成封面图设计参考文档。

#### 6.1 分析内容提取要点

从小红书文案中提取：
- **主题**: 文章核心主题（标题）
- **副标题**: 补充说明或价值主张
- **核心要点**: 3-10 个关键点（每个要点提炼为一个关键词）
- **一句话总结**: 核心原则或行动建议

#### 6.2 封面图设计文案格式

```markdown
# {主题} - 封面图要点

## 主题
**{主标题}**

## 副标题
{副标题或价值主张}

## 核心价值主张
- 价值点 1
- 价值点 2
- 价值点 3

---

## 风格说明
- **风格**：Notion 极简风格，手绘线条，纸张质感
- **配色**：柔和温暖，不刺眼
- **尺寸**：小红书竖版图片，比例约 3:4
- **调性**：专业、可信赖
- **标题**：字体大且醒目，突出主标题视觉层级

---

## 封面展示要点

| # | 要点 | 关键词 |
|---|------|--------|
| 1 | {要点1描述} | {关键词1} |
| 2 | {要点2描述} | {关键词2} |
| ... | ... | ... |

---

## 封面图设计建议

### 视觉层次
1. **主标题**：{主题}
2. **副标题**：{副标题关键词组合}
3. **核心展示**：要点关键词（可用图标+文字）

### 封面可展示的关键词云
```
{关键词1} | {关键词2} | {关键词3} | ...
```

---

## 核心原则一句话
**{一句话总结}**
```

#### 6.3 保存封面图设计文案

**文件名格式**: `YYYY-MM-DD_{文章标题}_cover-points.md`

**保存操作**:
```bash
# 统一在 OUTPUT_DIR 目录下生成封面设计文案
COVER_FILE="$OUTPUT_DIR/${BASENAME}_cover-points.md"
# 写入封面图设计文案
```

### 步骤 7：输出结果

直接展示小红书文案内容预览，并在结尾说明文件保存路径。

**输出格式**:
```markdown
## 小红书文案预览

[小红书文案内容...]

---

## 封面图设计文案预览

[封面图设计文案内容...]

---

📁 文件已保存至:
- 小红书文案: `$OUTPUT_DIR/YYYY-MM-DD_{文章标题}_xhs.md`
- 封面图设计: `$OUTPUT_DIR/YYYY-MM-DD_{文章标题}_cover-points.md`
```

## 内容转换原则

### 精简原则
- 删除冗余表述，保留核心信息
- 每个要点不超过 3 句话
- 使用短句和短语，提高可读性

### 情感化表达
- 使用"宝子们"、"家人们"等亲切称呼
- 添加"超赞"、"必看"、"神器"等情绪词
- 使用感叹号增强语气

### 视觉优化
- 合理使用 emoji 分隔内容
- 使用引用块、列表等格式
- 段落之间保持适当间距

## 常用 emoji 组合

- **开头**: ✨ 🔥 💡 📢 🎯
- **要点**: 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣
- **强调**: 💪 ⚡ 🌟 💎 🚀
- **总结**: 📝 ✅ 💡 🎁

## 示例

### 输入
```bash
# URL 抓取模式
/xhs-writer https://mp.weixin.qq.com/s/xxxxx

# URL 抓取并指定输出目录
/xhs-writer https://mp.weixin.qq.com/s/xxxxx --output-dir ~/Desktop/xhs

# 本地文件模式（生成产物到指定的或默认的 output 目录）
/xhs-writer ~/Desktop/article.md
```

### 输出

```markdown
## 小红书文案预览

# 🔥 Claude Code神器推荐！让AI变成你的项目经理！

✨ 还在为AI代码质量不稳定发愁？
✨ 还在担心漏掉关键功能？
✨ 还在想怎么把AI能力沉淀下来？

今天给大家安利一款宝藏工具——Superpowers！

---

## 🎯 什么是Superpowers？

简单说，它是一个**强制性的软件开发工作流**！

装上之后，Claude Code会被约束在标准流程里：
```
讨论需求 → 写计划 → 写代码 → 自己审查
```

不再是"拿到任务就开干"，而是像有个项目经理在旁边管着它！👨‍💼

---

## 💪 三大核心命令

| 命令 | 作用 |
|------|------|
| `/superpowers:brainstorm` | 项目启动前先头脑风暴 |
| `/superpowers:write-plan` | 创建详细实现计划 |
| `/superpowers:execute-plan` | 分批执行，带审查检查点 |

---

## 💡 核心价值

**防止遗漏 + 强制规范**

每次使用Claude Code的工作都会以skill的形式沉淀和积累下来！📚

#ClaudeCode #AI编程 #Superpowers #Skills #编程工具 #开发效率

---

## 封面图设计文案预览

# Superpowers - 封面图要点

## 主题
**Claude Code 神器 Superpowers**

## 副标题
让 AI 变成你的项目经理

## 核心价值主张
- 强制规范流程
- 防止功能遗漏
- 能力持续沉淀

---

## 风格说明
- **风格**：Notion 极简风格，手绘线条，纸张质感
- **配色**：柔和温暖，不刺眼
- **尺寸**：小红书竖版图片，比例约 3:4
- **调性**：专业、可信赖
- **标题**：字体大且醒目，突出主标题视觉层级

---

## 封面展示要点

| # | 要点 | 关键词 |
|---|------|--------|
| 1 | 强制性软件开发工作流 | 规范流程 |
| 2 | brainstorm 头脑风暴 | 先规划 |
| 3 | write-plan 写计划 | 写计划 |
| 4 | execute-plan 执行 | 带审查 |
| 5 | skill 形式沉淀 | 可沉淀 |

---

## 核心原则一句话
**防止遗漏 + 强制规范**

---

📁 文件已保存至:
- 小红书文案: `xhs-writer/output/YYYY-MM-DD_Claude Code神器推荐_xhs.md`
- 封面图设计: `xhs-writer/output/YYYY-MM-DD_Claude Code神器推荐_cover-points.md`
```

## 文件存储结构

```
xhs-writer/
└── output/                                         # 默认输出目录（建议加入 .gitignore）
    ├── YYYY-MM-DD_{文章标题}.md                    # 公众号原文
    ├── YYYY-MM-DD_{文章标题}_xhs.md                # 小红书文案
    └── YYYY-MM-DD_{文章标题}_cover-points.md       # 封面图设计文案
```

> 注：`YYYY-MM-DD` 为当前日期，`{文章标题}` 从页面自动提取

## 注意事项

- 保持原内容的核心价值不变
- 字数严格控制在 1000 字以内
- 标签要与内容高度相关
- 避免过度营销化，保持内容真实
- 技术类内容保持专业性，不过度娱乐化
- **输出目录**：默认为 `xhs-writer/output/`，可在调用时通过 `--output-dir` 参数自定义
- **依赖**：需要安装 `defuddle` 用于网页解析，以及 `jq` 用于处理 JSON 数据
