#!/usr/bin/env python3
"""热点提示词回归验证（改动 summarize_hot_topics_with_ai 后必跑）。

跑两轮：A 纯真实 feed；B 真实 feed + 注入 4 条活动/招募标题（模拟活动类标题条数最多、
最容易把规则压过去的情况）。断言三类问题：
  1. 热点出现活动/招募类词（嘉年华/报名/沙龙/招生/大会/训练营…）
  2. 热点出现报道腔元叙述（多篇文章报道/多篇报道/集中报道/篇数…）
  3. 热点不是一句话（含冒号的两截式）

用法: python3 scripts/verify_hot_topics.py   # 退出码 1 = 有失败项，需改提示词
注意: 会真实调用分类/热点模型两次，需要 .env 中已配置模型。
"""
import importlib.util
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parent / 'fetch_ai_news.py'
spec = importlib.util.spec_from_file_location('fan', SRC)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

ACTIVITY_KW = ['嘉年华', '报名', '沙龙', '征集', '招聘', '招生', '训练营', '比赛', '大会', '峰会']
META_KW = ['多篇文章', '多篇报道', '集中报道', '篇文章', '篇数']

INJECT = [
    '海淀公园 AI 嘉年华：可触可玩的 AI 体验，免费报名进行中',
    'ACC 2026 大会报名启动，早鸟票限时开售',
    'AI 嘉年华现场回顾：海淀公园三天活动直击',
    '某大模型训练营第 3 期招生，限额 50 人',
]

fails = []


def check(tag, topics):
    text = ' '.join(t['topic'] for t in topics)
    for kw in ACTIVITY_KW:
        if kw in text:
            fails.append(f'{tag}: 热点出现活动/招募词「{kw}」→ {text}')
    for kw in META_KW:
        if kw in text:
            fails.append(f'{tag}: 出现报道腔「{kw}」→ {text}')
    for t in topics:
        if '：' in t['topic'] or ':' in t['topic']:
            fails.append(f"{tag}: 两截式（含冒号）→ {t['topic']}")
    print(f'--- {tag}: {len(topics)} 条')
    for t in topics:
        print('  ·', t['topic'])


real = m.get_raw_news(days=1)
print(f'真实 feed {len(real)} 条')
check('A 纯真实 feed', m.summarize_hot_topics_with_ai(real))
injected = real[:12] + [
    {'title': t, 'link': 'https://example.com/x', 'biz_name': '测试'} for t in INJECT
]
check('B 注入活动标题', m.summarize_hot_topics_with_ai(injected))

if fails:
    print('\n❌ 失败项:')
    for f in fails:
        print(' -', f)
    sys.exit(1)
print('\n✅ 全部断言通过')
