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
1a. Дилерская цена берётся из PDF напрямую (колонка «Дилерская цена»), НЕ вычисляется
формулой retail×0.92. Решение: PDF — источник правды. Следствие: текущий prices.json
содержит дилерские цены, посчитанные формулой (например ВЕСТА-ФЛ-60-18: 1 534 958),
а PDF даёт 1 534 957 — расхождение ±1 руб из-за разного округления. Это ожидаемо при
переходе на PDF-источник. Round-trip-тест проверяет идемпотентность (запись→чтение→то же),
НЕ побайтовое совпадение с текущим prices.json.
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

**`_meta` поля:** `version`, `source_retail`, `source_dealer`, `currency`,
`vat_note`, `valid_from`, `notes` (array[str]), `updated_at`.

**`models[model_id]`** — поля объекта модели:
`retail` (int), `dealer_ru` (int), `dealer_discount_pct` (int),
опционально `data_incomplete` (bool), `label` (str).

**`options[option_key]`** — поля объекта опции:
`label`, `applies_to_lines` (list[str]), `applies_to_lengths` (list[int]),
`price_retail`, `price_dealer_ru`, `discount_pct`, `price_class`,
`on_request` (bool), `allow_customer_value` (bool),
`range_min`, `range_max`, `notes`.

**Кодировка «по запросу»:** булев флаг `"on_request": true` в объекте опции.
Отдельного null-поля нет — при `on_request: true` числовые поля цены могут
отсутствовать или быть `null`.

**Формирование ключей:**
- `model_id` — kebab-case с кириллицей линейки: `vesta-фл-60-18`
  (шаблон: `vesta-{линейка}-{грузоподъёмность}-{длина}`).
- `option_key` — snake_case латиницей: `ramp_set_fl_sl`, `frame_18`.

**Реальный пример модели:**
```json
"vesta-фл-60-18": {
  "retail": 1668432,
  "dealer_ru": 1534958,
  "dealer_discount_pct": 8
}
```

**Реальный пример опции:**
```json
"ramp_set_fl_sl": {
  "label": "Комплект пандусов под весы ВЕСТА-ФЛ/СЛ (L=2,9м)",
  "applies_to_lines": ["ФЛ", "СЛ"],
  "applies_to_lengths": [16, 18, 20, 22, 24],
  "price_retail": 280000,
  "price_dealer_ru": 257600,
  "discount_pct": 8,
  "price_class": "A_retail_and_dealer"
}
```

### R2. Контракты backend

**`PriceItem`** (`src/admin/price_models.py`) — frozen dataclass:
```
item_type:           PriceItemType  # "model" | "option"
key:                 str
label:               str
price_retail:        int | None
price_dealer_ru:     int | None
discount_pct:        int | float | None
price_class:         str  # "A_retail_and_dealer" | "B_retail_only" | "C_manual_range" | "UNKNOWN"
on_request:          bool
allow_customer_value:bool
range_min:           int | None
range_max:           int | None
applies_to_lines:    list[str]
applies_to_lengths:  list[int]
raw_payload:         dict[str, Any]
```

**`normalize_prices`** (`src/admin/price_normalizer.py`):
```python
def normalize_prices(prices: dict[str, Any]) -> list[PriceItem]:
```
Принимает десериализованный dict из `prices.json`. Итерирует
`prices["models"]` и `prices["options"]`, возвращает плоский список `PriceItem`.

**`validate_prices`** (`src/admin/price_validator.py`):
```python
def validate_prices(items: list[PriceItem]) -> list[ValidationIssue]:
```
`ValidationIssue` — frozen dataclass:
```
level:    Literal["error", "warning"]
item_key: str
field:    str
message:  str
```

**`diff_prices`** (`src/admin/price_diff.py`):
```python
def diff_prices(old_items: list[PriceItem], new_items: list[PriceItem]) -> PriceDiff:
```
`PriceDiff`: `added: list[PriceItem]`, `removed: list[PriceItem]`,
`changed: list[ChangedPriceItem]`.
`ChangedPriceItem`: `item_type`, `item_key`, `changes: list[FieldChange]`.
`FieldChange`: `field`, `old_value`, `new_value`.
Значимые поля для diff: `price_retail`, `price_dealer_ru`, `price_class`,
`range_min`, `range_max`, `on_request`.

### R3. Реальный вывод pdfplumber по дилерскому PDF

**Источник:** `knowledge_base/2026_03_01_Прайс_дилер_экспорт.pdf` (6 страниц).

**Структура по страницам:**

