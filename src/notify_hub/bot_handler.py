"""Telegram update handling (Russian UX)."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from notify_hub import subscribers
from notify_hub.config import Settings, get_settings
from notify_hub.telegram_api import calendar_keyboard, remove_keyboard, send_message

logger = logging.getLogger(__name__)

START_TEXT = (
    "👋 Это *DimKava Notify Hub* — единый хаб уведомлений Granit/DimKava.\n\n"
    "Подпишитесь на календарные события кнопкой «Календарь» "
    "или напишите слово calendar.\n"
    "Отписка: /stop или «Отписаться»."
)

ALREADY_SUBSCRIBED = "Вы уже подписаны на календарные уведомления ✅"
SUBSCRIBED_OK = "Подписка на calendar.* оформлена. Буду присылать события сюда."
UNSUBSCRIBED = "Вы отписаны от уведомлений. Вернуться: /start или «Календарь»."
HELP_FALLBACK = "Команды: /start, /stop. Кнопки: «Календарь», «Отписаться»."


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:32]


def get_offset(session: Session, token: str) -> int:
    row = session.execute(
        text(
            "SELECT update_offset FROM telegram_offsets WHERE token_hash = :h"
        ),
        {"h": token_hash(token)},
    ).first()
    return int(row[0]) if row else 0


def set_offset(session: Session, token: str, offset: int) -> None:
    session.execute(
        text(
            """
            INSERT INTO telegram_offsets (token_hash, update_offset, updated_at)
            VALUES (:h, :offset, NOW())
            ON CONFLICT (token_hash) DO UPDATE
            SET update_offset = EXCLUDED.update_offset, updated_at = NOW()
            """
        ),
        {"h": token_hash(token), "offset": offset},
    )


def _text_of(message: Dict[str, Any]) -> str:
    return (message.get("text") or "").strip()


def _is_calendar_intent(text: str, keyword: str) -> bool:
    lowered = text.lower().strip()
    kw = (keyword or "calendar").lower()
    if lowered in ("/calendar", kw, f"/{kw}"):
        return True
    if "календарь" in lowered:
        return True
    if kw in lowered and not lowered.startswith("/"):
        return True
    return False


def _is_unsubscribe_intent(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered in (
        "/stop",
        "отписаться",
        "unsubscribe",
        "/unsubscribe",
    ) or lowered.startswith("/stop")


def channel_for_token(settings: Settings, token: str) -> str:
    """Best-effort channel label for subscriptions created via this token."""
    if (
        settings.telegram_bot_token_private
        and token == settings.telegram_bot_token_private
        and token != settings.telegram_bot_token
    ):
        return "private"
    if (
        settings.telegram_bot_token_personal
        and token == settings.telegram_bot_token_personal
        and token != settings.telegram_bot_token
    ):
        return "personal"
    return "public"


def handle_message(
    session: Session,
    token: str,
    message: Dict[str, Any],
    settings: Optional[Settings] = None,
) -> None:
    settings = settings or get_settings()
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return
    chat_id = int(chat_id)
    text = _text_of(message)
    channel = channel_for_token(settings, token)
    keyword = settings.telegram_subscribe_keyword

    # Private channel allowlist gate for non-start messages (soft)
    if channel == "private" and settings.private_allowlist_chat_ids:
        if chat_id not in settings.private_allowlist_chat_ids:
            if text.startswith("/start"):
                send_message(
                    token,
                    chat_id,
                    "Доступ к private-каналу ограничен allowlist.",
                )
            return

    if text.startswith("/start"):
        send_message(
            token,
            chat_id,
            START_TEXT,
            reply_markup=calendar_keyboard(),
            parse_mode="Markdown",
        )
        return

    if _is_unsubscribe_intent(text):
        subscribers.unsubscribe(session, chat_id)
        send_message(
            token,
            chat_id,
            UNSUBSCRIBED,
            reply_markup=remove_keyboard(),
        )
        return

    if _is_calendar_intent(text, keyword):
        created = subscribers.subscribe(
            session, chat_id, subscribers.DEFAULT_CALENDAR_PREFIX, channel=channel
        )
        if created:
            send_message(
                token,
                chat_id,
                SUBSCRIBED_OK,
                reply_markup=calendar_keyboard(),
            )
        else:
            send_message(
                token,
                chat_id,
                ALREADY_SUBSCRIBED,
                reply_markup=calendar_keyboard(),
            )
        return

    if text.startswith("/"):
        send_message(token, chat_id, HELP_FALLBACK, reply_markup=calendar_keyboard())


def process_update(
    session: Session,
    token: str,
    update: Dict[str, Any],
    settings: Optional[Settings] = None,
) -> None:
    message = update.get("message") or update.get("edited_message")
    if message:
        handle_message(session, token, message, settings=settings)


def process_updates_batch(
    session: Session,
    token: str,
    updates: list,
    settings: Optional[Settings] = None,
) -> int:
    """Process updates and advance offset. Returns max update_id processed."""
    max_id = 0
    for upd in updates:
        uid = int(upd.get("update_id") or 0)
        if uid > max_id:
            max_id = uid
        try:
            process_update(session, token, upd, settings=settings)
        except Exception:
            logger.exception("Failed to process update_id=%s", uid)
    if max_id:
        set_offset(session, token, max_id + 1)
    return max_id
