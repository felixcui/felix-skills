#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 转微信公众号 HTML 工具

功能：
1. 将 Markdown 文件转换为带公众号样式的 HTML
2. 支持代码高亮
3. 可复制到剪贴板或保存为 HTML 文件
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import markdown
    from markdown.extensions import codehilite, fenced_code, tables, toc
    from pygments.formatters import HtmlFormatter
except ImportError:
    print("缺少必要的依赖包，请先安装：")
    print("pip install markdown pygments")
    sys.exit(1)

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False


# 公众号样式 CSS
WECHAT_CSS = """
<style>
/* 全局字体统一设置 */
*, *::before, *::after {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

/* 公众号样式 */
body {
    font-size: 16px;
    line-height: 1.8;
    color: #333;
    max-width: 100%;
    margin: 0 auto;
    padding: 20px;
}

/* 标题样式 */
h1 {
    font-size: 22px;
    font-weight: bold;
    color: #000;
    margin: 24px 0 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #3f51b5;
}

h2 {
    font-size: 19px;
    font-weight: bold;
    color: #000;
    margin: 20px 0 10px;
    padding-left: 8px;
    border-left: 3px solid #3f51b5;
}

h3 {
    font-size: 17px;
    font-weight: bold;
    color: #333;
    margin: 16px 0 8px;
}

h4 {
    font-size: 15px;
    font-weight: bold;
    color: #555;
    margin: 14px 0 6px;
}

/* 移动端适配 - 更紧凑的标题 */
@media screen and (max-width: 480px) {
    h1 {
        font-size: 20px;
        margin: 20px 0 10px;
        padding-bottom: 6px;
    }

    h2 {
        font-size: 17px;
        margin: 16px 0 8px;
        padding-left: 6px;
    }

    h3 {
        font-size: 15px;
        margin: 14px 0 6px;
    }

    h4 {
        font-size: 14px;
        margin: 12px 0 4px;
    }
}

/* 段落样式 */
p {
    margin: 10px 0;
    text-align: justify;
    word-wrap: break-word;
}

/* 链接样式 */
a {
    color: #3f51b5;
    text-decoration: none;
}

a:hover {
    color: #303f9f;
}

/* 列表样式 */
ul, ol {
    margin: 10px 0;
    padding-left: 30px;
}

li {
    margin: 5px 0;
    line-height: 1.8;
}

/* 引用样式 */
blockquote {
    margin: 15px 0;
    padding: 15px 20px;
    border-left: 4px solid #42a5f5;
    background-color: #e3f2fd;
    color: #555;
    border-radius: 4px;
}

blockquote p {
    margin: 0;
}

/* 代码样式 */
code, code *, pre, pre * {
    font-family: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace !important;
    font-size: 14px;
    padding: 2px 6px;
    margin: 0 2px;
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 3px;
    color: #e91e63;
}

/* 代码块样式 */
pre {
    margin: 15px 0;
    padding: 15px;
    background-color: #282c34;
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.6;
}

pre code {
    display: block;
    padding: 0;
    margin: 0;
    background-color: transparent;
    border: none;
    color: #ffffff;
    font-size: 14px;
}

/* Pygments 代码高亮样式 (Monokai 风格) */
.codehilite { background: #272822; color: #ffffff; }
.codehilite .hll { background-color: #49483e }
.codehilite .c { color: #75715e } /* Comment */
.codehilite .k { color: #66d9ef } /* Keyword */
.codehilite .l { color: #ae81ff } /* Literal */
.codehilite .n { color: #ffffff } /* Name */
.codehilite .o { color: #f92672 } /* Operator */
.codehilite .p { color: #ffffff } /* Punctuation */
.codehilite .cm { color: #75715e } /* Comment.Multiline */
.codehilite .cp { color: #75715e } /* Comment.Preproc */
.codehilite .c1 { color: #75715e } /* Comment.Single */
.codehilite .cs { color: #75715e } /* Comment.Special */
.codehilite .kc { color: #66d9ef } /* Keyword.Constant */
.codehilite .kd { color: #66d9ef } /* Keyword.Declaration */
.codehilite .kn { color: #f92672 } /* Keyword.Namespace */
.codehilite .kp { color: #66d9ef } /* Keyword.Pseudo */
.codehilite .kr { color: #66d9ef } /* Keyword.Reserved */
.codehilite .kt { color: #66d9ef } /* Keyword.Type */
.codehilite .ld { color: #e6db74 } /* Literal.Date */
.codehilite .m { color: #ae81ff } /* Literal.Number */
.codehilite .s { color: #e6db74 } /* Literal.String */
.codehilite .na { color: #a6e22e } /* Name.Attribute */
.codehilite .nb { color: #ffffff } /* Name.Builtin */
.codehilite .nc { color: #a6e22e } /* Name.Class */
.codehilite .no { color: #66d9ef } /* Name.Constant */
.codehilite .nd { color: #a6e22e } /* Name.Decorator */
.codehilite .ni { color: #ffffff } /* Name.Entity */
.codehilite .ne { color: #a6e22e } /* Name.Exception */
.codehilite .nf { color: #a6e22e } /* Name.Function */
.codehilite .nl { color: #ffffff } /* Name.Label */
.codehilite .nn { color: #ffffff } /* Name.Namespace */
.codehilite .nx { color: #a6e22e } /* Name.Other */
.codehilite .py { color: #ffffff } /* Name.Property */
.codehilite .nt { color: #f92672 } /* Name.Tag */
.codehilite .nv { color: #ffffff } /* Name.Variable */
.codehilite .ow { color: #f92672 } /* Operator.Word */
.codehilite .w { color: #ffffff } /* Text.Whitespace */
.codehilite .mf { color: #ae81ff } /* Literal.Number.Float */
.codehilite .mh { color: #ae81ff } /* Literal.Number.Hex */
.codehilite .mi { color: #ae81ff } /* Literal.Number.Integer */
.codehilite .mo { color: #ae81ff } /* Literal.Number.Oct */
.codehilite .sb { color: #e6db74 } /* Literal.String.Backtick */
.codehilite .sc { color: #e6db74 } /* Literal.String.Char */
.codehilite .sd { color: #e6db74 } /* Literal.String.Doc */
.codehilite .s2 { color: #e6db74 } /* Literal.String.Double */
.codehilite .se { color: #ae81ff } /* Literal.String.Escape */
.codehilite .sh { color: #e6db74 } /* Literal.String.Heredoc */
.codehilite .si { color: #e6db74 } /* Literal.String.Interpol */
.codehilite .sx { color: #e6db74 } /* Literal.String.Other */
.codehilite .sr { color: #e6db74 } /* Literal.String.Regex */
.codehilite .s1 { color: #e6db74 } /* Literal.String.Single */
.codehilite .ss { color: #e6db74 } /* Literal.String.Symbol */
.codehilite .bp { color: #ffffff } /* Name.Builtin.Pseudo */
.codehilite .vc { color: #ffffff } /* Name.Variable.Class */
.codehilite .vg { color: #ffffff } /* Name.Variable.Global */
.codehilite .vi { color: #ffffff } /* Name.Variable.Instance */
.codehilite .il { color: #ae81ff } /* Literal.Number.Integer.Long */

/* 图片样式 */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 15px auto;
    border-radius: 4px;
}

/* 表格样式 */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 14px;
}

table th {
    background-color: #7986CB;
    color: white;
    padding: 12px 8px;
    text-align: left;
    font-weight: bold;
    border: 1px solid #ddd;
}

table td {
    padding: 10px;
    border: 1px solid #ddd;
}

table tr:nth-child(even) {
    background-color: #f9f9f9;
}

table tr:hover {
    background-color: #f5f5f5;
}

/* 水平分割线 */
hr {
    margin: 25px 0;
    border: none;
    border-top: 2px solid #e0e0e0;
}

/* 强调样式 */
strong, b {
    font-weight: bold;
    color: #000;
}

em, i {
    font-style: italic;
    color: #555;
}
</style>
"""


