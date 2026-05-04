#!/usr/bin/env python3
"""
AICoding 资讯周报生成工具

自动计算日期范围并生成周报，保存到 weekly/ 目录
"""
import os
import sys
import argparse
import subprocess
import re
from datetime import datetime, timedelta

# 脚本目录：aicoding-news-weekly/scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Skill 根目录：aicoding-news-weekly/
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
# 加载环境变量
try:
    from dotenv import load_dotenv
    env_file = os.path.join(SKILL_DIR, ".env")
    load_dotenv(env_file)
except ImportError:
    pass

# 默认输出目录：优先从 env 读取，如果没有则使用 skill 内部的 output/ 子目录
env_output_dir = os.getenv("OUTPUT_DIR")
DEFAULT_OUTPUT_DIR = os.path.expanduser(env_output_dir) if env_output_dir else os.path.join(SKILL_DIR, "output")

# 导入 API 客户端
try:
    from wechat_api_client import WeChatAPIClient, WeChatAPIError
    HAS_API_CLIENT = True
except ImportError:
    HAS_API_CLIENT = False

# 公众号封面图素材 ID（固定）
WECHAT_THUMB_MEDIA_ID = "qxQUqgd9fe1MaWRFFohGgvlKAcpIakKP0x4GUfNTl3JbVRj64hVIZi8V68JE1q53"


def get_week_range(target_date: datetime = None) -> tuple[str, str]:
    """
    获取周报的日期范围

    Args:
        target_date: 目标日期，默认为今天

    Returns:
        (start_date, end_date): 格式为 YYYY-MM-DD 的日期元组
        周报以当前自然周的周六为结束日期，上周日为开始日期（共7天）
    """
    if target_date is None:
        target_date = datetime.now()

    # 计算当前自然周的周六作为结束日期
    # weekday(): 周一=0, 周二=1, ..., 周六=5, 周日=6
    current_weekday = target_date.weekday()

    # 计算到本周六的天数差
    # 如果今天是周日(6)，则本周六是昨天，需要-1天
    # 如果今天是周一(0)，则本周六是+5天
    # 如果今天是周六(5)，则本周六是今天，+0天
    if current_weekday == 6:  # 周日
        days_to_saturday = -1
    else:
        days_to_saturday = 5 - current_weekday

    end_date = target_date + timedelta(days=days_to_saturday)
    # 开始日期为上周日（本周六往前推6天）
    start_date = end_date - timedelta(days=6)

    return (
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    )


def extract_title_and_content(markdown_text: str) -> tuple[str, str]:
    """提取标题并预处理 Markdown 内容

    Args:
        markdown_text: Markdown 文本

    Returns:
        (标题, 处理后的内容)
    """
    # 提取标题（第一个 # 开头的行）
    title_match = re.search(r'^#\s+(.+)$', markdown_text, re.MULTILINE)
    title = title_match.group(1) if title_match else "无标题"

    # 移除第一个 H1 标题
    if title_match:
        markdown_text = markdown_text.replace(title_match.group(0), '', 1)
        markdown_text = markdown_text.lstrip('\n')

    # 移除水平分割线
    markdown_text = re.sub(r'^\s*[-*_]{3,}\s*$', '', markdown_text, flags=re.MULTILINE)

    return title, markdown_text


def convert_to_html(markdown_text: str) -> str:
    """调用 md_to_html.py 转换 Markdown 为 HTML

    Args:
        markdown_text: Markdown 文本

    Returns:
        HTML 内容
    """
    # 使用 md_to_html 模块进行转换
    sys.path.insert(0, SCRIPT_DIR)
    from md_to_html import MarkdownToWechat

    converter = MarkdownToWechat()
    return converter.get_content_only(markdown_text)


