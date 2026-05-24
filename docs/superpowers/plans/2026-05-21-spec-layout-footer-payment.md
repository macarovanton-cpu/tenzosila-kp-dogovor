# Spec Template Layout & Filler Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Закрыть три бага спецификации: п.15 отдельно от п.14 (разрыв keepWithNext-цепи), поле PAGE в footer уничтожается merge_runs, пустые строки П5/П6 в оплате.

**Architecture:**
- Проблема 1: `patch_spec_template.py` — добавить `cantSplit` на строки TABLE[1]/TABLE[2], `keepWithNext` на P[56] и строки TABLE[2][:-1], затем перезапустить скрипт.
- Проблема 2: `filler.py` — guard `if '{{' in paragraph.text:` перед обработкой header/footer не даёт `merge_runs` уничтожить field-runs с одинаковым rPr.
- Проблема 3: `filler.py` — после замен удалять body-level параграфы c пустым text и numPr (нумерованные пустышки П5/П6).

**Tech Stack:** python-docx, OOXML (w:cantSplit, w:keepWithNext, w:fldChar/instrText, w:numPr), pytest, zipfile

---

## Диагностика (уже проведена, зафиксировать перед кодом)

### footer2.xml — структура PAGE-поля
```
Run 1:  rPr={rStyle: ac}          + fldChar(begin)      ← одинаковый rPr с Run 2
Run 2:  rPr={rStyle: ac}          + instrText('PAGE  ') ← merge_runs удаляет этот run!
Run 3:  rPr={rStyle: ac}          + fldChar(separate)
Run 4:  rPr={rStyle: ac, noProof} + <w:t>14</w:t>       ← кешированное значение
Run 5:  rPr={rStyle: ac}          + fldChar(end)
```
`section.footer.paragraphs` возвращает параграф с `paragraph.text = '14'` — нет `{{`.

### Структура параграфов оплаты
```
P[14]: 'Порядок оплаты:' numPr ilvl=0 numId=1
P[15..20]: '{{СПЕЦ_ОПЛАТА_П1}}'..'{{СПЕЦ_ОПЛАТА_П6}}' numPr ilvl=1 numId=1
```
При пустом СПЕЦ_ОПЛАТА_П5 → параграф становится пустым нумерованным элементом «2.5 ».

### Разрыв keepWithNext-цепи
```
P[55]: Комплект поставки → keepWithNext (уже есть)
P[56]: ''                → keepWithNext ОТСУТСТВУЕТ ← разрыв!
TABLE[2]: Комплект поставки (8 строк) → cantSplit ОТСУТСТВУЕТ
```

---

## Task 1: Написать falling тесты — поведение filler.py

**Files:**
- Modify: `tests/contracts/test_filler.py`

- [ ] **Step 1: Добавить SPEC_TEMPLATE_PATH и SPEC_MOCK_DATA в начало файла**

После строки `TEMPLATE_PATH = ...` добавить:

