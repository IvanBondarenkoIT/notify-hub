# Каналы уведомлений

Три **отдельных** Telegram-бота (проверено live 18.09.2026). Имена — как у `@dimkava_promo_alerts_bot` / `@prices_monitoring_alerts_bot`: латиница, `snake_case`, суффикс `_alerts_bot`.

| Канал | Username | Отображаемое имя | Env токена |
|-------|----------|------------------|------------|
| public | [@dimkava_public_alerts_bot](https://t.me/dimkava_public_alerts_bot) | DimKava Public Alerts | `TELEGRAM_BOT_TOKEN` |
| private | [@dimkava_private_alerts_bot](https://t.me/dimkava_private_alerts_bot) | DimKava Private Alerts | `TELEGRAM_BOT_TOKEN_PRIVATE` |
| personal | [@dimkava_personal_alerts_bot](https://t.me/dimkava_personal_alerts_bot) | DimKava Personal Alerts | `TELEGRAM_BOT_TOKEN_PERSONAL` |

Три токена **разные**. Один long-poller на каждый. Старый `@prices_monitoring_alerts_bot` — только календарь, пока не включён cutover на хаб; **не** вешать на него второй `getUpdates`.

Подписка: `/start` → «Календарь» (префикс `calendar.*`). Для **personal** подписка запоминает chat_id, но рассылка идёт **только** если в событии указаны `targets.chat_ids`.

## public

- Общие оповещения (календарь, новости команды).
- Пустые `targets` → подписчики этого бота + `SEED_PUBLIC_CHAT_IDS`.
- Токен: `TELEGRAM_BOT_TOKEN`.

## private

- Служебные / чувствительные алерты.
- Подписчики private-бота + явные `chat_ids`. Если задан `PRIVATE_ALLOWLIST_CHAT_IDS` — только эти id.
- Токен: `TELEGRAM_BOT_TOKEN_PRIVATE` (без fallback на public в проде — токены разделены).

## personal

- Персональные задания / ECS.
- Доставка **только** `targets.chat_ids` / `user_ids`. Пустые targets → `accepted`, `outbox_enqueued: 0`.
- `require_ack=true` пишет в `acks` (кнопок «Подтвердить» пока нет).
- Токен: `TELEGRAM_BOT_TOKEN_PERSONAL`.

## Ack (подтверждение)

MVP: таблица `acks`; escalate ticker — stub (статус в БД, в Telegram не шлёт). Для пилота всегда `require_ack: false`.
