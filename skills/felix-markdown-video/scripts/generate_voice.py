#!/usr/bin/env python3
"""Edge TTS synthesis with real WordBoundary metadata; requires internet."""
import argparse
import asyncio
import json
from pathlib import Path


async def synthesize(text, destination, voice='zh-CN-YunxiNeural', rate='+10%'):
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError('当前 Python 缺少 edge-tts，请用安装依赖的虚拟环境运行') from exc
    destination = Path(destination)
    if destination.exists():
        raise ValueError(f'拒绝覆盖已有音频：{destination}')
    partial = destination.with_suffix(destination.suffix + '.partial')
    words = []
    try:
        async def stream():
            comm = edge_tts.Communicate(text, voice, rate=rate, boundary='WordBoundary')
            with partial.open('xb') as f:
                async for chunk in comm.stream():
                    if chunk['type'] == 'audio':
                        f.write(chunk['data'])
                    elif chunk['type'] == 'WordBoundary':
                        words.append({'text':chunk['text'], 'startMs':chunk['offset']/10000,
                                      'endMs':(chunk['offset']+chunk['duration'])/10000,
                                      'timestampMs':None, 'confidence':None})
        await asyncio.wait_for(stream(), timeout=60)
        if not partial.stat().st_size or not words:
            raise RuntimeError('Edge 未返回音频或 WordBoundary，不能完成配音')
        partial.rename(destination)
        return words
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--text',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--voice',default='zh-CN-YunxiNeural')
    p.add_argument('--rate',default='+10%')
    a=p.parse_args()
    out=Path(a.output).expanduser().resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    words=asyncio.run(synthesize(a.text,out,a.voice,a.rate))
    out.with_suffix('.words.json').write_text(json.dumps(words,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'audio':str(out),'voice':a.voice,'rate':a.rate,'word_boundaries':len(words)},ensure_ascii=False))

if __name__=='__main__':
    main()
