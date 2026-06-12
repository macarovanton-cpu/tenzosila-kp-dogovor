<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (apply)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-033 — Audit log schema/service

Status: planned  
Size: medium  
Depends on: AP-027

## Goal

Добавить таблицу `audit_log` и storage/service для записи audit events.

## Why

Production-админка должна отвечать, кто загрузил прайс, кто активировал
версию, кто изменил цену и кто согласовал отклонение.

## Likely touched files

- миграции
- `src/storage/__init__.py`
- `docs/admin_panel_status.md`

## New files

- `src/storage/audit_log.py`
- `tests/storage/test_audit_log.py`

## Tests

- Write event with actor/action/entity.
- Query by entity.
- before/after/metadata JSON persisted.
- Missing actor handled explicitly.

## Manual verification

- Записать тестовое событие в test DB.
- Прочитать его из storage service.

## Done criteria

- Audit service не импортирует Streamlit UI.
- Схема поддерживает actor_id nullable/system actor, если нужно.
- Payload sizes разумны.

## Risks

- Лог может начать хранить лишние персональные данные. Metadata держать
  минимальной.
