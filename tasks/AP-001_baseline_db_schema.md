<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_decision_before`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-001 — Зафиксировать текущую DB-схему и миграционный каркас

Status: planned  
Size: small  
Depends on: none

## Goal

Завести управляемое место для SQL-миграций и зафиксировать текущую схему
Supabase-таблиц `kps` и `contracts`, которые уже использует
`src/storage/supabase_client.py`.

## Why

Все следующие задачи добавляют таблицы прайсов, правил, ролей, согласований и
аудита. Сейчас SQL-миграций в репозитории нет, поэтому сначала нужен baseline,
иначе агенты начнут менять БД несогласованно.

## Likely touched files

- `docs/admin_panel_status.md`
- возможно `docs/STATUS.md`, если активная задача проекта будет обновляться

## New files

- `supabase/migrations/README.md`
- baseline SQL или schema-doc для текущих `kps`, `contracts`, `kps_test`,
  `contracts_test`

## Tests

- Тесты приложения не обязательны, если меняется только документация/SQL.
- Если добавлен SQL parser/lint command, запустить его.

## Manual verification

- Открыть README миграций и убедиться, что понятно, как добавлять следующую
  миграцию.
- Сверить описанные таблицы с `src/storage/supabase_client.py` и
  `tests/storage/conftest.py`.

## Done criteria

- Есть папка миграций или явно выбранный путь для миграций.
- Описаны текущие таблицы `kps`/`contracts` и тестовые таблицы.
- Написано правило: новые DB-изменения только через миграции.
- `docs/admin_panel_status.md` обновлён.

## Risks

- Можно неверно описать реальную Supabase-схему, если не свериться с live DB.
- Если live DB недоступна, зафиксировать задачу как partial и пометить, что
  требуется human review.
