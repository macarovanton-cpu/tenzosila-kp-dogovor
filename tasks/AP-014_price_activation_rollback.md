<!-- review-banner -->
> **[DEFERRED — Фаза 3]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (apply / смена active)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-014 — Активация, архив и rollback прайса

Status: planned  
Size: medium  
Depends on: AP-013

## Goal

Добавить сервис и UI для смены статусов price list: validate, activate,
archive и rollback к предыдущей active версии.

## Why

Production-прайс должен иметь ровно одну активную версию и быстрый способ
отката после ошибки.

## Likely touched files

- `src/storage/price_lists.py`
- `src/admin/price_list_view.py`
- `src/pages/3_Админка.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/price_activation.py`
- tests for activation transitions

## Tests

- Draft -> active archives previous active.
- Active -> archived forbidden unless replacement exists.
- Rollback restores previous version.
- Invalid draft cannot activate.

## Manual verification

- Activate draft in test DB.
- Refresh КП and confirm active loader sees new version.
- Roll back and confirm loader sees old version.

## Done criteria

- Only one active price list after every operation.
- Activation requires valid import/diff review state.
- Operation is ready for audit in AP-034.

## Risks

- Ошибка может переключить реальный active price. Использовать test DB first.
