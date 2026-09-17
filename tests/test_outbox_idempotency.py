"""Idempotency helpers: pure / mocked (no live Telegram)."""

import os

import pytest

from notify_hub.models import EventIn, EventTargets
from notify_hub.subscribers import merge_chat_targets


def test_event_in_normalizes_channels():
    e = EventIn(
        event_id="e1",
        type="calendar.event.v1",
        channels=["PUBLIC", "private", "public", "unknown"],
    )
    assert e.channels == ["public", "private"]


def test_event_in_default_channel():
    e = EventIn(event_id="e2", type="x.y")
    assert e.channels == ["public"]


def test_merge_targets_idempotent_set():
    a = merge_chat_targets([1, 2], [2, 3])
    b = merge_chat_targets(a, [1, 3])
    assert a == b == [1, 2, 3]


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skip Postgres integration",
)
def test_accept_event_idempotent_postgres():
    """Integration: duplicate event_id does not re-enqueue."""
    from notify_hub.config import clear_settings_cache
    from notify_hub.db import init_db, reset_engine, session_scope
    from notify_hub.outbox import accept_event

    clear_settings_cache()
    reset_engine()
    init_db()

    event = EventIn(
        event_id="idempotency-test-event-001",
        type="calendar.event.v1",
        title="Test",
        body="hello",
        channels=["public"],
        targets=EventTargets(chat_ids=[999001]),
    )
    with session_scope() as session:
        created1, n1 = accept_event(session, event)
    with session_scope() as session:
        created2, n2 = accept_event(session, event)

    assert created1 is True
    assert n1 >= 1
    assert created2 is False
    assert n2 == 0
