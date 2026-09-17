"""Subscription helpers (pure + DB-backed)."""

from __future__ import annotations

from typing import Iterable, List, Sequence, Set, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

# Default prefix when user subscribes via calendar keyword/button
DEFAULT_CALENDAR_PREFIX = "calendar."


def normalize_prefix(prefix: str) -> str:
    p = (prefix or "").strip()
    if not p:
        return DEFAULT_CALENDAR_PREFIX
    if not p.endswith(".") and "." not in p.rstrip("."):
        # allow exact type or prefix; ensure trailing dot for prefix semantics
        if p.endswith("*"):
            p = p[:-1]
        if not p.endswith("."):
            p = p + "."
    return p


def event_matches_prefix(event_type: str, prefix: str) -> bool:
    """Return True if event_type matches subscription prefix.

    Prefix ending with '.' matches that namespace (calendar. → calendar.event.v1).
    Exact equality also matches.
    """
    et = (event_type or "").strip()
    pref = (prefix or "").strip()
    if not et or not pref:
        return False
    if et == pref:
        return True
    if pref.endswith("."):
        return et.startswith(pref) or et.startswith(pref[:-1] + ".")
    if pref.endswith("*"):
        return et.startswith(pref[:-1])
    # treat bare prefix without dot as namespace start
    return et == pref or et.startswith(pref + ".")


def filter_matching_subscriptions(
    event_type: str,
    subscriptions: Sequence[Tuple[int, str, str]],
) -> List[Tuple[int, str, str]]:
    """Filter (chat_id, prefix, channel) tuples that match event_type."""
    return [
        (chat_id, prefix, channel)
        for chat_id, prefix, channel in subscriptions
        if event_matches_prefix(event_type, prefix)
    ]


def merge_chat_targets(
    explicit_chat_ids: Iterable[int],
    subscriber_chat_ids: Iterable[int],
) -> List[int]:
    """Deduplicate chat ids preserving order (explicit first)."""
    seen: Set[int] = set()
    result: List[int] = []
    for cid in list(explicit_chat_ids) + list(subscriber_chat_ids):
        if cid is None:
            continue
        try:
            value = int(cid)
        except (TypeError, ValueError):
            continue
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def subscribe(
    session: Session,
    chat_id: int,
    event_type_prefix: str,
    channel: str = "public",
) -> bool:
    """Insert subscription. Returns True if newly created, False if already existed."""
    prefix = normalize_prefix(event_type_prefix)
    channel = (channel or "public").lower()
    existing = session.execute(
        text(
            """
            SELECT 1 FROM subscriptions
            WHERE chat_id = :chat_id
              AND event_type_prefix = :prefix
              AND channel = :channel
            """
        ),
        {"chat_id": chat_id, "prefix": prefix, "channel": channel},
    ).first()
    if existing:
        return False
    session.execute(
        text(
            """
            INSERT INTO subscriptions (chat_id, event_type_prefix, channel)
            VALUES (:chat_id, :prefix, :channel)
            ON CONFLICT (chat_id, event_type_prefix, channel) DO NOTHING
            """
        ),
        {"chat_id": chat_id, "prefix": prefix, "channel": channel},
    )
    return True


def unsubscribe(
    session: Session,
    chat_id: int,
    event_type_prefix: str | None = None,
    channel: str | None = None,
) -> int:
    """Remove subscriptions. Returns number of deleted rows."""
    if event_type_prefix and channel:
        prefix = normalize_prefix(event_type_prefix)
        result = session.execute(
            text(
                """
                DELETE FROM subscriptions
                WHERE chat_id = :chat_id
                  AND event_type_prefix = :prefix
                  AND channel = :channel
                """
            ),
            {"chat_id": chat_id, "prefix": prefix, "channel": channel},
        )
    elif event_type_prefix:
        prefix = normalize_prefix(event_type_prefix)
        result = session.execute(
            text(
                """
                DELETE FROM subscriptions
                WHERE chat_id = :chat_id AND event_type_prefix = :prefix
                """
            ),
            {"chat_id": chat_id, "prefix": prefix},
        )
    else:
        result = session.execute(
            text("DELETE FROM subscriptions WHERE chat_id = :chat_id"),
            {"chat_id": chat_id},
        )
    return int(result.rowcount or 0)


def list_subscribers_for_event(
    session: Session,
    event_type: str,
    channel: str,
) -> List[int]:
    """Return chat_ids subscribed to prefixes matching event_type on channel."""
    rows = session.execute(
        text(
            """
            SELECT chat_id, event_type_prefix
            FROM subscriptions
            WHERE channel = :channel
            """
        ),
        {"channel": channel},
    ).fetchall()
    chat_ids: List[int] = []
    seen: Set[int] = set()
    for chat_id, prefix in rows:
        if event_matches_prefix(event_type, prefix) and chat_id not in seen:
            seen.add(chat_id)
            chat_ids.append(int(chat_id))
    return chat_ids


def is_subscribed(
    session: Session,
    chat_id: int,
    event_type_prefix: str,
    channel: str = "public",
) -> bool:
    prefix = normalize_prefix(event_type_prefix)
    row = session.execute(
        text(
            """
            SELECT 1 FROM subscriptions
            WHERE chat_id = :chat_id
              AND event_type_prefix = :prefix
              AND channel = :channel
            """
        ),
        {"chat_id": chat_id, "prefix": prefix, "channel": channel},
    ).first()
    return row is not None