```python
SPEC_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'templates', 'contracts',
    'spec_foundation_install.docx'
)

SPEC_MOCK_DATA = {
    "ДОГОВОР_НОМЕР": "Т-001/2026",
    "ДОГОВОР_ДАТА_ПОЛНАЯ": "15.03.2026",
    "СПЕЦ_НОМЕР": "1",
    "СПЕЦ_НДС": "22",
    "СПЕЦ_ИТОГО": "2 000 000",
    "СПЕЦ_ИТОГО_ПРОПИСЬ": "два миллиона",
    "СПЕЦ_П1_НАИМЕНОВАНИЕ": "Весы ВЕСТА-С-60-18-Ц",
    "СПЕЦ_П1_СУММА": "1 500 000",
    "СПЕЦ_П2_ПАРАМЕТРЫ": "ВЕСТА-С, 18м",
    "СПЕЦ_П2_СУММА": "500 000",
    "СПЕЦ_П3_НАИМЕНОВАНИЕ": "",
    "СПЕЦ_П3_СУММА": "",
    "СПЕЦ_П4_НАИМЕНОВАНИЕ": "",
    "СПЕЦ_П4_СУММА": "",
    "СПЕЦ_П5_НАИМЕНОВАНИЕ": "",
    "СПЕЦ_П5_СУММА": "",
    "СПЕЦ_ОПЛАТА_П1": "Предоплата 30% = 600 000 руб.",
    "СПЕЦ_ОПЛАТА_П2": "По отгрузке 70% = 1 400 000 руб.",
    "СПЕЦ_ОПЛАТА_П3": "",
    "СПЕЦ_ОПЛАТА_П4": "",
    "СПЕЦ_ОПЛАТА_П5": "",
    "СПЕЦ_ОПЛАТА_П6": "",
    "СПЕЦ_СРОК_ПОСТАВКИ": "30",
    "СПЕЦ_СРОК_ФУНДАМЕНТ": "20",
    "СПЕЦ_СРОК_МОНТАЖ": "10",
    "СПЕЦ_АДРЕС_ОБЪЕКТА": "г. Москва, промзона Северная",
    "СПЕЦ_АДРЕС_ОБЪЕКТА_ПОЛНЫЙ": "г. Москва, промзона Северная, уч. 5",
    "СПЕЦ_МОДЕЛЬ_КРАТКОЕ": "ВЕСТА-С-60-18",
    "СПЕЦ_МАКС_НАГРУЗКА": "60",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "Директор",
    "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "ООО «Тест»",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_КРАТКОЕ": "Тестов Т.Т.",
    "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "Т.Т. Тестов",
}
```

- [ ] **Step 2: Добавить тест на сохранение PAGE-поля в footer**

В конец `tests/contracts/test_filler.py`:

```python
def test_filler_preserves_footer_page_field(tmp_path):
    """После fill_template поле PAGE в footer сохраняется (merge_runs не уничтожает instrText)."""
    import zipfile

    template = os.path.normpath(SPEC_TEMPLATE_PATH)
    output = str(tmp_path / "spec_out.docx")

    fill_template(template, SPEC_MOCK_DATA, output)

    with zipfile.ZipFile(output) as z:
        footer_xml = z.read("word/footer2.xml").decode("utf-8")

    assert "instrText" in footer_xml, "instrText уничтожен в footer — поле PAGE сломано"
    assert "PAGE" in footer_xml, "Поле PAGE исчезло из footer"
```

- [ ] **Step 3: Добавить тест на удаление пустых строк оплаты**

```python
def test_filler_removes_empty_payment_rows(tmp_path):
    """При СПЕЦ_ОПЛАТА_П5='' пустой нумерованный параграф удаляется из вывода."""
    from docx import Document
    from docx.oxml.ns import qn

    template = os.path.normpath(SPEC_TEMPLATE_PATH)
    output = str(tmp_path / "spec_empty_payment.docx")

    data = {**SPEC_MOCK_DATA, "СПЕЦ_ОПЛАТА_П5": "", "СПЕЦ_ОПЛАТА_П6": ""}
    fill_template(template, data, output)

    doc = Document(output)
    body_tag = qn("w:body")
    NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    empty_numpr = [
        p for p in doc.paragraphs
        if p._p.getparent().tag == body_tag
        and p.text.strip() == ""
        and p._p.find(f".//{{{NS}}}numPr") is not None
    ]
    assert empty_numpr == [], (
        f"Найдено {len(empty_numpr)} пустых нумерованных параграфов после fill_template"
    )
```

- [ ] **Step 4: Запустить тесты — оба должны УПАСТЬ**

```
pytest tests/contracts/test_filler.py::test_filler_preserves_footer_page_field \
       tests/contracts/test_filler.py::test_filler_removes_empty_payment_rows -v
```

Ожидаемо: `FAILED` для обоих. Если вдруг Pass — диагноз неверен, стоп.

---

## Task 2: Исправить filler.py — footer guard + удаление пустых параграфов

