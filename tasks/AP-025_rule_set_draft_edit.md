<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_decision_before`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-025 — Draft-edit глобальных правил

Status: planned  
Size: medium  
Depends on: AP-024

## Goal

Добавить UI создания draft rule set и редактирования глобальных коэффициентов
для текущих классов цен.

## Why

Это первый mutable шаг управления правилами. Он должен менять только draft и не
затрагивать active расчёты до отдельной активации.

## Likely touched files

- `src/pages/3_Админка.py`
- `src/storage/pricing_rules.py`
- `src/pricing_engine.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/rule_sets_editor.py`
- `tests/admin/test_rule_sets_editor.py`

## Tests

- Create draft from active/fallback.
- Edit `MAX_COEFF`, `MIN_COEFF_B`, `SYNTHETIC_DEALER_FACTOR`.
- Invalid coeff rejected.
- Active rule set unchanged.

## Manual verification

- Создать draft.
- Изменить коэффициент.
- Перезагрузить страницу и увидеть draft.

## Done criteria

- Нет кнопки silent activate в этой задаче, если activation rules не готовы.
- Все изменения требуют комментарий/notes.
- НДС 22% не редактируется без отдельного решения.

## Risks

- Бизнес может не разрешить редактирование коэффициентов. Если нет решения,
  пометить blocked.
