from alembic import context
from stock_god.db.models import Base
from stock_god.db.session import database

config = context.config
engine, _ = database()
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