class MarkdownToWechat:
    """Markdown 转微信公众号 HTML 转换器"""

    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                'fenced_code',
                'codehilite',
                'tables',
                'toc',
                'nl2br',
                'sane_lists',
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'codehilite',
                    'linenums': False,
                    'guess_lang': False,
                }
            }
        )

    def convert_file(self, markdown_file: str) -> str:
        """转换 Markdown 文件为 HTML

        Args:
            markdown_file: Markdown 文件路径

        Returns:
            转换后的 HTML 字符串
        """
        if not os.path.exists(markdown_file):
            raise FileNotFoundError(f"文件不存在: {markdown_file}")

        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        return self.convert_text(markdown_content)

    def convert_text(self, markdown_text: str) -> str:
        """转换 Markdown 文本为 HTML

        Args:
            markdown_text: Markdown 文本

        Returns:
            转换后的 HTML 字符串
        """
        # 转换 Markdown 为 HTML
        html_content = self.md.convert(markdown_text)

        # 重置转换器状态（为下次转换做准备）
        self.md.reset()

        # 组合完整 HTML
        full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>微信公众号文章</title>
    {WECHAT_CSS}
</head>
<body>
{html_content}
</body>
</html>
"""
        return full_html

    def get_content_only(self, markdown_text: str) -> str:
        """仅转换 Markdown 内容，不包含完整 HTML 结构

        用于 API 发布，只返回 body 内容（不含 html/head/body 标签）。
        微信公众号不支持 <style> 块，因此将主要样式内联到各标签的 style 属性。

        Args:
            markdown_text: Markdown 文本

        Returns:
            转换后的带内联样式的 HTML 内容
        """
        html_content = self.md.convert(markdown_text)
        self.md.reset()
        # 将 CSS 样式内联，使公众号显示效果与本地预览一致
        html_content = self._apply_inline_styles(html_content)
        return html_content

    def _apply_inline_styles(self, html: str) -> str:
        """将主要 CSS 规则内联到对应 HTML 标签的 style 属性

        微信公众号会剥离 <style> 标签，所有样式须通过内联 style="" 属性传递。
        样式与 WECHAT_CSS 中的定义保持一致。
        """
        # 各标签对应的内联样式（与 WECHAT_CSS 保持一致）
        TAG_STYLES = {
            'h2': (
                'font-size:19px;font-weight:bold;color:#000;'
                'margin:20px 0 10px;padding-left:8px;border-left:3px solid #3f51b5;'
            ),
            'h3': 'font-size:17px;font-weight:bold;color:#333;margin:16px 0 8px;',
            'h4': 'font-size:15px;font-weight:bold;color:#555;margin:14px 0 6px;',
            'p':  'margin:10px 0;text-align:justify;word-wrap:break-word;',
            'a':  'color:#3f51b5;text-decoration:none;',
            'ul': 'margin:10px 0;padding-left:30px;',
            'ol': 'margin:10px 0;padding-left:30px;',
            'li': 'margin:5px 0;line-height:1.8;',
            'blockquote': (
                'margin:15px 0;padding:15px 20px;'
                'border-left:4px solid #42a5f5;background-color:#e3f2fd;'
                'color:#555;border-radius:4px;'
            ),
            'strong': 'font-weight:bold;color:#000;',
            'em':     'font-style:italic;color:#555;',
            'img': (
                'max-width:100%;height:auto;'
                'display:block;margin:15px auto;border-radius:4px;'
            ),
            'hr': 'margin:25px 0;border:none;border-top:2px solid #e0e0e0;',
        }

        for tag, style in TAG_STYLES.items():
            def _replacer(m, _style=style):
                """在开标签中追加 style 属性"""
                full = m.group(0)
                # 如果标签内已有 style 属性，追加；否则新增
                existing = re.search(r'\bstyle="([^"]*)"', full)
                if existing:
                    merged = existing.group(1).rstrip(';') + ';' + _style
                    return full[:existing.start(1)] + merged + full[existing.end(1):]
                # 在 > 或 /> 前插入
                return re.sub(r'(\s*/?>\s*)$', f' style="{_style}"\\1', full, count=1)

            html = re.sub(
                rf'<{tag}(?:\s[^>]*)?>',
                _replacer,
                html,
                flags=re.IGNORECASE,
            )

        return html


def save_html(html: str, output_file: str):
    """保存 HTML 到文件

    Args:
        html: HTML 内容
        output_file: 输出文件路径
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ HTML 已保存到: {output_file}")


