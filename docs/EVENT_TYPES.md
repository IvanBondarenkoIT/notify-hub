# Типы событий

Формат имени: `<domain>.<name>.v<version>` (например `calendar.event.v1`).

Подписка в боте на префикс `calendar.` матчит все типы, начинающиеся с `calendar.`.

## Рекомендуемые типы (пилот)

| type | Описание | Канал по умолчанию |
|------|----------|--------------------|
| `calendar.event.v1` | Календарное событие / напоминание | public |
| `calendar.reminder.v1` | Напоминание | public / personal |
| `ecs.task.assigned.v1` | Задача назначена (wave 2) | personal |
| `ecs.task.overdue.v1` | Просрочка (wave 2) | personal + ack |
| `stock.alert.v1` | Складской алерт (позже) | private |

## Поля тела события

См. API `POST /v1/events`: `event_id`, `type`, `severity`, `source`, `title`, `body`, `channels[]`, `targets`, `require_ack`, `ack_timeout_minutes`, `escalate_to`, `data`.

`data` — произвольный JSON для интеграций; хаб не интерпретирует его в MVP (кроме хранения в payload).
