<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_decision_before`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-028 — Current user adapter и guards

Status: planned  
Size: medium  
Depends on: AP-027

## Goal

Добавить минимальный adapter текущего пользователя и permission guards для
Streamlit-страниц.

## Why

До полноценной авторизации нужно хотя бы единое место, где определяется текущий
actor для админки, approvals и audit.

## Likely touched files

- `src/pages/3_Админка.py`
- `src/storage/*`
- `docs/admin_panel_status.md`

## New files

- `src/auth/__init__.py`
- `src/auth/current_user.py`
- `src/auth/permissions.py`
- `tests/auth/test_permissions.py`

## Tests

- User with permission allowed.
- User without permission denied.
- Missing user -> safe readonly/error state.

## Manual verification

- Задать test user через secrets/env.
- Открыть админку под admin и non-admin.

## Done criteria

- Guards не претендуют на полноценную security model.
- Все mutable admin actions проверяют permission.
- Current user id доступен audit/approval services.

## Risks

- Ложное чувство безопасности. В docs явно написать ограничения MVP auth.
