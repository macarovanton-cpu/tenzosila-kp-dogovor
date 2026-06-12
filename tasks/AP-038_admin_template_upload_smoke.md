<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (генерация DOCX)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-038 — Admin template upload + smoke

Status: planned  
Size: large  
Depends on: AP-037

## Goal

Добавить UI загрузки draft template version и smoke-генерацию на fixture deal
перед активацией.

## Why

Нельзя активировать шаблон, который не заполняется или ломает DOCX-генерацию.

## Likely touched files

- `src/pages/3_Админка.py`
- `src/contracts/filler.py`
- `src/contracts/spec_v2_filler.py`
- `src/generators/kp_generator.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/templates_view.py`
- `tests/admin/test_templates_view.py`
- smoke fixtures if needed

## Tests

- Upload valid template -> draft version.
- Missing required variables -> validation error.
- Smoke generation success/failure recorded.

## Manual verification

- Upload a copy of current contract/spec template.
- Run smoke and inspect result status.

## Done criteria

- Active template does not change without explicit activation.
- Smoke failure is visible and blocks activation.
- Generated temporary files do not pollute repo.

## Risks

- DOCX generation is fragile and slow.
- This task should get human review.
