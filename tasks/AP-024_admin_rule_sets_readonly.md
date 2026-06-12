<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-024 — Admin rule sets read-only

Status: planned  
Size: small  
Depends on: AP-023, AP-008

## Goal

Показать в админке active и archived pricing rule sets в read-only режиме.

## Why

Перед редактированием правил нужно дать администраторам и ревьюерам видеть,
какие правила применяются сейчас.

## Likely touched files

- `src/pages/3_Админка.py`
- `src/storage/pricing_rules.py`
- `docs/admin_panel_status.md`

## New files

- `src/admin/rule_sets_view.py`
- `tests/admin/test_rule_sets_view.py`

## Tests

- Empty state -> config fallback shown.
- Active DB rule set shown with version/status.
- No mutation.

## Manual verification

- Открыть админку с пустой DB.
- Открыть с active rule set.

## Done criteria

- Видны source, version, status, valid_from.
- Правила не редактируются.
- Нет влияния на КП.

## Risks

- Empty state должен быть понятным: приложение всё ещё работает на config
  fallback.
