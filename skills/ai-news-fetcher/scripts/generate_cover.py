#!/usr/bin/env python3
"""
生成微信公众号文章封面图：深蓝渐变背景 + 白色标题居中
标准比例 900x383 (2.35:1)

用法：python3 generate_cover.py [--title "每日 AI 资讯"] [--output /tmp/cover.jpg]
"""

from PIL import Image, ImageDraw, ImageFont
import argparse
import os

FONT_PATH = '/System/Library/Fonts/STHeiti Medium.ttc'

def generate_cover(title='每日 AI 资讯', subtitle='DAILY AI NEWS', output='/tmp/ai_news_cover_daily.jpg'):
    W, H = 900, 383
    img = Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(img)

    # 深蓝渐变背景
    for y in range(H):
        r = int(10 + 20 * y / H)
        g = int(18 + 40 * y / H)
        b = int(62 + 78 * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # 柔和光晕
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([(-120, -80), (350, 300)], fill=(50, 90, 200, 25))
    glow_draw.ellipse([W-300, H-200, W+50, H+50], fill=(30, 60, 160, 20))
    img = Image.alpha_composite(img.convert('RGBA'), glow).convert('RGB')
    draw = ImageDraw.Draw(img)

    # 主标题
    font = ImageFont.truetype(FONT_PATH, 80)
    bbox = draw.textbbox((0, 0), title, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - tw) / 2, (H - th) / 2 - 8), title, fill=(255, 255, 255), font=font)

    # 底部装饰线
    line_y = int((H + th) / 2 + 30)
    draw.line([(W//2 - 50, line_y), (W//2 + 50, line_y)], fill=(80, 120, 200), width=2)

    # 英文副标题
    if subtitle:
        font_sm = ImageFont.truetype(FONT_PATH, 16)
        bbox2 = draw.textbbox((0, 0), subtitle, font=font_sm)
        tw2 = bbox2[2] - bbox2[0]
        draw.text(((W - tw2) / 2, line_y + 10), subtitle, fill=(100, 140, 210), font=font_sm)

    img.save(output, 'JPEG', quality=95)
    print(f'封面图已保存: {output} ({os.path.getsize(output)} bytes)')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='生成微信公众号封面图')
    parser.add_argument('--title', default='每日 AI 资讯', help='主标题')
    parser.add_argument('--subtitle', default='DAILY AI NEWS', help='英文副标题')
    parser.add_argument('--output', default='/tmp/ai_news_cover_daily.jpg', help='输出路径')
    args = parser.parse_args()
    generate_cover(args.title, args.subtitle, args.output)
