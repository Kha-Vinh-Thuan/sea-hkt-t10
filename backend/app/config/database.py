"""Database engine and session. Postgres from DATABASE_URL; tests swap in SQLite.

Schema changes go through Alembic (backend/migrations); the app upgrades to the latest revision on startup.
"""

from collections.abc import Iterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

from app.config import settings

engine = create_engine(settings.database_url())
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"

def import_models() -> None:
    # Registers every module's tables on SQLModel.metadata (Alembic autogenerate and tests need them).
    from app.modules.applicants import models as _applicants  # noqa: F401
    from app.modules.interviews import models as _interviews  # noqa: F401
    from app.modules.jobs import models as _jobs  # noqa: F401
    from app.modules.talent_pools import models as _talent_pools  # noqa: F401
    from app.modules.users import models as _users  # noqa: F401

def migrate() -> None:
    command.upgrade(Config(str(ALEMBIC_INI)), "head")

def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
