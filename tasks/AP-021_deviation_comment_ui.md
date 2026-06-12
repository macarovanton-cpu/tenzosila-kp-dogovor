<!-- review-banner -->
> **[DEFERRED — Фаза 4]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-021 — UI комментариев по отклонениям

Status: planned  
Size: medium  
Depends on: AP-020

## Goal

Добавить в КП ввод комментария менеджера для позиций, где price status требует
обоснования.

## Why

Комментарий нужен руководителю для согласования и audit log. Без него
нестандартная цена остаётся невидимой причиной.

## Likely touched files

- `src/ui/specification_section.py`
- `src/state.py`
- `src/storage/snapshot_builder.py`
- `tests/test_specification_section.py`
- `tests/test_snapshot_builder.py`
- `docs/admin_panel_status.md`

## New files

- none

## Tests

- Comment field appears for `comment_required`.
- Comment saved in state and snapshot.
- Missing comment blocks or warns according to AP-020.

## Manual verification

- Поменять цену позиции.
- Ввести комментарий.
- Сохранить КП и проверить snapshot.

## Done criteria

- UI не перегружает обычные позиции без отклонений.
- Комментарий привязан к stable item_key.
- Повторный rerun не теряет введённый текст.

## Risks

- `st.data_editor` плохо подходит для per-row comments; возможно нужен
  отдельный expander/list below table.
