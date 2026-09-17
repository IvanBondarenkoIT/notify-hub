"""Outbox enqueue and delivery worker."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import text
from sqlalchemy.orm import Session

from notify_hub import ack as ack_mod
from notify_hub import subscribers
from notify_hub.config import Settings, get_settings
from notify_hub.models import EventIn
from notify_hub.telegram_api import TelegramError, send_message

logger = logging.getLogger(__name__)

OUTBOX_PENDING = "pending"
OUTBOX_SENT = "sent"
OUTBOX_FAILED = "failed"


def _payload_dict(event: EventIn) -> Dict[str, Any]:
    return event.model_dump(mode="json")


def format_message(event: EventIn) -> str:
    severity = (event.severity or "info").upper()
    title = event.title or event.type
    body = event.body or ""
    parts = [f"[{severity}] {title}"]
    if body:
        parts.append(body)
    parts.append(f"type: {event.type}")
    if event.source:
        parts.append(f"source: {event.source}")
    parts.append(f"id: {event.event_id}")
    return "\n".join(parts)


def resolve_chat_ids_for_channel(
    session: Session,
    event: EventIn,
    channel: str,
    settings: Settings,
) -> List[int]:
    explicit = list(event.targets.chat_ids or [])
    # personal: prefer explicit targets only (+ user_ids treated as chat ids for MVP)
    if channel == "personal":
        explicit.extend(event.targets.user_ids or [])
        return subscribers.merge_chat_targets(explicit, [])

    sub_ids = subscribers.list_subscribers_for_event(session, event.type, channel)
    if channel == "public" and settings.seed_public_chat_ids:
        sub_ids = subscribers.merge_chat_targets(settings.seed_public_chat_ids, sub_ids)
    if channel == "private" and settings.private_allowlist_chat_ids:
        allow: Set[int] = set(settings.private_allowlist_chat_ids)
        explicit = [c for c in explicit if c in allow]
        sub_ids = [c for c in sub_ids if c in allow]
    return subscribers.merge_chat_targets(explicit, sub_ids)


def enqueue_outbox_for_event(
    session: Session,
    event: EventIn,
    settings: Optional[Settings] = None,
) -> int:
    """Create outbox rows for an accepted event. Idempotent via UNIQUE."""
    settings = settings or get_settings()
    enqueued = 0
    personal_ack_chats: List[int] = []

    for channel in event.channels:
        chat_ids = resolve_chat_ids_for_channel(session, event, channel, settings)
        for chat_id in chat_ids:
            result = session.execute(
                text(
                    """
                    INSERT INTO outbox (event_id, channel, chat_id, status, attempts)
                    VALUES (:event_id, :channel, :chat_id, :status, 0)
                    ON CONFLICT (event_id, channel, chat_id) DO NOTHING
                    """
                ),
                {
                    "event_id": event.event_id,
                    "channel": channel,
                    "chat_id": chat_id,
                    "status": OUTBOX_PENDING,
                },
            )
            if result.rowcount:
                enqueued += 1
            if channel == "personal" and event.require_ack:
                personal_ack_chats.append(chat_id)

    if event.require_ack and personal_ack_chats:
        ack_mod.ensure_ack_rows(session, event.event_id, personal_ack_chats)

    return enqueued


def accept_event(
    session: Session,
    event: EventIn,
    settings: Optional[Settings] = None,
) -> tuple[bool, int]:
    """Insert event if new; enqueue outbox. Returns (created, outbox_enqueued).

    Idempotent on event_id: if event exists, returns created=False and outbox_enqueued=0.
    """
    settings = settings or get_settings()
    existing = session.execute(
        text("SELECT event_id FROM events WHERE event_id = :eid"),
        {"eid": event.event_id},
    ).first()
    if existing:
        return False, 0

    payload = _payload_dict(event)
    session.execute(
        text(
            """
            INSERT INTO events (
                event_id, type, severity, source, title, body, payload,
                status, require_ack, ack_timeout_minutes
            ) VALUES (
                :event_id, :type, :severity, :source, :title, :body,
                CAST(:payload AS jsonb), 'accepted', :require_ack, :ack_timeout
            )
            """
        ),
        {
            "event_id": event.event_id,
            "type": event.type,
            "severity": event.severity,
            "source": event.source,
            "title": event.title,
            "body": event.body,
            "payload": json.dumps(payload, ensure_ascii=False),
            "require_ack": event.require_ack,
            "ack_timeout": event.ack_timeout_minutes
            or settings.default_ack_timeout_minutes,
        },
    )
    count = enqueue_outbox_for_event(session, event, settings=settings)
    return True, count


def process_outbox_batch(
    session: Session,
    *,
    limit: int = 50,
    settings: Optional[Settings] = None,
) -> int:
    """Send pending outbox rows. Returns number successfully sent."""
    settings = settings or get_settings()
    rows = session.execute(
        text(
            """
            SELECT o.id, o.event_id, o.channel, o.chat_id, o.attempts,
                   e.payload
            FROM outbox o
            JOIN events e ON e.event_id = o.event_id
            WHERE o.status = :status
            ORDER BY o.id
            LIMIT :limit
            FOR UPDATE OF o SKIP LOCKED
            """
        ),
        {"status": OUTBOX_PENDING, "limit": limit},
    ).fetchall()

    sent = 0
    for row_id, event_id, channel, chat_id, attempts, payload in rows:
        token = settings.token_for_channel(channel)
        if not token:
            session.execute(
                text(
                    """
                    UPDATE outbox
                    SET status = :status, attempts = attempts + 1,
                        last_error = :err, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": row_id,
                    "status": OUTBOX_FAILED,
                    "err": "no telegram token for channel",
                },
            )
            continue

        try:
            event = EventIn.model_validate(payload if isinstance(payload, dict) else {})
            text_msg = format_message(event)
        except Exception:
            text_msg = f"[{event_id}] notification"

        try:
            send_message(token, int(chat_id), text_msg)
            session.execute(
                text(
                    """
                    UPDATE outbox
                    SET status = :status, attempts = attempts + 1,
                        last_error = NULL, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": row_id, "status": OUTBOX_SENT},
            )
            sent += 1
        except TelegramError as exc:
            logger.warning("outbox send failed id=%s: %s", row_id, exc)
            new_status = OUTBOX_FAILED if (attempts or 0) + 1 >= 5 else OUTBOX_PENDING
            session.execute(
                text(
                    """
                    UPDATE outbox
                    SET status = :status, attempts = attempts + 1,
                        last_error = :err, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": row_id,
                    "status": new_status,
                    "err": str(exc)[:500],
                },
            )
    return sent
