#!/usr/bin/env python3
"""Edge/system speech, sample-accurate captions and Remotion delivery helpers."""
import argparse
import asyncio
import importlib.util
from generate_voice import synthesize
import array
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def status(out, state, **kw):
    p = out / 'status.json'
    old = read_json(p) if p.exists() else {}
    write_json(p, {**old, 'state': state, **kw})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def preflight():
    result = {x: shutil.which(x) for x in ['python3', 'node', 'npm', 'ffmpeg', 'ffprobe', 'say']}
    result['edge_tts_installed'] = importlib.util.find_spec('edge_tts') is not None
    result['default_voice'] = {'method':'edge-tts','name':'zh-CN-YunxiNeural','rate':'+10%','requires_network':True}
    if result['say']:
        result['mandarin_voices'] = [x for x in run(['say', '-v', '?']).stdout.splitlines() if 'zh_CN' in x or 'zh_TW' in x]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def init(article):
    article = Path(article).expanduser().resolve(strict=True)
    require(article.is_file() and article.suffix.lower() in ['.md', '.markdown'], '需要 Markdown 文件')
    base = article.parent.parent / 'video' / article.stem
    base.parent.mkdir(parents=True, exist_ok=True)
    out = base
    for i in range(1, 10000):
        out = base if i == 1 else base / f'v{i:03}'
        try:
            out.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise ValueError('没有可用版本目录')
    status(out, 'draft', article=str(article), article_sha256=hashlib.sha256(article.read_bytes()).hexdigest())
    print(json.dumps({'output': str(out)}, ensure_ascii=False))


def validate_plan(p):
    for field, limit in [('title', 24), ('coverTitle', 24)]:
        require(isinstance(p.get(field), str) and 0 < len(p[field]) <= limit, f'{field} 须为 1—{limit} 字')
    require(3 <= len(p.get('framework', [])) <= 4, 'framework 必须 3—4 项')
    require(all(isinstance(s,str) and 0 < len(s) <= 16 for s in p['framework']), '封面框架每项 1—16 字')
    require(p.get('scenes'), '缺少分镜')
    for s in p['scenes']:
        require(0 < len(s['heading']) <= 20, '镜头标题须为 1—20 字')
        require(1 <= len(s['points']) <= 4 and all(0 < len(x) <= 22 for x in s['points']), '镜头 points 长度不合格')
        require(s.get('source') and s.get('visual') and s.get('transition'), '镜头缺少依据、画面说明或转场')
        require(s.get('segments'), '镜头没有口播')
        for text in s['segments']:
            require(isinstance(text,str) and 0 < len(text.replace('\n','')) <= 32, '口播短句须为 1—32 字')
            if '\n' in text:
                require(len(text.splitlines()) <= 2 and all(0 < len(x) <= 16 for x in text.splitlines()), '手动字幕每行最多 16 字，最多两行')
    if 'voice' not in p:
        p['voice'] = {'method':'edge-tts','name':'zh-CN-YunxiNeural','rate':'+10%'}
    if p['voice'].get('method') == 'edge-tts':
        p['voice'].setdefault('name','zh-CN-YunxiNeural')
        p['voice'].setdefault('rate','+10%')
        require(re.fullmatch(r'[+-]\d+%',p['voice']['rate']) is not None, 'Edge rate 应为 +10% 等百分比字符串')
    require(p.get('voice', {}).get('method') and p['voice'].get('name'), '记录实际配音方式及音色')
    pub = p['publish']
    require(pub.get('title') and pub.get('body') and isinstance(pub.get('tags'),list) and pub['tags'], '缺少共用发布文案/话题')


def wrap(text):
    if '\n' in text or len(text) <= 16:
        return text
    candidates = [i for i in range(max(1,len(text)-16),17) if text[i-1] in '，。！？；：、']
    at = candidates[-1] if candidates else min(16, math.ceil(len(text)/2))
    return text[:at] + '\n' + text[at:]


