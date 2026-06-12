<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (рефакторинг договора)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-042 — Contract service boundary

Status: planned  
Size: large  
Depends on: AP-032

## Goal

Вынести новую production-логику договора в `contract_service`, оставив страницу
договора более тонким UI.

## Why

`src/pages/2_Договор.py` уже большой и содержит UI, conversion, generation и
attachment logic. Для production нельзя дальше наращивать всё в странице.

## Likely touched files

- `src/pages/2_Договор.py`
- `src/contracts/from_kp.py`
- `src/contracts/state.py`
- tests/contracts page/service tests
- `docs/admin_panel_status.md`

## New files

- `src/contracts/contract_service.py`
- `tests/contracts/test_contract_service.py`

## Tests

- Mode A KP snapshot -> ContractDraft/service result.
- Mode B legacy path unaffected.
- Existing contract tests remain green.

## Manual verification

- Загрузить КП из базы.
- Сгенерировать договор и спецификацию.
- Проверить приложения.

## Done criteria

- Рефакторинг минимален и связан только с production gates/metadata.
- UI behavior не меняется.
- Нет изменений шаблонов DOCX.

## Risks

- Очень высокий regression-risk договора. Не смешивать с template/appendix
  changes.
