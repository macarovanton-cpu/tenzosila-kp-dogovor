<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-030 — Создание approval из КП

Status: planned  
Size: large  
Depends on: AP-029, AP-021

## Goal

При сохранении КП с `approval_required` создавать или обновлять pending approval
request и статус КП.

## Why

Менеджер не должен вручную заводить согласование. Процесс должен начинаться из
факта нестандартной цены и комментария.

## Likely touched files

- `src/ui/sidebar.py`
- `src/storage/snapshot_builder.py`
- `src/storage/supabase_client.py`
- `src/storage/approvals.py`
- `src/validation.py`
- `docs/admin_panel_status.md`

## New files

- `src/approvals/__init__.py`
- `src/approvals/service.py`
- tests for approval service

## Tests

- Save KP with approval_required -> one pending request.
- Re-save same KP -> no duplicate requests.
- Save KP after price fixed -> request cancelled or remains according to design.

## Manual verification

- Создать КП с ценой вне approval threshold.
- Сохранить КП и проверить approval request в test DB.

## Done criteria

- КП получает понятный status.
- Pending request содержит item_key, selected price, bounds, comment.
- Не ломает обычное сохранение КП.

## Risks

- Требуется решение lifecycle: что делать с pending request при изменении КП.
  Если не решено, blocked.
