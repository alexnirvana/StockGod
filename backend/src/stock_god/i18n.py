"""Translate presentation fields only; stored records and user text stay canonical."""
import json
import re
from contextvars import ContextVar
from pathlib import Path
from fastapi.responses import JSONResponse

CONTENT = Path(__file__).resolve().parents[3] / 'content'
MESSAGES = json.loads((CONTENT / 'locales' / 'en.json').read_text(encoding='utf-8'))
LOCALE = ContextVar('response_locale', default='zh-CN')
PATH = ContextVar('response_path', default='')
FIELDS = {'title', 'short_title', 'goal', 'practice', 'badge', 'prompt', 'options', 'explanation',
          'requirements', 'message', 'reason', 'data_label', 'notes', 'commission_note', 'detail', 'source', 'answer', 'error', 'msg', 'scope', 'kind'}


def negotiate(header):
    candidates = []
    for part in (header or '').split(','):
        bits = part.strip().split(';')
        try:
            quality = next((float(b.strip()[2:]) for b in bits[1:] if b.strip().startswith('q=')), 1)
        except ValueError:
            continue
        if quality > 0:
            candidates.append((quality, bits[0].lower()))
    for _, language in sorted(candidates, key=lambda entry: -entry[0]):
        if language == 'en' or language.startswith('en-'):
            return 'en'
        if language == 'zh' or language.startswith('zh-'):
            return 'zh-CN'
    return 'zh-CN'


def translate(text):
    if LOCALE.get() != 'en' or not isinstance(text, str):
        return text
    if text in MESSAGES:
        return MESSAGES[text]
    if text.startswith('Value error, '):
        return translate(text[13:])
    match = re.fullmatch(r'限价超出下一教学日的允许范围 (.+)–(.+) 元，请调整价格。', text)
    if match:
        return f'Limit price must be between CNY {match[1]} and {match[2]} for the next teaching day.'
    match = re.fullmatch(r'日线估算成交：按下一教学日开盘参考价 (.+) 元成交，费用 (.+) 元。无法还原真实排队与盘中路径。', text)
    if match:
        return f'Estimated daily execution at the next teaching open: CNY {match[1]}, fees CNY {match[2]}. Real order queues and intraday paths are not reproduced.'
    # Canonical messages sometimes join independently versioned explanations.
    parts = re.split(r'(?<=。)', text)
    if len(parts) > 1:
        return ' '.join(MESSAGES.get(p.strip(), p.strip()) for p in parts if p.strip()).strip()
    return text


def localize(value, field=''):
    if isinstance(value, dict):
        result = {k: localize(v, k) for k, v in value.items()}
        if 'symbol' in value and 'name' in value:
            result['name'] = translate(value['name'])
        if LOCALE.get() == 'en' and 'body' in value and value.get('id') in ('account', 'orders', 'market', 'risk', 'strategy'):
            result['body'] = (CONTENT / 'courses' / 'en' / (value['id'] + '.md')).read_text(encoding='utf-8')
        return result
    if isinstance(value, list):
        return [localize(v, field) for v in value]
    return translate(value) if field in FIELDS else value


class LocalizedJSONResponse(JSONResponse):
    def render(self, content):
        return super().render(content if PATH.get() == '/api/export' else localize(content))
