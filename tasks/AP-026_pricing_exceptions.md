<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_decision_before`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-026 — Исключения pricing

Status: planned  
Size: large  
Depends on: AP-025

## Goal

Добавить поддержку pricing exceptions по item/client/region в storage, engine и
admin UI.

## Why

Реальные продажи требуют точечных исключений, но они должны быть видимыми,
версионируемыми и тестируемыми, а не зашитыми в коде.

## Likely touched files

- `src/pricing_engine.py`
- `src/storage/pricing_rules.py`
- `src/pages/3_Админка.py`
- `tests/test_pricing_engine.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/pricing_exceptions.py`
- `tests/admin/test_pricing_exceptions.py`

## Tests

- Item exception overrides global bounds.
- Client/region scopes apply only when context matches.
- Priority/conflict behavior documented and tested.
- Expired exception ignored.

## Manual verification

- Создать exception для одного item_key.
- Открыть КП и увидеть изменённые bounds только для этой позиции.

## Done criteria

- Исключения сохраняются в draft/active rule set.
- Engine объясняет applied rule/exception.
- Snapshot сохраняет applied rule metadata.

## Risks

- Сложные конфликты правил могут потребовать бизнес-решения.
- Это не задача для ночного автономного запуска.
