<!-- review-banner -->
> **[DEFERRED — Фаза 4]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_decision_before (бизнес-пороги)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-020 — Валидация отклонений цены

Status: planned  
Size: medium  
Depends on: AP-019

## Goal

Добавить price statuses: `ok`, `comment_required`, `approval_required`,
`blocked_on_request` и использовать их в validation layer.

## Why

Production-процесс требует различать нормальную цену, отклонение с комментарием
и отклонение, которое нужно согласовать.

## Likely touched files

- `src/validation.py`
- `src/pricing_engine.py`
- `tests/test_validation.py`
- `docs/admin_panel_status.md`

## New files

- возможно `src/price_deviations.py`
- `tests/test_price_deviations.py`

## Tests

- Цена внутри recommended -> no warning.
- Цена вне recommended, но допустима -> warning/comment_required.
- Цена ниже min или критично выше max -> error или approval_required согласно
  выбранным правилам.
- `on_request` блокирует генерацию.

## Manual verification

- В КП выставить цену ниже/выше рекомендованной.
- Проверить messages и disabled generate button.

## Done criteria

- Правила порогов явно описаны в коде и тестах.
- Если пороги требуют бизнес-решения, задача помечена blocked.
- НДС не менялся.

## Risks

- Нужно бизнес-решение: какие отклонения требуют approval.
