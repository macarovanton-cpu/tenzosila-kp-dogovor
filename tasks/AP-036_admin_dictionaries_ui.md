<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-036 — Admin UI справочников

Status: planned  
Size: medium  
Depends on: AP-035

## Goal

Добавить админский UI для просмотра и draft-редактирования managers и payment
presets.

## Why

Отдел продаж должен менять менеджеров и условия оплаты без правки JSON и без
участия разработчика.

## Likely touched files

- `src/pages/3_Админка.py`
- `src/storage/dictionaries.py`
- `src/auth/permissions.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/dictionaries_view.py`
- `tests/admin/test_dictionaries_view.py`

## Tests

- Manager draft create/edit/deactivate.
- Payment preset draft edit.
- Invalid default preset rejected.

## Manual verification

- Добавить тестового manager.
- Создать draft payment preset and verify it is not active until activation.

## Done criteria

- Default payment remains `split_by_items`.
- Есть review/activate step, не silent edit active.
- UI показывает JSON fallback state.

## Risks

- Некорректный payment text попадёт в КП/договор. Требуется human review для
  реальных формулировок.
