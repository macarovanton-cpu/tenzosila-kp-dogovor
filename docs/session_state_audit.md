# Аудит session_state в конфигураторе КП

> Дата: 2026-05-08. Цель: карта состояния перед интеграцией с Supabase.
> Источник: анализ кода (`src/state.py`, `src/app.py`, `src/ui/*`, `src/generators/*`, `src/pages/2_Договор.py`).

---

## 1. Полный список ключей (страница КП)

Инициализируются в `state.py:initial_state()` через `setdefault`.

| # | Ключ | Тип | Источник | В data dict? | Пример значения | Заметка |
|---|------|-----|----------|:------------:|-----------------|---------|
| 1 | `kp_date` | `date` | UI date_input / `date.today()` | да (`kp_date`) | `2026-05-08` | Форматируется как DD.MM.YYYY |
| 2 | `kp_valid_days` | `int` | config.DEFAULT_KP_VALID_DAYS | да (`kp_valid_days`) | `15` | Плюрализуется: "15 дней" |
| 3 | `total_term_days` | `int \| None` | header slider / расчёт | да (`total_term_days`) | `35` | None = автоматический расчёт по составу |
| 4 | `kp_number` | `str` | UI text_input | да (`kp_number`) | `"КП-2026-042"` | |
| 5 | `manager_id` | `str` | UI selectbox | да (через lookup → `manager_full_name`, `manager_phone`, `manager_email`) | `"ivanov"` | Дефолт из managers.json |
| 6 | `client_name` | `str` | UI text_input | да (`client_name`) | `"ООО Ромашка"` | Также в filename |
| 7 | `model_line` | `str` | UI selectbox (каскад) | нет (через model lookup) | `"С"` | Одно из: С, СЛ, Ф, ФЛ, П |
| 8 | `model_max` | `int` | UI selectbox (каскад) | нет (через model lookup → `max_load_t`) | `60` | Тонны |
| 9 | `model_length` | `int` | UI selectbox (каскад) | нет (через model lookup → `platform_size`) | `18` | Метры |
| 10 | `model_id` | `str` | derived: `model_id_from_cascade()` | нет (через lookup → `model_full_name`) | `"vesta-с-60-18"` | Пересобирается при каскаде |
| 11 | `model_price` | `int \| None` | UI slider / None | нет (идёт через spec_items) | `2450000` | None = retail из prices.json |
| 12 | `sensor_id` | `str` | UI selectbox | да (через lookup → `sensor_label`, `sensor_temp_range`) | `"zemic_dhm9b_30t"` | |
| 13 | `indicator_id` | `str` | UI selectbox | да (через lookup → `indicator_label`, `indicator_temp_range`) | `"titan_3cs"` | |
| 14 | `cable_m` | `int` | UI number_input | нет | `20` | Длина кабеля, метры |
| 15 | `warranty_months` | `int` | UI number_input | да (`warranty_text`) | `36` | Плюрализуется: "36 месяцев" |
| 16 | `construction_beam` | `str` | construction_section | да (через `build_construction_description`) | `"Двутавр 20Б1"` | |
| 17 | `construction_beam_count` | `int` | construction_section | да (через описание) | `4` | |
| 18 | `construction_center_beam` | `str` | construction_section | да (через описание) | `""` | Пусто для рельсовых линеек |
| 19 | `construction_center_beam_count` | `int` | construction_section | да (через описание) | `0` | |
| 20 | `construction_deck_mm` | `int` | construction_section | да (через описание) | `6` | Толщина настила |
| 21 | `construction_underlining_mm` | `int` | construction_section | да (через описание) | `4` | Толщина подкладки |
| 22 | `is_dual_range` | `bool` | UI checkbox | да (`main_scale_label`) | `False` | Двухдиапазонный режим |
| 23 | `options` | `dict` | UI (чекбоксы + слайдеры) | нет (через spec_items) | см. ниже | Сбрасывается при смене модели |
| 24 | `spec_items_overrides` | `dict` | UI spec table edits | нет (применяется в spec_builder) | `{"vesta-с-60-18": {"price": 2500000}}` | Ручные правки qty/price |
| 25 | `payment_preset_id` | `str` | UI radio | нет (через render_payment_block → `payment_terms_block`) | `"split_by_items"` | |
| 26 | `payment_percents` | `dict` | — | нет | `{}` | **Legacy, не используется** |
| 27 | `payment_days` | `int` | UI number_input | нет (через payment_renderer) | `5` | Срок оплаты, банк. дни |
| 28 | `payment_custom_text` | `str` | UI text_area | нет (через payment_renderer) | `"Оплата по факту..."` | Только для preset=custom |
| 29 | `payment_split_state` | `dict` | UI number_inputs | нет (через payment_renderer) | `{"scales": {"prepay": 50, "postpay": 50}}` | Для split_by_items |
| 30 | `payment_v1_prepay` | `int` | UI number_input | нет (через payment_renderer) | `50` | % аванса V1 |
| 31 | `payment_v2_prepay` | `int` | UI number_input | нет (через payment_renderer) | `30` | % аванса V2 |
| 32 | `payment_v2_preship` | `int` | UI number_input | нет (через payment_renderer) | `40` | % перед отгрузкой V2 |
| 33 | `payment_v3_days` | `int` | UI number_input | нет (через payment_renderer) | `15` | Срок постоплаты V3, дни |
| 34 | `payment_v3_trigger_id` | `str` | UI selectbox | нет (через payment_renderer) | `"after_installation"` | Триггер отсчёта V3 |

