# Agent notes — notify-hub

Единый Notification Hub DimKava/Granit. Внешние сервисы **не** пишут в Telegram сами: шлют HTTP-событие сюда.

Полный контракт для других репо: [`docs/INTEGRATION.md`](docs/INTEGRATION.md).  
Сводка для руководителя: [`docs/SUMMARY.md`](docs/SUMMARY.md).  
Каналы / типы: [`docs/CHANNELS.md`](docs/CHANNELS.md), [`docs/EVENT_TYPES.md`](docs/EVENT_TYPES.md).  
Календарь: [`docs/INTEGRATION_DEC.md`](docs/INTEGRATION_DEC.md).

## Что это

- API: `GET /healthz`, `POST /v1/events` (ключ `X-Api-Key` или `Bearer`)
- Три бота на проде (live 18.09.2026): public / private / personal — [`docs/CHANNELS.md`](docs/CHANNELS.md)
- Идемпотентность по `event_id`
- Прод: Debian `~/apps/notify-hub`, compose 24/7, порт **8080** на хосте
- personal доставляет только явные `targets.chat_ids`

## Как трогать этот репо

- Только PostgreSQL, без SQLite
- Секреты только в `.env` (gitignored). Не коммитить токены, пароли, API keys
- Один long-poller на каждый уникальный bot token (не запускать второй poller с тем же токеном)
- Ack / escalate в MVP — stub; не обещать кнопки «Подтвердить»
- Деплой: из `D:\CursorProjects\ssh-alternative-server-connection`  
  `python scripts/deploy_app.py notify-hub` затем `python scripts/test_app.py notify-hub`
- Не слать live в Telegram без явной просьбы

## Локально

```powershell
copy .env.example .env
docker compose up -d --build
curl -s http://localhost:8080/healthz
```
