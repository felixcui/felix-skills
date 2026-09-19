"""Behavior checks using isolated temporary inputs; no network or cloud services."""
import contextlib
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
import pipeline


def plan():
    return {'title':'主题','coverTitle':'核心框架','framework':['选题','脚本','画面'],
            'voice':{'method':'local-test-input','name':'test'},
            'scenes':[{'heading':'标题','points':['重点'],'segments':['这是一条测试口播。'],'visual':'卡片','source':'原文','transition':'淡入'}],
            'publish':{'title':'标题','body':'正文','tags':['测试']}}


class Behavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.article = self.root/'articles'/"含 空格与'符号.md"
        self.article.parent.mkdir()
        self.article.write_text('原文不应更改',encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def allocate(self):
        result=io.StringIO()
        with contextlib.redirect_stdout(result): pipeline.init(self.article)
        return Path(json.loads(result.getvalue())['output'])

    def test_sibling_path_and_versions_preserve_source(self):
        first=self.allocate()
        self.assertEqual(first,self.root/'video'/self.article.stem)
        (first/'video.mp4').write_bytes(b'existing')
        second=self.allocate()
        self.assertEqual(second,first/'v002')
        self.assertEqual((first/'video.mp4').read_bytes(),b'existing')
        self.assertEqual(self.article.read_text(),'原文不应更改')

    def test_default_edge_voice_and_rate(self):
        p = plan()
        del p['voice']
        pipeline.validate_plan(p)
        self.assertEqual(p['voice'], {'method':'edge-tts','name':'zh-CN-YunxiNeural','rate':'+10%'})

    def test_caption_wrapping_and_srt_rounding(self):
        for n in range(1,33):
            parts=pipeline.wrap('字'*n).splitlines()
            self.assertLessEqual(len(parts),2)
            self.assertTrue(all(len(x)<=16 for x in parts))
            self.assertEqual(''.join(parts),'字'*n)
        self.assertEqual(pipeline.stamp(59999.8),'00:01:00,000')

    def test_missing_audio_keeps_text_without_fake_narration(self):
        out=self.allocate()
        pipeline.write_json(out/'plan.json',plan())
        with self.assertRaisesRegex(ValueError,'缺少真实语音'):
            pipeline.build(out,self.root/'missing')
        self.assertTrue((out/'voiceover.md').exists())
        self.assertTrue((out/'publish-copy.md').exists())
        self.assertFalse((out/'narration.wav').exists())

    def test_silence_rejected_without_fake_narration(self):
        out=self.allocate()
        pipeline.write_json(out/'plan.json',plan())
        audio=self.root/'audio'; audio.mkdir()
        with wave.open(str(audio/'000.wav'),'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(48000)
            f.writeframes(b'\0\0'*48000)
        with self.assertRaisesRegex(ValueError,'静音'):
            pipeline.build(out,audio)
        self.assertFalse((out/'narration.wav').exists())


if __name__=='__main__': unittest.main()