**Files:**
- Modify: `src/contracts/filler.py:87-93` (footer loop) и перед `doc.save`

- [ ] **Step 1: Добавить guard в footer/header loop**

Найти блок (строки ~87-93):
```python
    # Обрабатываем колонтитулы (header/footer)
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            replace_in_paragraph(paragraph, data)
        for paragraph in section.footer.paragraphs:
            replace_in_paragraph(paragraph, data)
```

Заменить на:
```python
    # Обрабатываем колонтитулы — только параграфы с плейсхолдерами.
    # Guard нужен: merge_runs уничтожает field-runs (fldChar/instrText) если у них
    # одинаковый rPr, а footer содержит поле PAGE без плейсхолдеров {{...}}.
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            if '{{' in paragraph.text:
                replace_in_paragraph(paragraph, data)
        for paragraph in section.footer.paragraphs:
            if '{{' in paragraph.text:
                replace_in_paragraph(paragraph, data)
```

- [ ] **Step 2: Добавить удаление пустых нумерованных параграфов перед doc.save**

Найти строку `doc.save(output_path)` в конце `fill_template`. Вставить перед ней:

```python
    # Удаляем пустые нумерованные параграфы (СПЕЦ_ОПЛАТА_П5/П6 без значения → «2.5 »)
    _NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    _body_tag = f'{{{_NS}}}body'
    for para in list(doc.paragraphs):
        if para.text.strip() == '':
            p_el = para._element
            if (p_el.getparent().tag == _body_tag
                    and p_el.find(f'.//{{{_NS}}}numPr') is not None):
                p_el.getparent().remove(p_el)

    doc.save(output_path)
```

(Убедиться что `doc.save(output_path)` больше не дублируется — оставить только один вызов в конце функции.)

- [ ] **Step 3: Запустить упавшие тесты — оба должны ПРОЙТИ**

```
pytest tests/contracts/test_filler.py::test_filler_preserves_footer_page_field \
       tests/contracts/test_filler.py::test_filler_removes_empty_payment_rows -v
```

Ожидаемо: `PASSED`.

- [ ] **Step 4: Прогнать все тесты filler + убедиться нет регрессий**

```
pytest tests/contracts/test_filler.py -v
```

Ожидаемо: все PASS.

- [ ] **Step 5: Коммит**

```
git add src/contracts/filler.py tests/contracts/test_filler.py
git commit -m "fix(contracts/filler): сохранять PAGE-поле в footer, удалять пустые строки оплаты"
```

---

## Task 3: Написать тесты структуры шаблона (часть сразу пройдут, часть упадут)

**Files:**
- Modify: `tests/contracts/test_templates.py`

Перед написанием добавить в импорты (если ещё нет):
```python
from docx.oxml.ns import qn
```
(уже добавлен в Промте B)

- [ ] **Step 1: Добавить вспомогательную функцию проверки trPr/cantSplit**

В `tests/contracts/test_templates.py` добавить после `_has_para_prop`:

```python
def _row_has_cant_split(row) -> bool:
    trPr = row._tr.find(qn("w:trPr"))
    if trPr is None:
        return False
    cs = trPr.find(qn("w:cantSplit"))
    if cs is None:
        return False
    return cs.get(qn("w:val"), "1") not in ("0", "false", "off")
```

- [ ] **Step 2: Добавить тест на PAGE field в шаблоне** (регрессионный, сразу PASS)

```python
def test_spec_footer_has_page_field():
    """Шаблон spec_foundation_install.docx содержит поле PAGE в footer2."""
    import zipfile
    with zipfile.ZipFile(CONTRACTS / "spec_foundation_install.docx") as z:
        footer_xml = z.read("word/footer2.xml").decode("utf-8")
    assert "instrText" in footer_xml, "instrText отсутствует в footer2"
    assert "PAGE" in footer_xml, "Поле PAGE отсутствует в footer2"
```

- [ ] **Step 3: Добавить тест на keepWithNext п.15** (регрессионный, сразу PASS — из Промта B)

