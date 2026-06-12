# AP-013 — Price diff (две версии прайса)

- **task_id:** AP-013
- **Status:** planned
- **Phase:** 1 (Foundation)
- **Size:** small
- **Depends on:** AP-003
- **Agent safety level:** `safe_for_autonomous_agent`

> Изменено в ревью: было «Depends on AP-005, AP-010» (БД + UI). Diff — чистая
> функция над двумя нормализованными прайсами, без БД и без UI. UI-обёртка
> делается отдельно в AP-010 (Фаза 2).

## Goal

Написать чистую функцию, которая сравнивает два нормализованных прайса (AP-003) и
возвращает структурированный diff: добавленные, удалённые и изменённые позиции
(с указанием изменившихся полей).

## Business value

Перед заменой прайса нужно видеть, что именно меняется (новые/ушедшие/изменённые
цены). Без БД, прямо на файлах: «старый» = текущий `data/prices.json`, «новый» =
загруженный кандидат. Это ядро безопасного сценария AP-010.

## Context

- Сопоставление позиций — по паре (`item_type`, `item_key`).
- Сравнивать значимые поля: `price_retail`, `price_dealer_ru`, `price_class`,
  `range_min`, `range_max`, `on_request` (для модели — `retail`, `dealer_ru`).
- Нормализованный формат — из `src/admin/price_normalizer.py` (AP-003).

## Affected files

- `tests/admin/`
- `docs/admin_panel_status.md`

## New files

- `src/admin/price_diff.py` (`diff_prices(old_items, new_items) -> PriceDiff`)
- `tests/admin/test_price_diff.py`

## Allowed changes

- Создать diff-функцию и тесты в `src/admin/` и `tests/admin/`.
- Обновить статус AP-013.

## Forbidden changes

- НЕ менять `data/prices.json`.
- НЕ трогать БД и storage (их пока нет — Фаза 3).
- НЕ создавать UI (UI — это AP-010).

## Implementation steps

1. Определить структуру результата: `added`, `removed`, `changed`
   (по каждой changed-позиции — список (field, old, new)).
2. Реализовать `diff_prices()`: индексировать по (item_type, item_key), вычислить
   множества added/removed, для общих — сравнить значимые поля.
3. Тесты: новая позиция, удалённая позиция, изменён retail/dealer/class/range,
   идентичные прайсы → пустой diff.
4. Обновить статус AP-013.

## Tests

- `rtk python -m pytest tests/admin/test_price_diff.py -q`.
- `rtk python -m pytest tests/ -q` — зелёный.

## Manual verification

- Сделать копию `data/prices.json`, изменить пару цен, прогнать diff — counts и
  детали совпадают с правкой.

## Done criteria

- Diff — чистая функция, ничего не пишет.
- Сопоставление по (item_type, item_key).
- Изменения значимых полей видны построчно.

## Stop condition

Один commit (`feat: добавить diff версий прайса`), краткий отчёт, **стоп**.
AP-009 не начинать.

## Risks

- При смене ключей нормализатором возможны ложные added/removed — сопоставление
  строго по нормализованному `item_key`.