def stamp(ms):
    ms = round(ms)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def build(out, audio_dir=None):
    require(not (out/'remotion').exists(), '本次目录已构建；请 init 创建新版本后重试')
    p = read_json(out/'plan.json')
    validate_plan(p)
    article = Path(read_json(out/'status.json')['article'])
    flat = [t for s in p['scenes'] for t in s['segments']]
    (out/'voiceover.md').write_text('# '+p['title']+'\n\n'+'\n\n'.join(t.replace('\n','') for t in flat)+'\n', encoding='utf-8')
    pub = p['publish']
    (out/'publish-copy.md').write_text('# '+pub['title']+'\n\n'+pub['body']+'\n\n'+' '.join('#'+t.lstrip('#') for t in pub['tags'])+'\n', encoding='utf-8')
    (out/'storyboard.md').write_text('# 分镜（待配音生成时间轴）\n\n'+'\n\n'.join(f"## {s['heading']}\n{s['visual']}\n依据：{s['source']}\n转场：{s['transition']}\n" for s in p['scenes']),encoding='utf-8')
    project = out/'remotion'
    shutil.copytree(ROOT/'assets/remotion', project)
    public = project/'public'
    public.mkdir()
    voice = p['voice']
    write_json(out/'voice-config.json', voice)
    require(shutil.which('ffmpeg'), '缺少 FFmpeg')
    if not audio_dir and voice['method'] == 'edge-tts':
        require(importlib.util.find_spec('edge_tts') is not None, '当前 Python 未安装 edge-tts；使用已安装依赖的虚拟环境')
    elif not audio_dir:
        require(voice['method'] == 'macos-say' and shutil.which('say'), '没有可用内置引擎，请配置已有本地语音并使用 --audio-dir')
        listed = run(['say','-v','?']).stdout
        candidates = [line.split('zh_')[0].strip() for line in listed.splitlines() if 'zh_CN' in line or 'zh_TW' in line]
        require(voice['name'] in candidates, '指定普通话音色未安装')
        require(100 <= int(voice.get('rate',175)) <= 220, '语速超出正常试读范围 100—220')
    else:
        require(voice['method'] not in ['macos-say','edge-tts'], '--audio-dir 时请记录实际生成方式并使用非内置引擎名称')
    work = out/'speech-segments'
    work.mkdir()
    chunks, captions, samples = [], [], 0
    all_words = []
    for i, text in enumerate(flat):
        wav = work/f'{i:03}.wav'
        if audio_dir:
            src = Path(audio_dir)/f'{i:03}.wav'
            require(src.is_file(), f'缺少真实语音 {src}')
        elif voice['method'] == 'edge-tts':
            src = work/f'{i:03}.mp3'
            try:
                words = asyncio.run(synthesize(text.replace('\n',''),src,voice['name'],voice['rate']))
            except Exception as exc:
                raise ValueError(f'Edge 配音第 {i+1} 句失败：{exc}；不自动替换声音') from exc
            write_json(work/f'{i:03}.words.json',words)
            all_words.extend({**w,'startMs':w['startMs']+samples/48,'endMs':w['endMs']+samples/48,'segment':i} for w in words)
        else:
            src = work/f'{i:03}.aiff'
            txt = work/f'{i:03}.txt'
            txt.write_text(text.replace('\n',''), encoding='utf-8')
            run(['say','-v',voice['name'],'-r',str(voice.get('rate',175)),'-f',txt,'-o',src])
        run(['ffmpeg','-nostdin','-v','error','-i',src,'-ac','1','-ar','48000','-c:a','pcm_s16le',wav])
        with wave.open(str(wav),'rb') as f:
            raw = f.readframes(f.getnframes())
            n = len(raw)//2
        amp = array.array('h',raw)
        if sys.byteorder != 'little':
            amp.byteswap()
        rms = math.sqrt(sum(x*x for x in amp)/max(1,len(amp)))
        require(n > 4800 and rms > 20, f'第 {i+1} 句为空或近乎静音，停止交付')
        captions.append({'text':wrap(text),'startMs':samples/48,'endMs':(samples+n)/48,'timestampMs':None,'confidence':None})
        samples += n
        chunks.append(raw)
    narration = out/'narration.wav'
    with wave.open(str(narration),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(48000)
        for raw in chunks:
            f.writeframes(raw)
    shutil.copy2(narration, public/'narration.wav')
    write_json(out/'captions.json',captions)
    if all_words:
        write_json(out/'word-boundaries.json',all_words)
    (out/'subtitles.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['startMs'])} --> {stamp(c['endMs'])}\n{c['text']}" for i,c in enumerate(captions))+'\n',encoding='utf-8')
    scenes, cursor, rows = [], 0, ['# 分镜与时间轴\n']
    for i, s in enumerate(p['scenes']):
        start = captions[cursor]['startMs']
        cursor += len(s['segments'])
        end = captions[cursor-1]['endMs']
        image = None
        if s.get('image'):
            src = Path(unquote(s['image'])).expanduser()
            src = src if src.is_absolute() else article.parent/src
            require(src.is_file(), f'配图不存在：{src}')
            image = f'image-{i:03}{src.suffix.lower()}'
            shutil.copy2(src,public/image)
        scenes.append({**s,'image':image,'startFrame':math.ceil(start*30/1000),'endFrame':math.ceil(end*30/1000)})
        rows.append(f"## {i+1}. {s['heading']}（{start/1000:.3f}—{end/1000:.3f}s）\n\n口播：{''.join(s['segments'])}\n\n画面：{s['visual']}\n\n屏幕文字：{' / '.join(s['points'])}\n\n依据/素材：{s['source']} / {s.get('image') or '原创文字与图示'}\n\n转场：{s['transition']}\n")
    (out/'storyboard.md').write_text('\n'.join(rows),encoding='utf-8')
    duration = samples/48000
    write_json(project/'src/data.json',{**p,'scenes':scenes,'captions':captions,'durationInFrames':math.ceil(duration*30)})
    status(out,'prepared',duration=duration)
    print(json.dumps({'duration':duration,'output':str(out)},ensure_ascii=False))
    require(55 <= duration <= 65, f'实际配音 {duration:.2f}s，须改稿至 55—65s，再创建新版本生成')


def render(out, browser):
    d = read_json(out/'remotion/src/data.json')
    require(55 <= d['durationInFrames']/30 <= 65, '时长未达标，先改稿')
    require((out/'narration.wav').is_file(), '缺少真实配音')
    project = out/'remotion'
    cli = project/'node_modules/.bin/remotion'
    require(cli.exists(), '请在生成的 remotion 目录安装固定版本依赖')
    require(not (out/'video.mp4').exists() and not (out/'cover.png').exists(), '已有渲染产物，请使用新版本目录')
    extra = ['--browser-executable',browser] if browser else []
    for args in [ ['render','src/index.tsx','Video',str(out/'video.mp4'),'--codec=h264','--audio-codec=aac','--pixel-format=yuv420p','--concurrency=2'], ['still','src/index.tsx','Cover',str(out/'cover.png')] ]:
        proc = subprocess.run([str(cli),*args,'--overwrite=false',*extra],cwd=project)
        require(proc.returncode == 0, 'Remotion 渲染失败，检查日志；已保留候选文件')
    status(out,'needs_review',reason='待技术校验、画面检查和声音试听')


def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path]).stdout)


