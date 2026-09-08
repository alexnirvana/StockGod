from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from fastapi.testclient import TestClient
from stock_god.db.models import Account
from stock_god.db.session import transaction
from test_workflows import client, post, register


def current(client):
    return client.get('/api/accounts/free').json()


def context(account):
    return {'expected_account_id': account['id'], 'expected_day': account['day']}


def free_order(client, account=None, **values):
    return post(client, '/accounts/free/orders', {
        **context(account or current(client)), 'symbol': 'SG001', 'side': 'buy',
        'quantity': 100, 'limit_price': '22.00', **values})


def restart(client, account=None, key=None):
    return post(client, '/practice/rounds', context(account or current(client)), key)


def test_round_archive_preserves_cash_positions_reflections_and_clock(client):
    initial = current(client)
    tutorial = client.get('/api/accounts/tutorial').json()
    assert free_order(client).status_code == 200
    settled = post(client, '/accounts/free/advance', context(initial)).json()
    assert settled['positions'][0]['quantity'] == 100
    reflection = post(client, '/reflections', {
        'account_id': 'free', **context(settled),
        'plan': '只用一手虚拟股票观察成交和费用。', 'review': '成交按开盘价估算，费用另计且今日不可卖。'})
    assert reflection.status_code == 200
    new = restart(client, settled, 'new-practice-round').json()
    assert new['id'] != initial['id'] and new['round_number'] == 2
    assert new['cash'] == '100000.00' and new['day'] == 19
    assert new['orders'] == new['positions'] == [] and len(new['ledger']) == 1
    assert restart(client, settled, 'new-practice-round').json() == new
    old = client.get('/api/practice/rounds/' + initial['id']).json()
    assert old['archived_at'] and old['cash'] == settled['cash']
    assert old['positions'] == settled['positions'] and old['orders'] == settled['orders']
    assert old['ledger'] == settled['ledger'] and old['day'] == settled['day']
    assert old['reflections'][0]['id'] == reflection.json()['id']
    profile_record = client.get('/api/state').json()['reflections'][0]
    assert profile_record['account_mode'] == 'free' and profile_record['round_number'] == 1
    assert max(b['day'] for b in old['bars']) == old['day']
    assert Decimal(old['cash']) == sum(Decimal(row['cash_delta']) for row in old['ledger'])
    assert client.get('/api/accounts/tutorial').json() == tutorial
    assert client.get('/api/state').json()['player']['xp'] == 0
    exported = client.get('/api/export').json()['tables']
    assert len(exported['accounts']) == 3
    assert {row['account_id'] for row in exported['reflections']} == {initial['id']}
    post(client, '/auth/logout')
    post(client, '/auth/login', {'username': 'testlearner', 'password': 'a-test-password-123'})
    assert current(client)['id'] == new['id']


def test_pending_orders_block_archive_and_stale_pages_cannot_write_to_new_round(client):
    old = current(client)
    pending = free_order(client).json()
    assert restart(client, old).status_code == 409
    assert current(client)['id'] == old['id']
    assert post(client, '/accounts/free/orders/' + pending['id'] + '/cancel').status_code == 200
    assert restart(client, old).status_code == 200
    assert free_order(client, old).status_code == 409
    assert post(client, '/accounts/free/advance', context(old)).status_code == 409
    assert post(client, '/accounts/free/advance').status_code == 409
    assert post(client, '/reflections', {'account_id': 'free', **context(old),
        'plan': 'This belongs to the old round.', 'review': 'Keep it out of the new round.'}).status_code == 409
    assert post(client, '/accounts/free/orders/' + pending['id'] + '/cancel').status_code == 404
    assert current(client)['cash'] == '100000.00'
    assert current(client)['day'] == 19 and current(client)['orders'] == []


def test_concurrent_round_creation_and_day_advance_have_one_outcome(client):
    old = current(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: restart(client, old), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    active = current(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: post(client, '/accounts/free/advance', context(active)), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert current(client)['day'] == active['day'] + 1
    assert free_order(client, active).status_code == 409
    assert len(client.get('/api/practice/rounds').json()['items']) == 2


def test_history_is_private_paginated_and_uses_saved_data_version(client):
    first = current(client)
    for _ in range(3):
        assert restart(client).status_code == 200
    page = client.get('/api/practice/rounds?limit=2').json()
    assert [r['round_number'] for r in page['items']] == [4, 3]
    assert page['next_before'] == 3
    older = client.get('/api/practice/rounds?limit=2&before=3').json()
    assert [r['round_number'] for r in older['items']] == [2, 1]
    assert older['next_before'] is None
    with TestClient(client.app) as other:
        assert other.get('/api/practice/rounds').status_code == 401
        register(other, 'otherpractice')
        assert len(other.get('/api/practice/rounds').json()['items']) == 1
        assert other.get('/api/practice/rounds/' + first['id']).status_code == 404
        assert restart(other, first).status_code == 409
        assert first['id'] not in str(other.get('/api/export').json())
    assert client.get('/api/practice/rounds/' + client.get('/api/accounts/tutorial').json()['id']).status_code == 404
    assert client.get('/api/practice/rounds?limit=101').status_code == 422
    with transaction(client.app.state.factory) as s:
        s.get(Account, first['id']).data_version = 'missing-version'
    client.headers['Accept-Language'] = 'en'
    response = client.get('/api/practice/rounds/' + first['id'])
    assert response.status_code == 503 and not any('\u4e00' <= c <= '\u9fff' for c in response.text)
    assert len(client.get('/api/practice/rounds').json()['items']) == 4


def test_last_day_can_start_again_and_original_round_is_immutable(client):
    old = current(client)
    with transaction(client.app.state.factory) as s:
        s.get(Account, old['id']).day = 59
    ended = current(client)
    assert post(client, '/accounts/free/advance', context(ended)).status_code == 409
    assert restart(client, ended).status_code == 200
    assert client.get('/api/practice/rounds/' + old['id']).json()['day'] == 59
    assert current(client)['day'] == 19


def test_order_and_archive_race_cannot_lose_an_accepted_order(client):
    old = current(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        ordering = pool.submit(free_order, client, old)
        archiving = pool.submit(restart, client, old)
        order_result, archive_result = ordering.result(), archiving.result()
    assert sorted([order_result.status_code, archive_result.status_code]) == [200, 409]
    if order_result.status_code == 200:
        assert current(client)['id'] == old['id']
        assert current(client)['orders'][0]['id'] == order_result.json()['id']
    else:
        assert current(client)['id'] != old['id'] and current(client)['orders'] == []
