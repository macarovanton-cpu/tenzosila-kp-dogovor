<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_decision_before (apply / список ролей)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-027 — Users/roles/permissions schema

Status: planned  
Size: medium  
Depends on: AP-001

## Goal

Добавить миграции для `users`, `roles`, `permissions`,
`role_permissions` и базового seed ролей.

## Why

Админка, согласования и аудит требуют понимать, кто выполняет действие и какие
у него права.

## Likely touched files

- миграции
- `docs/admin_panel_status.md`

## New files

- SQL migration users/roles/permissions
- возможно seed SQL для ролей manager/lead/admin/tech/auditor

## Tests

- Dry-run migration.
- Insert/select basic roles.

## Manual verification

- Проверить, что роли из architecture plan есть в test DB.
- Проверить, что нет прав на изменение существующих `kps`.

## Done criteria

- Роли и permissions заведены.
- Seed не создаёт реальных пользователей с секретами.
- Источник user identity оставлен для AP-028.

## Risks

- Нужно бизнес-решение по реальным пользователям и email.
