"""Alembic entry: runs migrations against DATABASE_URL using every module's SQLModel tables.

New column: edit modules/<x>/models.py, then `alembic revision --autogenerate -m "..."`, review, `alembic upgrade head`.
"""

from alembic import context
from sqlmodel import SQLModel

from app.config.database import engine, import_models

import_models()

def run(connection) -> None:
    # render_as_batch lets SQLite alter columns too (it copies the table).
    context.configure(connection=connection, target_metadata=SQLModel.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()

# Tests hand in their own connection; otherwise use the app's DATABASE_URL.
if (given := context.config.attributes.get("connection")) is not None:
    run(given)
else:
    with engine.connect() as connection:
        run(connection)
