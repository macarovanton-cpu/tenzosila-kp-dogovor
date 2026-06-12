<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-037 — Template versions и scanner

Status: planned  
Size: medium  
Depends on: AP-001

## Goal

Добавить хранение версий document templates и scanner переменных DOCX.

## Why

Шаблоны КП, договора и спецификации - бизнес-артефакты. Их нужно
версионировать и проверять перед активацией.

## Likely touched files

- `src/contracts/filler.py`
- `src/generators/kp_generator.py`
- tests/contracts templates
- `docs/admin_panel_status.md`

## New files

- SQL migration `document_templates`, `document_template_versions`
- `src/storage/document_templates.py`
- `src/contracts/template_scanner.py`
- `tests/contracts/test_template_scanner.py`

## Tests

- Scanner finds placeholders in current DOCX templates.
- Storage can create template/version.
- Required variables persisted.

## Manual verification

- Просканировать текущие `templates/kp/*` и `templates/contracts/*`.
- Проверить список variables.

## Done criteria

- Scanner handles split runs as far as current filler supports.
- Textbox/unsupported placeholders documented.
- No template activation in this task.

## Risks

- DOCX placeholders can live in runs/textboxes; scanner may miss edge cases.
