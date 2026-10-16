#!/usr/bin/env python3
"""P0 修复的回归测试：重放 review 中实测到的 5 类异常返回。

覆盖 fetch_ai_news._normalize_categories 的防御逻辑，以及
format_news_markdown 的返回类型契约。

运行：python3 tests/test_classify_normalize.py
不依赖网络：直接调用纯函数，不触发任何模型请求。
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_ai_news as F

FAILURES = []


def check(label, condition, detail=""):
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}  {detail}")
        FAILURES.append(label)


def flatten(categories):
    """把分类结果压平成 {0-based 索引: [分类名, ...]}，便于查重复与越界。"""
    out = {}
    for cat, idxs in categories.items():
        for i in idxs:
            out.setdefault(i, []).append(cat)
    return out


print("=" * 66)
print("场景 1：模型返回 0-based 索引（原代码会产生 -1 回绕，重复末条+丢首条）")
# 契约是 1-based，因此 raw=0 是非法值；raw=1 合法地指向 news[0]。
# 关键回归点：不得出现 -1 回绕，也不得凭空占用列表末条 news[n-1]。
r, s = F._normalize_categories({"模型技术": [0]}, 3)
check("raw=0 未产生负索引", all(i >= 0 for i in flatten(r)), f"实际 {[i for i in flatten(r) if i < 0]}")
check("raw=0 未回绕占用末条 news[2]", 2 not in r["模型技术"], f"模型技术={r['模型技术']}")
check("末条由补漏填充而非回绕", r["其他"] == [0, 1, 2], f"其他={r['其他']}")
check("总数守恒 = 3", sum(len(v) for v in r.values()) == 3, f"实得 {sum(len(v) for v in r.values())}")
# 混合场景：0-based 返回后模型继续给 1,2,3
r2, s2 = F._normalize_categories({"模型技术": [0, 1, 2, 3]}, 6)
check("混合场景无负索引", all(i >= 0 for i in flatten(r2)))
check("混合场景总数守恒 = 6", sum(len(v) for v in r2.values()) == 6, f"实得 {sum(len(v) for v in r2.values())}")
check("混合场景 raw=0 被计为越界", s2["越界索引"] == 1, f"实得 {s2['越界索引']}")

print()
print("=" * 66)
print("场景 2：索引越界（原代码集合大小恰好=n，补漏不触发，后续 IndexError）")
r, s = F._normalize_categories({"模型技术": [1, 2, 3, 4, 5, 99]}, 6)
flat = flatten(r)
check("越界被拦截", 98 not in flat, f"泄漏索引 98")
check("总数守恒 = 6", sum(len(v) for v in r.values()) == 6, f"实得 {sum(len(v) for v in r.values())}")
check("告警统计到越界", s["越界索引"] == 1, f"实得 {s['越界索引']}")
check("缺失的第 6 条被补入兜底桶", 5 in r["其他"], f"其他={r['其他']}")

print()
print("=" * 66)
print("场景 3：索引重复（原代码重复项保留，总量 7≠6）")
r, s = F._normalize_categories({"模型技术": [1, 2, 3, 4, 5, 5]}, 6)
check("总数守恒 = 6", sum(len(v) for v in r.values()) == 6, f"实得 {sum(len(v) for v in r.values())}")
check("无重复归属", all(len(v) == 1 for v in flatten(r).values()))
check("告警统计到跨类重复", s["跨类重复"] == 1, f"实得 {s['跨类重复']}")

print()
print("=" * 66)
print("场景 4：模型自创分类名（原代码整类静默丢失）")
r, s = F._normalize_categories({"模型技术": [1, 2], "火星分类": [3, 4]}, 6)
check("未知分类未丢失条目", sum(len(v) for v in r.values()) == 6, f"实得 {sum(len(v) for v in r.values())}")
check("未知分类归入兜底桶", 2 in r["其他"] and 3 in r["其他"], f"其他={r['其他']}")
check("告警统计到未知分类", s["未知分类"] == 1, f"实得 {s['未知分类']}")

print()
print("=" * 66)
print("场景 5：跨类重复按 CATEGORY_ORDER 优先级去重（实测 #35 曾同时属算力+终端）")
r, s = F._normalize_categories({"智能终端": [1], "AI 算力": [1]}, 3)
# 「AI 算力」在 CATEGORY_ORDER 中靠前，应胜出
check("保留优先级更高的「AI 算力」", r["AI 算力"] == [0], f"算力={r['AI 算力']} 终端={r['智能终端']}")
check("总数守恒 = 3", sum(len(v) for v in r.values()) == 3, f"实得 {sum(len(v) for v in r.values())}")

print()
print("=" * 66)
print("场景 6：bool 索引（isinstance(True,int) 为 True，会穿过原校验）")
r, s = F._normalize_categories({"模型技术": [True, 2, 3, 4, 5, 6]}, 6)
check("bool 被判为非法索引", s["非法索引"] == 1, f"实得 {s['非法索引']}")
check("总数守恒 = 6", sum(len(v) for v in r.values()) == 6, f"实得 {sum(len(v) for v in r.values())}")

print()
print("=" * 66)
print("场景 7：非 list 的索引值（原代码会遍历字符串/数字）")
r, s = F._normalize_categories({"模型技术": "123", "模型技术 ": None, "Agent基建": [1]}, 4)
check("未崩溃且总数守恒 = 4", sum(len(v) for v in r.values()) == 4, f"实得 {sum(len(v) for v in r.values())}")

print()
print("=" * 66)
print("场景 8：format_news_markdown 返回类型契约（原代码早退返回 str 会致 TypeError）")
news = [{"title": f"标题{i}", "link": f"http://x/{i}", "biz_name": "号"} for i in range(3)]
empty_out = F.format_news_markdown(news, {c: [] for c in F.CATEGORY_ORDER}, "d", "d")
check("早退分支返回 tuple", isinstance(empty_out, tuple), f"实得 {type(empty_out).__name__}")
result, filtered = empty_out  # 模拟 get_news_summary 的无条件解包
check("可正常解包", isinstance(result, str) and isinstance(filtered, list))
check("提示语正确", "暂无AI相关资讯" in result)

full_out = F.format_news_markdown(news, {"模型技术": [0, 1, 2]}, "d", "d")
check("正常分支同样返回 tuple", isinstance(full_out, tuple))
result2, filtered2 = full_out
check("正常分支可解包", isinstance(result2, str) and isinstance(filtered2, list))

print()
print("=" * 66)
print("场景 9：全量条目落入兜底桶时不会崩溃（原先的沉睡崩溃点）")
all_fallback = {c: [] for c in F.CATEGORY_ORDER}
all_fallback["其他"] = [0, 1, 2]
res3, filt3 = F.format_news_markdown(news, all_fallback, "d", "d")
check("全兜底场景正常返回", isinstance(res3, str))
check("兜底条目进入 filtered 列表", len(filt3) == 3, f"实得 {len(filt3)}")

print()
print("=" * 66)
print("场景 10：CATEGORY_ORDER 与 CATEGORY_ICONS 键集一致")
check("图标覆盖全部分类", set(F.CATEGORY_ORDER) == set(F.CATEGORY_ICONS),
      f"差异 {set(F.CATEGORY_ORDER) ^ set(F.CATEGORY_ICONS)}")
check("CONTENT_CATEGORIES 不含兜底桶", F.FALLBACK_CATEGORY not in F.CONTENT_CATEGORIES)
check("CONTENT_CATEGORIES 长度为 9", len(F.CONTENT_CATEGORIES) == 9)

print()
print("=" * 66)
print("场景 11：分类名与 prompt 一致性（防止只改一处导致模型返回名对不上）")
# 分类名曾在「智能终端」与「AI硬件及终端」之间反复，本场景不锁死具体名称，
# 而是锁死「各处名称必须一致」这个不变量：改名时漏改 prompt，模型会返回
# 对不上的分类名，进而被 _normalize_categories 当作未知分类静默归入兜底桶。
_src = (Path(__file__).resolve().parent.parent / "scripts" / "fetch_ai_news.py").read_text(encoding="utf-8")
_prompt_block = _src[_src.index("**AI 算力**"):_src.index("请以 JSON 格式输出分类结果")]
_json_block = _src[_src.index("请以 JSON 格式输出分类结果"):_src.index("只输出 JSON，不要输出其他内容")]

check("当前分类名为「智能终端」", "智能终端" in F.CATEGORY_ORDER)
check("CATEGORY_ORDER 共 10 项", len(F.CATEGORY_ORDER) == 10)
# 生效结构之间必须同名
for _name in F.CATEGORY_ORDER:
    check(f"图标表含「{_name}」", _name in F.CATEGORY_ICONS)
for _name in F.CONTENT_CATEGORIES:
    check(f"CONTENT_CATEGORIES 含「{_name}」", _name in F.CONTENT_CATEGORIES)
# prompt 的定义块与 JSON 示例块必须与 CATEGORY_ORDER 逐一对应
for _name in F.CATEGORY_ORDER:
    check(f"prompt 定义含「{_name}」", f"**{_name}**" in _prompt_block)
for _name in F.CATEGORY_ORDER:
    check(f"prompt JSON 示例含「{_name}」", f'"{_name}"' in _json_block)
# 反向校验：prompt 里不得出现 CATEGORY_ORDER 之外的分类名
for _token in ["AI硬件及终端", "AI硬件"]:
    check(f"prompt 已无废弃名「{_token}」", _token not in _prompt_block and _token not in _json_block)

print()
print("=" * 66)
if FAILURES:
    print(f"❌ {len(FAILURES)} 项失败: {FAILURES}")
    sys.exit(1)
print("✅ 全部 P0 回归测试通过")
