<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-041 — Data quality dashboard

Status: planned  
Size: small  
Depends on: AP-040, AP-008

## Goal

Показать результаты data quality checks в админке.

## Why

Проверки должны быть доступны администратору в UI, а не только в тестах или
терминале.

## Likely touched files

- `src/pages/3_Админка.py`
- `src/admin/data_quality.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/data_quality_view.py`
- `tests/admin/test_data_quality_view.py`

## Tests

- Empty/ok/warning/error states render.
- Dashboard does not mutate data.

## Manual verification

- Открыть админку.
- Увидеть список checks, статусы и короткие пояснения.

## Done criteria

- Dashboard compact and readable.
- Errors are actionable.
- Нет автозапуска тяжёлой генерации DOCX на каждом rerun.

## Risks

- Dashboard может превратиться в свалку. Показывать только production-critical
  checks.
