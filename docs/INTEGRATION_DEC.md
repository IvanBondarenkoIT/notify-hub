# Integration DEC — events-calendar pilot

## Цель

Перевести календарные уведомления с отдельного Telegram-бота на **Notify Hub**, сохранив UX подписки в одном боте хаба.

## Контракт

`POST /v1/events` с заголовком `X-Api-Key` или `Authorization: Bearer …`.

Минимальный пример:

```json
{
  "event_id": "calendar-2026-09-17-meeting-42",
  "type": "calendar.event.v1",
  "severity": "info",
  "source": "events-calendar",
  "title": "Планерка",
  "body": "17.09.2026 10:00 Asia/Tbilisi",
  "channels": ["public"],
  "targets": { "chat_ids": [], "user_ids": [] },
  "require_ack": false,
  "ack_timeout_minutes": null,
  "escalate_to": { "chat_ids": [] },
  "data": {
    "starts_at": "2026-09-17T10:00:00+04:00",
    "calendar_id": "main"
  }
}
```

Правила:

1. `event_id` стабилен и уникален на стороне календаря (идемпотентность хаба).
2. `type` начинается с `calendar.` — попадают подписчики префикса `calendar.`.
3. Пустые `targets.chat_ids` — доставка только подписчикам (+ seed public ids).
4. Повторная отправка того же `event_id` безопасна (`duplicate`).

## Миграция с отдельного calendar-бота

1. Поднять notify-hub, выдать API key сервису календаря.
2. Пользователей перевести на бота хаба: `/start` → «Календарь».
3. В events-calendar заменить прямую отправку в Telegram на `POST /v1/events`.
4. Остановить старый calendar-бот после проверки доставки.
5. Не дублировать long-poll на одном токене (один poller на token в хабе).

## Вне скоупа

- firebird-db-proxy не меняем.
- Сложный recurrence / редактирование событий — на стороне календаря; хаб только нотифицирует.