| Страница | Таблиц | Строк × столбцов | Содержимое |
|----------|--------|------------------|------------|
| 1 | 1 | 47 × 6 | Автовесы ВЕСТА-ФЛ, ВЕСТА-СЛ |
| 2 | 1 | 38 × 6 | Продолжение: ВЕСТА-Ф, ВЕСТА-П |
| 3 | 1 | 49 × 6 | Платформенные и прочие модели |
| 4 | 1 | 48 × 6 | Аксессуары / опции (размерные) |
| 5 | 1 | 31 × 6 | Опции с длинными описаниями |

**6 столбцов во всех таблицах:**
1. Линейка / название опции (merged → `None` у продолжений)
2. Артикул / размер (60т-18м, 500×1250 и т.п.)
3. Розничная цена с НДС, руб. — формат `"1 668 432"` (пробел как разделитель тысяч)
4. Дилерская скидка — `"8%"` или `"9%"` или `"10%"`
5. Дилерская цена, руб.
6. Напольная цена руб. / доп. заголовок

**Merged-ячейки линеек:** `pdfplumber` отдаёт `None` во всех строках группы
кроме первой — стандартное и предсказуемое поведение:
```
['ВЕСТА-ФЛ', '60т-18м', '1 668 432', '8%', '1 534 957', ...]
[None,        '60т-20м', '1 883 287', '8%', '1 732 624', ...]
```

**Переносы строк в ячейках:** встречаются в заголовках (`"Розничная\nцена, руб"`)
и длинных названиях опций на стр. 5 — `\n` внутри строки, легко убираются
`.replace('\n', ' ')`.

**Нестандартный символ:** `‑` (неразрывный дефис) в названиях опций на стр. 5 —
нужна замена `str.replace('‑', '-')` при нормализации текста.

**Вердикт: данные чистые → Sonnet достаточен для Задачи 2.**
Структура таблиц предсказуема: 1 таблица/страница, 6 колонок, `None` для merged-ячеек,
пробелы как разделитель тысяч. Парсер сводится к strip пробелов + `int()`,
обработке `None` и `.replace('\n', ' ')`. Никакой перекрёстной логики.

### R4. Кэширование чтения prices.json

**Функция с кэшем:** `load_prices()` в `src/data_loader.py:30` —
декорирована `@st.cache_data(ttl=3600)` (кэш на 1 час).

```python
@st.cache_data(ttl=3600)
def load_prices() -> dict[str, Any]:
    return _read_json(PRICES_JSON)
```

**Последствие для write-service:** после записи нового `prices.json` нужен
`load_prices.clear()` перед следующим рендером страницы — иначе КП и договор
считают по старому прайсу до истечения TTL.

**Вспомогательная функция без кэша:** `load_prices_file(path)` в
`src/admin/price_diagnostics.py:108` — читает напрямую через `json.loads`,
без Streamlit runtime, для диагностических скриптов.

### R5. Опись кандидатов на удаление/архив (ничего не удалять — только список)

| Путь | Причина | На что завязан |
|------|---------|----------------|
| `tasks/AP-000…AP-043_*.md` (44 файла) | Enterprise-карта, отложена. Заменена новым docs-пакетом (ADMIN_PANEL_ARCHITECTURE.md + STATUS.md). | Только markdown, нет импортов/ссылок из кода |
| `docs/admin_panel_status.md` | Старая разбивка статусов АП. Дублирует секцию «Админ-панель» в STATUS.md. | Нет импортов |
| `docs/admin_panel_task_breakdown.md` | Старая декомпозиция 5 фаз (Phase 1–5). Заменена ADMIN_PANEL_ARCHITECTURE.md. | Нет импортов |
| `docs/admin_panel_agent_rules.md` | Старые правила агента (v2.1-era). Заменена. | Нет импортов |
| Ветка `feature/admin-panel-phase-1` | Устарела (Фаза 1 влита в main). | — |
| Ветка `sunrise-hyacinth` | Ветка-артефакт (worktree-имя). | — |
| Ветка `backup-home-gitignore-fix` | Ветка-артефакт фикса gitignore. | — |
| Неиспользуемые модули `src/admin/` | **Не найдено.** Все 9 модулей в активных импортах: `price_models` ← `price_normalizer`, `price_validator`, `price_diff` ← `price_diagnostics` ← `price_overview_view` ← `3_Админка.py` + `price_upload_service` ← `price_upload_view` ← `3_Админка.py`. | — |
| `price_upload_*` | **НЕ предлагать.** Переоценим после Фазы 1. | `3_Админка.py` |
