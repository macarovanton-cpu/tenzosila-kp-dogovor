<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (apply)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-022 — Миграции rule set таблиц

Status: planned  
Size: medium  
Depends on: AP-001, AP-017

## Goal

Добавить SQL-миграции для `pricing_rule_sets`, `pricing_rules` и
`pricing_exceptions`.

## Why

Правила цен должны версионироваться отдельно от прайса. Это позволит менять
коридоры, комментарии и approval thresholds без подмены самих цен.

## Likely touched files

- миграционные файлы
- `docs/admin_panel_status.md`

## New files

- SQL migration для pricing rules

## Tests

- Dry-run migration.
- Если есть storage helpers, smoke insert/select.

## Manual verification

- В test DB создать draft rule set.
- Проверить, что rule set можно связать с future КП.

## Done criteria

- Таблицы соответствуют architecture plan.
- Есть статусы draft/active/archived.
- Есть поля params JSONB, priority, scope_type/scope_value.

## Risks

- Слишком универсальный rules engine может раздуть scope. Делать только схему,
  нужную следующим задачам.
