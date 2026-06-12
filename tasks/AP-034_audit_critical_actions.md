<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-034 — Аудит critical actions

Status: planned  
Size: large  
Depends on: AP-033, AP-014, AP-031

## Goal

Подключить audit log к критичным действиям: активация прайса, изменение правил,
manual price deviation, создание/решение approval.

## Why

Сам audit service бесполезен, если важные действия не пишут события.

## Likely touched files

- `src/admin/price_activation.py`
- `src/admin/rule_sets_editor.py`
- `src/approvals/service.py`
- `src/ui/specification_section.py` or snapshot/save service
- `docs/admin_panel_status.md`

## New files

- `src/audit/__init__.py`
- `src/audit/events.py`
- tests for event payloads

## Tests

- Activate price writes audit event.
- Approval decision writes audit event.
- Manual price deviation writes audit event or snapshot event.
- Normal rerun does not spam audit.

## Manual verification

- Выполнить каждое critical action в test DB.
- Открыть audit rows and verify actor/action/entity.

## Done criteria

- События имеют стабильные action codes.
- before/after не содержат огромные snapshots без необходимости.
- Ошибка audit не должна silently corrupt business action.

## Risks

- Высокий cross-module scope. Делать только перечисленные actions.
- Не запускать автономно ночью без review.
