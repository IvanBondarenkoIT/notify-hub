# Roadmap — Notification Hub

## Wave 0 — Hub MVP (сейчас)

- HTTP `POST /v1/events` + idempotency по `event_id`
- PostgreSQL: events / outbox / subscriptions / acks
- Telegram: public / private / personal (токены + fallback на primary)
- Подписка через бота (calendar.*), outbox worker, all-in-one процесс
- Ack: таблицы + stub escalate ticker (без реальной эскалации в TG)

## Wave 1 — events-calendar pilot

- Источник: сервис календаря шлёт `calendar.event.v1` в хаб
- Миграция с отдельного calendar-бота на подписки хаба
- Контракт: см. `docs/INTEGRATION_DEC.md`
- Стабилизация доставки и форматов сообщений

## Wave 2 — execution-control-system (personal + ack)

- Personal-канал для ответственных
- Реальный ack UX (кнопки / команды) и escalate_to
- Таймауты, повторные напоминания, аудит

## Далее — stock-safety-monitor

- События склада / безопасности через тот же `/v1/events`
- Private allowlist + severity routing
- После стабилизации personal+ack

## Вне скоупа хаба

- **firebird-db-proxy** — не трогаем; остаётся отдельным сервисом
- Хаб только принимает уже сформированные события по HTTP
