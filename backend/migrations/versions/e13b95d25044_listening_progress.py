"""Store per-account, per-language narration bookmarks without changing rewards."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = 'e13b95d25044'
down_revision = 'd02a84c14f33'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('listening_progress',
        sa.Column('id', sa.String(191), primary_key=True),
        sa.Column('player_id', sa.String(191), nullable=False),
        sa.Column('lesson_id', sa.String(191), nullable=False),
        sa.Column('locale', sa.String(16), nullable=False),
        sa.Column('audio_version', sa.String(64), nullable=False),
        sa.Column('position_ms', sa.Integer(), nullable=False),
        sa.Column('playback_rate', sa.Numeric(3, 2), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True).with_variant(DATETIME(fsp=6), 'mysql'), nullable=False))
    op.create_index('ix_listening_progress_player_id', 'listening_progress', ['player_id'])


def downgrade():
    raise RuntimeError('Listening history is retained. Restore a backup to roll back this migration.')