```python
def test_spec_п15_has_keep_with_next():
    """Параграф п.15 (Комплект поставки) имеет keepWithNext."""
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    p = _find_body_para(doc, "Комплект поставки")
    assert p is not None, "Параграф 'Комплект поставки' не найден"
    assert _has_para_prop(p, "w:keepWithNext"), "п.15 должен иметь keepWithNext"
```

- [ ] **Step 4: Добавить тест на cantSplit в TABLE[2]** (УПАДЁТ до Task 4)

```python
def test_spec_table2_rows_have_cant_split():
    """Все строки TABLE[2] (Комплект поставки) имеют cantSplit."""
    doc = Document(CONTRACTS / "spec_foundation_install.docx")
    assert len(doc.tables) > 2, "TABLE[2] не найдена в шаблоне"
    for i, row in enumerate(doc.tables[2].rows):
        assert _row_has_cant_split(row), (
            f"TABLE[2] row[{i}] должна иметь cantSplit"
        )
```

- [ ] **Step 5: Запустить — убедиться что тесты 1-3 PASS, тест 4 FAIL**

```
pytest tests/contracts/test_templates.py -v
```

Ожидаемо:
- `test_spec_footer_has_page_field` → PASS
- `test_spec_п15_has_keep_with_next` → PASS
- `test_spec_table2_rows_have_cant_split` → FAIL (cantSplit не проставлен)

---

## Task 4: Расширить patch_spec_template.py + перезапустить патч

**Files:**
- Modify: `scripts/patch_spec_template.py`
- Regenerate: `templates/contracts/spec_foundation_install.docx`

- [ ] **Step 1: Добавить функцию set_table_no_split**

После `set_keep_with_next` добавить:

```python
def set_table_no_split(table) -> None:
    """Запретить разрыв строк таблицы между страницами (idempotent)."""
    for row in table.rows:
        tr = row._tr
        trPr = tr.get_or_add_trPr()
        if trPr.find(qn("w:cantSplit")) is None:
            cant_split = OxmlElement("w:cantSplit")
            cant_split.set(qn("w:val"), "1")
            trPr.append(cant_split)
```

- [ ] **Step 2: Расширить main() — добавить новые правки после существующих**

Найти в `main()` блок после п.15 (`# п.15 (Комплект поставки)`). После строки `print(f"п.15: keepWithNext: ...")` добавить:

```python
    # Продолжаем keepWithNext-цепь: п.15 → пустой → TABLE[2]
    if p15:
        p15_next = _next_body_para(doc, p15)
        if p15_next is not None and not p15_next.text.strip():
            set_keep_with_next(p15_next)
            print("п.15 next (пустой): keepWithNext")

    # TABLE[2] — Комплект поставки: keepWithNext на строках кроме последней
    if len(doc.tables) > 2:
        kp_table = doc.tables[2]
        for row in kp_table.rows[:-1]:
            for cell in row.cells:
                for p in cell.paragraphs:
                    set_keep_with_next(p)
        print(f"TABLE[2] rows[:-1]: keepWithNext на {len(kp_table.rows) - 1} строках")
    else:
        print("WARNING: TABLE[2] (Комплект поставки) не найдена")

    # TABLE[1] и TABLE[2]: cantSplit на всех строках
    for tbl_idx, tbl_name in [(1, "ТХ"), (2, "Комплект поставки")]:
        if len(doc.tables) > tbl_idx:
            set_table_no_split(doc.tables[tbl_idx])
            print(f"TABLE[{tbl_idx}] ({tbl_name}): cantSplit на {len(doc.tables[tbl_idx].rows)} строках")
        else:
            print(f"WARNING: TABLE[{tbl_idx}] ({tbl_name}) не найдена")
```

- [ ] **Step 3: Восстановить шаблон из git и запустить обновлённый скрипт**

```
git checkout HEAD -- templates/contracts/spec_foundation_install.docx
python scripts/patch_spec_template.py
```

