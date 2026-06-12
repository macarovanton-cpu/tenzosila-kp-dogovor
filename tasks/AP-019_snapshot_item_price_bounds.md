<!-- review-banner -->
> **[DEFERRED — Фаза 4]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (snapshot/HANDOFF)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-019 — Bounds в snapshot позиций КП

Status: planned  
Size: medium  
Depends on: AP-018

## Goal

Сохранять по позициям КП расчётные `min_price`, `recommended_price`,
`max_price`, `selected_price` и `price_status`.

## Why

Старые КП, договоры, approvals и аудит должны ссылаться на границы, которые
действовали в момент создания КП, а не пересчитывать их по новому прайсу.

## Likely touched files

- `src/spec_builder.py`
- `src/storage/snapshot_builder.py`
- `tests/test_spec_builder.py`
- `tests/test_snapshot_builder.py`
- `docs/admin_panel_status.md`

## New files

- none

## Tests

- Model item содержит bounds.
- Option item содержит bounds.
- Custom item имеет понятный fallback status.
- Старые snapshot fields сохранены.

## Manual verification

- Создать КП и проверить JSONB snapshot.
- Загрузить КП на странице договора Mode A.

## Done criteria

- Bounds сохраняются без изменения визуального КП.
- Договорный экран не требует bounds для старых КП.
- `foundation_execution`, `foundation_sections`, `model_code` не затронуты.

## Risks

- Snapshot может стать сильно больше.
- Нельзя ломать `src/contracts/from_kp.py`.
