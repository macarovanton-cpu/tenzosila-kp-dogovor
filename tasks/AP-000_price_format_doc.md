# AP-000 — Документация формата прайса

- **task_id:** AP-000
- **Status:** planned
- **Phase:** 1 (Foundation)
- **Size:** small
- **Depends on:** none
- **Agent safety level:** `safe_for_autonomous_agent`

## Goal

Описать в одном документе (`docs/price_format.md`) реальный формат
`data/prices.json`: верхние ключи, структуру записи модели, структуру записи
опции, перечень классов цен и какие поля каких классов обязательны.

## Business value

Сейчас формат прайса знает только код (`src/pricing.py`, `src/data_loader.py`).
Единый человекочитаемый референс разблокирует следующие задачи (валидатор,
нормализатор, diff) и даёт владельцу понятную инструкцию, как готовить новый
прайс руками. Чистая документация — нулевой риск, быстрая польза.

## Context

- `data/prices.json` сейчас: `_meta`, `models{}` (45 записей), `options{}`
  (65 записей).
- `_meta` содержит: `version`, `source_retail`, `source_dealer`, `currency`,
  `vat_note`, `valid_from`, `notes`, `updated_at`.
- Запись модели (ключ — это `model_id`, кириллица, напр. `веста-...`): поля
  `retail`, `dealer_ru`, `dealer_discount_pct`; у 4 моделей есть
  `data_incomplete`.
- Запись опции (ключ — `option_key`): `label`, `price_retail`, `price_dealer_ru`,
  `discount_pct`, `applies_to_lengths`, и опционально `applies_to_lines`,
  `price_class`, `notes`/`dealer_note`, `components`, `range_min`/`range_max`,
  `on_request`, `allow_customer_value`.
- Классы цен (поле `price_class`), фактическое распределение:
  `A_retail_and_dealer` = 20, `B_retail_only` = 36, `C_manual_range` = 4,
  отсутствует/`None` (UNKNOWN) = 5, флаг `on_request` = 1.
- Логику классов смотреть в `src/pricing.py::get_slider_params`
  (A: dealer→retail→retail×1.4; B: retail×0.6→retail×1.4; C: range_min/range_max;
  UNKNOWN: synthetic dealer ×0.92; on_request: блок).
- Коэффициенты — в `src/config.py` (`MAX_COEFF`, `MIN_COEFF_B`,
  `SYNTHETIC_DEALER_FACTOR`, `VAT_RATE=0.22`).

## Affected files

- `docs/admin_panel_status.md` (обновить строку AP-000)

## New files

- `docs/price_format.md`

## Allowed changes

- Создать `docs/price_format.md`.
- Обновить статус AP-000 в `docs/admin_panel_status.md`.

## Forbidden changes

- НЕ менять `data/prices.json` и любые `data/`-справочники.
- НЕ менять код (`src/**`).
- НЕ менять расчёт цен или классы.

## Implementation steps

1. Прочитать `data/prices.json`, `src/pricing.py`, `src/config.py`,
   `src/data_loader.py` (или через CodeGraph) и сверить фактические поля.
2. Написать `docs/price_format.md`: разделы `_meta`, «Запись модели», «Запись
   опции», «Классы цен» (таблица класс → обязательные поля → как считается
   коридор), «Как подготовить новый прайс вручную».
3. Указать фактические counts (45 моделей, 65 опций, распределение классов) как
   ориентир.
4. Обновить строку AP-000 в `docs/admin_panel_status.md` (`status: done`,
   `commit`, `tests`, `notes`).

## Tests

- Тесты не требуются (только документация).
- Опционально: ничего не запускать или быстрый `rtk python -m pytest tests/ -q`
  для подтверждения, что ничего не сломано (ожидаемо — без изменений).

## Manual verification

- Открыть `docs/price_format.md` и сверить хотя бы 2 модели и по 1 опции каждого
  класса с реальным `data/prices.json` — поля совпадают.

## Done criteria

- `docs/price_format.md` существует и точно описывает текущий формат.
- Все 5 классов (A/B/C/UNKNOWN/on_request) описаны с обязательными полями.
- Строка AP-000 в `docs/admin_panel_status.md` обновлена.

## Stop condition

После создания документа и обновления статуса — один commit
(`docs: добавить документацию формата прайса`), краткий отчёт, **стоп**. Следующую
задачу (AP-003) не начинать.
