<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (склейка приложений)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-039 — Appendix library versioning

Status: planned  
Size: large  
Depends on: AP-037

## Goal

Версионировать библиотеку приложений: строительные задания, контрольные листы и
будущие ОРИОН-приложения.

## Why

Сейчас `src/contracts/fundament_lookup.py` выбирает файлы из `data/fundament/`.
Production должен знать human name, applicability, version и active status.

## Likely touched files

- `src/contracts/fundament_lookup.py`
- `src/contracts/compose.py`
- tests/contracts/test_fundament_lookup.py
- tests/contracts/test_compose.py
- `docs/admin_panel_status.md`

## New files

- SQL migration `appendix_library_items`
- `src/storage/appendix_library.py`
- `src/admin/appendix_library_view.py`
- tests for appendix storage/lookup

## Tests

- Current lookup works with fallback files.
- Active library item selected by execution/sections.
- Missing appendix gives readable reason.

## Manual verification

- Проверить пандусный/приямок build task and control sheet.
- Сгенерировать спецификацию с приложениями.

## Done criteria

- Existing step 9 compose behavior preserved.
- Human-readable names are stored/displayed.
- Files are not deleted from `data/fundament/`.

## Risks

- Высокий риск сломать договорные приложения. Не запускать без review.
