"""Application configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _split_int_csv(value: str | None) -> List[int]:
    result: List[int] = []
    for part in _split_csv(value):
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


@dataclass(frozen=True)
class Settings:
    app_timezone: str = "Asia/Tbilisi"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    service_api_keys: List[str] = field(default_factory=list)
    database_url: str = "postgresql+psycopg://notify:notify@localhost:5432/notify_hub"
    telegram_bot_token: str = ""
    telegram_bot_token_private: str = ""
    telegram_bot_token_personal: str = ""
    telegram_disable_ssl_verify: bool = False
    private_allowlist_chat_ids: List[int] = field(default_factory=list)
    seed_public_chat_ids: List[int] = field(default_factory=list)
    telegram_subscribe_keyword: str = "calendar"
    ack_check_interval_seconds: int = 60
    default_ack_timeout_minutes: int = 30

    def token_for_channel(self, channel: str) -> str:
        """Resolve Telegram bot token for a channel with primary fallback."""
        channel = (channel or "public").lower()
        if channel == "private":
            return self.telegram_bot_token_private or self.telegram_bot_token
        if channel == "personal":
            return self.telegram_bot_token_personal or self.telegram_bot_token
        return self.telegram_bot_token

    def unique_tokens(self) -> List[str]:
        """Unique non-empty tokens for pollers (one poller per token)."""
        seen: set[str] = set()
        ordered: List[str] = []
        for token in (
            self.telegram_bot_token,
            self.telegram_bot_token_private,
            self.telegram_bot_token_personal,
        ):
            if token and token not in seen:
                seen.add(token)
                ordered.append(token)
        return ordered

    def is_valid_api_key(self, key: str | None) -> bool:
        if not key or not self.service_api_keys:
            return False
        return key in self.service_api_keys


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_timezone=os.getenv("APP_TIMEZONE", "Asia/Tbilisi"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8080")),
        service_api_keys=_split_csv(os.getenv("SERVICE_API_KEYS", "dev-key-change-me")),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://notify:notify@localhost:5432/notify_hub",
        ),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_bot_token_private=os.getenv("TELEGRAM_BOT_TOKEN_PRIVATE", "").strip(),
        telegram_bot_token_personal=os.getenv("TELEGRAM_BOT_TOKEN_PERSONAL", "").strip(),
        telegram_disable_ssl_verify=os.getenv(
            "TELEGRAM_DISABLE_SSL_VERIFY", "false"
        ).lower()
        in ("1", "true", "yes"),
        private_allowlist_chat_ids=_split_int_csv(
            os.getenv("PRIVATE_ALLOWLIST_CHAT_IDS", "")
        ),
        seed_public_chat_ids=_split_int_csv(os.getenv("SEED_PUBLIC_CHAT_IDS", "")),
        telegram_subscribe_keyword=os.getenv(
            "TELEGRAM_SUBSCRIBE_KEYWORD", "calendar"
        ).strip()
        or "calendar",
        ack_check_interval_seconds=int(os.getenv("ACK_CHECK_INTERVAL_SECONDS", "60")),
        default_ack_timeout_minutes=int(
            os.getenv("DEFAULT_ACK_TIMEOUT_MINUTES", "30")
        ),
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
