<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-040 — Data quality service

Status: planned  
Size: medium  
Depends on: AP-014, AP-023, AP-037

## Goal

Добавить сервис проверок качества данных: active price, active rules, active
templates, просроченные версии, нулевые цены, `on_request`, missing mappings.

## Why

Админка должна предупреждать о проблемах до того, как менеджер формирует КП.

## Likely touched files

- storage loaders
- `src/admin/*`
- tests
- `docs/admin_panel_status.md`

## New files

- `src/admin/data_quality.py`
- `tests/admin/test_data_quality.py`

## Tests

- No active price -> error.
- JSON fallback -> warning.
- No active template -> error/warning by type.
- On request rows -> warning.
- NDS remains 22%.

## Manual verification

- Запустить checks на пустой test DB.
- Запустить checks с seeded active price/rules/templates.

## Done criteria

- Checks return structured errors/warnings.
- Service has no Streamlit dependency.
- False positives documented.

## Risks

- Слишком строгие checks могут мешать работе. Разделять error vs warning.