def publish_to_wechat_api(
    title: str,
    content: str,
    author: str = "",
    digest: str = "",
    thumb_media_id: str = None
) -> str:
    """发布到微信公众号 API

    Args:
        title: 文章标题
        content: HTML 内容
        author: 作者
        digest: 摘要
        thumb_media_id: 封面图 media_id

    Returns:
        media_id: 草稿的 media_id
    """
    if not HAS_API_CLIENT:
        raise ImportError("缺少 wechat_api_client 模块")

    # 初始化 API 客户端
    try:
        client = WeChatAPIClient()
    except ValueError as e:
        print(f"❌ {e}")
        print("\n配置步骤：")
        print("1. 在项目根目录创建 .env 文件")
        print("2. 填入 WECHAT_APPID 和 WECHAT_APPSECRET")
        print("3. 在公众号后台设置 IP 白名单")
        raise

    # 处理 HTML 中的图片（下载并上传到微信）
    print("🔄 正在处理文章中的图片...")
    processed_content, img_count = client.process_html_images(content)

    # 创建草稿
    try:
        media_id = client.create_draft(
            title=title,
            content=processed_content,
            author=author,
            digest=digest,
            thumb_media_id=thumb_media_id
        )
        return media_id

    except WeChatAPIError as e:
        print(f"❌ 微信 API 错误: {e}")
        if e.errcode == 88000:
            print("\n可能的原因：")
            print("1. 你的公众号不是认证服务号")
            print("2. 未开通草稿箱和发布接口权限")
            print("3. IP 未加入白名单")
        raise


