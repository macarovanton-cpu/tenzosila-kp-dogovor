<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (apply миграции к реальной БД)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-002 — Миграции price list таблиц

Status: planned  
Size: medium  
Depends on: AP-001

## Goal

Добавить SQL-миграции для `price_lists`, `price_items`, `price_imports` и
`price_import_errors`.

## Why

Версионирование прайсов - первый production-риск из архитектурного плана.
Админка не должна активировать или импортировать прайс без устойчивой схемы.

## Likely touched files

- `docs/admin_panel_status.md`
- миграционные файлы из AP-001

## New files

- новая SQL-миграция price list таблиц
- возможно schema notes для статусов `draft`, `validated`, `active`, `archived`

## Tests

- Dry-run миграции на test Supabase или локальной PostgreSQL, если доступна.
- Storage tests добавлять не здесь, а в AP-005.

## Manual verification

- Применить миграцию к test DB.
- Проверить, что индексы есть на `price_list_id`, `item_key`, `status`.
- Проверить, что возможно иметь только одну active-версию, если это реализовано
  SQL-constraint или будет делаться сервисом.

## Done criteria

- Миграция создаёт четыре таблицы и связи между ними.
- Поля соответствуют `docs/production_architecture_plan.md`.
- Миграция не трогает `kps` и `contracts`.

## Risks

- Ошибка схемы заблокирует последующие задачи импорта.
- Требование "один active прайс" может быть неочевидно реализовано в SQL; если
  выбран service-level контроль, это нужно явно записать.
