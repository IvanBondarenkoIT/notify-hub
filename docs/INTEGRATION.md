# Notify Hub — как пользоваться из другого проекта

Читать агентам и разработчикам сервисов, которые хотят слать уведомления.  
Хаб **принимает события по HTTP** и сам доставляет их в Telegram. Не ходить в Telegram Bot API напрямую, если событие идёт через хаб.

Репозиторий хаба: `D:\CursorProjects\notify-hub` · GitHub: https://github.com/IvanBondarenkoIT/notify-hub

## Куда стучаться

| Где крутится вызывающий код | URL |
|-----------------------------|-----|
| Тот же Debian-хост (cron, ssh, контейнер с `network_mode: host`) | `http://127.0.0.1:8080` |
| Другой Docker-контейнер на том же хосте | `http://172.17.0.1:8080` (docker bridge gateway) |
| Локальная разработка хаба | `http://127.0.0.1:8080` |

Проверка: `GET {URL}/healthz` → `{"status":"ok","service":"notify-hub"}`.

Env вызывающего сервиса (секреты не в git):

```
NOTIFY_HUB_URL=http://127.0.0.1:8080
NOTIFY_HUB_API_KEY=<ключ из SERVICE_API_KEYS хаба>
```

Ключ выдаёт тот, кто держит `~/apps/notify-hub/.env`. Не брать Telegram-токен календаря для HTTP — для API нужен `SERVICE_API_KEYS`.

## Запрос

`POST {NOTIFY_HUB_URL}/v1/events`

Заголовки: `Content-Type: application/json` и `X-Api-Key: {NOTIFY_HUB_API_KEY}`  
(альтернатива: `Authorization: Bearer {NOTIFY_HUB_API_KEY}`).

```json
{
  "event_id": "myapp-2026-09-17-unique-id",
  "type": "calendar.event.v1",
  "severity": "info",
  "source": "my-service-name",
  "title": "Заголовок",
  "body": "Текст сообщения",
  "channels": ["public"],
  "targets": { "chat_ids": [], "user_ids": [] },
  "require_ack": false,
  "data": {}
}
```

Ответ `200`:

- `"status": "accepted"` — новое событие, смотри `outbox_enqueued`
- `"status": "duplicate"` — такой `event_id` уже был, повторно не шлётся

`401` — нет/неверный ключ.

## Как выбираются получатели

| Что передали | Кто получит |
|--------------|-------------|
| `targets.chat_ids`: конкретные id | эти чаты (плюс подписчики, кроме канала `personal`) |
| `targets.chat_ids`: `[]` на `public` | подписчики бота на префикс типа + `SEED_PUBLIC_CHAT_IDS` |
| канал `personal` | только `targets.chat_ids` / `user_ids` |

Пилот календаря: `type` `calendar.event.v1`, канал **`public`**, бот [@dimkava_public_alerts_bot](https://t.me/dimkava_public_alerts_bot). Подписка: `/start` → «Календарь».

ECS: канал **`personal`**, бот [@dimkava_personal_alerts_bot](https://t.me/dimkava_personal_alerts_bot), в событии обязательны `targets.chat_ids`.

Служебные алерты: канал **`private`**, [@dimkava_private_alerts_bot](https://t.me/dimkava_private_alerts_bot).

## Правила `event_id` и `type`

1. `event_id` стабильный и уникальный **на вашей стороне** (не `uuid()` на каждый ретрай). Повтор с тем же id безопасен.
2. `type`: `<domain>.<name>.v<version>`, например `calendar.event.v1`, `stock.alert.v1`.
3. Подписка `calendar.` матчит все `calendar.…`.
4. `channels`: только `public` | `private` | `personal`. Иначе отбрасываются; пустой список → `public`.
5. `data` — любой JSON; хаб его не разбирает, только кладёт в payload.
6. **`require_ack: false` всегда**, пока в хабе нет кнопок «Подтвердить» и реальной эскалации в Telegram (таблица `acks` есть, UX — stub).
7. Канал `personal` доставляет **только** `targets.chat_ids` / `user_ids` (подписок нет). Пустые targets → `accepted` и `outbox_enqueued: 0` без ошибки.

## Минимальный клиент (Python)

```python
import json
import os
import urllib.request

def notify(event: dict) -> dict:
    url = os.environ["NOTIFY_HUB_URL"].rstrip("/") + "/v1/events"
    key = os.environ["NOTIFY_HUB_API_KEY"]
    req = urllib.request.Request(
        url,
        data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Api-Key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))
```

Не логировать API key и bot token.

## Чего не делать

- Не вызывать `api.telegram.org` из сервиса, если событие уже уходит в хаб (двойные сообщения).
- Не поднимать второй `getUpdates` long-poller на том же bot token (хаб уже поллит, если токен задан). `sendMessage` из другого сервиса на том же токене допустим, пока миграция не завершена.
- Не коммитить `.env` хаба и ключи.
- Не ходить в `firebird-db-proxy` из хаба и не ждать, что хаб ходит в Jira — только готовые события.

## Потребители (промпты агентам)

Код клиентов в этих репо **ещё не внедрён**. Промпт — инструкция, как подключить доставку, когда скажут писать код.

| Сервис | Промпт | Канал |
|--------|--------|-------|
| events-calendar | [`D:\CursorProjects\events-calendar\PROMPTS\NOTIFY_HUB.md`](D:\CursorProjects\events-calendar\PROMPTS\NOTIFY_HUB.md) | `public`, `calendar.event.v1` |
| execution-control-system | [`D:\CursorProjects\xAgents\execution-control-system\PROMPTS\NOTIFY_HUB.md`](D:\CursorProjects\xAgents\execution-control-system\PROMPTS\NOTIFY_HUB.md) | `personal`, `ecs.*` |

Приём API и отправка в Telegram на хабе **готовы**. Live 18.09.2026: события дошли в public, private и personal ботов (три разных токена на Debian `~/apps/notify-hub`).

Боты: [`CHANNELS.md`](CHANNELS.md). Календарь и ECS к хабу ещё не переключены — см. промпты выше.

## Деплой хаба (если чините сам хаб)

Из `D:\CursorProjects\ssh-alternative-server-connection`:

```powershell
python scripts/deploy_app.py notify-hub
python scripts/test_app.py notify-hub
```

Прод-каталог: `~/apps/notify-hub`. Сборка на сервере: `docker compose -f docker-compose.prod.yml up -d --build`.

## Смежные доки в этом репо

- [`CHANNELS.md`](CHANNELS.md) — public / private / personal
- [`EVENT_TYPES.md`](EVENT_TYPES.md) — имена типов
- [`INTEGRATION_DEC.md`](INTEGRATION_DEC.md) — пилот events-calendar
- [`../ROADMAP.md`](../ROADMAP.md) — волны
- [`../AGENTS.md`](../AGENTS.md) — как менять код хаба
- [`SUMMARY.md`](SUMMARY.md) — сводка для руководителя (зачем хаб и что уже работает)
