from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from stock_god.adapters.data import PROVIDER
from test_workflows import client, post, order


def test_unmatched_limit_expires_and_releases(client):
    assert order(client, limit_price='20.00').status_code == 200
    response = post(client, '/accounts/tutorial/advance').json()
    assert response['orders'][0]['status'] == 'expired'
    assert response['frozen_cash'] == '0.00'
    assert response['cash'] == '100000.00'
    assert len(response['ledger']) == 1


def test_missing_next_bar_rolls_back_entire_advance(client, monkeypatch):
    order(client)
    original = PROVIDER.bar
    monkeypatch.setattr(PROVIDER, 'bar', lambda symbol, day: None if symbol == 'SG002' and day == 20 else original(symbol, day))
    assert post(client, '/accounts/tutorial/advance').status_code == 409
    state = client.get('/api/accounts/tutorial').json()
    assert state['day'] == 19
    assert state['orders'][0]['status'] == 'pending'
    assert state['cash'] == '100000.00'


def test_cancel_and_fill_race_has_one_outcome(client):
    created = order(client).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        cancel = pool.submit(post, client, '/accounts/tutorial/orders/' + created['id'] + '/cancel')
        settle = pool.submit(post, client, '/accounts/tutorial/advance')
        assert settle.result().status_code == 200
        assert cancel.result().status_code in (200, 409)
    account = client.get('/api/accounts/tutorial').json()
    assert account['orders'][0]['status'] in ('filled', 'cancelled')
    assert account['frozen_cash'] == '0.00'
    assert sum(Decimal(l['cash_delta']) for l in account['ledger']) == Decimal(account['cash'])
    assert len([l for l in account['ledger'] if l['kind'] == 'buy']) <= 1


def test_suspension_blocks_execution_without_debit(client):
    for _ in range(3):
        assert post(client, '/accounts/tutorial/advance').status_code == 200
    assert order(client, symbol='SG002', limit_price='15.00').status_code == 200
    account = post(client, '/accounts/tutorial/advance').json()
    assert account['orders'][0]['status'] == 'expired'
    assert '停牌' in account['orders'][0]['reason']
    assert account['cash'] == '100000.00'
    assert order(client, symbol='SG002', limit_price='15.00').status_code == 409


def test_all_symbol_endpoints_respect_current_clock(client):
    for symbol in ('SG001', 'SG002'):
        bars = client.get('/api/accounts/tutorial/bars/' + symbol).json()
        assert len(bars) == 20
        assert max(bar['day'] for bar in bars) == 19
    assert client.get('/api/accounts/tutorial/bars/600519').status_code == 404


def test_foreign_origin_cannot_mutate_local_data(client):
    response = client.post('/api/profile', json={'name': 'external'}, headers={'Origin': 'https://example.com', 'Idempotency-Key': 'external-origin'})
    assert response.status_code == 403


def test_complete_five_lesson_journey_requires_practice_and_reflection(client):
    from stock_god.jobs.worker import run_once
    assert post(client, '/courses/account/answers', {'answers': [1, 2]}).json()['passed']
    assert not post(client, '/courses/orders/answers', {'answers': [1, 1]}).json()['passed']
    order(client)
    post(client, '/accounts/tutorial/advance')
    assert post(client, '/courses/orders/answers', {'answers': [1, 1]}).json()['passed']
    assert post(client, '/courses/market/answers', {'answers': [1, 1]}).json()['passed']
    assert not post(client, '/courses/risk/answers', {'answers': [1, 2]}).json()['passed']
    assert post(client, '/reflections', {'plan': '这次只使用少量仓位观察限价和订单处理。', 'review': '订单按下一日开盘处理，并扣除了模拟费用。'}).status_code == 200
    assert post(client, '/courses/risk/answers', {'answers': [1, 2]}).json()['passed']
    assert not post(client, '/courses/strategy/answers', {'answers': [1, 2]}).json()['passed']
    post(client, '/experiments', {'short_window': 5, 'long_window': 15, 'allocation': 30})
    assert run_once(client.app.state.factory)
    assert post(client, '/courses/strategy/answers', {'answers': [1, 2]}).json()['passed']
    state = client.get('/api/state').json()
    assert all(c['completed'] for c in state['courses'])
    assert state['player']['xp'] == 145
    assert len(state['rewards']) == 5
    assert all(r['created_at'].endswith('+00:00') for r in state['rewards'])
