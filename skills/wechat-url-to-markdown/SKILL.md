---
name: wechat-url-to-markdown
description: 将微信公众号链接内容保存为本地 Markdown 格式，默认存储到 skill 内部的 output/ 目录
---

# 微信公众号文章保存工具

## 无参数时的处理

**当用户未提供文章 URL 时**，输出以下用法提示，然后等待用户输入：

---

👋 **欢迎使用微信公众号文章保存工具！**

请提供一个微信公众号文章链接，我会将其抓取并保存为 Markdown 文件。

**用法：**
> 「帮我保存这篇文章：**[微信公众号链接]**」

**示例：**
- `帮我保存这篇文章：https://mp.weixin.qq.com/s/xxxxx`
- `保存到桌面：https://mp.weixin.qq.com/s/xxxxx`（自定义输出目录）

**输出位置：** 默认保存到 `wechat-url-to-markdown/output/` 目录，也可以告诉我保存到哪里。

---

将微信公众号文章抓取并保存为 Markdown 格式，便于本地阅读和知识管理。

## 目录结构

```
wechat-url-to-markdown/                  # skill 目录（可放置在任意位置）
├── SKILL.md                  # 本文档
├── scripts/
│   └── save_wechat.py        # 主脚本：抓取并保存文章
└── output/                   # 默认输出目录（自动创建，建议加入 .gitignore）
    └── YYYY-MM-DD_文章标题.md
```

## 环境准备

### 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 验证安装

```bash
python wechat-url-to-markdown/scripts/save_wechat.py --check
```

## 使用方法

### 基本用法（输出到默认 output/ 目录）

```bash
python wechat-url-to-markdown/scripts/save_wechat.py "微信文章链接"
```

### 自定义输出目录

```bash
python wechat-url-to-markdown/scripts/save_wechat.py "微信文章链接" -o /path/to/output
```

### 示例

```bash
# 保存到默认目录（wechat-url-to-markdown/output/）
python wechat-url-to-markdown/scripts/save_wechat.py "https://mp.weixin.qq.com/s/xxxxx"

# 保存到自定义目录
python wechat-url-to-markdown/scripts/save_wechat.py "https://mp.weixin.qq.com/s/xxxxx" -o ~/Desktop/articles

# 被其他 skill 调用时指定目录（如 wechat-to-xiaohongshu）
python wechat-url-to-markdown/scripts/save_wechat.py "$URL" -o "$OUTPUT_DIR"
```

## 输出目录

| 优先级 | 方式 | 说明 |
|--------|------|------|
| 1 | `-o /path/to/dir` | 指定输出目录 |
| 2 | 默认 | skill 内部的 `output/` 子目录 |

## 输出格式

保存的 Markdown 文件包含以下元数据：

```yaml
---
title: "文章标题"
author: "公众号名称"
date: "2026-01-28"
source: "原文链接"
---
```

文件名格式：`YYYY-MM-DD_文章标题.md`

## 功能特性

- ✓ 自动提取文章标题、作者、发布时间
- ✓ 保留原文格式（标题、列表、加粗、斜体等）
- ✓ 图片链接转换（保留微信图片 CDN 链接）
- ✓ 生成包含元数据的 YAML Front Matter
- ✓ 自动清理文件名中的非法字符

## 注意事项

1. **网络要求**: 需要能够访问微信域名 `mp.weixin.qq.com`
2. **反爬机制**: 微信有反爬虫机制，请合理控制请求频率
3. **图片处理**: 图片保留微信 CDN 链接，不会下载到本地
4. **动态内容**: 部分动态加载的内容可能无法完全抓取
5. **版权说明**: 请尊重原作者版权，仅供个人学习使用

## 故障排除

### 无法抓取内容

- 确保文章链接可以公开访问（不是付费或私密文章）
- 检查网络连接是否正常
- 尝试增加等待时间（修改脚本中的 `await asyncio.sleep(2)`）

### 中文乱码

文件使用 UTF-8 编码保存，如遇到乱码请使用支持 UTF-8 的编辑器打开。

### 依赖问题

```bash
pip install --upgrade pip
pip install playwright --force-reinstall
playwright install chromium
```
