# AP-015 — Read-only панель прайса и правил

- **task_id:** AP-015
- **Status:** planned
- **Phase:** 2 (Minimal admin UI)
- **Size:** small
- **Depends on:** AP-008, AP-009
- **Agent safety level:** `requires_human_review_after`

> Гейт: Фаза 2 (UI). Не начинать до закрытия v2.1.

## Goal

Показать в админке read-only панель: диагностику текущего прайса (из AP-009) и
текущие классы цен A/B/C/UNKNOWN/on_request с коэффициентами из `src/config.py`.
Только просмотр, без редактирования.

## Business value

Владелец видит состояние прайса и применяемые ценовые правила прямо в UI, без
терминала, не рискуя ничего изменить. Подготавливает почву под управляемые
правила (Фаза 4), но сама ничего не меняет.

## Context

- Диагностика — `src/admin/price_diagnostics.diagnose_prices()` (AP-009).
- Коэффициенты — `src/config.py`: `VAT_RATE=0.22`, `MAX_COEFF=1.4`,
  `MIN_COEFF_B=0.6`, `SYNTHETIC_DEALER_FACTOR=0.92`.
- Логика классов — `src/pricing.py::get_slider_params` (для текста-справки).
- Страница-хост — `src/pages/3_Админка.py` (AP-008).

## Affected files

- `src/pages/3_Админка.py` (подключить раздел)
- `docs/admin_panel_status.md`

## New files

- `src/admin/price_overview_view.py` (render-функция раздела + view-model)
- `tests/admin/test_price_overview_view.py`

## Allowed changes

- Создать render-функцию и view-model, подключить раздел на страницу админки.
- Обновить статус AP-015.

## Forbidden changes

- НЕ добавлять поля редактирования (всё read-only).
- НЕ менять `src/config.py`, `src/pricing.py` (только импорт/чтение).
- НЕ менять НДС (22%).
- НЕ трогать КП/Договор.

## Implementation steps

1. View-model: собрать диагностику (AP-009) + значения коэффициентов + краткое
   текстовое описание каждого класса.
2. Render-функция выводит сводку и таблицу классов; явная подпись «правила пока в
   коде, редактирование появится в Фазе 4».
3. Подключить раздел в `3_Админка.py`.
4. Тест view-model: возвращает VAT 22%, MAX_COEFF, MIN_COEFF_B,
   SYNTHETIC_DEALER_FACTOR и упоминает все 5 классов.
5. Обновить статус AP-015 (`human_review: pending`).

## Tests

- `rtk python -m pytest tests/admin/test_price_overview_view.py -q`.
- `rtk python -m pytest tests/ -q` — зелёный.

## Manual verification

- Открыть «Админка» → раздел прайса/правил; сверить коэффициенты с `config.py`,
  увидеть диагностику текущего прайса.

## Done criteria

- Нет полей редактирования.
- НДС = 22%, коэффициенты совпадают с `config.py`.
- Видна диагностика прайса (counts/классы/expired/нулевые цены).
- Есть предупреждение про будущее редактирование.

## Stop condition

Один commit (`feat: read-only панель прайса и правил в админке`), пометить
`human_review: pending`, краткий отчёт, **стоп**. AP-010 не начинать.

## Risks

- Админ может ожидать редактирование — явная подпись про read-only снимает это.
