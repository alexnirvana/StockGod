"""Registered users, revocable sessions and onboarding; preserve legacy records."""
from alembic import op
import sqlalchemy as sa

revision = 'b81e94a02d11'
down_revision = '0ac7d706b8a3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('players') as batch:
        batch.add_column(sa.Column('username', sa.String(32), nullable=True))
        batch.add_column(sa.Column('password_hash', sa.String(255), nullable=True))
        batch.add_column(sa.Column('guide_step', sa.Integer(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('guide_status', sa.String(16), nullable=False, server_default='pending'))
        batch.create_unique_constraint('uq_players_username', ['username'])
    with op.batch_alter_table('accounts') as batch:
        batch.create_unique_constraint('uq_accounts_player_mode', ['player_id', 'mode'])
    with op.batch_alter_table('requests') as batch:
        batch.add_column(sa.Column('player_id', sa.String(191), nullable=False, server_default='local'))
        batch.create_index('ix_requests_player_id', ['player_id'])
    op.create_table('auth_sessions',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('player_id', sa.String(191), nullable=False),
        sa.Column('csrf_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_auth_sessions_player_id', 'auth_sessions', ['player_id'])
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])
    op.create_table('auth_throttles',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('hits', sa.Integer(), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    raise RuntimeError('Auth downgrade would discard account credentials; restore a verified backup instead.')
