"""SQLAlchemy engine and session handling for the SQLite database."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(expire_on_commit=False)
_engine: Engine | None = None


def _sqlite_pragmas(dbapi_conn, _record) -> None:
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def init_engine(url: str) -> Engine:
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(_engine, "connect", _sqlite_pragmas)
    SessionLocal.configure(bind=_engine)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine not initialised")
    return _engine


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def request_user(request: Request) -> str:
    """Name of the Home Assistant user behind an ingress request."""
    headers = request.headers
    return (
        headers.get("x-remote-user-display-name") or headers.get("x-remote-user-name") or "unknown"
    )


def get_db(request: Request) -> Iterator[Session]:
    with SessionLocal() as session:
        session.info["user"] = request_user(request)
        yield session
