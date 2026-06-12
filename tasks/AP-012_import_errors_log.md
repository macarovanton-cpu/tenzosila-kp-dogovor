<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-012 — Журнал ошибок импорта

Status: planned  
Size: small  
Depends on: AP-004, AP-010

## Goal

Сохранять и показывать ошибки импорта прайса из `price_import_errors`.

## Why

Администратор должен видеть, какие строки и поля не прошли проверку, без
терминала и без повторной загрузки файла.

## Likely touched files

- `src/storage/price_lists.py`
- `src/pages/3_Админка.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/import_errors_view.py`
- tests for storage/view formatting

## Tests

- Bad fixture creates import row and errors.
- Errors include row_number, item_key, field, message, raw_value.
- UI formatter handles empty errors.

## Manual verification

- Upload bad import fixture.
- Open import details and see grouped errors.

## Done criteria

- Errors persist after Streamlit rerun.
- No draft is marked validated when errors exist.
- Error text is non-technical enough for admin.

## Risks

- Too much raw payload may expose unnecessary data.
