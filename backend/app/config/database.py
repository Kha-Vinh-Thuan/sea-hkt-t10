"""Database engine and session. Postgres from DATABASE_URL; tests swap in SQLite."""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url())


def create_tables() -> None:
    # Import every module's models so their tables are registered before create_all.
    from app.modules.applicants import models as _applicants  # noqa: F401
    from app.modules.interviews import models as _interviews  # noqa: F401
    from app.modules.jobs import models as _jobs  # noqa: F401

    # ponytail: create_all only adds missing tables, never alters columns; add Alembic once the schema settles.
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
