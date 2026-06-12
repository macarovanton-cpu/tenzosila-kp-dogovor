<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-035 — Справочники managers/payment terms в DB

Status: planned  
Size: medium  
Depends on: AP-028

## Goal

Добавить storage и loader для часто меняемых справочников: managers и payment
presets, сохраняя JSON fallback.

## Why

Это самые безопасные справочники для начала dictionary management. Модели и ТТХ
пока лучше не редактировать свободной формой.

## Likely touched files

- `src/data_loader.py`
- `src/generators/payment_renderer.py`
- `src/ui/payment_section.py`
- `tests/test_payment_renderer.py`
- `docs/admin_panel_status.md`

## New files

- миграция dictionary/payment tables, если не покрыта ранее
- `src/storage/dictionaries.py`
- `tests/storage/test_dictionaries.py`

## Tests

- No DB -> reads JSON.
- Active DB managers -> loader returns DB data.
- Active DB payment presets -> default remains `split_by_items`.

## Manual verification

- Запустить КП без DB and with DB.
- Проверить payment preview для default preset.

## Done criteria

- JSON files in `data/` unchanged.
- Loader output compatible with existing UI/generator.
- No free editing of model technical data.

## Risks

- Ошибка payment preset может сломать КП и договорные payment lines.