def copy_to_clipboard(html: str):
    """复制 HTML 到剪贴板

    Args:
        html: HTML 内容
    """
    if not HAS_CLIPBOARD:
        print("⚠️  未安装 pyperclip，无法复制到剪贴板")
        print("提示: pip install pyperclip")
        return

    try:
        pyperclip.copy(html)
        print("✅ HTML 已复制到剪贴板！")
        print("💡 现在可以直接粘贴到公众号编辑器")
    except Exception as e:
        print(f"❌ 复制失败: {e}")


def preprocess_markdown(markdown_text: str) -> tuple[str, Optional[str]]:
    """预处理 Markdown 文本

    1. 提取标题（第一个 # 开头的行）
    2. 移除第一个 H1 标题
    3. 移除水平分割线

    Args:
        markdown_text: Markdown 文本

    Returns:
        (处理后的文本, 标题)
    """
    # 提取标题（第一个 # 开头的行）
    title_match = re.search(r'^#\s+(.+)$', markdown_text, re.MULTILINE)
    title = title_match.group(1) if title_match else None

    # 移除第一个 H1 标题
    if title_match:
        markdown_text = markdown_text.replace(title_match.group(0), '', 1)
        markdown_text = markdown_text.lstrip('\n')

    # 移除水平分割线（--- 或 *** 或 ___）
    markdown_text = re.sub(r'^\s*[-*_]{3,}\s*$', '', markdown_text, flags=re.MULTILINE)

    return markdown_text, title


