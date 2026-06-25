# Админ-панель прайса — техническая архитектура (Фаза 1)

## Принцип

Без БД, ролей, approval workflow, audit log. Новых тяжёлых зависимостей нет
(`pdfplumber` уже в проекте). Парсеры и сервис записи — чистые функции без Streamlit, UI тонкий.

## Сохраняем (контракт НЕ меняем)

- `price_models.py` — `PriceItem` (цель извлечения)
- `price_normalizer.py`
- `price_validator.py`
- `price_diff.py`
- `price_diagnostics.py`
- `data/prices.json` — источник правды
- `tests/admin/*`

## Новые модули — чистый backend без Streamlit

| Файл | Назначение |
|------|-----------|
| `src/admin/price_pdf_dealer.py` | Дилерский PDF → `list[PriceItem]` |
| `src/admin/price_pdf_retail.py` | Розничный (стр. 3/4/19) → `list[PriceItem]` |
| `src/admin/price_pdf_merge.py` | Объединение + дедуп |
| `src/admin/price_business_summary.py` | `diff_prices` → человеческие группы |
| `src/admin/price_write_service.py` | Backup + atomic write + rollback |
| `src/admin/price_validation_split.py` | `validate_prices` → блокеры/предупреждения |

## UI-слой (тонкий, Streamlit)

| Файл | Назначение |
|------|-----------|
| `src/admin/price_update_view.py` | Таблица + поток (PDF и «текущий») |
| `src/pages/3_Админка.py` | Обзор + откат + подключение `update_view` |

## Поток данных

```
PDF (2 файла) → merge ┐
                       ├→ рабочая таблица (st.data_editor) → ручная правка
текущий prices.json ──┘
        ↓
    validate → split(блокеры/предупреждения)
        ↓
  при 0 блокеров: diff(current, new) → business_summary
        ↓
  подтверждение → backup(prices→backup) → atomic write

откат: backup → prices
```

## Защита КП и договоров от регрессии

1. Формат `prices.json` после записи байт-в-байт совместим со старым (тест round-trip).
2. `model_id` / `option_key` не переименовываются.
3. Новые парсеры **НЕ трогают** `src/contracts/extractor.py` и `src/contracts/prompts/`.
4. При наличии кэша чтения прайса — сброс кэша при записи (см. разведку R4).
5. Фаза 5 — полная регрессия КП/договора на обновлённом прайсе.

## Обязательные тесты

- Парсеры на реальных PDF-фикстурах (выборочная сверка конкретных цен)
- Merge (счётчики + дедуп)
- Write-service на temp-каталоге (бэкап + atomic + rollback + сбой не бьёт исходный)
- Round-trip формата
- Обновлённый smoke страницы (`AppTest`)

---

## Разведка Фазы 0 (заполняется Claude Code до реализации)

Раздел заполняется результатами разведзадачи. До заполнения реализацию не начинать.

### R1. Схема prices.json

Точная схема: поля `_meta`, устройство `models` и `options`, кодировка `on_request`
(null/флаг), формирование `model_id` / `option_key`.

> _[не заполнено]_

### R2. Контракты backend

Сигнатуры и возвраты: `PriceItem`, `normalize_prices`, `validate_prices`, `diff_prices`.

> _[не заполнено]_

### R3. Реальный вывод pdfplumber по дилерскому PDF

Сколько таблиц/строк берётся чисто, как выглядят merged-ячейки линеек и переносы
названий опций. Определяет выбор модели для Задачи 2 (Sonnet vs Opus).

> _[не заполнено]_

### R4. Кэширование чтения prices.json

`@st.cache_data` или аналог? Если есть — нужен сброс при записи.

> _[не заполнено]_

### R5. Опись кандидатов на удаление/архив

Путь, причина, на что завязан. **Ничего не удалять — только список.**

> _[не заполнено]_
