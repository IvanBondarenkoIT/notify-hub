# Каналы уведомлений

Три логических канала Telegram:

## public

- Общие оповещения (календарь, новости команды).
- Подписка через бота (`/start` → «Календарь»).
- Опционально `SEED_PUBLIC_CHAT_IDS` — всегда доставлять в эти чаты.
- Токен: `TELEGRAM_BOT_TOKEN` (primary).

## private

- Служебные / чувствительные алерты.
- Фильтр: `PRIVATE_ALLOWLIST_CHAT_IDS` (если задан — только эти chat_id).
- Токен: `TELEGRAM_BOT_TOKEN_PRIVATE` или fallback на primary.

## personal

- Персональные задания / контроль исполнения (wave 2).
- Доставка в основном по `targets.chat_ids` / `user_ids`.
- `require_ack=true` создаёт строки в `acks` (MVP: schema + stub).
- Токен: `TELEGRAM_BOT_TOKEN_PERSONAL` или fallback на primary.

## Ack (подтверждение)

Назначение personal+ack: ответственный должен подтвердить получение критичного события.

MVP:

- Таблица `acks (event_id, chat_id, status, updated_at)`.
- Escalate ticker — **stub**: по таймауту статус → `escalated` / `expired` и лог; реальной отправки в `escalate_to` ещё нет.

Позже: кнопки «Подтвердить», эскалация в чаты из `escalate_to.chat_ids`.
