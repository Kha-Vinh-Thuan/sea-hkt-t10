"""Database engine and session. Postgres from DATABASE_URL; tests swap in SQLite."""

import os
from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///hr.db"))


def create_tables() -> None:
    # ponytail: create_all only adds missing tables, never alters columns; add Alembic once the schema settles.
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
