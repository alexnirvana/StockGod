"""Upgrade a real pre-review schema without losing existing learner state."""
from datetime import datetime, timezone
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, select


def test_existing_unresolved_mistakes_migrate_and_upgrade_is_repeatable(tmp_path, monkeypatch):
    url = 'sqlite:///' + (tmp_path / 'migration.sqlite').as_posix()
    monkeypatch.setenv('DATABASE_URL', url)
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / 'backend' / 'alembic.ini'))
    command.upgrade(config, 'b81e94a02d11')
    engine = create_engine(url)
    old = MetaData()
    old.reflect(engine)
    clock = datetime(2026, 9, 1, tzinfo=timezone.utc)
    with engine.begin() as c:
        c.execute(old.tables['players'].insert().values(id='local', name='Legacy learner', xp=20, onboarded=True, reduced_motion=False))
        c.execute(old.tables['progress'].insert().values(id='local:account:1', player_id='local', lesson_id='account', version=1, completed=True, review_due=True, attempts=2, last_score=50, updated_at=clock))
        c.execute(old.tables['attempts'].insert().values(id='last-attempt', player_id='local', lesson_id='account', answers=[0, 2], score=50, feedback=[{'passed': False}, {'passed': True}], created_at=clock))
    command.upgrade(config, 'head')
    command.upgrade(config, 'head')
    command.check(config)
    new = MetaData()
    new.reflect(engine)
    with engine.connect() as c:
        rows = c.execute(select(new.tables['review_items'])).mappings().all()
        assert len(rows) == 1
        assert rows[0]['player_id'] == 'local' and rows[0]['question_index'] == 0
        assert rows[0]['stage'] == 0 and rows[0]['content_version'] == 1
        assert c.execute(select(new.tables['players'].c.xp)).scalar() == 20
        assert c.execute(select(new.tables['progress'].c.completed)).scalar() is True
    engine.dispose()
