import os
import hashlib
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from .models import Account, Ledger, Player

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_URL = "sqlite:///" + (ROOT / "data" / "stockgod.db").as_posix()


def heartbeat_path(engine):
    database_id = hashlib.sha256(str(engine.url).encode()).hexdigest()[:12]
    return ROOT / "data" / f"worker-{database_id}.json"


def database(url=None):
    url = url or os.getenv("DATABASE_URL", DEFAULT_URL)
    (ROOT / "data").mkdir(exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}, pool_pre_ping=True)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def configure(dbapi, _):
            dbapi.execute("PRAGMA foreign_keys=ON")
            dbapi.execute("PRAGMA journal_mode=WAL")
    return engine, sessionmaker(engine, expire_on_commit=False)


@contextmanager
def transaction(factory, player_id=None):
    # Serialize mutations for one authenticated player, not the whole application.
    with factory() as session:
        try:
            if session.bind.dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            elif player_id:
                session.execute(select(Player).where(Player.id == player_id).with_for_update())
            if player_id:
                session.info['player_id'] = player_id
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def owner(session):
    return session.info['player_id']


@contextmanager
def owned_session(factory, player_id):
    with factory() as session:
        session.info['player_id'] = player_id
        yield session


def create_accounts(session, player_id):
    for mode in ('tutorial', 'free'):
        account_id = f'{player_id}:{mode}'
        session.add(Account(id=account_id, player_id=player_id, mode=mode))
        session.add(Ledger(account_id=account_id, source='initial', kind='initial', cash_delta=100000, day=19))
