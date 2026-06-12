# AP-004 — Валидатор формата прайса

- **task_id:** AP-004
- **Status:** planned
- **Phase:** 1 (Foundation)
- **Size:** medium
- **Depends on:** AP-003
- **Agent safety level:** `safe_for_autonomous_agent`

> Изменено в ревью: валидатор работает над нормализованными items в памяти, без
> БД и без UI. Это «структурный валидатор прайса», не «сервис импорта в БД».

## Goal

Написать чистую функцию-валидатор, которая проверяет нормализованный прайс
(AP-003) на структурную корректность и возвращает структурированные ошибки
(item_key / field / message / level), не падая на первой проблеме.

## Business value

Плохой прайс ловится до того, как им кто-то воспользуется. Валидатор — ядро
будущего безопасного импорта (AP-010) и диагностики (AP-009), но полезен уже
сейчас как самостоятельная проверка `data/prices.json` и любого кандидата.

## Context

- Вход — результат `src/admin/price_normalizer.normalize_prices()` (AP-003).
- Правила корректности по классам (из `src/pricing.py`):
  - `A_retail_and_dealer`: `price_retail` > 0 и `price_dealer_ru` > 0.
  - `B_retail_only`: `price_retail` > 0.
  - `C_manual_range`: есть `range_min` и `range_max`, `range_min <= range_max`.
  - UNKNOWN (нет класса): `price_retail` > 0 (synthetic dealer считается из него).
  - `on_request`: цена может быть пустой; позиция помечается «под запрос».
- Модель: `retail` > 0 и `dealer_ru` > 0; для помеченных `data_incomplete` —
  warning, не error.

## Affected files

- `tests/admin/`
- `docs/admin_panel_status.md`

## New files

- `src/admin/price_validator.py`
  (`validate_prices(items) -> list[ValidationIssue]`, level error/warning)
- `tests/admin/test_price_validator.py`

## Allowed changes

- Создать валидатор и тесты в `src/admin/` и `tests/admin/`.
- Обновить статус AP-004.

## Forbidden changes

- НЕ менять `data/prices.json`.
- НЕ менять runtime-код КП (`src/pricing.py` и пр. — только читать).
- НЕ делать валидацию слишком строгой: текущий `prices.json` обязан проходить
  **без error** (допустимы warning, напр. `data_incomplete`).

## Implementation steps

1. Определить `ValidationIssue` (level: error/warning; item_key; field; message).
2. Реализовать `validate_prices()`: пройти items, применить правила по классам
   (см. Context), собрать все issues.
3. Тесты на хороших и плохих фикстурах: отсутствует dealer у A,
   `range_min > range_max` у C, нулевой retail у B, on_request без цены (ок),
   модель без цены, модель `data_incomplete` (warning).
4. **Ключевой тест:** реальный `data/prices.json` (через normalizer) проходит без
   error.
5. Обновить статус AP-004.

## Tests

- `rtk python -m pytest tests/admin/test_price_validator.py -q`.
- `rtk python -m pytest tests/ -q` — общий прогон зелёный.

## Manual verification

- Прогнать валидатор на текущем `data/prices.json` — ноль error.
- Прогнать на намеренно испорченной копии — ошибки структурированы по
  item/field/message.

## Done criteria

- Текущий `prices.json` валиден (без error).
- Ошибки структурированы (item/field/message/level) и не прерываются на первой.
- Покрытие good/bad кейсов тестами.

## Stop condition

Один commit (`feat: добавить валидатор формата прайса`), краткий отчёт, **стоп**.
AP-013 не начинать.

## Risks

- Слишком строгая валидация заблокирует реальный прайс — тест на реальном
  `prices.json` это страхует.
