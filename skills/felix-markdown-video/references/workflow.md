# 数据约定与执行

## 配音环境与默认音色

使用随附的 `scripts/generate_voice.py`（默认语速已设为 +10%）：基于 [edge-tts](https://github.com/rany2/edge-tts) 的 `zh-CN-YunxiNeural`、`rate="+10%"`、`boundary="WordBoundary"`。这是联网服务，无需 API Key；先真实试读确认可用。

优先使用已安装 edge-tts 的 Python；否则在 Skill 内建立独立环境，不修改全局 Python：

```bash
python3 -m venv "$SKILL_DIR/.venv"
"$SKILL_DIR/.venv/bin/python" -m pip install -r "$SKILL_DIR/scripts/requirements.txt"
"$SKILL_DIR/.venv/bin/python" "$SKILL_DIR/scripts/generate_voice.py" --text "先选一个核心问题，再把文章讲清楚。" --output /tmp/voice-check-unique.mp3
```

下面命令的 `python3` 应替换为该环境的 Python。每次试读使用新的文件名；网络失败最多人工重试一次，不自动降级成另一个声音。

## 命令

```bash
python3 "$SKILL_DIR/scripts/pipeline.py" preflight
python3 "$SKILL_DIR/scripts/pipeline.py" init /absolute/path/articles/article.md
# 读取 init 返回的 output，向该目录写入 plan.json
python3 "$SKILL_DIR/scripts/pipeline.py" build /absolute/path/video/article
# 按实际输出时长修订；重跑请 init 分配新版本，不覆盖已生成内容
cd /absolute/path/video/article/remotion
npm ci
npm run studio -- --no-open
python3 "$SKILL_DIR/scripts/pipeline.py" render /absolute/path/video/article
python3 "$SKILL_DIR/scripts/pipeline.py" verify /absolute/path/video/article
```

可用 `render --browser /absolute/path/to/chrome` 指定已有 Chromium，避免自动下载。渲染命令固定 H.264、AAC、yuv420p；默认不覆盖。脚本的 `verify` 不会把状态标记 complete，实际图像/音频检查仍由执行者完成。

## plan.json

以下仅为字段示例，不是可交付的一分钟稿。必须基于输入文章写足内容。

```json
{
  "title": "文章核心主题",
  "coverTitle": "封面突出标题",
  "framework": ["关键问题", "解决步骤", "实际限制"],
  "voice": {"method": "edge-tts", "name": "zh-CN-YunxiNeural", "rate": "+10%", "note": "联网普通话男声，无需 API Key；需试听确认"},
  "scenes": [
    {"heading": "先明确问题", "points": ["核心关键词"], "visual": "标题加问题卡片", "source": "原文章第一节", "transition": "短淡入", "image": null,
     "segments": ["先说结论。", "这句话需要与你的文章一致。"]}
  ],
  "publish": {"title": "通用发布标题", "body": "忠于文章的一段简洁发布文案。", "tags": ["知识分享", "内容创作"]}
}
```

- 封面标题最多 24 个字符，framework 3—4 项、每项最多 16 个字符；镜头 heading 最多 20 字，points 1—4 项且每项最多 22 字。超长时改写，不裁切。
- 每条 `segments` 是一个自然语义短句、1—32 个字符；模板按最多每行 16 字显示为一/两行。优先在标点处断行，必要时直接在字符串中写 `\n` 指定断行，每行最多 16 字。声音合成时移除换行。
- `image` 可省略或为相对于原文章目录的图片路径；脚本解码 URL 字符、检查文件存在、复制至 public，以免重渲染依赖原路径。远程图片需助手先按授权下载且验证，再传入本地路径；脚本不会盲目请求远程地址。复杂 Markdown/Obsidian 链接由助手读取并解析。
- 默认 voice 为 Edge Yunxi；可省略 voice，脚本会填充默认值并记录至 voice-config.json。Edge rate 是 `+10%` 字符串。系统替代配置是 `{"method":"macos-say","name":"实际安装的完整音色名","rate":175}`，rate 是系统语速整数。改变内容来满足时长，不使用后期音频加速。
- build 失败不会删除文稿/工程；时长不合格会生成 timing 数据帮助改稿，但 render 会拒绝渲染。

## 已有其他离线引擎

用实际已配置的本地引擎逐条生成 `000.wav`、`001.wav`……（跨镜头连续编号），并提供 `build OUTPUT --audio-dir DIR`。voice.method 写明真实引擎名称，voice.name 写实际模型/音色，voice.note 说明选声与替代原因。脚本将统一转换为 48kHz 单声道 PCM，检查非静音，再拼接。文件必须和各 segments 一一对应，不可用录制静音来绕过缺失能力。脚本不能验证语音内容是否正确，必须试听/使用本地识别核对。此入口用于已有本地音频；联网 Edge 配音应直接使用内置 edge-tts 分支。

## 可重复渲染

项目固定 Remotion 各包为相同版本，保存 package-lock.json、public 中音频/图片、src/data.json 和源码。不要把指向外部 node_modules 的软链接当作项目依赖归档。渲染修复可写入新的候选文件或新版本目录；不覆盖之前交付的文件。

开发测试与已知验证边界见 [验证记录](validation.md)。

## 时间戳兼容

借鉴原脚本的音频流和 WordBoundary 采集，但不直接照搬按字符数消耗词边界的映射：数字、英文和缩写的规范化可能改变长度。当前按原有短句逐条合成，SRT 显示整句，保留服务返回的真实词边界供精细高亮使用。字幕不是逐字高亮。维持 55—65 秒验收范围，不沿用原脚本严格小于 60 秒的断言。
