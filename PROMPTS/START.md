# PROMPT: DimKava / Granit Notification Hub MVP (START)

Создай полный рабочий Python-проект **notify-hub** — единый Notification Hub для DimKava/Granit.

## Стек (обязательно)

- Python 3.11+
- FastAPI + uvicorn
- **PostgreSQL** (НЕ SQLite) через SQLAlchemy 2.0 + `psycopg[binary]`
- requests, python-dotenv, pytest
- Docker Compose: сервисы `db` (postgres:16-alpine) и `hub` (приложение)
- Один процесс может запускать API + telegram poller + outbox worker (MVP); также CLI-режимы

## Каналы

- public / private / personal (конфиг)
- Один основной токен: `TELEGRAM_BOT_TOKEN`. Опционально `TELEGRAM_BOT_TOKEN_PRIVATE` и `TELEGRAM_BOT_TOKEN_PERSONAL` — если пусто, fallback на primary.
- `PRIVATE_ALLOWLIST_CHAT_IDS` для private
- Ack: schema + stub only в MVP (таблицы/поля есть; escalate ticker может только логировать stub)

## API

- `POST /v1/events` с Bearer или `X-Api-Key` (`SERVICE_API_KEYS` через запятую)
- Идемпотентность по `event_id`
- `GET /healthz`
- Тело: `event_id`, `type`, `severity`, `source`, `title`, `body`, `channels[]`, `targets{chat_ids,user_ids}`, `require_ack`, `ack_timeout_minutes`, `escalate_to{chat_ids}`, `data{}`

## Bot UX (русский)

- `/start` — объяснить DimKava notify hub; reply keyboard с «Календарь»
- keyword calendar / кнопка → подписка на `calendar.*`
- уже подписан — мягкое сообщение
- `/stop` или «Отписаться» → отписка
- long-poll `getUpdates`, один poller на каждый уникальный token

## Структура проекта

```
notify-hub/
  README.md
  ROADMAP.md
  PROMPTS/START.md
  docs/EVENT_TYPES.md
  docs/INTEGRATION_DEC.md
  docs/CHANNELS.md
  requirements.txt
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  docker-compose.prod.yml
  src/notify_hub/
    __init__.py
    __main__.py
    config.py
    db.py
    models.py
    api.py
    outbox.py
    subscribers.py
    telegram_api.py
    bot_handler.py
    ack.py
    main.py
  tests/
    test_subscribers.py
    test_outbox_idempotency.py
    test_ack.py
```

## Схема БД (Postgres)

- `events` (event_id PK, type, payload jsonb, status, created_at, …)
- `outbox` (id, event_id, channel, chat_id, status, attempts, …) UNIQUE(event_id, channel, chat_id)
- `subscriptions` (chat_id, event_type_prefix, channel, created_at) unique together
- `acks` (event_id, chat_id, status, updated_at) — stub usable later

На старте создавать таблицы если нет (простой SQL в `db.py`).

## CLI

```text
python -m notify_hub           # all-in-one
python -m notify_hub api
python -m notify_hub worker
python -m notify_hub once      # один getUpdates batch
```

## .env.example

Включить как минимум:

```
APP_TIMEZONE=Asia/Tbilisi
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8080
SERVICE_API_KEYS=
POSTGRES_PASSWORD=
DATABASE_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_TOKEN_PRIVATE=
TELEGRAM_BOT_TOKEN_PERSONAL=
TELEGRAM_DISABLE_SSL_VERIFY=false
PRIVATE_ALLOWLIST_CHAT_IDS=
SEED_PUBLIC_CHAT_IDS=
TELEGRAM_SUBSCRIBE_KEYWORD=calendar
ACK_CHECK_INTERVAL_SECONDS=60
DEFAULT_ACK_TIMEOUT_MINUTES=30
```

## Документы

- **ROADMAP**: wave0 hub → wave1 events-calendar pilot → wave2 execution-control-system personal+ack → stock-safety-monitor позже; firebird-db-proxy не трогать
- **INTEGRATION_DEC**: POST calendar.event.v1; миграция с отдельного calendar-бота
- **CHANNELS**: три канала + personal ack
- **README** (RU): setup, venv, docker, тест подписки, curl event, деплой через ssh-alternative-server-connection → `~/apps/notify-hub`, compose 24/7, позже `ghcr.io/ivanbondarenkoit/notify-hub:latest`

## Качество

- Реальный рабочий код (не пустые stubs)
- Тесты без живого Telegram; pure helpers без БД где возможно
- Интеграционные тесты с Postgres — skip если нет `DATABASE_URL`
- **Запрещено SQLite**
- Не класть реальные секреты; не вызывать Telegram; не деплоить без запроса

## Критерий готовности

- `python -m compileall src` без ошибок
- `pytest` проходит unit-тесты
- `docker compose` поднимает `db` + `hub`
