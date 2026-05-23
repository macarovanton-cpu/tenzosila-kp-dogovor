# План: Доработка spec_v2.docx до production-ready

## Context

Шаблон `spec_v2.docx` создан из `spec_foundation_install.docx` скриптом `create_spec_v2_template.py`, который только удалил хардкод clauses и вставил маркеры `{{CLAUSE_SECTION_*}}`. Всё остальное (ТТХ, комплект поставки, оплата, сроки, год) унаследовано из legacy-шаблона в захардкоженном виде для ВЕСТА-СЛ-80-18-Ц. Нужно сделать все секции динамическими до перехода к задаче 6 (UI).

---

## Текущая структура шаблона (по результатам инспекции)

| Элемент | Расположение | Статус |
|---------|-------------|--------|
| Таблица позиций | Table 0 (7 rows: header + 5 шаблонных + итого) | ❌ БАГ: строки создаются, но ячейки пустые |
| Оплата | Параграфы [15]-[20]: `{{СПЕЦ_ОПЛАТА_П1..П6}}` | ❌ 6 статичных слотов |
| Сроки | Параграфы [23], [25], [27]: 3 строки (поставка/фундамент/монтаж) | ❌ Все 3 всегда показаны |
| Clauses | Параграфы [29]-[32]: `{{CLAUSE_SECTION_*}}` маркеры | ✅ Динамические |
| ТТХ | Table 1 (11 rows), строки 2-6 захардкожены | ❌ Значения для СЛ-80-18 |
| Комплект | Table 2 (8 rows), захардкожен под СЛ-80-18 | ❌ Состав зависит от модели |
| Подписи | Table 3, год "2026" в обеих ячейках | ❌ Хардкод |
| Приложение | Параграф [48]: `{{СПЕЦ_НОМЕР}}` для номера приложения | ❌ Нужен отдельный плейсхолдер |
| Кавычки | Preamble и Table 3: `«Тензосила»` (1 закрывающая вместо 2) | ❌ Опечатка |

---

## Коммит-стратегия

Атомарные коммиты, каждый с зелёным pytest:

1. `fix(contracts): _set_cell_text — создание w:t при отсутствии + тесты на контент ячеек`
2. `refactor(template): патч spec_v2.docx — маркеры, плейсхолдеры, кавычки, год`
3. `feat(contracts): terms_renderer — динамические сроки из deal + term_days`
4. `feat(contracts): tth_context — ТТХ плейсхолдеры из models.json + equipment_specs`
5. `feat(contracts): kit_renderer — комплект поставки из модели`
6. `feat(contracts): spec_v2_filler — payment/terms/kit/appendix рендер`
7. `feat(contracts): build_spec_v2_data + integration-тесты + 3 примера DOCX`

---

## Порядок реализации

### Коммит 1. Фикс Item 2 — пустые ячейки таблицы позиций

**Файлы:** `src/contracts/filler.py`, `tests/contracts/test_fill_spec_v2.py`

**Причина бага:** `fill_template()` заменяет `{{СПЕЦ_П1_НАИМЕНОВАНИЕ}}` на `""`. Python-docx при `run.text = ""` **удаляет `w:t` XML-элементы**. `_set_cell_text()` не находит `w:t` → молча ничего не делает.

**Текущий код `_set_cell_text` (filler.py:194-198):**
```python
def _set_cell_text(tc_el, text: str) -> None:
    t_els = tc_el.findall('.//' + qn('w:t'))
    if t_els:
        t_els[0].text = text
    # ← если t_els пуст, ничего не происходит
```

**Существующие 10 тестов — что assert-ят:**
- 8 из 10 проверяют clauses (секции, нумерацию, адрес, тексты)
- 2 проверяют таблицу, но ТОЛЬКО `len(table.rows)` — ни один не проверяет содержимое ячеек

**Фикс `_set_cell_text`:**
```python
def _set_cell_text(tc_el, text: str) -> None:
    t_els = tc_el.findall('.//' + qn('w:t'))
    if t_els:
        t_els[0].text = text
    else:
        p_els = tc_el.findall('.//' + qn('w:p'))
        if p_els:
            r = OxmlElement('w:r')
            t = OxmlElement('w:t')
            t.text = text
            t.set(qn('xml:space'), 'preserve')
            r.append(t)
            p_els[0].append(r)
```

