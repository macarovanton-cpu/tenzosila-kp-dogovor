# AP-003 — Canonical model + normalizer прайса

- **task_id:** AP-003
- **Status:** planned
- **Phase:** 1 (Foundation)
- **Size:** medium
- **Depends on:** AP-000
- **Agent safety level:** `safe_for_autonomous_agent`

> Изменено в ревью: убрана зависимость от БД-миграций (был «Depends on AP-002»).
> Нормализатор — чистый Python, БД не нужна.

## Goal

Описать canonical-структуру одной price-item записи и написать чистый
нормализатор, который превращает текущий `data/prices.json` (`models{}` +
`options{}`) в плоский список price items **без потери полей**, нужных
`src/pricing.py`.

## Business value

Единый плоский формат — основа для валидатора (AP-004), diff (AP-013),
диагностики (AP-009) и в будущем для БД. Делается один раз, переиспользуется
везде. Не меняет runtime КП — значит безопасно.

## Context

- `data/prices.json`: `_meta`, `models{}` (45), `options{}` (65). Поля — см.
  `docs/price_format.md` (AP-000).
- Модель использует поля `retail`, `dealer_ru`, `dealer_discount_pct`
  (`src/data_loader.py::get_price_by_model_id`).
- Опция использует `price_retail`, `price_dealer_ru`, `price_class`, `range_min`,
  `range_max`, `on_request`, `allow_customer_value`, `applies_to_lines`,
  `applies_to_lengths` (`src/pricing.py::get_slider_params`,
  `src/data_loader.py::get_option_price`).
- Классы: `A_retail_and_dealer`, `B_retail_only`, `C_manual_range`,
  отсутствие класса = UNKNOWN, флаг `on_request`.

## Affected files

- `tests/admin/` (новый пакет тестов)
- `docs/admin_panel_status.md`

## New files

- `src/admin/__init__.py`
- `src/admin/price_models.py` (dataclass(es) canonical price item)
- `src/admin/price_normalizer.py` (`normalize_prices(prices: dict) -> list[...]`)
- `tests/admin/__init__.py`
- `tests/admin/test_price_normalizer.py`

## Allowed changes

- Создать пакет `src/admin/` и модули нормализатора/моделей.
- Создать тесты в `tests/admin/`.
- Обновить статус AP-003.

## Forbidden changes

- НЕ менять `data/prices.json`.
- НЕ менять `src/pricing.py`, `src/data_loader.py`, `src/config.py` (только
  читать). Если нужен общий хелпер — добавить в `src/admin/`, не трогая runtime.
- НЕ менять поведение КП. Нормализатор — отдельный слой, никто его пока не
  вызывает в runtime.

## Implementation steps

1. Определить canonical dataclass price item: тип (`model`/`option`), key, label,
   `price_retail`, `price_dealer_ru`, `price_class` (с явным `UNKNOWN`), флаги
   `on_request`/`allow_customer_value`, `range_min`/`range_max`,
   `applies_to_lines`, `applies_to_lengths`, плюс сырой payload для полноты.
2. `normalize_prices()` проходит `models{}` и `options{}`, маппит поля, выводит
   `price_class=UNKNOWN`, если у опции класса нет.
3. Сохранить все исходные поля (через raw payload), чтобы ничего не терялось.
4. Тесты: counts (45 моделей, 65 опций), распределение классов
   (A=20, B=36, C=4, UNKNOWN=5, on_request=1), и что у выборочных записей
   сохранены `retail/dealer_ru` (модель) и
   `price_retail/price_dealer_ru/range_*` (опция).
5. Обновить статус AP-003.

## Tests

- `rtk python -m pytest tests/admin/test_price_normalizer.py -q` — зелёный.
- `rtk python -m pytest tests/ -q` — не сломан остальной проект.

## Manual verification

- Запустить нормализатор на реальном `data/prices.json` (короткий скрипт или
  тест) и убедиться: counts и классы совпадают с `docs/price_format.md`.

## Done criteria

- Нормализатор не меняет runtime КП.
- Все поля, нужные `src/pricing.py`, сохраняются (проверено тестом).
- Тесты на реальных JSON-данных зелёные.

## Stop condition

Один commit (`feat: добавить нормализатор формата прайса`), краткий отчёт,
**стоп**. AP-004 не начинать.

## Risks

- Потеря `applies_to_lines`/`applies_to_lengths` сломает фильтрацию позже —
  хранить их явно.