### Динамические ключи (widget keys, не в initial_state)

| Паттерн | Тип | Где создаётся | Заметка |
|---------|-----|---------------|---------|
| `opt_{key}_enabled__{model_id}` | `bool` | options_section.py (checkbox key=) | Виджетный ключ, НЕ хранится явно — Streamlit sync |
| `opt_{key}_price__{model_id}` | `int` | options_section.py (slider key=) | Виджетный ключ |
| `opt_{key}_qty__{model_id}` | `int` | options_section.py (number_input key=) | Для блоков с qty |
| `opt_{key}_side__{model_id}` | `str` | options_section.py (radio key=) | "Исполнитель" / "Заказчик" |
| `split_{group_id}_prepay` | `int` | payment_section.py (number_input key=) | Виджетный ключ для split |
| `split_{group_id}_postpay` | `int` | payment_section.py (number_input key=) | Виджетный ключ для split |
| `total_term_days_user_set` | `bool` | header.py callback | Флаг ручной правки; pop при смене модели |

---

## 2. Ключи страницы "Договор" (`src/pages/2_Договор.py`)

Эти ключи живут в том же session_state, но относятся к отдельному flow.

| # | Ключ | Тип | Источник | Пример |
|---|------|-----|----------|--------|
| 1 | `upload_kp` | `UploadedFile` | file_uploader | PDF файл |
| 2 | `upload_card` | `UploadedFile` | file_uploader | PDF/DOCX файл |
| 3 | `contract_data` | `dict` | AI extraction | `{"ЗАКАЗЧИК_ИНН": "7701234567", ...}` |
| 4 | `manual_contract_number` | `str` | text_input | `"1-2026"` |
| 5 | `manual_contract_date` | `date` | date_input | `2026-05-08` |
| 6 | `manual_object_address` | `str` | text_input | `"г. Москва, ул. Ленина, 1"` |
| 7 | `manual_spec_number` | `str` | text_input | `"1"` |

### Извлечённые AI-поля (записываются в session_state как отдельные ключи)

**Реквизиты (19 ключей):**
`ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ`, `ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ`, `ЗАКАЗЧИК_ИНН`, `ЗАКАЗЧИК_КПП`, `ЗАКАЗЧИК_ОГРН`, `ЗАКАЗЧИК_АДРЕС_ЮР`, `ЗАКАЗЧИК_АДРЕС_ПОЧТ`, `ЗАКАЗЧИК_РС`, `ЗАКАЗЧИК_БАНК`, `ЗАКАЗЧИК_КС`, `ЗАКАЗЧИК_БИК`, `ЗАКАЗЧИК_ТЕЛЕФОН`, `ЗАКАЗЧИК_EMAIL`, `ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ`, `ЗАКАЗЧИК_ДИРЕКТОР_ФИО`, `ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП`, `ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП`, `ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ`, `ЗАКАЗЧИК_ОСНОВАНИЕ`

**Спецификация (23 ключа):**
`СПЕЦ_НДС`, `СПЕЦ_МОДЕЛЬ_КРАТКОЕ`, `СПЕЦ_МАКС_НАГРУЗКА`, `СПЕЦ_П1_НАИМЕНОВАНИЕ`, `СПЕЦ_П1_СУММА`, `СПЕЦ_П1_СРОК`, `СПЕЦ_П2_ПАРАМЕТРЫ`, `СПЕЦ_П2_СУММА`, `СПЕЦ_П2_СРОК`, `СПЕЦ_П3_НАИМЕНОВАНИЕ`, `СПЕЦ_П3_СУММА`, `СПЕЦ_П3_СРОК`, `СПЕЦ_П4_НАИМЕНОВАНИЕ`, `СПЕЦ_П4_СУММА`, `СПЕЦ_П4_СРОК`, `СПЕЦ_П5_НАИМЕНОВАНИЕ`, `СПЕЦ_П5_СУММА`, `СПЕЦ_П5_СРОК`, `СПЕЦ_ИТОГО`, `СПЕЦ_ИТОГО_ПРОПИСЬ`, `СПЕЦ_ОПЛАТА_П1`..`СПЕЦ_ОПЛАТА_П6`, `СПЕЦ_СРОК_ПОСТАВКИ`, `СПЕЦ_СРОК_ФУНДАМЕНТ`, `СПЕЦ_СРОК_МОНТАЖ`

