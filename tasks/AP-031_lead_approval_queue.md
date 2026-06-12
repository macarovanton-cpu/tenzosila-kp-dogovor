<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-031 — Очередь согласований руководителя

Status: planned  
Size: medium  
Depends on: AP-028, AP-030

## Goal

Добавить UI очереди pending approval requests для руководителя и действия
approve/reject с комментарием.

## Why

Нестандартная цена становится управляемой только тогда, когда руководитель
видит очередь и может принять решение.

## Likely touched files

- `src/pages/3_Админка.py`
- `src/storage/approvals.py`
- `src/auth/permissions.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/approval_queue.py`
- `tests/admin/test_approval_queue.py`

## Tests

- Lead/admin sees pending requests.
- Manager without permission cannot decide.
- Approve/reject writes decided_by, decided_at, decision_comment.

## Manual verification

- Создать pending request.
- Открыть очередь под lead.
- Approve и проверить статус.

## Done criteria

- UI показывает kp_number, item, selected price, bounds, manager comment.
- Решение обновляет request exactly once.
- Нет изменений договора в этой задаче.

## Risks

- Нужны тестовые пользователи и роли.
- Нельзя давать руководителю согласовывать собственные отклонения, если бизнес
  это запрещает; при неясности blocked.
