from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import uuid4
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from stock_god.api.main import create_app
    url = os.getenv('TEST_DATABASE_URL', f"sqlite:///{tmp_path / 'test.db'}")
    if os.getenv('TEST_DATABASE_URL'):
        from stock_god.db.session import database
        from stock_god.db.models import Base
        engine, _ = database(url)
        if engine.url.database != 'stockgod_tests':
            raise ValueError('Database tests require the dedicated stockgod_tests database.')
        Base.metadata.drop_all(engine)
        engine.dispose()
    with TestClient(create_app(url)) as api:
        register(api)
        yield api


def post(client, path, body=None, key=None):
    return client.post('/api' + path, json=body or {}, headers={'Idempotency-Key': key or str(uuid4()), 'X-StockGod-Client': 'web', 'X-CSRF-Token': client.cookies.get('stockgod_csrf', '')})


def register(client, username='testlearner', password='a-test-password-123'):
    response = post(client, '/auth/register', {'username': username, 'password': password})
    assert response.status_code == 201, response.text
    return response.json()['user']


def order(client, **kwargs):
    return post(client, '/accounts/tutorial/orders', {'symbol': 'SG001', 'side': 'buy', 'quantity': 100, 'limit_price': '22.00', **kwargs})


def test_rewards_are_server_evaluated_and_unique(client):
    course = client.get('/api/courses/account').json()
    assert 'correct' not in str(course)
    assert post(client, '/courses/orders/answers', {'answers': [1, 1]}).status_code == 409
    wrong = post(client, '/courses/account/answers', {'answers': [0, 0]}).json()
    assert not wrong['passed']
    key = str(uuid4())
    result = post(client, '/courses/account/answers', {'answers': [1, 2]}, key)
    assert result.status_code == 200, result.text
    assert result.json()['xp_awarded'] == 20
    assert post(client, '/courses/account/answers', {'answers': [1, 2]}, key).json() == result.json()
    assert post(client, '/courses/account/answers', {'answers': [1, 2]}).json()['xp_awarded'] == 0
    assert client.get('/api/state').json()['player']['xp'] == 20


def test_cash_reservation_cancel_and_idempotency(client):
    key = str(uuid4())
    body = {'symbol': 'SG001', 'side': 'buy', 'quantity': 100, 'limit_price': '22.00'}
    first = post(client, '/accounts/tutorial/orders', body, key)
    assert first.status_code == 200, first.text
    assert post(client, '/accounts/tutorial/orders', body, key).json() == first.json()
    assert post(client, '/accounts/tutorial/orders', {**body, 'quantity': 200}, key).status_code == 409
    account = client.get('/api/accounts/tutorial').json()
    assert Decimal(account['frozen_cash']) > 2200
    assert len(account['orders']) == 1
    assert post(client, f"/accounts/tutorial/orders/{first.json()['id']}/cancel").status_code == 200
    account = client.get('/api/accounts/tutorial').json()
    assert account['frozen_cash'] == '0.00'
    assert account['cash'] == '100000.00'


def test_settlement_t_plus_one_and_reconciliation(client):
    assert order(client).status_code == 200
    key = str(uuid4())
    settled = post(client, '/accounts/tutorial/advance', key=key)
    assert settled.status_code == 200, settled.text
    assert post(client, '/accounts/tutorial/advance', key=key).json() == settled.json()
    account = client.get('/api/accounts/tutorial').json()
    assert account['orders'][0]['status'] == 'filled'
    assert account['positions'][0]['sellable'] == 0
    assert order(client, side='sell', limit_price='20.00').status_code == 409
    assert post(client, '/accounts/tutorial/advance').status_code == 200
    assert order(client, side='sell', limit_price='20.00').status_code == 200
    assert post(client, '/accounts/tutorial/advance').status_code == 200
    account = client.get('/api/accounts/tutorial').json()
    ledger_cash = sum((Decimal(row['cash_delta']) for row in account['ledger']), Decimal(0))
    assert ledger_cash == Decimal(account['cash'])
    assert account['positions'] == []
    assert account['frozen_cash'] == '0.00'


def test_constraints_and_isolation(client):
    assert order(client, quantity=101).status_code == 422
    assert order(client, quantity=100000).status_code == 409
    assert order(client, limit_price='NaN').status_code == 422
    assert order(client, limit_price='21.001').status_code == 422
    assert order(client, symbol='600519').status_code == 422
    assert order(client, limit_price='99.00').status_code == 409
    assert client.get('/api/accounts/real').status_code == 404
    assert order(client).status_code == 200
    assert client.get('/api/accounts/free').json()['orders'] == []
    assert client.get('/api/accounts/free').json()['cash'] == '100000.00'


def test_no_future_data_and_no_duplicate_concurrent_spending(client):
    before = client.get('/api/accounts/tutorial').json()
    assert all(bar['day'] <= before['day'] for bar in before['bars'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: order(client, quantity=2000), range(4)))
    assert sum(r.status_code == 200 for r in responses) == 2
    after = client.get('/api/accounts/tutorial').json()
    assert Decimal(after['available_cash']) >= 0
    assert len(after['bars']) == len(before['bars'])


def test_missing_idempotency_and_extra_input(client):
    assert client.post('/api/accounts/tutorial/advance', json={}, headers={'X-StockGod-Client': 'web', 'X-CSRF-Token': client.cookies.get('stockgod_csrf', '')}).status_code == 422
    assert post(client, '/courses/account/answers', {'answers': [1, 2], 'xp': 9999}).status_code == 422
