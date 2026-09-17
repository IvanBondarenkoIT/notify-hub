"""Thin Telegram Bot API client (requests)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from notify_hub.config import get_settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramError(RuntimeError):
    pass


def _session() -> requests.Session:
    s = requests.Session()
    settings = get_settings()
    if settings.telegram_disable_ssl_verify:
        s.verify = False
    return s


def api_call(
    token: str,
    method: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    if not token:
        raise TelegramError("Telegram token is empty")
    url = f"{TELEGRAM_API}/bot{token}/{method}"
    with _session() as http:
        resp = http.post(url, json=payload or {}, timeout=timeout)
    try:
        data = resp.json()
    except Exception as exc:
        raise TelegramError(f"Invalid JSON from Telegram: {exc}") from exc
    if not data.get("ok"):
        raise TelegramError(data.get("description") or f"Telegram error HTTP {resp.status_code}")
    return data


def get_updates(
    token: str,
    offset: Optional[int] = None,
    timeout: int = 25,
) -> List[Dict[str, Any]]:
    payload: Dict[str, Any] = {
        "timeout": timeout,
        "allowed_updates": ["message", "callback_query"],
    }
    if offset is not None:
        payload["offset"] = offset
    # long poll needs larger HTTP timeout
    data = api_call(token, "getUpdates", payload, timeout=float(timeout + 15))
    result = data.get("result") or []
    return list(result)


def send_message(
    token: str,
    chat_id: int,
    text: str,
    *,
    reply_markup: Optional[Dict[str, Any]] = None,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return api_call(token, "sendMessage", payload, timeout=30.0)


def calendar_keyboard() -> Dict[str, Any]:
    """Russian reply keyboard with Calendar and Unsubscribe."""
    return {
        "keyboard": [
            [{"text": "Календарь"}],
            [{"text": "Отписаться"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def remove_keyboard() -> Dict[str, Any]:
    return {"remove_keyboard": True}
