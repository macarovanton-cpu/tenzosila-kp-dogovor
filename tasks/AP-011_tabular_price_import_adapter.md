<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-011 — CSV/XLSX adapter импорта

Status: planned  
Size: medium  
Depends on: AP-010

## Goal

Добавить adapter для подготовленного CSV/XLSX формата, который преобразуется в
тот же canonical format, что и JSON import.

## Why

В эксплуатации прайс часто приходит таблицей. Универсальный PDF parser
отложен, но структурированный CSV/XLSX нужен для реального админа.

## Likely touched files

- `src/admin/price_import_view.py`
- `src/admin/price_import_validator.py`
- `requirements.txt` только после явного одобрения, если нужна новая зависимость
- `docs/admin_panel_status.md`

## New files

- `src/admin/price_tabular_import.py`
- `tests/admin/test_price_tabular_import.py`
- `docs/price_import_format.md`

## Tests

- CSV fixture с model/option rows.
- XLSX fixture, если parsing доступен без новой зависимости или зависимость
  одобрена.
- Bad columns -> readable validation errors.

## Manual verification

- Upload prepared CSV.
- Confirm draft items count.
- Confirm import format doc matches UI.

## Done criteria

- Формат колонок документирован.
- Adapter не меняет validator rules.
- Нет PDF parsing.

## Risks

- Excel support может потребовать новую зависимость.
- Если формат реального прайса неизвестен, задачу нужно blocked.