**Новые тесты (в test_fill_spec_v2.py):**
- `test_items_cell_names` — 2 items: проверить `table.rows[1].cells[0].text == "Позиция weights"`
- `test_items_cell_amounts` — 2 items: проверить `"100 000" in table.rows[1].cells[1].text`
- `test_customer_side_shows_zakazchik` — item с `metadata.customer_side=True` → ячейка "ЗАКАЗЧИК"

---

### Коммит 2. Патч шаблона

**Файл:** `scripts/patch_spec_v2_template.py` (новый, идемпотентный)

**2.1 Кавычки (Item 1)**
- Preamble (para [7]): `«Тензосила»,` → `«Тензосила»»,` (добавить закрывающую »)
- Table 3 Cell 0: `«Тензосила»\n` → `«Тензосила»»\n`
- Table 1 Row 10: уже корректно (`»»`), проверить

**2.2 Оплата → маркер (Item 4)**
- Удалить параграфы с `{{СПЕЦ_ОПЛАТА_П1}}` .. `{{СПЕЦ_ОПЛАТА_П6}}`
- Вставить `{{PAYMENT_SECTION}}` перед "Порядок оплаты:"

**2.3 Сроки → маркер (Item 3)**
- Удалить 3 параграфа сроков (поставка/фундамент/монтаж)
- Вставить `{{TERMS_SECTION}}` после "Срок поставки Весов..."

**2.4 ТТХ → плейсхолдеры (Item 5)**
Table 1 cell[2] замены:
- Row 2: `11` → `{{ТТХ_НАГРУЗКА_НА_ОСЬ}}`
- Row 3: `не более 50 м` → `{{ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА}}`
- Row 4: `20\n50` → `{{ТТХ_ДИСКРЕТНОСТЬ_БЛОК}}`
- Row 5: `18×3` → `{{ТТХ_ГАБАРИТЫ}}`
- Row 6: `От -30 до +40` → `{{ТТХ_ТЕМПЕРАТУРА}}`

**2.5 Комплект (Item 6)**
Table 2: оставить header (Row 0) + 1 шаблонную строку (Row 1), удалить Row 2-7. Очистить текст шаблонной строки.

**2.6 Год (Item 7)**
Table 3: `2026` → `{{ТЕКУЩИЙ_ГОД}}` через ZIP-замену в XML.

**2.7 Приложение (Item 8)**
Para [48]: первый `{{СПЕЦ_НОМЕР}}` → `{{ПРИЛОЖЕНИЕ_НОМЕР}}`.

**2.8 Контрольный лист (Item 9)**
Вставить после "Строительного задания" маркер `{{APPENDIX_FOUNDATION_CHECK}}`.

---

### Коммит 3. terms_renderer

**Файл:** `src/contracts/terms_renderer.py` (новый, ~40 строк)

```python
def render_terms_section(deal: dict, spec_items: list[dict]) -> list[str]:
```

- Через `build_clauses_context(deal)` → `foundation_scope`, `installation_scope`
- Через `calculate_term_days_per_item(spec_items)` → дни по позициям
- Всегда: строка поставки с `{scales_days}` дней
- Если `foundation_scope in ("contractor_full", "contractor_with_materials")`: строка фундамента
- Если `installation_scope != "none"`: строка монтажа+поверки
- Возвращает `list[str]`

**Тесты:** `tests/contracts/test_terms_renderer.py`
- delivery-only → 1 строка
- foundation+install → 3 строки
- customer_builds → нет строки фундамента (заказчик строит сам)

---

### Коммит 4. tth_context

**Файл:** `src/contracts/tth_context.py` (новый, ~50 строк)

```python
def build_tth_data(model: dict, sensor: dict) -> dict[str, str]:
```

Возвращает:
- `ТТХ_НАГРУЗКА_НА_ОСЬ` ← `str(model["axle_loads_t"]["single"])`
- `ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА` ← `"не более 50 м"` (константа)
- `ТТХ_ДИСКРЕТНОСТЬ_БЛОК` ← из `model["dual_range"]` (многострочный) или `model["verification_division_kg"]`
- `ТТХ_ГАБАРИТЫ` ← `f"{model['length_m']}×{model['width_m']}"`
- `ТТХ_ТЕМПЕРАТУРА` — формат со знаком:

