<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-043 — Generation metadata and runbook

Status: planned  
Size: medium  
Depends on: AP-034, AP-038

## Goal

Сохранять metadata генерации документов и написать runbook администратора для
обновления прайсов, правил и шаблонов.

## Why

Production-система должна объяснять, на каких версиях прайса, правил и
шаблонов были созданы КП/договор, и как безопасно проводить обновления.

## Likely touched files

- `src/generators/kp_generator.py`
- `src/contracts/*`
- `src/storage/supabase_client.py`
- `docs/admin_panel_status.md`

## New files

- `docs/admin_runbook.md`
- возможно `src/storage/generation_log.py`
- tests for generation metadata

## Tests

- КП generation metadata includes price/rules/template versions.
- Договор generation metadata includes contract/spec template versions.
- Existing generator tests remain green.

## Manual verification

- Сгенерировать КП и договор.
- Проверить metadata в saved row или generated result.
- Прочитать runbook and follow dry-run steps.

## Done criteria

- Runbook covers price import, activation, rollback, template smoke and audit.
- Metadata does not require recalculating old KP.
- Если хранение generated files не решено, это отмечено как future decision.

## Risks

- Нужно бизнес/ops решение по хранению файлов и срокам хранения.
