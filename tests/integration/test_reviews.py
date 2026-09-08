from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import select
from stock_god.db.models import ReviewAttempt, ReviewItem
from stock_god.learning.reviews import BANK
from stock_god.learning.service import LESSONS
from test_workflows import client, post, register


def queue(client):
    response = client.get('/api/reviews')
    assert response.status_code == 200, response.text
    return response.json()


def submit(client, item, answer=None, key=None):
    correct = BANK['lessons'][item['lesson_id']][0]['variants'][item['variant']]['correct']
    return post(client, f"/reviews/{item['id']}/answers", {
        'answer': correct if answer is None else answer, 'revision': item['revision'],
        'variant': item['variant'], 'content_version': item['content_version']}, key)


def mistake(client):
    assert post(client, '/courses/account/answers', {'answers': [0, 2]}).status_code == 200
    return queue(client)['items'][0]


def test_mistakes_are_per_knowledge_and_do_not_bypass_course_rewards(client):
    item = mistake(client)
    assert queue(client)['summary']['due'] == 1
    assert item['title'] == '可用资金与冻结资金'
    assert 'correct' not in str(queue(client)) and 'explanation' not in str(queue(client))
    assert item['question']['prompt'] not in [q['prompt'] for q in LESSONS[0]['questions']]
    # Retaking the original quiz cannot silently clear the new-case review.
    assert post(client, '/courses/account/answers', {'answers': [1, 2]}).json()['xp_awarded'] == 20
    assert queue(client)['summary']['due'] == 1
    assert submit(client, item).json()['xp_awarded'] == 0
    state = client.get('/api/state').json()
    assert state['player']['xp'] == 20 and state['courses'][0]['completed']
    assert not state['courses'][0]['review_due']
    assert state['reviews']['scheduled'] == 1
    assert len(state['rewards']) == 1


def test_review_schedule_uses_elapsed_time_and_recovers_after_login(client, monkeypatch):
    from stock_god.learning import reviews
    clock = datetime(2030, 1, 1, microsecond=789123, tzinfo=timezone.utc)
    monkeypatch.setattr(reviews, 'now', lambda: clock)
    item = mistake(client)
    for stage, days in enumerate((1, 3, 7), 1):
        result = submit(client, item)
        assert result.status_code == 200, result.text
        assert result.json()['stage'] == stage
        due = datetime.fromisoformat(result.json()['due_at'])
        assert due == clock + timedelta(days=days)
        post(client, '/auth/logout')
        post(client, '/auth/login', {'username': 'testlearner', 'password': 'a-test-password-123'})
        item = queue(client)['items'][0]
        assert not item['due'] and item['stage'] == stage
        assert submit(client, item).status_code == 409
        clock = due - timedelta(seconds=1)
        assert queue(client)['summary']['due'] == 0
        clock = due
        item = queue(client)['items'][0]
        assert item['due']
    assert submit(client, item).json()['stage'] == 4
    assert queue(client)['summary'] == {'due': 0, 'scheduled': 0, 'mastered': 1, 'next_due_at': None}
    assert mistake(client)['stage'] == 0  # A later mistake reopens mastered knowledge.


def test_wrong_review_rotates_case_and_stale_or_forged_answers_fail(client):
    item = mistake(client)
    assert submit(client, item, answer=99).status_code == 422
    assert submit(client, item, answer=True).status_code == 422
    assert submit(client, {**item, 'content_version': 99}).status_code == 409
    wrong = submit(client, item, answer=0).json()
    assert not wrong['passed'] and wrong['stage'] == 0
    fresh = queue(client)['items'][0]
    assert fresh['due'] and fresh['variant'] != item['variant']
    assert fresh['question'] != item['question']
    assert submit(client, item).status_code == 409
    assert submit(client, fresh).status_code == 200
    assert client.get('/api/state').json()['player']['xp'] == 0


def test_review_owner_isolation_export_and_concurrent_idempotency(client):
    item = mistake(client)
    with TestClient(client.app) as other:
        assert other.get('/api/reviews').status_code == 401
        register(other, 'review_other')
        assert queue(other)['items'] == []
        assert submit(other, item).status_code == 404
        exported = other.get('/api/export').json()['tables']
        assert exported['review_items'] == exported['review_attempts'] == []
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: submit(client, item, key='review-one-intent'), range(3)))
    assert all(r.status_code == 200 for r in results)
    assert all(r.json() == results[0].json() for r in results)
    exported = client.get('/api/export').json()['tables']
    assert len(exported['review_items']) == len(exported['review_attempts']) == 1
    assert exported['review_attempts'][0]['explanation']
    with client.app.state.factory() as session:
        assert len(session.scalars(select(ReviewAttempt)).all()) == 1
        assert session.scalar(select(ReviewItem)).review_count == 1


def test_every_course_knowledge_has_distinct_versioned_review_cases():
    assert BANK['version'] == 1
    assert set(BANK['lessons']) == {l['id'] for l in LESSONS}
    for lesson in LESSONS:
        concepts = BANK['lessons'][lesson['id']]
        assert len(concepts) == len(lesson['questions'])
        for concept in concepts:
            prompts = set()
            for q in concept['variants']:
                assert q['prompt'] not in [p['prompt'] for p in lesson['questions']]
                assert q['prompt'] not in prompts
                assert 0 <= q['correct'] < len(q['options'])
                assert q['explanation'] and concept['title']
                prompts.add(q['prompt'])
            assert len(prompts) >= 2
