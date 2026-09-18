# Типы событий

Формат имени: `<domain>.<name>.v<version>` (например `calendar.event.v1`).

Подписка в боте `@dimkava_public_alerts_bot` (канал public) на префикс `calendar.` матчит все типы, начинающиеся с `calendar.`. ECS идёт в `@dimkava_personal_alerts_bot` с явными `chat_ids`. Список ботов: [`CHANNELS.md`](CHANNELS.md).

## Рекомендуемые типы (пилот)

| type | Описание | Канал по умолчанию |
|------|----------|--------------------|
| `calendar.event.v1` | Календарное событие / напоминание | public |
| `calendar.reminder.v1` | Напоминание (nags) | public |
| `ecs.digest.mon.v1` | Понедельник: сводка планов недели | personal |
| `ecs.digest.wed.v1` | Среда: P0 at-risk для владельца | personal |
| `ecs.p0.reminder.v1` | Среда: напомни исполнителю обновить P0 | personal |
| `ecs.p0.at_risk.v1` | P0 не в Done | personal |
| `ecs.score.weekly.v1` | Пятница: персональный балл | personal |
| `ecs.plan.missing.v1` | Нет weekly-plan к понедельнику | personal |
| `ecs.task.assigned.v1` | Задача / план назначены | personal |
| `ecs.task.overdue.v1` | Просрочка (ack UX в хабе пока stub) | personal |
| `stock.alert.v1` | Складской алерт (позже) | private |

Пока в хабе нет кнопок «Подтвердить», для всех типов ставить `require_ack: false`.

## Поля тела события

См. API `POST /v1/events`: `event_id`, `type`, `severity`, `source`, `title`, `body`, `channels[]`, `targets`, `require_ack`, `ack_timeout_minutes`, `escalate_to`, `data`.

`data` — произвольный JSON для интеграций; хаб не интерпретирует его в MVP (кроме хранения в payload).
