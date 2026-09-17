"""Database engine, sessions, and schema bootstrap (PostgreSQL)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from notify_hub.config import get_settings

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_id        TEXT PRIMARY KEY,
    type            TEXT NOT NULL,
    severity        TEXT,
    source          TEXT,
    title           TEXT,
    body            TEXT,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          TEXT NOT NULL DEFAULT 'accepted',
    require_ack     BOOLEAN NOT NULL DEFAULT FALSE,
    ack_timeout_minutes INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outbox (
    id              BIGSERIAL PRIMARY KEY,
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    channel         TEXT NOT NULL,
    chat_id         BIGINT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (event_id, channel, chat_id)
);

CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status);

CREATE TABLE IF NOT EXISTS subscriptions (
    id              BIGSERIAL PRIMARY KEY,
    chat_id         BIGINT NOT NULL,
    event_type_prefix TEXT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'public',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chat_id, event_type_prefix, channel)
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_prefix ON subscriptions(event_type_prefix);

CREATE TABLE IF NOT EXISTS acks (
    event_id        TEXT NOT NULL REFERENCES events(event_id),
    chat_id         BIGINT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_id, chat_id)
);

CREATE TABLE IF NOT EXISTS telegram_offsets (
    token_hash      TEXT PRIMARY KEY,
    update_offset   BIGINT NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
        _SessionLocal = sessionmaker(
            bind=_engine, autoflush=False, autocommit=False, future=True
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    engine = get_engine()
    with engine.begin() as conn:
        for statement in SCHEMA_SQL.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(text(stmt))
    logger.info("Database schema ensured")


def reset_engine() -> None:
    """Reset cached engine (tests)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
