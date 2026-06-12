<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (snapshot/HANDOFF)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-007 — Сохранять price metadata в snapshot КП

Status: planned  
Size: small  
Depends on: AP-006

## Goal

Добавить в snapshot КП metadata о версии прайса: `price_list_id`, source
(`db`/`json_fallback`) и, если доступно, version/valid_from.

## Why

Старые КП должны воспроизводиться по данным, на которых были созданы. Без
версии прайса договор может быть восстановлен на новых ценах.

## Likely touched files

- `src/storage/snapshot_builder.py`
- `src/ui/sidebar.py`, если именно там передаются metadata
- `tests/test_snapshot_builder.py`
- `docs/admin_panel_status.md`

## New files

- none

## Tests

- Snapshot с DB price metadata.
- Snapshot с JSON fallback metadata.
- Старые snapshot-related tests обновлены без изменения HANDOFF полей.

## Manual verification

- Создать КП через UI и проверить сохранённый JSONB `data.metadata`.
- Загрузить это КП на странице договора и убедиться, что Mode A не падает.

## Done criteria

- `foundation_execution`, `foundation_sections`, `model_code` не сломаны.
- Metadata не требует миграции старых КП.
- Нет изменений JSON-справочников.

## Risks

- Нарушение КП->Договор handoff.
- Расширение snapshot может потребовать обновить тестовые fixtures.
