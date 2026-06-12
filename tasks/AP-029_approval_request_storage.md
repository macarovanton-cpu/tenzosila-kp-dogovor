<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-029 — Approval request storage

Status: planned  
Size: medium  
Depends on: AP-027, AP-020

## Goal

Добавить схему и storage для заявок на согласование price deviations.

## Why

Когда цена требует согласования, это должно быть отдельной сущностью со
статусом, причиной, requester и decision history.

## Likely touched files

- миграции
- `src/storage/__init__.py`
- `docs/admin_panel_status.md`

## New files

- `src/storage/approvals.py`
- `tests/storage/test_approvals.py`

## Tests

- Create pending request.
- Approve/reject/cancel transitions.
- List pending by role/scope.
- Duplicate prevention by entity/item where appropriate.

## Manual verification

- Создать request в test DB.
- Принять/отклонить и проверить timestamps/actor.

## Done criteria

- Status values: pending/approved/rejected/cancelled.
- Decision comment supported.
- Storage не импортирует Streamlit UI.

## Risks

- Связка approval с item в JSON snapshot может быть хрупкой; использовать
  stable item_key и kp id.
