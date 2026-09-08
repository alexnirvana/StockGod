"""Keep existing accounts as round one and retain every subsequent practice round."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

revision = 'f24ca6e36155'
down_revision = 'e13b95d25044'
branch_labels = None
depends_on = None


def upgrade():
    clock = sa.DateTime(timezone=True).with_variant(DATETIME(fsp=6), 'mysql')
    with op.batch_alter_table('accounts') as batch:
        batch.add_column(sa.Column('round_number', sa.Integer(), nullable=False, server_default='1'))
        # Legacy accounts have no trustworthy creation timestamp.
        batch.add_column(sa.Column('created_at', clock, nullable=True))
        batch.add_column(sa.Column('archived_at', clock, nullable=True))
        batch.add_column(sa.Column('data_version', sa.String(191), nullable=False, server_default='teaching-v1-76958d6814cd'))
        batch.drop_constraint('uq_accounts_player_mode', type_='unique')
        batch.create_unique_constraint('uq_accounts_player_mode_round', ['player_id', 'mode', 'round_number'])
        batch.create_index('ix_accounts_player_active', ['player_id', 'mode', 'archived_at'])
    with op.batch_alter_table('accounts') as batch:
        batch.alter_column('round_number', existing_type=sa.Integer(), server_default=None)
        batch.alter_column('data_version', existing_type=sa.String(191), server_default=None)


def downgrade():
    raise RuntimeError('Practice history is retained. Restore a backup to roll back this migration.')
