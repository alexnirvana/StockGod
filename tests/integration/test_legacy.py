import importlib.util
from pathlib import Path
import pytest
from stock_god.db.models import Account, Ledger, Player, Progress, Reward
from stock_god.db.session import transaction
from test_workflows import client, post, order

spec = importlib.util.spec_from_file_location('legacy_claim', Path(__file__).resolve().parents[2] / 'scripts/claim-legacy.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def legacy(factory):
    with transaction(factory) as s:
        s.add(Player(id='local', name='旧版学员', xp=20))
        s.add(Progress(id='local:account:1', player_id='local', lesson_id='account', completed=True))
        s.add(Reward(id='local:account:1', player_id='local', lesson_id='account', xp=20, badge='新手探索者'))
        for mode in ('tutorial', 'free'):
            s.add(Account(id=mode, player_id='local', mode=mode))
            s.add(Ledger(account_id=mode, source='initial', kind='initial', cash_delta=100000, day=19))


def test_claim_preserves_legacy_progress_and_uses_users_own_password(client):
    legacy(client.app.state.factory)
    module.claim_legacy(client.app.state.factory, 'testlearner')
    assert client.get('/api/state').status_code == 401
    assert post(client, '/auth/login', {'username': 'testlearner', 'password': 'a-test-password-123'}).status_code == 200
    state = client.get('/api/state').json()
    assert state['player']['xp'] == 20
    assert state['player']['name'] == '旧版学员'
    assert state['player']['guide_status'] == 'pending'
    assert state['courses'][0]['completed']
    assert state['account']['cash'] == '100000.00'
    assert post(client, '/courses/account/answers', {'answers': [1, 2]}).json()['xp_awarded'] == 0


def test_claim_refuses_to_overwrite_an_active_registered_account(client):
    legacy(client.app.state.factory)
    assert order(client).status_code == 200
    with pytest.raises(ValueError, match='activity'):
        module.claim_legacy(client.app.state.factory, 'testlearner')
    assert len(client.get('/api/accounts/tutorial').json()['orders']) == 1
    assert client.get('/api/state').json()['player']['xp'] == 0
