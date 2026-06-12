<!-- review-banner -->
> **[DEFERRED — Фаза 4]** Отложена в ревью (см. `docs/admin_panel_review_notes.md`). Это **НЕ** next task.
> Брать только по явной команде человека и только после входа в свою фазу.
> **Agent safety level:** `requires_human_review_after`.
> Актуальный scope и зависимости — в `docs/admin_panel_task_breakdown.md`.
> Текст ниже — исходный черновик Codex; будет детализирован при входе в фазу.

---

# AP-017 — Parity engine для текущих правил

Status: planned  
Size: medium  
Depends on: AP-016

## Goal

Реализовать pricing engine, который повторяет текущую логику A/B/C/UNKNOWN,
`on_request` и масштабирование цены модели по ширине платформы.

## Why

Перед управляемыми правилами нужно доказать, что новый engine не меняет расчёты
менеджерского КП.

## Likely touched files

- `src/pricing_engine.py`
- `src/pricing.py`
- `tests/test_pricing.py`
- `docs/admin_panel_status.md`

## New files

- `tests/test_pricing_engine.py`

## Tests

- Класс A: dealer -> min, retail -> recommended, retail * 1.4 -> max.
- Класс B: retail * 0.6 -> min.
- Класс C: manual range.
- UNKNOWN: synthetic dealer factor.
- `on_request`: блокирующий status.
- Width 3.5/4.0 для model price.

## Manual verification

- На нескольких реальных option entries сравнить engine result с текущими
  `get_slider_params`.

## Done criteria

- Все parity tests green.
- Округления совпадают с текущими `_ceil_to_1000`, `_floor_to_1000`,
  `_round_to_1000`.
- НДС остаётся 22%.

## Risks

- Незаметное изменение округления изменит коммерческие цены.
