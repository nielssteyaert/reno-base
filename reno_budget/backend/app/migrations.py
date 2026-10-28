"""Run Alembic migrations from code (on startup and after a restore)."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from app.config import get_config

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _alembic_config(db_url: str) -> AlembicConfig:
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.attributes["configure_logger"] = False
    return cfg


def run_migrations(db_url: str | None = None) -> None:
    command.upgrade(_alembic_config(db_url or get_config().db_url), "head")


def current_revision(db_url: str) -> str | None:
    engine = create_engine(db_url)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()
