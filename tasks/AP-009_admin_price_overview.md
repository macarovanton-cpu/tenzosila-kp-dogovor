# AP-009 — Read-only диагностика прайса

- **task_id:** AP-009
- **Status:** planned
- **Phase:** 1 (Foundation)
- **Size:** small
- **Depends on:** AP-004
- **Agent safety level:** `safe_for_autonomous_agent`

> Изменено в ревью: было «admin price overview» поверх БД-storage (`AP-005`) и UI
> (`AP-008`). Переописано как чистая диагностика без БД и без UI — функция/CLI над
> текущим `data/prices.json`. UI-обёртка — AP-015 (Фаза 2).

## Goal

Написать чистую диагностику текущего прайса: counts моделей/опций, распределение
классов, просроченность `valid_from`, нулевые/пустые цены там, где это не
`on_request`, модели без записи цены. Доступна как функция и как CLI-скрипт.

## Business value

Владелец одной командой видит «здоровье» текущего прайса из терминала, без БД и
UI. Та же функция потом питает read-only панель в админке (AP-015). Нулевой риск.

## Context

- Источник — `data/prices.json` через `src/data_loader.load_prices()` или прямое
  чтение; нормализация — `src/admin/price_normalizer.py` (AP-003); проверки —
  `src/admin/price_validator.py` (AP-004).
- `_meta.valid_from` — дата действия прайса (сравнить с сегодняшней).
- Текущие counts-ориентиры: 45 моделей, 65 опций; классы A=20, B=36, C=4,
  UNKNOWN=5, on_request=1.

## Affected files

- `tests/admin/`
- `docs/admin_panel_status.md`

## New files

- `src/admin/price_diagnostics.py`
  (`diagnose_prices(prices) -> PriceDiagnostics`; плюс `__main__` для CLI)
- `tests/admin/test_price_diagnostics.py`

## Allowed changes

- Создать диагностику и тесты в `src/admin/` и `tests/admin/`.
- Обновить статус AP-009.

## Forbidden changes

- НЕ менять `data/prices.json`.
- НЕ создавать Streamlit-UI (это AP-015).
- НЕ трогать runtime КП.
- НЕ импортировать Streamlit в `price_diagnostics.py` (должен работать как чистый
  CLI без streamlit-рантайма).

## Implementation steps

1. Реализовать `diagnose_prices()`: counts, распределение классов, expired-флаг по
   `valid_from`, список нулевых/пустых цен (кроме on_request), список моделей без
   цены.
2. Добавить тонкий CLI (`python -m src.admin.price_diagnostics`), печатающий
   сводку по `data/prices.json`.
3. Тесты на синтетических данных: expired vs актуальный, наличие нулевой цены,
   корректные counts/классы.
4. Обновить статус AP-009.

## Tests

- `rtk python -m pytest tests/admin/test_price_diagnostics.py -q`.
- `rtk python -m pytest tests/ -q` — зелёный.

## Manual verification

- `rtk python -m src.admin.price_diagnostics` — печатает осмысленную сводку по
  текущему прайсу (counts/классы/expired/нулевые цены).

## Done criteria

- Диагностика — чистая, без Streamlit и БД.
- CLI выдаёт сводку по реальному `data/prices.json`.
- Тесты покрывают expired, нулевые цены, counts.

## Stop condition

Один commit (`feat: добавить read-only диагностику прайса`), краткий отчёт,
**стоп**. На этом Фаза 1 завершается; Фазу 2 (UI) начинать только по команде
пользователя и желательно после закрытия v2.1.

## Risks

- Ложные «нулевые цены» для on_request — исключить on_request из этого чека.
