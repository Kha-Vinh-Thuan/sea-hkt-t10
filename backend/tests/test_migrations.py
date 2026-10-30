"""Migrations build exactly the tables the models describe: fails when a model changed without a new revision."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlmodel import SQLModel, create_engine

from app.config.database import ALEMBIC_INI, import_models


def test_migrations_match_models():
    import_models()
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        config = Config(str(ALEMBIC_INI))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        diff = compare_metadata(MigrationContext.configure(connection), SQLModel.metadata)
    assert diff == [], f"Run `alembic revision --autogenerate`: {diff}"
