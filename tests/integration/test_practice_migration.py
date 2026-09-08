"""Upgrade populated v0.5 accounts without rewriting their balances or linked records."""
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, select


def test_v05_accounts_and_linked_records_survive_upgrade(tmp_path, monkeypatch):
    url = 'sqlite:///' + (tmp_path / 'practice-migration.sqlite').as_posix()
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config(str(Path(__file__).resolve().parents[2] / 'backend' / 'alembic.ini'))
    command.upgrade(config, 'e13b95d25044')
    engine = create_engine(url)
    old = MetaData()
    old.reflect(engine)
    clock = datetime(2026, 9, 8, tzinfo=timezone.utc)
    with engine.begin() as c:
        c.execute(old.tables['players'].insert().values(id='existing-player', username='existing', name='Existing learner',
            password_hash='preserved-hash', guide_step=3, guide_status='completed', locale='en', onboarded=True, reduced_motion=False, xp=20))
        c.execute(old.tables['accounts'].insert().values(id='existing-free', player_id='existing-player', mode='free',
            cash='97790.56', frozen_cash='0', day=20, rule_version='cn-mainboard-teaching-v1'))
        c.execute(old.tables['positions'].insert().values(account_id='existing-free', symbol='SG001', quantity=100, sellable=0, frozen=0, cost='2209.44'))
        c.execute(old.tables['ledger'].insert(), [
            {'account_id': 'existing-free', 'source': 'initial', 'kind': 'initial', 'cash_delta': '100000', 'quantity_delta': 0, 'symbol': None, 'day': 19, 'rule_version': 'cn-mainboard-teaching-v1', 'created_at': clock},
            {'account_id': 'existing-free', 'source': 'old-fill', 'kind': 'buy', 'cash_delta': '-2209.44', 'quantity_delta': 100, 'symbol': 'SG001', 'day': 20, 'rule_version': 'cn-mainboard-teaching-v1', 'created_at': clock}])
        c.execute(old.tables['reflections'].insert().values(id='old-reflection', player_id='existing-player', account_id='existing-free', plan='Original plan', review='Original review', created_at=clock))
    names = ['players', 'accounts', 'positions', 'ledger', 'reflections']
    with engine.connect() as c:
        before = {name: [dict(row) for row in c.execute(select(old.tables[name])).mappings()] for name in names}
    command.upgrade(config, 'head')
    command.upgrade(config, 'head')
    command.check(config)
    new = MetaData()
    new.reflect(engine)
    with engine.begin() as c:
        for name in names:
            columns = [new.tables[name].c[col.name] for col in old.tables[name].c]
            assert [dict(row) for row in c.execute(select(*columns)).mappings()] == before[name]
        account = c.execute(select(new.tables['accounts'])).mappings().one()
        assert account['round_number'] == 1 and account['archived_at'] is None and account['created_at'] is None
        assert account['data_version'] == 'teaching-v1-76958d6814cd'
        c.execute(new.tables['accounts'].insert().values(**{**dict(account), 'id': 'second-round', 'round_number': 2}))
        assert len(c.execute(select(new.tables['accounts'])).all()) == 2
    engine.dispose()
