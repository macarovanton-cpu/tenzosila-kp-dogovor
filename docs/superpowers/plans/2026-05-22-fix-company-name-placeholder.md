# Fix: Company Name Placeholder (КРАТКОЕ → ПОЛНОЕ) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `{{ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ}}` with `{{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}` in preambles and signature blocks of both contract templates, so "ООО «МЕРИДИАН»" appears instead of just "МЕРИДИАН".

**Architecture:** Idempotent patch script (`scripts/patch_placeholder_names.py`) opens each DOCX, finds target paragraphs/cells by content anchors, applies run-level replacement (same pattern as `filler.py`'s `merge_runs` + run iteration), saves. Then adds a unit test in `tests/contracts/test_templates.py`.

**Tech Stack:** Python 3.11, python-docx, pytest.

---

## Confirmed Inspection Results

| # | File | Location | Context | Action |
|---|------|----------|---------|--------|
| 1 | `contract.docx` | Body para containing `«Заказчик»` | Preamble | КРАТКОЕ → ПОЛНОЕ |
| 2 | `contract.docx` | TABLE[0] row[2] cell[1] (реквизиты) | Card header | КРАТКОЕ → ПОЛНОЕ |
| 3 | `contract.docx` | TABLE[1] row[0] cell[1] (подписи) | Signatures | КРАТКОЕ → ПОЛНОЕ |
| 4 | `spec.docx` | Body para containing `«Подрядчик»` | Preamble | КРАТКОЕ → ПОЛНОЕ |
| 5 | `spec.docx` | TABLE[3] row[0] cell[1] (подписи) | Signatures | КРАТКОЕ → ПОЛНОЕ |

---

## Files

- **Create:** `scripts/patch_placeholder_names.py`
- **Modify:** `tests/contracts/test_templates.py` (add 2 tests at the end)

---

## Task 1: Write failing tests

**File:** `tests/contracts/test_templates.py`

- [ ] **Step 1: Add the two failing tests at the end of the file**

```python
# --- плейсхолдер ПОЛНОЕ_НАИМЕНОВАНИЕ ---

def _filled_text(template_name: str) -> str:
    """Генерирует документ с тестовой карточкой, возвращает текст всех параграфов и таблиц."""
    import tempfile, os
    from src.contracts.filler import fill_template

    data = {
        "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "МЕРИДИАН",
        "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": 'ООО «МЕРИДИАН»',
        "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "Генеральный директор",
        "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП": "генерального директора",
        "ЗАКАЗЧИК_ДИРЕКТОР_ФИО": "Иванов Иван Иванович",
        "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП": "Иванова Ивана Ивановича",
        "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "И.И. Иванов",
        "ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ": "male",
        "ЗАКАЗЧИК_ОСНОВАНИЕ": "Устава",
        "ЗАКАЗЧИК_ИНН": "1234567890",
        "ЗАКАЗЧИК_КПП": "123456789",
        "ЗАКАЗЧИК_ОГРН": "1234567890123",
        "ЗАКАЗЧИК_АДРЕС_ЮР": "г. Москва, ул. Тестовая, 1",
        "ЗАКАЗЧИК_АДРЕС_ПОЧТ": "г. Москва, ул. Тестовая, 1",
        "ЗАКАЗЧИК_РС": "40702810000000000001",
        "ЗАКАЗЧИК_БАНК": "Тестбанк",
        "ЗАКАЗЧИК_КС": "30101810000000000001",
        "ЗАКАЗЧИК_БИК": "044525001",
        "ЗАКАЗЧИК_ТЕЛЕФОН": "+7 (999) 000-00-00",
        "ЗАКАЗЧИК_EMAIL": "test@example.com",
        # contract-specific
        "ДОГОВОР_НОМЕР": "1",
        "ДОГОВОР_ДАТА_ПОЛНАЯ": "01 января 2026 г.",
        "ДИРЕКТОР_ПРИЧАСТИЕ": "действующего",
        "ИСПОЛНИТЕЛЬ_ДИРЕКТОР_ФИО_РП": "Сенаторова Олега Александровича",
        # spec-specific
        "СПЕЦ_НОМЕР": "1",
        "СПЕЦ_НАИМЕНОВАНИЕ": "Поставка весового оборудования",
        "СПЕЦ_ОБЩАЯ_СУММА": "1 000 000",
        "СПЕЦ_ОБЩАЯ_СУММА_ПРОПИСЬЮ": "Один миллион рублей 00 копеек",
        "СПЕЦ_ОПЛАТА_П1": "50% — 500 000 руб.",
        "СПЕЦ_ОПЛАТА_П2": "50% — 500 000 руб.",
        "СПЕЦ_ОПЛАТА_П3": "",
        "СПЕЦ_ОПЛАТА_П4": "",
        "СПЕЦ_ОПЛАТА_П5": "",
        "СПЕЦ_ОПЛАТА_П6": "",
    }

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        out = tmp.name

    try:
        fill_template(str(CONTRACTS / template_name), data, out)
        doc = Document(out)
        parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        parts.append(p.text)
        return "\n".join(parts)
    finally:
        os.unlink(out)


def test_contract_preamble_and_signatures_use_full_name():
    """В теле договора и подписях должно быть ООО «МЕРИДИАН», не просто МЕРИДИАН."""
    text = _filled_text("contract.docx")
    # преамбула и тело содержат полное наименование
    assert 'ООО «МЕРИДИАН»' in text, "Полное наименование отсутствует в договоре"
    # В преамбуле/подписях «МЕРИДИАН» не должен стоять сам по себе (без ООО «»)
    # Ищем вхождение «МЕРИДИАН» без предшествующего «ООО «»
    import re
    # Допускаем "МЕРИДИАН" только внутри "ООО «МЕРИДИАН»"
    bare = re.findall(r'(?<!«)МЕРИДИАН', text)
    assert bare == [], f"Найдено голое «МЕРИДИАН» без ООО «»: {bare}"


def test_spec_preamble_and_signatures_use_full_name():
    """В преамбуле и подписях спецификации должно быть ООО «МЕРИДИАН», не просто МЕРИДИАН."""
    text = _filled_text("spec_foundation_install.docx")
    assert 'ООО «МЕРИДИАН»' in text, "Полное наименование отсутствует в спецификации"
    import re
    bare = re.findall(r'(?<!«)МЕРИДИАН', text)
    assert bare == [], f"Найдено голое «МЕРИДИАН» без ООО «»: {bare}"
```

- [ ] **Step 2: Run the tests to confirm they FAIL**

```
pytest tests/contracts/test_templates.py::test_contract_preamble_and_signatures_use_full_name tests/contracts/test_templates.py::test_spec_preamble_and_signatures_use_full_name -v
```

Expected: **FAIL** — `AssertionError: Найдено голое «МЕРИДИАН»` (both tests).

---

## Task 2: Create patch script

**File:** `scripts/patch_placeholder_names.py`

- [ ] **Step 3: Create the patch script**

```python
"""
Патч плейсхолдеров наименования заказчика:
  ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ → ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ
  в преамбуле и блоке подписей (реквизиты — без изменений).

Idempotent: повторный запуск безопасен.
Запускать из корня проекта:
    python scripts/patch_placeholder_names.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
import shutil

from docx import Document
from docx.oxml.ns import qn

OLD = "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"
NEW = "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ"
OLD_PH = f"{{{{{OLD}}}}}"
NEW_PH = f"{{{{{NEW}}}}}"

CONTRACTS = Path("templates/contracts")
BACKUP_DIR = Path("templates/contracts/backup")


def _merge_runs(para) -> None:
    """Склеивает соседние runs с одинаковым rPr (idempotent)."""
    runs = para.runs
    if len(runs) < 2:
        return
    i = 0
    while i < len(runs) - 1:
        curr, nxt = runs[i], runs[i + 1]
        curr_rpr = curr._r.find(qn("w:rPr"))
        nxt_rpr = nxt._r.find(qn("w:rPr"))
        cx = "" if curr_rpr is None else curr_rpr.xml
        nx = "" if nxt_rpr is None else nxt_rpr.xml
        if cx == nx:
            curr.text += nxt.text
            nxt._r.getparent().remove(nxt._r)
            runs = para.runs
        else:
            i += 1


def _replace_in_para(para) -> bool:
    """Заменяет OLD_PH → NEW_PH в runs параграфа. Возвращает True если изменено."""
    _merge_runs(para)
    changed = False
    for run in para.runs:
        if OLD_PH in run.text:
            run.text = run.text.replace(OLD_PH, NEW_PH)
            changed = True
    return changed


def _body_paras(doc):
    body_tag = qn("w:body")
    return [p for p in doc.paragraphs if p._p.getparent().tag == body_tag]


def patch_contract(path: Path) -> None:
    doc = Document(path)
    count = 0

    # Преамбула: body para содержащий «Заказчик»
    for p in _body_paras(doc):
        if "Заказчик" in p.text and OLD_PH in p.text:
            if _replace_in_para(p):
                count += 1
                print(f"  contract преамбула: {p.text[:100]!r}")

    # Реквизиты: TABLE[0] row[2] cell[1]
    if len(doc.tables) > 0:
        req_cell = doc.tables[0].rows[2].cells[1]
        for p in req_cell.paragraphs:
            if _replace_in_para(p):
                count += 1
                print(f"  contract реквизиты: {p.text[:80]!r}")

    # Подписи: TABLE[1] row[0] cell[1]
    if len(doc.tables) > 1:
        sig_cell = doc.tables[1].rows[0].cells[1]
        for p in sig_cell.paragraphs:
            if _replace_in_para(p):
                count += 1
                print(f"  contract подписи: {p.text[:80]!r}")

    doc.save(path)
    print(f"  Сохранено: {path}. Заменено: {count} вхождений.")


def patch_spec(path: Path) -> None:
    doc = Document(path)
    count = 0

    # Преамбула: body para содержащий «Подрядчик»
    for p in _body_paras(doc):
        if "Подрядчик" in p.text and OLD_PH in p.text:
            if _replace_in_para(p):
                count += 1
                print(f"  spec преамбула: {p.text[:100]!r}")

    # Подписи: TABLE[3] row[0] cell[1]
    if len(doc.tables) > 3:
        sig_cell = doc.tables[3].rows[0].cells[1]
        for p in sig_cell.paragraphs:
            if _replace_in_para(p):
                count += 1
                print(f"  spec подписи: {p.text[:80]!r}")

    doc.save(path)
    print(f"  Сохранено: {path}. Заменено: {count} вхождений.")


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    contract = CONTRACTS / "contract.docx"
    spec = CONTRACTS / "spec_foundation_install.docx"

    shutil.copy2(contract, BACKUP_DIR / "contract.docx")
    shutil.copy2(spec, BACKUP_DIR / "spec_foundation_install.docx")
    print(f"Бэкапы: {BACKUP_DIR}/")

    print("\nPatch contract.docx:")
    patch_contract(contract)

    print("\nPatch spec_foundation_install.docx:")
    patch_spec(spec)

    print("\nГотово. Проверь: python -m pytest tests/contracts/test_templates.py -v")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the patch script**

```
python scripts/patch_placeholder_names.py
```

Expected output (5 replacements total):
```
Бэкапы: templates/contracts/backup/
Patch contract.docx:
  contract преамбула: '{{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}, именуемое в дальнейшем «Заказчик»...'
  contract реквизиты: '{{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}'
  contract подписи: '{{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}'
  Сохранено: ... Заменено: 3 вхождений.
Patch spec_foundation_install.docx:
  spec преамбула: '...и {{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}, именуемое...'
  spec подписи: '{{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}'
  Сохранено: ... Заменено: 2 вхождений.
```

---

## Task 3: Verify all tests pass

- [ ] **Step 5: Run the two new tests to confirm they PASS**

```
pytest tests/contracts/test_templates.py::test_contract_preamble_and_signatures_use_full_name tests/contracts/test_templates.py::test_spec_preamble_and_signatures_use_full_name -v
```

Expected: **PASS**

- [ ] **Step 6: Run the full test suite to confirm no regressions**

```
pytest tests/ -v
```

Expected: all tests green (234+ existing + 2 new).

---

## Task 4: Commit

- [ ] **Step 7: Commit**

```bash
git add scripts/patch_placeholder_names.py \
        tests/contracts/test_templates.py \
        templates/contracts/contract.docx \
        templates/contracts/spec_foundation_install.docx \
        templates/contracts/backup/contract.docx \
        templates/contracts/backup/spec_foundation_install.docx
git commit -m "fix(contracts/templates): КРАТКОЕ → ПОЛНОЕ наименование в преамбуле и подписях"
```