def verify(out):
    for name in ['video.mp4','voiceover.md','storyboard.md','cover.png','publish-copy.md','narration.wav','subtitles.srt','remotion/src/data.json','voice-config.json']:
        require((out/name).is_file() and (out/name).stat().st_size > 0, f'缺少产物 {name}')
    info = probe(out/'video.mp4')
    v = next(x for x in info['streams'] if x['codec_type']=='video')
    a = next(x for x in info['streams'] if x['codec_type']=='audio')
    seconds = float(info['format']['duration'])
    require((v['width'],v['height'],v['codec_name']) == (1080,1920,'h264') and v['pix_fmt'] in ['yuv420p','yuvj420p'], '画幅/编码错误')
    n,d = map(int,v['avg_frame_rate'].split('/'))
    require(n/d == 30 and 55 <= seconds <= 65, '帧率或时长错误')
    require(a['codec_name'] == 'aac','音轨须为 AAC')
    cover = probe(out/'cover.png')['streams'][0]
    require((cover['width'],cover['height']) == (1080,1920),'封面尺寸错误')
    captions = read_json(out/'captions.json')
    with wave.open(str(out/'narration.wav'),'rb') as f:
        audio_seconds = f.getnframes()/f.getframerate()
    require(abs(audio_seconds-seconds) < 0.15,'成片与配音时长不同')
    require(abs(captions[-1]['endMs']/1000-audio_seconds) < .001,'字幕时间轴与配音不一致')
    for i,c in enumerate(captions):
        require(c['startMs'] < c['endMs'] and (i==0 or abs(c['startMs']-captions[i-1]['endMs']) < .001),'字幕时间轴重叠/间断')
        require(len(c['text'].splitlines()) <= 2 and all(len(x)<=16 for x in c['text'].splitlines()),'字幕超过两行')
    run(['ffmpeg','-nostdin','-v','error','-i',out/'video.mp4','-f','null','-'])
    analysis = run(['ffmpeg','-nostdin','-hide_banner','-i',out/'video.mp4','-af','volumedetect','-vn','-f','null','-']).stderr
    match = re.search(r'mean_volume: ([-\w.]+) dB',analysis)
    require(match and float(match.group(1)) > -60,'成片音轨静音或音量过低')
    report = {'technical_checks':'passed','duration':seconds,'resolution':[1080,1920],'fps':30,'pixel_format':v['pix_fmt'],'audio_mean_db':float(match.group(1)),'visual_review':'pending','listening_review':'pending'}
    write_json(out/'validation.json',report)
    status(out,'needs_review',reason='技术校验通过，仍需画面检查和声音试听')
    print(json.dumps(report,ensure_ascii=False,indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command',required=True)
    subs.add_parser('preflight')
    subs.add_parser('init').add_argument('article')
    for cmd in ['build','render','verify']:
        p = subs.add_parser(cmd); p.add_argument('output')
        if cmd == 'build': p.add_argument('--audio-dir')
        if cmd == 'render': p.add_argument('--browser')
    a = parser.parse_args()
    out = Path(a.output).expanduser().resolve(strict=True) if hasattr(a,'output') else None
    try:
        if a.command == 'preflight': preflight()
        elif a.command == 'init': init(a.article)
        elif a.command == 'build': build(out,a.audio_dir)
        elif a.command == 'render': render(out,a.browser)
        elif a.command == 'verify': verify(out)
    except (ValueError, OSError, KeyError, StopIteration, subprocess.CalledProcessError) as e:
        message = str(e)
        if isinstance(e,subprocess.CalledProcessError): message += '\n'+(e.stderr or '')[-2000:]
        if out: status(out,'blocked',reason=message)
        print(message,file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
