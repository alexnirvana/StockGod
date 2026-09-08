"""Prepare and package reproducible bilingual narration; no cloud service is used."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'content'
BUILD = ROOT / 'data' / 'narration-build'
OUTPUT = CONTENT / 'narration'
sys.path.insert(0, str(ROOT / 'backend' / 'src'))
from stock_god.learning.coach import ANSWERS


def plain(markdown):
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', markdown)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'^\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+)', '', text, flags=re.M)
    text = text.replace('**', '').replace('`', '')
    return re.sub(r'\n{2,}', '\n', text).strip()


def prepare():
    BUILD.mkdir(parents=True, exist_ok=True)
    messages = json.loads((CONTENT / 'locales/en.json').read_text(encoding='utf-8'))
    lessons = json.loads((CONTENT / 'courses/catalog.json').read_text(encoding='utf-8'))
    tracks = []
    for locale, voice in [('zh-CN', 'Microsoft Huihui Desktop'), ('en', 'Microsoft Zira Desktop')]:
        for lesson in lessons:
            path = CONTENT / 'courses' / ('en' if locale == 'en' else '') / (lesson['id'] + '.md')
            markdown = path.read_text(encoding='utf-8')
            blocks = re.split(r'(?=^## )', markdown, flags=re.M)
            sections = [{'title': plain(block.splitlines()[0]), 'text': plain(block)} for block in blocks if block.strip()]
            tracks.append({'id': 'lesson-' + lesson['id'], 'course_id': lesson['id'], 'locale': locale, 'voice': voice, 'sections': sections})
            text = ' '.join(messages[lesson[k]] if locale == 'en' else lesson[k] for k in ('goal', 'practice'))
            tracks.append({'id': 'coach-lesson-' + lesson['id'], 'course_id': lesson['id'], 'locale': locale, 'voice': voice, 'sections': [{'title': 'Explanation' if locale == 'en' else '讲解', 'text': text}]})
        for key, answer in ANSWERS.items():
            tracks.append({'id': 'coach-' + key, 'course_id': None, 'locale': locale, 'voice': voice, 'sections': [{'title': 'Explanation' if locale == 'en' else '讲解', 'text': messages[answer] if locale == 'en' else answer}]})
    for track in tracks:
        track['version'] = hashlib.sha256(json.dumps(track, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
        track['build_id'] = track['id'] + '-' + track['locale']
    (BUILD / 'plan.json').write_text(json.dumps(tracks, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Prepared {len(tracks)} narration tracks.')


def package():
    OUTPUT.mkdir(exist_ok=True)
    tracks = json.loads((BUILD / 'plan.json').read_text(encoding='utf-8'))
    manifest = {'format': 1, 'engine': 'Windows System.Speech', 'tracks': []}
    for track in tracks:
        merged = BUILD / (track['build_id'] + '.wav')
        elapsed = 0
        sections = []
        with wave.open(str(merged), 'wb') as out:
            for i, section in enumerate(track['sections']):
                with wave.open(str(BUILD / f"{track['build_id']}-{i}.wav"), 'rb') as source:
                    if i == 0:
                        out.setparams(source.getparams())
                    else:
                        assert source.getparams()[:3] == out.getparams()[:3]
                    sections.append({'title': section['title'], 'start_ms': round(elapsed * 1000)})
                    out.writeframes(source.readframes(source.getnframes()))
                    elapsed += source.getnframes() / source.getframerate()
                    silence = round(source.getframerate() * .3)
                    out.writeframes(bytes(silence * source.getsampwidth() * source.getnchannels()))
                    elapsed += silence / source.getframerate()
        filename = f"{track['build_id']}-{track['version']}.mp3"
        target = OUTPUT / filename
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(merged), '-af', 'loudnorm=I=-18:TP=-2:LRA=11', '-codec:a', 'libmp3lame', '-b:a', '64k', '-ar', '24000', str(target)], check=True)
        duration = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(target)], text=True).strip())
        manifest['tracks'].append({k: track[k] for k in ('id', 'course_id', 'locale', 'voice', 'version')} | {'file': filename, 'duration_ms': round(duration * 1000), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'sections': sections})
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Packaged {len(tracks)} MP3 files ({sum((OUTPUT / t["file"]).stat().st_size for t in manifest["tracks"]) / 1e6:.1f} MB).')


if __name__ == '__main__':
    {'prepare': prepare, 'package': package}[sys.argv[1]]()
