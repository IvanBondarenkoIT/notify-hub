"""Acknowledgement schema + stub logic for MVP (no real escalation yet)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ACK_PENDING = "pending"
ACK_ACKNOWLEDGED = "acknowledged"
ACK_ESCALATED = "escalated"
ACK_EXPIRED = "expired"

VALID_TRANSITIONS = {
    ACK_PENDING: {ACK_ACKNOWLEDGED, ACK_ESCALATED, ACK_EXPIRED},
    ACK_ACKNOWLEDGED: set(),
    ACK_ESCALATED: {ACK_ACKNOWLEDGED},
    ACK_EXPIRED: {ACK_ACKNOWLEDGED},
}


def can_transition(current: str, new_status: str) -> bool:
    """Pure helper: whether status transition is allowed."""
    if current == new_status:
        return True
    return new_status in VALID_TRANSITIONS.get(current, set())


def next_ack_status_on_timeout(
    current: str,
    *,
    timed_out: bool,
    escalate_configured: bool,
) -> Optional[str]:
    """Pure helper for escalate ticker stub."""
    if current != ACK_PENDING or not timed_out:
        return None
    if escalate_configured:
        return ACK_ESCALATED
    return ACK_EXPIRED


def ensure_ack_rows(
    session: Session,
    event_id: str,
    chat_ids: Iterable[int],
) -> int:
    """Create pending ack rows for chat_ids. Returns number inserted."""
    inserted = 0
    for chat_id in chat_ids:
        result = session.execute(
            text(
                """
                INSERT INTO acks (event_id, chat_id, status, updated_at)
                VALUES (:event_id, :chat_id, :status, NOW())
                ON CONFLICT (event_id, chat_id) DO NOTHING
                """
            ),
            {
                "event_id": event_id,
                "chat_id": int(chat_id),
                "status": ACK_PENDING,
            },
        )
        if result.rowcount:
            inserted += 1
    return inserted


def mark_acknowledged(session: Session, event_id: str, chat_id: int) -> bool:
    row = session.execute(
        text(
            "SELECT status FROM acks WHERE event_id = :event_id AND chat_id = :chat_id"
        ),
        {"event_id": event_id, "chat_id": chat_id},
    ).first()
    if not row:
        return False
    current = row[0]
    if not can_transition(current, ACK_ACKNOWLEDGED):
        return False
    session.execute(
        text(
            """
            UPDATE acks
            SET status = :status, updated_at = NOW()
            WHERE event_id = :event_id AND chat_id = :chat_id
            """
        ),
        {
            "event_id": event_id,
            "chat_id": chat_id,
            "status": ACK_ACKNOWLEDGED,
        },
    )
    return True


def run_escalate_ticker_stub(session: Session, default_timeout_minutes: int = 30) -> int:
    """MVP stub: find pending acks past timeout and log escalate intent.

    Does not send Telegram messages; only updates status and logs.
    Returns number of rows transitioned.
    """
    rows = session.execute(
        text(
            """
            SELECT a.event_id, a.chat_id, a.status, e.ack_timeout_minutes,
                   e.created_at, e.payload
            FROM acks a
            JOIN events e ON e.event_id = a.event_id
            WHERE a.status = :pending AND e.require_ack = TRUE
            """
        ),
        {"pending": ACK_PENDING},
    ).fetchall()

    now = datetime.now(timezone.utc)
    changed = 0
    for event_id, chat_id, status, timeout_min, created_at, payload in rows:
        timeout = timeout_min if timeout_min is not None else default_timeout_minutes
        created = created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        timed_out = now >= created + timedelta(minutes=int(timeout))
        escalate_to = []
        if isinstance(payload, dict):
            esc = payload.get("escalate_to") or {}
            if isinstance(esc, dict):
                escalate_to = esc.get("chat_ids") or []
        new_status = next_ack_status_on_timeout(
            status,
            timed_out=timed_out,
            escalate_configured=bool(escalate_to),
        )
        if not new_status or not can_transition(status, new_status):
            continue
        session.execute(
            text(
                """
                UPDATE acks
                SET status = :status, updated_at = NOW()
                WHERE event_id = :event_id AND chat_id = :chat_id
                """
            ),
            {
                "event_id": event_id,
                "chat_id": chat_id,
                "status": new_status,
            },
        )
        logger.info(
            "ack escalate stub: event_id=%s chat_id=%s -> %s (escalate_to=%s)",
            event_id,
            chat_id,
            new_status,
            escalate_to,
        )
        changed += 1
    return changed


def list_pending_acks(session: Session, event_id: str) -> List[int]:
    rows = session.execute(
        text(
            """
            SELECT chat_id FROM acks
            WHERE event_id = :event_id AND status = :status
            """
        ),
        {"event_id": event_id, "status": ACK_PENDING},
    ).fetchall()
    return [int(r[0]) for r in rows]
