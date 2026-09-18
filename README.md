# DimKava / Granit Notification Hub (MVP)

Единый хаб уведомлений: Telegram (public / private / personal) + HTTP API приёма событий.

Стек: **Python 3.11+**, **FastAPI**, **PostgreSQL** (SQLAlchemy 2 + psycopg), Docker Compose.

## Быстрый старт (venv)

```bash
cd notify-hub
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# заполните TELEGRAM_BOT_TOKEN (+ _PRIVATE, _PERSONAL), SERVICE_API_KEYS, DATABASE_URL
export PYTHONPATH=src
```

Поднятие Postgres локально:

```bash
docker compose up -d db
# DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/notify_hub
python -m notify_hub          # API + poller + outbox worker
# или: python -m notify_hub api | worker | once
```

## Docker (всё вместе)

```bash
cp .env.example .env
# задайте три TELEGRAM_BOT_TOKEN* и ключи
docker compose up -d --build
curl -s http://localhost:8080/healthz
```

## Подписка в Telegram

Три бота (токены в `.env` хаба):

| Канал | Бот |
|-------|-----|
| public | [@dimkava_public_alerts_bot](https://t.me/dimkava_public_alerts_bot) |
| private | [@dimkava_private_alerts_bot](https://t.me/dimkava_private_alerts_bot) |
| personal | [@dimkava_personal_alerts_bot](https://t.me/dimkava_personal_alerts_bot) |

1. `/start` — объяснение + клавиатура «Календарь».
2. **«Календарь»** или слово `calendar` → подписка на `calendar.*`.
3. Повторная подписка — «уже подписаны».
4. `/stop` или **«Отписаться»**.

Канал **personal** подписку запоминает, но события приходят только с явным `targets.chat_ids`. Подробности: [`docs/CHANNELS.md`](docs/CHANNELS.md).

## Отправка события (curl)

```bash
curl -s -X POST http://localhost:8080/v1/events \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY" \
  -d '{
    "event_id": "cal-demo-001",
    "type": "calendar.event.v1",
    "severity": "info",
    "source": "events-calendar",
    "title": "Встреча",
    "body": "Завтра в 10:00",
    "channels": ["public"],
    "targets": {"chat_ids": [], "user_ids": []},
    "require_ack": false,
    "data": {}
  }'
```

Идемпотентность: повтор с тем же `event_id` вернёт `status: duplicate`.

Также поддерживается `Authorization: Bearer <key>`.

## Режимы CLI

| Команда | Назначение |
|---------|------------|
| `python -m notify_hub` | all-in-one: API + Telegram poller + outbox/ack worker |
| `python -m notify_hub api` | только HTTP API |
| `python -m notify_hub worker` | outbox + poller |
| `python -m notify_hub once` | один batch `getUpdates` |

## Тесты

```bash
export PYTHONPATH=src
pytest -q
# интеграция с Postgres (опционально):
# export DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/notify_hub
```

## Деплой (Debian)

Целевой хост через проект `D:\CursorProjects\ssh-alternative-server-connection` → каталог `~/apps/notify-hub`.

1. Скопировать проект на сервер в `~/apps/notify-hub`.
2. Положить `.env` (секреты не в git).
3. `docker compose -f docker-compose.prod.yml up -d --build`.
4. Держать compose 24/7 (`restart: unless-stopped`).
5. Позже можно перейти на образ: `ghcr.io/ivanbondarenkoit/notify-hub:latest`.

Документы: [`docs/INTEGRATION.md`](docs/INTEGRATION.md) (другие сервисы / агенты), [`AGENTS.md`](AGENTS.md), `docs/CHANNELS.md`, `docs/EVENT_TYPES.md`, `docs/INTEGRATION_DEC.md`, `ROADMAP.md`.

## Важно

- Только **PostgreSQL** (не SQLite).
- Один long-poller на каждый уникальный bot token.
- Ack: схема + stub escalate ticker в MVP.

## Для руководителя

Что задумано, что сделано и зачем — простым языком: [`docs/SUMMARY.md`](docs/SUMMARY.md).
