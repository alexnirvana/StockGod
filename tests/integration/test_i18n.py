import json
import re
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select
from stock_god.db.models import RequestRecord, Player
from stock_god.i18n import negotiate, MESSAGES
from stock_god.learning.service import LESSONS
from stock_god.learning.reviews import BANK
from test_workflows import client, post, register, order


def no_chinese(value):
    assert not re.search(r'[\u4e00-\u9fff]', json.dumps(value, ensure_ascii=False)), value


def test_language_preference_is_account_scoped_and_login_restores_it(client):
    assert client.get('/api/auth/me').json()['user']['locale'] == 'zh-CN'
    assert post(client, '/preferences/language', {'locale': 'fr'}).status_code == 422
    assert post(client, '/preferences/language', {'locale': 'en'}).json() == {'locale': 'en'}
    post(client, '/auth/logout')
    login = post(client, '/auth/login', {'username': 'testlearner', 'password': 'a-test-password-123'})
    assert login.json()['user']['locale'] == 'en'
    with TestClient(client.app) as other:
        register(other, 'other_locale')
        assert other.get('/api/auth/me').json()['user']['locale'] == 'zh-CN'
    client.headers['Accept-Language'] = 'en'
    assert client.get('/api/state').json()['player']['xp'] == 0


def test_english_content_grading_and_cross_language_idempotency(client):
    client.headers['Accept-Language'] = 'en-US,en;q=0.8'
    lesson = client.get('/api/courses/account')
    assert lesson.headers['content-language'] == 'en'
    no_chinese(lesson.json())
    assert 'Meet your simulated account' in lesson.json()['body']
    assert 'correct' not in lesson.json()['questions'][0]
    result = post(client, '/courses/account/answers', {'answers': [1, 2]}, key='locale-shared-key').json()
    no_chinese(result)
    assert result['passed'] and result['xp_awarded'] == 20
    client.headers['Accept-Language'] = 'zh-CN'
    repeated = post(client, '/courses/account/answers', {'answers': [1, 2]}, key='locale-shared-key').json()
    assert repeated['passed'] and repeated['xp_awarded'] == 20
    assert '可用资金' in repeated['feedback'][0]['explanation']
    assert client.get('/api/state').json()['player']['xp'] == 20
    with client.app.state.factory() as s:
        records = s.scalars(select(RequestRecord)).all()
        assert any('可用资金' in json.dumps(r.result, ensure_ascii=False) for r in records)


def test_reviews_orders_errors_and_coach_are_translated_without_user_text_changes(client):
    client.headers['Accept-Language'] = 'en'
    post(client, '/courses/account/answers', {'answers': [0, 2]})
    no_chinese(client.get('/api/reviews').json())
    no_chinese(order(client).json())
    no_chinese(post(client, '/accounts/tutorial/advance').json())
    no_chinese(order(client, quantity=101).json())
    no_chinese(order(client, limit_price='99').json())
    for question in ['Why was my order not filled?', 'Explain this step', 'Show another example', 'Trading fees', 'Predict tomorrow']:
        no_chinese(post(client, '/coach', {'question': question}).json())
    post(client, '/profile', {'name': '学习主页'})
    plan, review = '我的中文交易计划必须保留原文。', '我的中文交易复盘必须保留原文。'
    post(client, '/reflections', {'plan': plan, 'review': review})
    state = client.get('/api/state').json()
    assert state['player']['name'] == '学习主页'
    assert state['reflections'][0]['plan'] == plan and state['reflections'][0]['review'] == review
    no_chinese(client.get('/api/status').json())


def test_language_context_is_isolated_and_every_graded_case_is_translated(client):
    def read(locale):
        response = client.get('/api/courses/account', headers={'Accept-Language': locale})
        return locale, response.json()['title']
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(read, ['en', 'zh-CN'] * 5))
    assert all(title == ('Meet your simulated account' if locale == 'en' else '认识你的模拟账户') for locale, title in results)
    for lesson in LESSONS:
        for key in ('title','short_title','goal','practice','badge'):
            no_chinese(MESSAGES[lesson[key]])
        for q in lesson['questions']:
            for text in [q['prompt'],q['explanation'],*q['options']]: no_chinese(MESSAGES[text])
    for concepts in BANK['lessons'].values():
        for concept in concepts:
            no_chinese(MESSAGES[concept['title']])
            for q in concept['variants']:
                for text in [q['prompt'],q['explanation'],*q['options']]: no_chinese(MESSAGES[text])
    assert negotiate('fr, en-US;q=0.8, zh-CN;q=0.9') == 'zh-CN'
    assert negotiate('en;q=0,zh-CN;q=0.3') == 'zh-CN'


def test_unexpected_error_keeps_requested_language_after_middleware_unwinds(client):
    @client.app.get('/test-localized-error')
    def fail():
        raise RuntimeError('Injected failure')
    with TestClient(client.app, raise_server_exceptions=False) as guest:
        response = guest.get('/test-localized-error', headers={'Accept-Language': 'en'})
        assert response.status_code == 500
        assert response.headers['Content-Language'] == 'en'
        no_chinese(response.json())
