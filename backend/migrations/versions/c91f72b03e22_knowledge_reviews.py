"""Persistent knowledge reviews and answer history, including legacy mistakes."""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime

revision = 'c91f72b03e22'
down_revision = 'b81e94a02d11'
branch_labels = None
depends_on = None


def upgrade():
    review_time = sa.DateTime(timezone=True).with_variant(MySQLDateTime(fsp=6), 'mysql')
    items = op.create_table('review_items',
        sa.Column('id', sa.String(191), primary_key=True),
        sa.Column('player_id', sa.String(191), nullable=False),
        sa.Column('lesson_id', sa.String(191), nullable=False),
        sa.Column('question_index', sa.Integer(), nullable=False),
        sa.Column('content_version', sa.Integer(), nullable=False),
        sa.Column('stage', sa.Integer(), nullable=False),
        sa.Column('mistakes', sa.Integer(), nullable=False),
        sa.Column('review_count', sa.Integer(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('due_at', review_time, nullable=True),
        sa.Column('updated_at', review_time, nullable=False),
        sa.UniqueConstraint('player_id', 'lesson_id', 'question_index', 'content_version', name='uq_review_knowledge'))
    op.create_index('ix_review_player_due', 'review_items', ['player_id', 'due_at'])
    op.create_table('review_attempts',
        sa.Column('id', sa.String(191), primary_key=True),
        sa.Column('player_id', sa.String(191), nullable=False),
        sa.Column('review_id', sa.String(191), nullable=False),
        sa.Column('variant', sa.Integer(), nullable=False),
        sa.Column('content_version', sa.Integer(), nullable=False),
        sa.Column('answer', sa.Integer(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('created_at', review_time, nullable=False))
    op.create_index('ix_review_attempts_player_id', 'review_attempts', ['player_id'])
    op.create_index('ix_review_attempts_review_id', 'review_attempts', ['review_id'])
    bind = op.get_bind()
    progress = sa.table('progress', sa.column('player_id'), sa.column('lesson_id'), sa.column('version'), sa.column('review_due'), sa.column('updated_at', sa.DateTime(timezone=True)))
    attempts = sa.table('attempts', sa.column('player_id'), sa.column('lesson_id'), sa.column('feedback', sa.JSON()), sa.column('created_at'))
    # The v1 catalog has two questions in each of these five lessons. Keep the
    # migration independent of future catalog edits; only unresolved mistakes migrate.
    for p in bind.execute(sa.select(progress).where(progress.c.review_due == sa.true())).mappings():
        if p['version'] != 1 or p['lesson_id'] not in ('account', 'orders', 'market', 'risk', 'strategy'):
            continue
        feedback = bind.execute(sa.select(attempts.c.feedback).where(attempts.c.player_id == p['player_id'], attempts.c.lesson_id == p['lesson_id']).order_by(attempts.c.created_at.desc()).limit(1)).scalar()
        wrong = [i for i, f in enumerate(feedback or []) if i < 2 and not f['passed']] if feedback else [0, 1]
        for index in wrong:
            bind.execute(items.insert().values(id=str(uuid4()), player_id=p['player_id'], lesson_id=p['lesson_id'], question_index=index, content_version=1, stage=0, mistakes=1, review_count=0, revision=0, due_at=p['updated_at'], updated_at=p['updated_at']))


def downgrade():
    raise RuntimeError('Downgrade would discard review history; restore a verified backup instead.')
