<!-- review-banner -->
> **[PARKED — Фаза 5]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `do_not_run_autonomously (договорный экран)`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-032 — Блокировка договора при pending approval

Status: planned  
Size: medium  
Depends on: AP-031

## Goal

Заблокировать генерацию договора для КП, у которого есть unresolved approval
requests.

## Why

Договор не должен фиксировать нестандартную цену, пока она не согласована.

## Likely touched files

- `src/pages/2_Договор.py`
- `src/storage/approvals.py`
- `tests/contracts/test_page_dogovor.py` или page-level tests
- `docs/admin_panel_status.md`

## New files

- возможно `src/contracts/approval_gate.py`
- tests for approval gate

## Tests

- КП без approvals -> договор работает как раньше.
- КП с pending approval -> generate disabled and message shown.
- Legacy Mode B не блокируется из-за отсутствия kp_id.

## Manual verification

- Загрузить в договоре КП с pending approval.
- Проверить, что кнопка генерации недоступна и причина понятна.
- Approve request и проверить, что блокировка ушла.

## Done criteria

- Изменение в договорном экране минимально и изолировано.
- Старые Mode A/B сценарии не сломаны.
- Нет пересчёта цен в договоре.

## Risks

- `src/pages/2_Договор.py` большой и чувствительный. Не рефакторить его шире
  gate-логики.