def main():
    parser = argparse.ArgumentParser(
        description='将 Markdown 文件转换为微信公众号 HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 转换并复制到剪贴板
  python md_to_html.py article.md

  # 转换并保存为 HTML 文件
  python md_to_html.py article.md -o output.html

  # 预览模式（保存为临时 HTML 并打开浏览器）
  python md_to_html.py article.md --preview
        """
    )

    parser.add_argument(
        'markdown_file',
        help='Markdown 文件路径'
    )

    parser.add_argument(
        '-o', '--output',
        help='输出 HTML 文件路径（不指定则只复制到剪贴板）'
    )

    parser.add_argument(
        '--preview',
        action='store_true',
        help='预览模式：生成 HTML 并在浏览器中打开'
    )

    parser.add_argument(
        '--no-clipboard',
        action='store_true',
        help='不复制到剪贴板'
    )

    args = parser.parse_args()

    # 转换 Markdown
    converter = MarkdownToWechat()

    try:
        print(f"📄 正在转换: {args.markdown_file}")

        # 读取文件
        with open(args.markdown_file, 'r', encoding='utf-8') as f:
            markdown_text = f.read()

        # 预处理：移除标题和分割线
        markdown_text, title = preprocess_markdown(markdown_text)

        html = converter.convert_text(markdown_text)

        # 保存到文件
        if args.output:
            save_html(html, args.output)

        # 预览模式
        if args.preview:
            import webbrowser

            if args.output:
                # 已有 -o 输出文件，直接用它打开浏览器，无需临时文件
                preview_path = os.path.abspath(args.output)
            else:
                # 没有指定输出文件时，才创建临时文件
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.html',
                    delete=False,
                    encoding='utf-8'
                )
                temp_file.write(html)
                temp_file.close()
                preview_path = temp_file.name

            print(f"🌐 预览文件: {preview_path}")
            webbrowser.open(f'file://{preview_path}')

        # 复制到剪贴板
        if not args.no_clipboard:
            copy_to_clipboard(html)

        print("\n✨ 转换完成！")

    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