Ожидаемый вывод (все строки без WARNING):
```
Бэкап: templates\contracts\backup\spec_foundation_install.docx
п.14: pageBreakBefore + keepWithNext: ...
п.14 next (пустой): keepWithNext
TABLE[1] row[0]: keepWithNext на 3 ячейках
п.15: keepWithNext: ...
п.15 next (пустой): keepWithNext
TABLE[2] rows[:-1]: keepWithNext на 7 строках
TABLE[1] (ТХ): cantSplit на 11 строках
TABLE[2] (Комплект поставки): cantSplit на 8 строках
Приложение: pageBreakBefore: ...
Сохранено: templates\contracts\spec_foundation_install.docx
```

- [ ] **Step 4: Проверить что тест test_spec_table2_rows_have_cant_split теперь PASS**

```
pytest tests/contracts/test_templates.py -v
```

Ожидаемо: все 6 тестов PASS.

- [ ] **Step 5: Коммит скрипта и шаблона**

```
git add scripts/patch_spec_template.py templates/contracts/spec_foundation_install.docx \
        tests/contracts/test_templates.py
git commit -m "fix(templates/spec): cantSplit таблиц + keepWithNext-цепь п.15 (Промт C-prep)"
```

---

## Task 5: Финальная верификация

- [ ] **Step 1: Прогнать все тесты contracts + storage**

```
pytest tests/contracts/ tests/storage/ -v --tb=short
```

Ожидаемо: все unit-тесты PASS (синтетика e2e — ожидаемо падает по B1/B3/C5, это норма).

- [ ] **Step 2: Обновить STATUS.md**

В таблице багов:
```
| 1 | Пустые строки 2.5/2.6 в оплате | ✅ Закрыт (быстрый фикс filler.py) |
```

В разделе «Что выполнено» добавить блок «Промт C-prep ✅»:
- filler.py: guard для header/footer без плейсхолдеров (сохраняет PAGE-поле)
- filler.py: удаление пустых нумерованных параграфов после подстановки
- patch_spec_template.py: cantSplit TABLE[1]/TABLE[2], keepWithNext-цепь через P[56]
- +4 новых теста (2 в test_filler.py, 2 в test_templates.py → итого 10 в templates, 4 в filler)

- [ ] **Step 3: Коммит STATUS.md**

```
git add docs/STATUS.md
git commit -m "docs: закрыты баги 1/PAGE-field, расширена верстка spec"
```

---

## Self-Review

**Spec coverage:**
- Проблема 1 (п.15 отдельно) → Task 4: cantSplit + P[56] keepWithNext + TABLE[2] rows keepWithNext ✓
- Проблема 2 (PAGE=14) → Task 2: footer guard in fill_template ✓
- Проблема 3 (пустые П5/П6) → Task 2: remove empty numPr paragraphs ✓
- test_spec_п15_has_keep_with_next → Task 3 Step 3 ✓
- test_spec_footer_has_page_field → Task 3 Step 2 ✓
- test_filler_preserves_footer_page_field → Task 1 Step 2 + Task 2 ✓
- (test_filler_removes_empty_payment_rows — добавлен для TDD) ✓
- (test_spec_table2_rows_have_cant_split — добавлен для TDD Проблемы 1) ✓

**Placeholder scan:** нет TBD/TODO/«похоже на Task N»

**Type consistency:** `_find_body_para`, `_has_para_prop`, `_body_paras` — определены в test_templates.py в Промте B, используются в Task 3 без изменений ✓. `set_keep_with_next`, `set_page_break_before`, `_next_body_para` — уже в patch_spec_template.py ✓.

**Edge case:** `СПЕЦ_АДРЕС_ОБЪЕКТА_ПОЛНЫЙ` добавлен в SPEC_MOCK_DATA (из полного текста параграфа 48 в шаблоне). Если плейсхолдер отличается — тест footer/empty всё равно пройдёт (они не проверяют unfilled).