Все `str`. Заполняются из AI-extraction, редактируются в text_input/text_area.

---

## 3. Группировка по смыслу

### A. Метаданные КП
`kp_date`, `kp_valid_days`, `kp_number`, `manager_id`, `client_name`

### B. Модель весов (каскад)
`model_line`, `model_max`, `model_length`, `model_id`, `model_price`

### C. Оборудование
`sensor_id`, `indicator_id`, `cable_m`, `warranty_months`

### D. Конструкция
`construction_beam`, `construction_beam_count`, `construction_center_beam`, `construction_center_beam_count`, `construction_deck_mm`, `construction_underlining_mm`

### E. Метрология
`is_dual_range`

### F. Комплектация (опции)
`options` (dict of dicts), `spec_items_overrides`

Структура одной опции внутри `options[key]`:
```
{
  "enabled": bool,
  "price": int,          # текущая цена (после слайдера)
  "qty": int,            # количество
  "customer_side": bool,  # силами заказчика (price=0)
  "is_on_request": bool,  # "по запросу" в прайсе
  "retail": int,          # retail из prices.json
  "dealer_is_synthetic": bool,
  "block": str            # ramps/fences/foundations/...
}
```

### G. Условия оплаты
`payment_preset_id`, `payment_days`, `payment_custom_text`, `payment_split_state`, `payment_v1_prepay`, `payment_v2_prepay`, `payment_v2_preship`, `payment_v3_days`, `payment_v3_trigger_id`

Legacy (не используется): `payment_percents`

### H. Договор (страница 2_Договор.py)
`contract_data`, `manual_contract_number`, `manual_contract_date`, `manual_object_address`, `manual_spec_number`, + 42 ключа `ЗАКАЗЧИК_*` / `СПЕЦ_*`

---

## 4. Вычисляемые значения (НЕ в session_state)

Считаются на каждом рендере в `app.py`, не хранятся:

| Значение | Функция | Файл |
|----------|---------|------|
| `spec_items` (список позиций П1-Пn) | `build_spec_items()` | `src/spec_builder.py` |
| `totals` (with_vat, without_vat, vat) | `calc_totals()` | `src/pricing.py` |
| `term_days` (дни по ролям + total) | `resolve_term_days()` | `src/term_days.py` |
| `errors`, `warnings` | `validate()` | `src/validation.py` |
| `payment_preview` (markdown) | `render_payment_section()` | `src/ui/payment_section.py` |
| template context (22 ключа) | `build_template_context()` | `src/generators/kp_generator.py` |

---

## 5. Сброс при смене модели

`on_cascade_change()` (state.py:104) при изменении `model_id`:

| Ключ | Действие |
|------|----------|
| `model_id` | пересобирается из каскада |
| `model_price` | → `None` |
| `options` | → `{}` (полный сброс) |
| `spec_items_overrides` | → `{}` |
| `is_dual_range` | → `False` |
| `total_term_days` | → `None` |
| `total_term_days_user_set` | удаляется (`pop`) |
| `construction_*` | → defaults из line_defaults для новой линейки |

---

## 6. Предложение по структуре Supabase

### 6.1 Отдельные колонки (для поиска и индексирования)

```
id              UUID PK
kp_number       TEXT          -- поиск по номеру
kp_date         DATE          -- сортировка, фильтр по периоду
client_name     TEXT          -- поиск по клиенту
model_id        TEXT          -- фильтр по модели
total_price     INTEGER       -- сортировка по сумме
manager_id      TEXT          -- фильтр по менеджеру
created_at      TIMESTAMPTZ   -- аудит
updated_at      TIMESTAMPTZ   -- аудит
```

### 6.2 JSON-блоки (внутри колонки `data JSONB`)

