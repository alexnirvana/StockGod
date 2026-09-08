import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from stock_god.db.models import ListeningProgress, iso_time, now
from stock_god.db.session import owner
from stock_god.i18n import LOCALE
from stock_god.learning.service import course_detail, LESSONS

ROOT = Path(__file__).resolve().parents[4] / 'content' / 'narration'


def catalog():
    try:
        return json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))['tracks']
    except (OSError, ValueError):
        raise HTTPException(503, '课程音频尚未准备好，文字讲解仍可使用。')


def track_for(track_id, locale, version=None):
    track = next((t for t in catalog() if t['id'] == track_id and t['locale'] == locale), None)
    if not track or (version is not None and track['version'] != version):
        raise HTTPException(404, '没有找到这个版本的讲解音频，请重新打开讲解。')
    return track


def progress_id(session, lesson_id, locale):
    return hashlib.sha256(f'{owner(session)}:{lesson_id}:{locale}'.encode()).hexdigest()


def bookmark(row, track):
    return {'position_ms': min(row.position_ms, track['duration_ms']) if row and row.audio_version == track['version'] else 0,
            'playback_rate': float(row.playback_rate) if row else 1,
            'revision': row.revision if row else 0}


def detail(session, track_id, locale=None, saved=False):
    track = track_for(track_id, locale or LOCALE.get())
    result = {k: track[k] for k in ('id', 'locale', 'version', 'duration_ms', 'sections')}
    result['url'] = f"/api/narration/{track['id']}/{track['locale']}/{track['version']}.mp3"
    if saved:
        row = session.get(ListeningProgress, progress_id(session, track['course_id'], track['locale']))
        result.update(course_id=track['course_id'], owner_id=owner(session), bookmark=bookmark(row, track))
    return result


class BookmarkBody(BaseModel):
    owner_id: str = Field(min_length=1, max_length=191)
    locale: Literal['zh-CN', 'en']
    version: str = Field(min_length=20, max_length=64)
    position_ms: int = Field(ge=0, strict=True)
    playback_rate: Literal[0.75, 1.0, 1.25, 1.5, 2.0]
    revision: int = Field(ge=0, strict=True)


def save(session, lesson_id, body):
    # An old page must not save its bookmark into a newly signed-in account.
    if body.owner_id != owner(session):
        raise HTTPException(403, '当前账号已切换，请重新打开讲解后继续收听。')
    course_detail(session, lesson_id)
    track = track_for('lesson-' + lesson_id, body.locale)
    if body.version != track['version']:
        raise HTTPException(409, '讲解音频已更新，请重新打开后继续收听。')
    if body.position_ms > track['duration_ms']:
        raise HTTPException(422, '收听位置超过音频时长。')
    identifier = progress_id(session, lesson_id, body.locale)
    row = session.get(ListeningProgress, identifier)
    if body.revision != (row.revision if row else 0):
        raise HTTPException(409, '另一个窗口已更新收听位置，请重新打开讲解后继续保存。')
    if not row:
        row = ListeningProgress(id=identifier, player_id=owner(session), lesson_id=lesson_id, locale=body.locale)
        session.add(row)
    row.audio_version, row.position_ms = track['version'], body.position_ms
    row.playback_rate, row.revision, row.updated_at = Decimal(str(body.playback_rate)), body.revision + 1, now()
    session.flush()
    return bookmark(row, track)


def history(session):
    rows = session.scalars(select(ListeningProgress).where(ListeningProgress.player_id == owner(session)).order_by(ListeningProgress.updated_at.desc())).all()
    lessons = {l['id']: l for l in LESSONS}
    result = []
    for row in rows:
        if row.lesson_id not in lessons:
            continue
        track = track_for('lesson-' + row.lesson_id, row.locale)
        result.append({'lesson_id': row.lesson_id, 'title': lessons[row.lesson_id]['title'], 'locale': row.locale,
                       **bookmark(row, track), 'duration_ms': track['duration_ms'], 'updated_at': iso_time(row.updated_at)})
    return result
