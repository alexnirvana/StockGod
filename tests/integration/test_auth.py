from datetime import timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select
from stock_god.db.models import AuthSession, Player, now
from stock_god.db.session import transaction
from test_workflows import client, post, order, register


def test_auth_required_credentials_and_revocation(client):
    with TestClient(client.app) as other:
        for path in ('/state', '/accounts/tutorial', '/courses/account', '/experiments', '/export', '/status', '/auth/me'):
            assert other.get('/api' + path).status_code == 401
        assert post(other, '/auth/login', {'username': 'testlearner', 'password': 'wrong-password-123'}).status_code == 401
        assert post(other, '/auth/register', {'username': 'TestLearner', 'password': 'another-password'}).status_code == 409
        assert post(other, '/auth/register', {'username': 'invalid space', 'password': 'another-password'}).status_code == 422
        assert post(other, '/auth/register', {'username': 'valid', 'password': 'short'}).status_code == 422
        response = post(other, '/auth/login', {'username': 'TESTLEARNER', 'password': 'a-test-password-123'})
        assert response.status_code == 200
        assert 'HttpOnly' in response.headers['set-cookie']
        token = other.cookies.get('stockgod_session')
        assert post(other, '/auth/logout').status_code == 200
        other.cookies.set('stockgod_session', token)
        assert other.get('/api/state').status_code == 401
    with client.app.state.factory() as s:
        player = s.scalar(select(Player).where(Player.username == 'testlearner'))
        assert player.password_hash.startswith('$argon2id$')
        assert 'a-test-password' not in player.password_hash


def test_two_users_isolate_every_record_and_idempotency(client):
    alice = client.get('/api/auth/me').json()['user']
    created = order(client).json()
    assert post(client, '/courses/account/answers', {'answers': [1, 2]}, key='shared-intent').status_code == 200
    assert post(client, '/profile', {'name': 'Alice学习昵称'}).status_code == 200
    assert post(client, '/reflections', {'plan': '这是属于Alice的交易前计划。', 'review': '这是属于Alice的交易后复盘。'}).status_code == 200
    assert post(client, '/experiments', {'short_window': 5, 'long_window': 15, 'allocation': 30}).status_code == 200
    with TestClient(client.app) as bob:
        user = register(bob, 'secondlearner')
        state = bob.get('/api/state').json()
        assert state['player']['id'] != alice['id']
        assert state['player']['xp'] == 0
        assert state['account']['orders'] == state['account']['positions'] == state['reflections'] == state['rewards'] == []
        assert state['last_attempt'] is None
        assert bob.get('/api/experiments').json() == []
        assert post(bob, '/accounts/tutorial/orders/' + created['id'] + '/cancel').status_code == 404
        assert bob.get('/api/accounts/' + state['account']['id']).status_code == 404
        assert post(bob, '/courses/account/answers', {'answers': [0, 0]}, key='shared-intent').json()['score'] == 0
        assert post(bob, '/courses/account/answers', {'answers': [1, 2]}).json()['xp_awarded'] == 20
        exported = bob.get('/api/export').json()
        assert 'auth_sessions' not in exported['tables']
        assert 'password_hash' not in str(exported)
        assert alice['id'] not in str(exported)
        assert 'Alice' not in str(exported)
        assert all(a['player_id'] == user['id'] for a in exported['tables']['accounts'])
    assert client.get('/api/state').json()['player']['name'] == 'Alice学习昵称'
    account = client.get('/api/accounts/tutorial').json()
    assert account['orders'][0]['status'] == 'pending'
    assert Decimal(account['frozen_cash']) > 0


def test_csrf_expiration_and_session_rotation(client):
    headers = {'Idempotency-Key': 'csrf-probe', 'X-StockGod-Client': 'web'}
    assert client.post('/api/profile', json={'name': 'Intruder'}, headers=headers).status_code == 403
    assert post(client, '/auth/login', {'username': 'testlearner', 'password': 'a-test-password-123'}).status_code == 200
    with transaction(client.app.state.factory) as s:
        for auth in s.scalars(select(AuthSession)):
            auth.expires_at = now() - timedelta(seconds=1)
    assert client.get('/api/state').status_code == 401


def test_onboarding_progress_is_per_user_and_persistent(client):
    assert client.get('/api/state').json()['player']['guide_status'] == 'pending'
    assert post(client, '/onboarding', {'step': 2, 'status': 'pending'}).status_code == 200
    post(client, '/auth/logout')
    post(client, '/auth/login', {'username': 'testlearner', 'password': 'a-test-password-123'})
    player = client.get('/api/state').json()['player']
    assert (player['guide_step'], player['guide_status']) == (2, 'pending')
    assert post(client, '/onboarding', {'step': 3, 'status': 'completed'}).status_code == 200
    assert client.get('/api/state').json()['player']['guide_status'] == 'completed'
    with TestClient(client.app) as other:
        register(other, 'guidelearner')
        assert other.get('/api/state').json()['player']['guide_step'] == 0
        assert post(other, '/onboarding', {'step': 0, 'status': 'skipped'}).status_code == 200
        assert other.get('/api/state').json()['player']['guide_status'] == 'skipped'


def test_login_throttling_survives_session_changes(client):
    for _ in range(12):
        assert post(client, '/auth/login', {'username': 'nosuchuser', 'password': 'wrong-password-123'}).status_code == 401
    assert post(client, '/auth/login', {'username': 'nosuchuser', 'password': 'wrong-password-123'}).status_code == 429
