---
name: wechat-to-xiaohongshu
description: 将公众号文章保存到本地并转换为小红书风格文案，同时生成封面图设计文案
---

# 公众号文章转小红书文案

将公众号文章保存到输出目录，然后转换为小红书风格文案，并生成封面图设计文案，所有文件存储到同一目录，保持内容精华的同时适配小红书的内容呈现方式。

## 参数

- `$ARGUMENTS`: 公众号文章的 URL（必填），以及可选的输出目录路径

## 输出目录

输出目录按以下优先级确定（从高到低）：

| 优先级 | 方式 | 示例 |
|--------|------|------|
| 1 | 用户在参数中明确指定目录 | `/wechat-to-xiaohongshu <URL> --output-dir ~/Desktop/xhs` |
| 2 | 默认：skill 内部的 `output/` 子目录 | `wechat-to-xiaohongshu/output/` |

> 执行前，先向用户确认使用何种输出目录，若用户未特别说明则使用默认目录。

## 执行步骤

### 步骤 0：确定输出目录

根据上方优先级规则确定 `$OUTPUT_DIR`：
- 若用户指定了目录，使用用户指定的路径（支持 `~` 和相对路径）
- 否则默认为：`<本 SKILL.md 所在目录>/output/`（即 `wechat-to-xiaohongshu/output/`）

确保目录存在：
```bash
mkdir -p "$OUTPUT_DIR"
```

### 步骤 1：保存公众号文章

使用 `baoyu-url-to-markdown` skill 抓取并保存文章内容。

#### 1.1 确定运行时和脚本路径

```bash
# 确定 bun 运行时
if command -v bun &> /dev/null; then
  BUN_X="bun"
elif command -v npx &> /dev/null; then
  BUN_X="npx -y bun"
else
  # 提示用户安装 bun
fi

# baoyu-url-to-markdown 脚本路径
URL_TO_MD_SCRIPT="<baoyu-url-to-markdown skill 路径>/scripts/main.ts"
```

#### 1.2 执行抓取

```bash
# 使用 --output-dir 指定输出目录（自动生成文件名）
$BUN_X "$URL_TO_MD_SCRIPT" "$ARTICLE_URL" --output-dir "$OUTPUT_DIR"
```

脚本会自动从页面提取标题并生成文件。

**输出说明**:
- Markdown 文件: `$OUTPUT_DIR/mp.weixin.qq.com/{slug}.md`（初始输出）
- HTML 快照: `$OUTPUT_DIR/mp.weixin.qq.com/{slug}-captured.html`

#### 1.3 重命名文件（使用日期+文章标题）

从保存的 Markdown 文件的 YAML front matter 中提取 `title`，然后重命名文件，添加日期前缀：

```bash
# 定位初始保存的文件
INITIAL_MD=$(ls -t "$OUTPUT_DIR/mp.weixin.qq.com/"*.md 2>/dev/null | grep -v captured | head -1)

# 从 YAML front matter 提取标题
ARTICLE_TITLE=$(grep -m1 "^title:" "$INITIAL_MD" | sed 's/^title: *//' | tr -d '"')

# 清理标题中的非法字符（用于文件名）
CLEAN_TITLE=$(echo "$ARTICLE_TITLE" | sed 's/[\/\\:*?"<>|]//g')

# 获取当前日期（YYYY-MM-DD 格式）
CURRENT_DATE=$(date +%Y-%m-%d)

# 重命名文件到 output 目录根目录（添加日期前缀）
mv "$INITIAL_MD" "$OUTPUT_DIR/${CURRENT_DATE}_${CLEAN_TITLE}.md"
#mv "${INITIAL_MD%.md}-captured.html" "$OUTPUT_DIR/${CURRENT_DATE}_${CLEAN_TITLE}-captured.html" 2>/dev/null || true

# 删除空的域名子目录
rmdir "$OUTPUT_DIR/mp.weixin.qq.com" 2>/dev/null || true

# 最终文件路径
SAVED_MD="$OUTPUT_DIR/${CURRENT_DATE}_${CLEAN_TITLE}.md"
```

### 步骤 2：读取保存的文章

从输出目录读取刚保存的 Markdown 文件，提取内容用于转换。

```bash
# 使用步骤 1.3 中确定的文件路径
# SAVED_MD 变量已设置为 "$OUTPUT_DIR/${CURRENT_DATE}_${CLEAN_TITLE}.md"
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

将生成的小红书文案保存到 `$OUTPUT_DIR/` 目录（与原文同级）。

**文件名格式**: `YYYY-MM-DD_{文章标题}_xhs.md`（与原文 `YYYY-MM-DD_{文章标题}.md` 对应）

**文件内容结构**:
```markdown
# 小红书文案标题

[文案内容...]
```

> 注意：不添加 YAML frontmatter 元信息

**保存操作**:
```bash
# 基于原文文件名生成小红书文案文件名
# 原文: YYYY-MM-DD_{文章标题}.md → 小红书: YYYY-MM-DD_{文章标题}_xhs.md
XHS_FILE="${SAVED_MD%.md}_xhs.md"

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
COVER_FILE="${SAVED_MD%.md}_cover-points.md"
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
/wechat-to-xiaohongshu https://mp.weixin.qq.com/s/xxxxx
# 或指定输出目录
/wechat-to-xiaohongshu https://mp.weixin.qq.com/s/xxxxx --output-dir ~/Desktop/xhs
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
- 小红书文案: `wechat-to-xiaohongshu/output/YYYY-MM-DD_Claude Code神器推荐_xhs.md`
- 封面图设计: `wechat-to-xiaohongshu/output/YYYY-MM-DD_Claude Code神器推荐_cover-points.md`
```

## 文件存储结构

```
wechat-to-xiaohongshu/
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
- **输出目录**：默认为 `wechat-to-xiaohongshu/output/`，可在调用时通过 `--output-dir` 参数自定义
- **依赖**：需要安装 `bun` 运行时，用于执行 `baoyu-url-to-markdown` 脚本