```jsonc
{
  "metadata": {
    "kp_valid_days": 15,
    "warranty_months": 36
  },
  "model": {
    "line": "С",
    "max": 60,
    "length": 18,
    "price": 2450000     // null = retail
  },
  "equipment": {
    "sensor_id": "zemic_dhm9b_30t",
    "indicator_id": "titan_3cs",
    "cable_m": 20
  },
  "construction": {
    "beam": "Двутавр 20Б1",
    "beam_count": 4,
    "center_beam": "",
    "center_beam_count": 0,
    "deck_mm": 6,
    "underlining_mm": 4
  },
  "metrology": {
    "is_dual_range": false
  },
  "options": {
    "frame_std_с": {"price": 85000, "qty": 2, "customer_side": false},
    "foundation_s_f_pamp_18": {"price": 350000, "qty": 1, "customer_side": false}
  },
  "spec_overrides": {
    "vesta-с-60-18": {"price": 2500000}
  },
  "payment": {
    "preset_id": "split_by_items",
    "days": 5,
    "custom_text": "",
    "split_state": {"scales": {"prepay": 50, "postpay": 50}},
    "v1_prepay": 50,
    "v2_prepay": 30,
    "v2_preship": 40,
    "v3_days": 15,
    "v3_trigger_id": "after_installation"
  }
}
```

### 6.3 Что НЕ хранить (вычисляется при загрузке)

| Ключ | Причина |
|------|---------|
| `model_id` | Собирается из `line + max + length` (но хранить в колонке для индекса) |
| `spec_items` | Пересчитывается из options + prices.json |
| `totals` | Пересчитывается из spec_items |
| `term_days` | Пересчитывается из spec_items + total_term_days |
| `errors`, `warnings` | Пересчитываются при валидации |
| `payment_percents` | Legacy, не используется |
| `total_term_days_user_set` | Служебный флаг UI |
| Виджетные ключи (`opt_*__*`, `split_*`) | Streamlit-артефакты, дублируют `options` и `payment_split_state` |

### 6.4 Что переименовать для долгосрочной ясности

| Текущий ключ | Предложение | Причина |
|-------------|-------------|---------|
| `model_max` | `max_load_t` | Явные единицы |
| `model_length` | `platform_length_m` | Явные единицы |
| `cable_m` | `cable_length_m` | Явные единицы |
| `construction_deck_mm` | `deck_thickness_mm` | Убрать prefix "construction_" в JSON-блоке |
| `construction_underlining_mm` | `underlining_thickness_mm` | Аналогично |
| `payment_days` | `payment_term_bank_days` | Уточнить семантику |
| `payment_v3_days` | `postpay_term_days` | Уточнить семантику |
| `is_dual_range` | `dual_range_enabled` | Консистентность с bool-naming |

### 6.5 Данные договора — отдельная таблица

Ключи `ЗАКАЗЧИК_*`, `СПЕЦ_*`, `manual_*` и `contract_data` относятся к другому flow (генерация договора). Предлагаю отдельную таблицу `contracts`:

```
id                  UUID PK
kp_id               UUID FK → kp.id   -- связь с КП
contract_number     TEXT
contract_date       DATE
object_address      TEXT
spec_number         TEXT
requisites          JSONB              -- все ЗАКАЗЧИК_* ключи
specification       JSONB              -- все СПЕЦ_* ключи
created_at          TIMESTAMPTZ
```

---

## 7. Открытые вопросы для Антона

1. **`options` — хранить `retail` и `dealer_is_synthetic`?**
   Эти поля приходят из prices.json и могут измениться при обновлении прайса. Хранить снэпшот цен на момент создания КП, или при загрузке подтягивать актуальные?

2. **`payment_percents` — удалить?**
   Ключ инициализируется как `{}` и нигде не записывается/читается. Похоже на legacy от предыдущей версии оплаты. Безопасно ли убрать из initial_state?

3. **`total_term_days` — хранить в колонке?**
   Если менеджер вручную поставил срок (флаг `total_term_days_user_set`), это пользовательское решение. Если None — расчёт. Хранить оба варианта, или только финальное число?

4. **`cable_m` — не идёт в data dict.**
   Длина кабеля хранится в state, но не передаётся в шаблон КП. Нужна ли в Supabase? Или это будущая фича?

5. **Страница договора пишет 42 ключа `ЗАКАЗЧИК_*`/`СПЕЦ_*` прямо в корень session_state.**
   При загрузке сохранённого КП эти ключи могут конфликтовать, если два КП открыты параллельно. Для Supabase лучше изолировать в отдельный namespace (`contract_requisites`, `contract_spec`)?

6. **`spec_items_overrides` — хранить как отдельный блок или мержить в `options`?**
   Сейчас overrides отдельны от options (могут быть для модели и для опций). В Supabase удобнее хранить рядом, но семантика разная. Как лучше?

7. **Версионирование prices.json.**
   Если прайс обновится после создания КП, при загрузке из Supabase spec_items пересчитаются по новым ценам. Нужно ли хранить `prices_version` или снэпшот цен?