```python
def _format_temp(val: int) -> str:
    return f"+{val}" if val > 0 else str(val)

temp = f"От {_format_temp(t_min)} до {_format_temp(t_max)}"
# "От -30 до +40", "От -50 до +50", "От -10 до -5"
```

**Тесты:** `tests/contracts/test_tth_context.py`
- dual-range → дискретность многострочная
- single-range → одно значение
- temperature: -30/+40, -50/+50, 0/+40 (нет ведущего +)

---

### Коммит 5. kit_renderer

**Файл:** `src/contracts/kit_renderer.py` (новый, ~60 строк)

```python
def build_kit_items(
    model: dict, line_defaults: dict, sensor: dict,
    indicator: dict, cable_length_m: int = 20,
) -> list[dict[str, str]]:
```

Возвращает `[{name: str, qty: str}, ...]`:
1. Платформа (`line_defaults["platform_type"]` → "сплошного"/"колейного" типа)
2. Датчик (`sensor["model"]`, qty = `model["sensors_count"]`)
3. Терминал (`indicator["model"]`, qty = 1)
4. Коробка соединительная (КБТ-N-Ц / КСТ-N по типу датчика)
5. Металлорукав (1 компл)
6. Кабель сигнальный (cable_length_m м)
7. Документация (1 компл)

**Тесты:** `tests/contracts/test_kit_renderer.py`
- digital sensors → КБТ-8-Ц
- analog sensors → КСТ-8
- sensors_count = 10 → qty = "10"

---

### Коммит 6. spec_v2_filler — расширение

**Файл:** `src/contracts/spec_v2_filler.py`

Сигнатура НЕ меняется. Новые данные передаются через `data` dict.

Новый поток:
1. `fill_spec_with_items()` — таблица позиций + `{{KEY}}` плейсхолдеры (ТТХ, год, приложение)
2. `doc = Document(output_path)`
3. `{{PAYMENT_SECTION}}` → параграфы из `data["_payment_lines"]` (list[str])
4. `{{TERMS_SECTION}}` → параграфы из `render_terms_section(deal, spec_items)`
5. Kit Table 2 → template-row-cloning из `data["_kit_items"]` (list[dict])
6. `{{APPENDIX_FOUNDATION_CHECK}}` → контрольный лист если customer_builds, иначе удалить маркер
7. Clauses (существующий код)
8. `doc.save(output_path)`

**Контрольный лист (Item 9):**
Контент из `docs/contract_templates_v1/Автовесы_монтаж_gemini.md:85-101`:
- Заголовок: `Приложение №{{ПРИЛОЖЕНИЕ_2_НОМЕР}} к Спецификации №{{СПЕЦ_НОМЕР}} от {{ДОГОВОР_ДАТА_ПОЛНАЯ}} г.`
- Подзаголовок: `Контрольный лист на фундамент весов {{СПЕЦ_МОДЕЛЬ_КРАТКОЕ}}`
- Таблица 7×3: L/W/X1/X2/h1..h12/L1..L3 — все ячейки пустые (заполняются вручную на объекте)
- Примечание: "Размеры h – абсолютные значения по нивелиру (по рейке в мм)"

**Нумерация приложений (фиксированная v1.0):**
- Приложение №1 = Строительное задание (если подрядчик строит фундамент)
- Приложение №2 = Контрольный лист (только если customer_builds)
- Остальные (ОРИОН, материалы) — backlog v1.1, фиксируем в STATUS.md

Хелперы:
```python
def _replace_marker_with_paragraphs(doc, marker: str, paras: list) -> bool
def _fill_kit_table(doc, kit_items: list[dict]) -> None
def _render_foundation_check(doc, data: dict) -> None  # Item 9
```

---

### Коммит 7. build_spec_v2_data + integration + примеры

**Файл:** `src/contracts/from_kp.py` — новая функция:

```python
def build_spec_v2_data(
    kp_row: dict, prices: dict, models_json: dict,
    payment_terms: dict, equipment_specs: dict,
) -> tuple[dict, list[dict], dict]:
    """Возвращает (data, items, deal) для fill_spec_v2()."""
```

**Integration-тесты** (`tests/contracts/test_fill_spec_v2.py`):
- `TestPaymentSection`: маркер заменён, строки оплаты присутствуют
- `TestTermsSection`: delivery-only (1 строка), full (3 строки)
- `TestTTXSection`: значения подставлены, нет хардкода "11"/"18×3"
- `TestKitSection`: rows = header + N items
- `TestYear`: "2026" отсутствует
- `TestAppendix`: ПРИЛОЖЕНИЕ_НОМЕР заполнен
- `TestFoundationCheck`: контрольный лист при customer_builds

**3 примера DOCX:**

| # | Модель | Конфигурация | Что проверяем |
|---|--------|-------------|---------------|
| 1 | ВЕСТА-СЛ-40-18 | Только поставка | 1 строка сроков, ТТХ СЛ-40, секция 7, нет контр. листа |
| 2 | ВЕСТА-С-80-18 | contractor_full + монтаж | 3 строки сроков, Прил.№1, секции 4-5-7 |
| 3 | ВЕСТА-С-100-24 | customer_builds + монтаж + ОРИОН | Прил.№1 + Прил.№2, все 4 секции |

Для каждого: `get_unfilled_placeholders()` → пустой список.

---

## Критические файлы

| Файл | Действие | Коммит |
|------|---------|--------|
| `src/contracts/filler.py` | Фикс `_set_cell_text` | 1 |
| `scripts/patch_spec_v2_template.py` | Создать | 2 |
| `src/contracts/terms_renderer.py` | Создать | 3 |
| `src/contracts/tth_context.py` | Создать | 4 |
| `src/contracts/kit_renderer.py` | Создать | 5 |
| `src/contracts/spec_v2_filler.py` | Расширить | 6 |
| `src/contracts/from_kp.py` | Добавить `build_spec_v2_data` | 7 |
| `tests/contracts/test_fill_spec_v2.py` | Расширить | 1, 7 |
| `tests/contracts/test_terms_renderer.py` | Создать | 3 |
| `tests/contracts/test_tth_context.py` | Создать | 4 |
| `tests/contracts/test_kit_renderer.py` | Создать | 5 |
| `docs/STATUS.md` | Ограничение: нумерация приложений v1.0 | 7 |

НЕ трогаем: `clauses_renderer.py`, `clauses_context.py`, `clauses_dsl.py`, `payment_renderer.py`, `term_days.py`.

---

## Чек-лист верификации

- [ ] `pytest tests/` зелёный после каждого коммита
- [ ] Item 2: ячейки таблицы содержат имена и суммы (не пустые)
- [ ] `python scripts/patch_spec_v2_template.py` идемпотентный
- [ ] 3 примера DOCX без unfilled placeholders
- [ ] Нет хардкода "2026"
- [ ] ТТХ соответствуют models.json
- [ ] Комплект — правильный датчик и количество
- [ ] Сроки — только применимые строки
- [ ] Оплата — строки из payment_renderer
- [ ] Кавычки: `«ТПК «Тензосила»»` (2 закрывающие) везде
- [ ] Температура: корректный формат знака (+/-)
- [ ] Контрольный лист: есть при customer_builds, нет при contractor_full

---

## Закрытые вопросы

1. **ТТХ_РАССТОЯНИЕ_ДО_ТЕРМИНАЛА** — константа "не более 50 м".
2. **Приложение №2** — контент из `docs/contract_templates_v1/Автовесы_монтаж_gemini.md:85-101` (таблица h1-h12, L, W, X1-X2).
3. **Item 2** — БАГ: `_set_cell_text` не создаёт `w:t` при их отсутствии. Фикс + тесты на контент.
4. **ТТХ_ТЕМПЕРАТУРА** — `_format_temp(val)`: `+N` для >0, `N` для <=0. Без `+-` артефактов.
5. **Нумерация приложений** — фиксированная: №1=Строительное задание, №2=Контрольный лист. Остальные — backlog v1.1.
