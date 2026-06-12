<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-023 — Storage и loader rule sets

Status: planned  
Size: medium  
Depends on: AP-022

## Goal

Добавить storage и loader активного pricing rule set с fallback на текущие
константы `src/config.py`.

## Why

Pricing engine должен получать правила из одного места и не зависеть от
Streamlit UI или прямых SQL-запросов.

## Likely touched files

- `src/pricing_engine.py`
- `src/config.py`
- `src/storage/__init__.py`
- `docs/admin_panel_status.md`

## New files

- `src/storage/pricing_rules.py`
- `tests/storage/test_pricing_rules.py`
- `tests/test_pricing_rule_loader.py`

## Tests

- No active rule set -> config fallback.
- Active rule set -> engine params loaded.
- Invalid rule set -> structured error/fallback according to design.

## Manual verification

- Создать active rule set in test DB.
- Проверить, что readonly admin view или loader видит версию.

## Done criteria

- Loader не ломает текущие tests pricing.
- Fallback явно помечает source.
- Кэш можно сбросить при активации rule set.

## Risks

- Несовпадение active price list и active rule set versions.
