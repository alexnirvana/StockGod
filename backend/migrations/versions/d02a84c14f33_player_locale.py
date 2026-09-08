"""Persist each player's UI and content language without changing progress."""
from alembic import op
import sqlalchemy as sa

revision = 'd02a84c14f33'
down_revision = 'c91f72b03e22'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('players') as batch:
        batch.add_column(sa.Column('locale', sa.String(16), nullable=False, server_default='zh-CN'))


def downgrade():
    with op.batch_alter_table('players') as batch:
        batch.drop_column('locale')
