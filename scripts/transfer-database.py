"""Portable, verified transfer of business records into an EMPTY database.

Uses DATABASE_URL. Never transfers live authentication sessions or passwords.
Old anonymous records remain unclaimed until assigned by the local administrator.
"""
import argparse
from datetime import datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from sqlalchemy import create_engine, MetaData, select, DateTime, Numeric

TABLES = ('players', 'accounts', 'positions', 'orders', 'ledger', 'progress', 'rewards', 'attempts', 'reflections', 'jobs', 'requests')


def export_data(engine, path):
    metadata = MetaData()
    metadata.reflect(engine, only=TABLES)
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            rows = {name: [dict(row) for row in connection.execute(select(metadata.tables[name])).mappings()] for name in TABLES}
    # Legacy source has no credentials. Do not allow this utility to downgrade a registered user.
    if any(row.get('username') for row in rows['players']):
        raise ValueError('Registered users require full database backup, not legacy transfer.')
    payload = {'format': 'stockgod-legacy-transfer-v1', 'tables': rows,
               'counts': {name: len(value) for name, value in rows.items()},
               'ledger_cash': str(sum((Decimal(str(r['cash_delta'])) for r in rows['ledger']), Decimal(0)))}
    with path.open('x', encoding='utf-8') as output:
        json.dump(payload, output, default=str, ensure_ascii=False, indent=2)
    print(json.dumps({'counts': payload['counts'], 'ledger_cash': payload['ledger_cash']}))


def import_data(engine, path):
    from stock_god.db.models import Base
    from sqlalchemy.orm import Session
    data = json.loads(path.read_text(encoding='utf-8'))
    if data['format'] != 'stockgod-legacy-transfer-v1':
        raise ValueError('Unknown transfer format')
    models = {m.local_table.name: m.class_ for m in Base.registry.mappers}
    with Session(engine) as session, session.begin():
        for name in TABLES:
            if session.execute(select(Base.metadata.tables[name]).limit(1)).first():
                raise ValueError(f'Target {name} is not empty; nothing imported.')
        for name in TABLES:
            table = Base.metadata.tables[name]
            for source in data['tables'][name]:
                row = dict(source)
                if name == 'requests':
                    row.setdefault('player_id', 'local')
                for column in table.c:
                    value = row.get(column.name)
                    if value is not None and isinstance(column.type, DateTime):
                        row[column.name] = datetime.fromisoformat(value)
                    if value is not None and isinstance(column.type, Numeric):
                        row[column.name] = Decimal(value)
                session.add(models[name](**row))
        session.flush()
        for name in TABLES:
            if len(session.execute(select(Base.metadata.tables[name])).all()) != data['counts'][name]:
                raise ValueError('Row count mismatch; import rolled back')
        total = sum(session.scalars(select(Base.metadata.tables['ledger'].c.cash_delta)), Decimal(0))
        if total != Decimal(data['ledger_cash']):
            raise ValueError('Ledger mismatch; import rolled back')
    print('Verified import: counts and ledger match. Legacy account remains unclaimed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'import'])
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    engine = create_engine(os.environ['DATABASE_URL'])
    try:
        (export_data if args.action == 'export' else import_data)(engine, args.path)
    finally:
        engine.dispose()