def publish_to_wechat(
    md_file: str,
    end_date: str = None,
    preview: bool = False,
    weixin: bool = False,
    draft_only: bool = False
) -> bool:
    """
    处理 markdown 文件并发布

    Args:
        md_file: markdown 文件路径
        end_date: 周报结束日期 (YYYY-MM-DD)，用于生成标题
        preview: 是否预览模式
        weixin: 是否直接发布到公众号
        draft_only: 是否仅创建草稿

    Returns:
        是否成功
    """
    # 读取 Markdown 文件
    with open(md_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # 提取标题并预处理内容
    title, processed_content = extract_title_and_content(markdown_text)

    # 如果是周报，使用固定标题格式
    if end_date:
        formatted_date = end_date.replace('-', '.')
        title = f"AI Coding资讯周报-{formatted_date}"

    if weixin:
        # 公众号 API 发布模式
        print(f"\n📱 调用公众号 API 发布工具...")
        print(f"📝 创建草稿: {title}")

        if not HAS_API_CLIENT:
            print("❌ 缺少 wechat_api_client 模块")
            return False

        # 转换 Markdown 为 HTML
        content_html = convert_to_html(processed_content)

        # 发布到微信
        try:
            media_id = publish_to_wechat_api(
                title=title,
                content=content_html,
                author="AICoding基地",
                digest="工具动态，编程实践，编程模型，业界观点",
                thumb_media_id=WECHAT_THUMB_MEDIA_ID
            )

            print(f"✅ 草稿创建成功！media_id: {media_id}")
            print(f"💡 请在公众号后台查看: https://mp.weixin.qq.com/ → 素材管理 → 草稿箱")
            print("\n✨ 完成！")

        except Exception as e:
            print(f"❌ 发布失败: {e}")
            return False

    else:
        # HTML 转换模式（调用 md_to_html.py）
        md_to_html_script = os.path.join(SCRIPT_DIR, "md_to_html.py")
        cmd = [sys.executable, md_to_html_script, md_file]

        if preview:
            cmd.append("--preview")

        print(f"\n📱 调用 HTML 转换工具{' (预览模式)' if preview else ''}...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"⚠️ 转换工具调用失败: {result.stderr}")
            return False

        print(result.stdout)

    return True


def generate_weekly_report(
    start_date: str,
    end_date: str,
    output_file: str = None,
    output_dir: str = None,
    publish: bool = False,
    preview: bool = False,
    weixin: bool = False,
    include_other: bool = False
) -> str:
    """
    生成周报

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        output_file: 输出文件路径（优先级最高，指定此项则忽略 output_dir）
        output_dir: 输出目录，默认为 skill 内部的 output/ 子目录
        publish: 是否调用公众号发布工具（HTML 转换）
        preview: 是否预览模式（生成公众号预览网页）
        weixin: 是否直接发布到公众号 API

    Returns:
        生成的文件路径
    """
    # 支持 ~ 目录展开
    if output_file:
        output_file = os.path.expanduser(output_file)
    if output_dir:
        output_dir = os.path.expanduser(output_dir)

    # 确定输出路径：--output > --output-dir > 默认目录
    if output_file is None:
        target_dir = output_dir if output_dir else DEFAULT_OUTPUT_DIR
        output_file = os.path.join(target_dir, f"{end_date}.md")
    else:
        target_dir = os.path.dirname(os.path.abspath(output_file))

    # 如果文件已存在，先删除
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"已删除旧文件: {output_file}")

    # 确保目录存在
    os.makedirs(target_dir, exist_ok=True)

    # 调用 feishu_news.py 生成周报
    feishu_script = os.path.join(SCRIPT_DIR, "feishu_news.py")
    cmd = [sys.executable, feishu_script, "--start", start_date, "--end", end_date]
    if include_other:
        cmd.append("--include-other")

    print(f"正在生成周报 ({start_date} 至 {end_date})...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 错误检查：退出码非零 或 stdout 为空都视为失败
    if result.returncode != 0:
        print(f"❌ 获取资讯失败（退出码: {result.returncode}）")
        if result.stderr:
            print(result.stderr.strip())
        return None

    content = result.stdout.strip()
    if not content:
        print(f"❌ 获取资讯失败：未返回任何内容")
        if result.stderr:
            print(result.stderr.strip())
        return None

    # 保存到文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✓ 周报已保存到: {output_file}")

    # 调用公众号发布工具
    if publish or preview or weixin:
        publish_to_wechat(output_file, end_date=end_date, preview=preview, weixin=weixin, draft_only=True)

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='生成 AICoding 资讯周报',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成本周周报
  python generate_weekly.py

  # 生成指定日期的周报
  python generate_weekly.py --date 2026-01-15

  # 生成指定日期范围的周报
  python generate_weekly.py --start 2026-01-01 --end 2026-01-07

  # 生成周报并调用公众号发布工具（复制到剪贴板）
  python generate_weekly.py --publish

  # 生成周报并生成公众号预览网页
  python generate_weekly.py --preview

  # 生成周报后直接发布到公众号（创建草稿）
  python generate_weekly.py --weixin
        """
    )
    parser.add_argument('--date', type=str, help='目标日期 (YYYY-MM-DD)，默认为今天')
    parser.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, help='输出文件路径（优先级最高）')
    parser.add_argument('--output-dir', type=str, dest='output_dir',
                        help=f'输出目录（不指定则使用默认目录: {DEFAULT_OUTPUT_DIR}）')
    parser.add_argument('--publish', action='store_true', help='生成后调用公众号发布工具（HTML 转换）')
    parser.add_argument('--preview', action='store_true', help='生成公众号预览网页')
    parser.add_argument('--weixin', action='store_true', help='生成后直接发布到公众号 API（创建草稿）')
    parser.add_argument('--include-other', action='store_true', dest='include_other',
                        help='包含分类为"其他"的资讯（默认过滤掉）')

    args = parser.parse_args()

    # 确定日期范围
    if args.start and args.end:
        start_date, end_date = args.start, args.end
    elif args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d")
        start_date, end_date = get_week_range(target_date)
    else:
        start_date, end_date = get_week_range()

    print(f"📅 日期范围: {start_date} 至 {end_date}")

    # 生成周报（--output 优先，其次 --output-dir，最后默认目录）
    result = generate_weekly_report(
        start_date,
        end_date,
        output_file=args.output,
        output_dir=args.output_dir,
        publish=args.publish,
        preview=args.preview,
        weixin=args.weixin,
        include_other=args.include_other
    )

    if not result:
        sys.exit(1)

    print("\n✅ 周报生成完成!")


if __name__ == "__main__":
    main()
