"""Deterministic, versioned review schedule. Never changes course rewards."""
import json
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from stock_god.adapters.data import CONTENT
from stock_god.db.models import ReviewItem, ReviewAttempt, iso_time, now
from stock_god.db.session import owner

BANK = json.loads((CONTENT / 'questions' / 'reviews-v1.json').read_text(encoding='utf-8'))
INTERVAL_DAYS = (1, 3, 7)


def entries(session):
    return session.scalars(select(ReviewItem).where(ReviewItem.player_id == owner(session)).order_by(ReviewItem.updated_at, ReviewItem.id)).all()


def is_due(item, clock):
    return item.due_at is not None and datetime.fromisoformat(iso_time(item.due_at)) <= clock


def summary(session):
    items, clock = entries(session), now()
    future = [i.due_at for i in items if i.due_at and not is_due(i, clock)]
    return {'due': sum(is_due(i, clock) for i in items), 'scheduled': len(future),
            'mastered': sum(i.stage == 4 for i in items),
            'next_due_at': iso_time(min(future)) if future else None}


def record_mistakes(session, lesson_id, feedback):
    clock = now()
    for index, result in enumerate(feedback):
        if result['passed']:
            continue
        item = session.scalar(select(ReviewItem).where(ReviewItem.player_id == owner(session), ReviewItem.lesson_id == lesson_id,
            ReviewItem.question_index == index, ReviewItem.content_version == BANK['version']))
        if item is None:
            session.add(ReviewItem(id=str(uuid4()), player_id=owner(session), lesson_id=lesson_id,
                question_index=index, due_at=clock, updated_at=clock))
        else:
            item.stage, item.due_at, item.updated_at = 0, clock, clock
            item.mistakes += 1
            item.revision += 1
    session.flush()


def knowledge(item):
    if item.content_version != BANK['version'] or item.lesson_id not in BANK['lessons']:
        raise HTTPException(409, '这个知识点的复习内容暂不可用，请先重看课程讲解。')
    return BANK['lessons'][item.lesson_id][item.question_index]


def item_view(item, clock):
    concept = knowledge(item)
    variant = item.review_count % len(concept['variants'])
    question = concept['variants'][variant]
    return {'id': item.id, 'lesson_id': item.lesson_id, 'title': concept['title'],
        'stage': item.stage, 'mistakes': item.mistakes, 'review_count': item.review_count,
        'due': is_due(item, clock), 'due_at': iso_time(item.due_at) if item.due_at else None,
        'revision': item.revision, 'variant': variant, 'content_version': item.content_version,
        'question': {'prompt': question['prompt'], 'options': question['options']}}


def queue(session):
    clock = now()
    items = entries(session)
    items.sort(key=lambda i: (not is_due(i, clock), i.due_at is None, iso_time(i.due_at) if i.due_at else '', i.id))
    return {'summary': summary(session), 'items': [item_view(i, clock) for i in items]}


def answer(session, review_id, body):
    item = session.scalar(select(ReviewItem).where(ReviewItem.id == review_id, ReviewItem.player_id == owner(session)))
    if item is None:
        raise HTTPException(404, '没有找到这个复习项。')
    clock = now()
    view = item_view(item, clock)
    if body.revision != item.revision or body.variant != view['variant'] or body.content_version != item.content_version:
        raise HTTPException(409, '这道题的进度已经更新，请返回复习列表后重新打开。')
    if not view['due']:
        raise HTTPException(409, '这次复习已完成，请在下次到期时再来巩固。')
    q = knowledge(item)['variants'][body.variant]
    if body.answer >= len(q['options']):
        raise HTTPException(422, '请选择题目中的一个答案。')
    passed = body.answer == q['correct']
    item.stage = min(4, item.stage + 1) if passed else 0
    item.review_count += 1
    item.revision += 1
    item.mistakes += int(not passed)
    item.updated_at = clock
    item.due_at = (clock + timedelta(days=INTERVAL_DAYS[item.stage - 1]) if item.stage else clock) if item.stage < 4 else None
    session.add(ReviewAttempt(id=str(uuid4()), player_id=owner(session), review_id=item.id, variant=body.variant,
        content_version=item.content_version, answer=body.answer, passed=passed, explanation=q['explanation']))
    session.flush()
    return {'passed': passed, 'explanation': q['explanation'], 'stage': item.stage,
        'due_at': iso_time(item.due_at) if item.due_at else None, 'xp_awarded': 0,
        'message': ('这个知识点已完成本轮巩固。' if item.stage == 4 else '回答正确，下次复习已安排。') if passed else '先理解原因，再换一个案例试试。'}
