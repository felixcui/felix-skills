# 改日报排版/热点口径后：验证 + 原地刷新草稿

改动 `fetch_ai_news.py` 的排版或热点提示词后按这两步收尾。**不要重跑 `publish_to_wechat.py --create-draft`**：当天草稿已存在时会多出一份。

## 0. 补跑前先确认当天有没有草稿

采集停更、cron 失败后补跑当天日报，先列草稿再决定跑不跑：

```python
import os, sys, datetime
sys.path.insert(0, os.path.expanduser('~/.hermes/skills/felix-skills/skills/aicoding-news-weekly/scripts'))
from dotenv import load_dotenv; load_dotenv('.env')          # 在 ai-news-fetcher 目录下执行
from wechat_api_client import WeChatAPIClient               # 类名是 WeChatAPIClient，不是 WeChatClient
c = WeChatAPIClient()
r = c._api_call('POST', 'draft/batchget', json={'offset': 0, 'count': 20, 'no_content': 1})
for it in r.get('item', []):
    n = it['content']['news_item'][0]
    print(datetime.datetime.fromtimestamp(it['update_time']).strftime('%m-%d %H:%M'), n['title'], it['media_id'][:16])
```

判据：列表里**没有** `AI 资讯日报-YYYY.MM.DD`（当天）才跑 `publish_to_wechat.py` 建草稿；已有就走下面的 `draft/update` 原地刷新。补跑完再 `batchget` 一次，确认首条 `update_time` 是今天、标题是当天日期——`publish_to_wechat.py` 的日志刷屏，别只靠它说「✅ 草稿创建成功」。

## 1. 先验证脚本产物（不要只读代码）

- 热点提示词类改动——import 脚本函数、用真实数据实跑：

  ```python
  import importlib.util, pathlib
  SRC = pathlib.Path('~/.hermes/skills/felix-skills/skills/ai-news-fetcher/scripts/fetch_ai_news.py').expanduser()
  spec = importlib.util.spec_from_file_location('fan', SRC); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
  news = m.get_raw_news(days=1)                      # 只读 RSS，无副作用
  topics = m.summarize_hot_topics_with_ai(news)
  md, _filtered = m.format_news_markdown(news, {'模型技术': [0, 1]}, '2026-01-01', '2026-01-02', 'feishu', topics)
  ```

  注意 `format_news_markdown` 返回 **tuple** `(markdown, filtered)`，直接当字符串写文件会报 `data must be str, not tuple`。
  断言禁用口吻（「多篇文章」等）计数为 0、含冒号的两截式条数为 0。

- 排版类改动——按发布路径单跑渲染器，再查 HTML：

  ```bash
  bun "$BAOYU_MARKDOWN_TO_HTML_DIR/scripts/main.ts" <md> --theme default   # stdout JSON 里的 htmlPath
  ```

  数 `<strong>`（用户口径下应为 0），热点条目 `<li>` 的 style 串应与分类条目**逐字一致**。

## 2. 原地更新草稿（`draft/update`）

- `POST /cgi-bin/draft/batchget`（`{"offset":0,"count":20,"no_content":0}`）按 `title` 找到目标草稿：`media_id` 在 **item 级**，标题/作者/摘要/封面在 `content.news_item[0]`。
- **`batchget` 不返回封面 `thumb_media_id`（返回空串）**：从 `publish_to_wechat.py` 里的 `DEFAULT_THUMB_MEDIA_ID` 取值补上，否则 update 会因封面非法失败。
- 正文用与发布脚本同一条路径渲染（`--theme default`）并只取 `<body>` 片段，保证除目标改动外与线上一致。
- payload → `POST /cgi-bin/draft/update`：

  ```json
  {"media_id": "<同值>", "index": 0, "articles": {"title": "...", "author": "...", "digest": "...",
    "content": "<html>", "content_source_url": "", "thumb_media_id": "<封面>",
    "need_open_comment": 1, "only_fans_can_comment": 0}}
  ```

  `update` 的 `articles` 是**对象**（不是数组），这点与 `draft/add` 不同。`errcode: 0` 即成功。
- 回读校验：再 `batchget` 一次，确认 ① `media_id` 未变（没新建草稿）、② `update_time` 已变、③ 结构计数（`<li>`/`<h3>`/`<a>`/`<code>`）与改前一致、④ 目标属性（如 `<strong>` 计数）已按预期变化。

## 为什么必须回读存稿

微信会改写内联样式：实测它把 h3 的 `font-size: calc(16px * 1.1)` **整条删掉**，其它属性保留。因此「本地浏览器渲染没问题」推不出「线上没问题」——只读本地 HTML 会把不存在的问题当成问题、把真实差异当成没问题。要在本地比对，就把 `batchget` 取回的存稿 HTML 片段包成完整页面，用 `getComputedStyle` 量 font-size / font-weight / color，比截图肉眼判断可靠。
