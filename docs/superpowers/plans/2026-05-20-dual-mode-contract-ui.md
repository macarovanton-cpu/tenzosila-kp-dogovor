# Двухрежимный UI договора (Шаг 9) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в страницу договора два режима — «Из базы» (Supabase КП snapshot → плейсхолдеры) и «Из PDF» (существующий AI-парсинг), закрыть баги шаблонов A2/A3/P1.3.

**Architecture:** Новый модуль `src/contracts/from_kp.py` конвертирует kp_row из Supabase в плейсхолдеры СПЕЦ_* через `build_spec_items` + `render_payment_block`. Новая `extract_card_data` парсит только карточку контрагента (19 полей ЗАКАЗЧИК_*). Страница разветвляется через `st.radio`.

**Tech Stack:** Python 3.11, Streamlit, python-docx, pytest, Supabase (supabase-py), OpenRouter API (openai SDK).

---

## Уточнения перед исполнением

1. **Плейсхолдер даты в заголовке** → `{{ДОГОВОР_ДАТА_ПОЛНАЯ}}` (формат `27.05.2026`, возвращается `format_date_parts`). Проверено: `format_date_parts('2026-05-27')['ДОГОВОР_ДАТА_ПОЛНАЯ'] == '27.05.2026'`. Уже используется в patch_template.py Task 1.
2. **ОРИОН → П1**: `resolve_payment_group("orion_*")` попадает в `default → return "scales"`, т.е. все ОРИОН-опции агрегируются в П1. Потеря суммы невозможна — `resolve_payment_group` всегда возвращает одну из 4 групп.
3. **П5 всегда пустой** → `СПЕЦ_П5_НАИМЕНОВАНИЕ = ""`, `СПЕЦ_П5_СУММА = ""`. Word покажет пустые ячейки. Рекомендуется визуальная проверка первого сгенерированного документа.
4. **СПЕЦ_П*_СРОК поля** → оставить в форме SPEC_FIELDS без изменений (шаблоны Этапа 3 могут использовать). `from_kp.py` их не заполняет → поля пустые по умолчанию.

---

## Файловая карта

| Файл | Действие | Назначение |
|------|----------|-----------|
| `templates/backup/contract.docx` | Создать | Бекап перед патчем |
| `templates/backup/spec_foundation_install.docx` | Создать | Бекап перед патчем |
| `templates/contracts/contract.docx` | Изменить | Убрать захардкоженный header |
| `templates/contracts/spec_foundation_install.docx` | Изменить | Убрать header + «Компания Тензосила» |
| `scripts/patch_template.py` | Создать | Одноразовый скрипт патча шаблонов |
| `src/contracts/prompts/extract_card_data.txt` | Создать | Промт только для 19 ЗАКАЗЧИК_* полей |
| `src/contracts/extractor.py` | Изменить | Rename + alias + новая extract_card_data |
| `src/contracts/from_kp.py` | Создать | Маппинг kp_row → СПЕЦ_* плейсхолдеры |
| `src/contracts/state.py` | Изменить | set_specification, set_requisites, is_extracted update |
| `src/pages/2_Договор.py` | Изменить | st.radio + режимы A/B |
| `tests/contracts/test_extractor.py` | Создать | Тесты extractor refactor |
| `tests/contracts/test_from_kp.py` | Создать | Тесты build_specification_from_kp_snapshot |
| `tests/contracts/test_page_dogovor.py` | Создать | Тесты state helpers + mode logic |

---

## Task 1: Патч DOCX-шаблонов

**Files:**
- Create: `scripts/patch_template.py`
- Create: `templates/backup/` (директория)
- Modify: `templates/contracts/contract.docx`
- Modify: `templates/contracts/spec_foundation_install.docx`

- [ ] **Step 1.1: Написать failing-тест для наличия плейсхолдеров в заголовках**

```python
# tests/contracts/test_templates.py  (новый файл)
import re
from pathlib import Path
from docx import Document

CONTRACTS = Path("templates/contracts")

def _header_text(docx_path: Path) -> str:
    doc = Document(docx_path)
    parts = []
    for section in doc.sections:
        for p in section.header.paragraphs:
            parts.append(p.text)
    return "\n".join(parts)

def _all_text(docx_path: Path) -> str:
    doc = Document(docx_path)
    parts = []
    for p in doc.paragraphs:
        parts.append(p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    parts.append(p.text)
    return "\n".join(parts)

def test_contract_header_has_placeholder():
    text = _header_text(CONTRACTS / "contract.docx")
    assert "{{ДОГОВОР_НОМЕР}}" in text, f"Hardcoded header: {text!r}"
    assert "{{ДОГОВОР_ДАТА_ПОЛНАЯ}}" in text

def test_spec_header_has_placeholder():
    text = _header_text(CONTRACTS / "spec_foundation_install.docx")
    assert "{{ДОГОВОР_НОМЕР}}" in text, f"Hardcoded header: {text!r}"

def test_spec_no_kompaniya_tenzosila():
    text = _all_text(CONTRACTS / "spec_foundation_install.docx")
    assert "Компания Тензосила" not in text, "Нашли захардкоженное название"

def test_spec_has_tpk_tenzosila():
    text = _all_text(CONTRACTS / "spec_foundation_install.docx")
    assert "ТПК" in text, "ООО «ТПК «Тензосила»» должно быть в тексте"
```

- [ ] **Step 1.2: Запустить тест, убедиться что он падает**

```
pytest tests/contracts/test_templates.py -v
```

Ожидаем 3 FAIL: contract_header, spec_header, spec_no_kompaniya.

- [ ] **Step 1.3: Создать scripts/patch_template.py**

```python
"""scripts/patch_template.py — одноразовый патч шаблонов. Запускать из корня проекта."""
from pathlib import Path
import shutil
from docx import Document

TEMPLATES = Path("templates/contracts")
BACKUP = Path("templates/backup")


def _replace_in_paragraph(paragraph, old: str, new: str) -> bool:
    """Заменяет old→new в параграфе, склеивая runs при необходимости."""
    if old not in paragraph.text:
        return False
    # Пробуем прямую замену по runs
    for run in paragraph.runs:
        if old in run.text:
            run.text = run.text.replace(old, new)
            return True
    # Текст разбит на runs — склеиваем в первый run
    combined = paragraph.text
    if paragraph.runs:
        paragraph.runs[0].text = combined.replace(old, new)
        for r in paragraph.runs[1:]:
            r.text = ""
        return True
    return False


def _patch_header(doc, old: str, new: str) -> bool:
    for section in doc.sections:
        for p in section.header.paragraphs:
            if _replace_in_paragraph(p, old, new):
                return True
    return False


def _patch_table_cells(doc, old: str, new: str) -> int:
    count = 0
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    if _replace_in_paragraph(p, old, new):
                        count += 1
    return count


def patch_contract():
    src = TEMPLATES / "contract.docx"
    BACKUP.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, BACKUP / "contract.docx")
    doc = Document(src)
    ok = _patch_header(
        doc,
        "Договор № 29/2026 от 27.03.2026г",
        "Договор № {{ДОГОВОР_НОМЕР}} от {{ДОГОВОР_ДАТА_ПОЛНАЯ}}г",
    )
    if not ok:
        print("WARNING: contract.docx header — строка не найдена, возможно уже исправлено")
        return
    doc.save(src)
    print("contract.docx header ✓")


def patch_spec():
    src = TEMPLATES / "spec_foundation_install.docx"
    BACKUP.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, BACKUP / "spec_foundation_install.docx")
    doc = Document(src)
    ok = _patch_header(
        doc,
        "Договор № 110/2026 от 29.05.2026г",
        "Договор № {{ДОГОВОР_НОМЕР}} от {{ДОГОВОР_ДАТА_ПОЛНАЯ}}г",
    )
    if not ok:
        print("WARNING: spec header — строка не найдена")
    else:
        print("spec header ✓")
    n = _patch_table_cells(doc, "ООО «Компания Тензосила»", "ООО «ТПК «Тензосила»»")
    if n == 0:
        print("WARNING: «Компания Тензосила» — не найдено в ячейках")
    else:
        print(f"spec table cells ({n} шт.) ✓")
    doc.save(src)


if __name__ == "__main__":
    patch_contract()
    patch_spec()
    print("Готово.")
```

- [ ] **Step 1.4: Запустить скрипт патча**

```
python scripts/patch_template.py
```

Ожидаемый вывод:
```
contract.docx header ✓
spec header ✓
spec table cells (2 шт.) ✓
Готово.
```

- [ ] **Step 1.5: Запустить тест снова — все должны зеленеть**

```
pytest tests/contracts/test_templates.py -v
```

Ожидаем: 4 PASS.

- [ ] **Step 1.6: Commit**

```bash
git add templates/contracts/contract.docx templates/contracts/spec_foundation_install.docx
git add templates/backup/ scripts/patch_template.py tests/contracts/test_templates.py
git commit -m "fix(templates): убрать захардкоженные реквизиты из заголовков шаблонов (A2/A3/P1.3)"
```

---

## Task 2: Новый промт extract_card_data.txt

**Files:**
- Create: `src/contracts/prompts/extract_card_data.txt`

- [ ] **Step 2.1: Создать промт-файл**

```
# src/contracts/prompts/extract_card_data.txt
Ты — инструмент извлечения реквизитов контрагента для автоматизации договоров.

Тебе передаётся КАРТОЧКА КОНТРАГЕНТА — документ с реквизитами заказчика.

Твоя задача: извлечь данные и вернуть СТРОГО JSON без пояснений, markdown или комментариев.

ПРАВИЛА ИЗВЛЕЧЕНИЯ:

1. Должность и ФИО директора — четыре варианта:
   ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ    — именительный: "Генеральный директор"
   ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП — родительный:  "генерального директора"
   ЗАКАЗЧИК_ДИРЕКТОР_ФИО          — именительный: "Фокин Сергей Владимирович"
   ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП       — родительный:  "Фокина Сергея Владимировича"
   ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ     — краткая форма: "С.В. Фокин"

2. ЗАКАЗЧИК_ОСНОВАНИЕ — ВСЕГДА в родительном падеже.
   Примеры: "Устава", "Доверенности № 12 от 01.03.2026".
   НЕ писать: "Устав", "Доверенность".

3. Если поле не найдено — оставь пустую строку "".

Верни JSON строго в следующей структуре:

{
  "requisites": {
    "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "",
    "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": "",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП": "",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО": "",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП": "",
    "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "",
    "ЗАКАЗЧИК_ОСНОВАНИЕ": "",
    "ЗАКАЗЧИК_ИНН": "",
    "ЗАКАЗЧИК_КПП": "",
    "ЗАКАЗЧИК_ОГРН": "",
    "ЗАКАЗЧИК_АДРЕС_ЮР": "",
    "ЗАКАЗЧИК_АДРЕС_ПОЧТ": "",
    "ЗАКАЗЧИК_РС": "",
    "ЗАКАЗЧИК_БАНК": "",
    "ЗАКАЗЧИК_КС": "",
    "ЗАКАЗЧИК_БИК": "",
    "ЗАКАЗЧИК_ТЕЛЕФОН": "",
    "ЗАКАЗЧИК_EMAIL": ""
  }
}
```

- [ ] **Step 2.2: Commit**

```bash
git add src/contracts/prompts/extract_card_data.txt
git commit -m "feat(contracts): новый промт extract_card_data — только 19 реквизитов ЗАКАЗЧИК_*"
```

---

## Task 3: Рефакторинг extractor.py

**Files:**
- Create: `tests/contracts/test_extractor.py`
- Modify: `src/contracts/extractor.py`

- [ ] **Step 3.1: Написать failing-тесты**

```python
# tests/contracts/test_extractor.py
from __future__ import annotations
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_ai_client():
    """Мок OpenAI клиента для OpenRouter."""
    with patch("src.contracts.extractor.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture()
def mock_st():
    with patch("src.contracts.extractor.st") as m:
        m.secrets = {"OPENROUTER_API_KEY": "test-key"}
        yield m


@pytest.fixture()
def minimal_card_docx(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_paragraph("ООО Ромашка")
    doc.add_paragraph("ИНН 7701234567")
    path = tmp_path / "card.docx"
    doc.save(str(path))
    return str(path)


CARD_AI_RESPONSE = {
    "requisites": {
        "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "ООО Ромашка",
        "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": "Общество с ограниченной ответственностью «Ромашка»",
        "ЗАКАЗЧИК_ИНН": "7701234567",
        "ЗАКАЗЧИК_КПП": "770101001",
        "ЗАКАЗЧИК_ОГРН": "1234567890123",
        "ЗАКАЗЧИК_АДРЕС_ЮР": "г. Москва, ул. Ленина, 1",
        "ЗАКАЗЧИК_АДРЕС_ПОЧТ": "г. Москва, ул. Ленина, 1",
        "ЗАКАЗЧИК_РС": "40702810000000000001",
        "ЗАКАЗЧИК_БАНК": "Сбербанк",
        "ЗАКАЗЧИК_КС": "30101810400000000225",
        "ЗАКАЗЧИК_БИК": "044525225",
        "ЗАКАЗЧИК_ТЕЛЕФОН": "+7 495 123 45 67",
        "ЗАКАЗЧИК_EMAIL": "info@romashka.ru",
        "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "Генеральный директор",
        "ЗАКАЗЧИК_ДИРЕКТОР_ФИО": "Иванов Иван Иванович",
        "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП": "генерального директора",
        "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП": "Иванова Ивана Ивановича",
        "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "И.И. Иванов",
        "ЗАКАЗЧИК_ОСНОВАНИЕ": "Устава",
    }
}


class TestExtractCardData:
    def test_returns_only_requisites_key(self, mock_ai_client, mock_st, minimal_card_docx):
        mock_ai_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(CARD_AI_RESPONSE)))
        ]
        from src.contracts.extractor import extract_card_data
        result = extract_card_data(minimal_card_docx)
        assert "requisites" in result
        assert "specification" not in result

    def test_returns_19_requisite_fields(self, mock_ai_client, mock_st, minimal_card_docx):
        mock_ai_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(CARD_AI_RESPONSE)))
        ]
        from src.contracts.extractor import extract_card_data
        result = extract_card_data(minimal_card_docx)
        assert len(result["requisites"]) == 19
        assert result["requisites"]["ЗАКАЗЧИК_ИНН"] == "7701234567"

    def test_uses_card_only_prompt(self, mock_ai_client, mock_st, minimal_card_docx):
        """AI вызывается с промтом из extract_card_data.txt, не extract_contract_data.txt."""
        mock_ai_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(CARD_AI_RESPONSE)))
        ]
        from src.contracts.extractor import extract_card_data
        extract_card_data(minimal_card_docx)
        call_args = mock_ai_client.chat.completions.create.call_args
        system_prompt = call_args[1]["messages"][0]["content"]
        # Карточный промт — только реквизиты, не упоминает СПЕЦ_ поля
        assert "СПЕЦ_П1" not in system_prompt
        assert "ЗАКАЗЧИК_ИНН" in system_prompt

    def test_card_data_accepts_pdf(self, mock_ai_client, mock_st, tmp_path):
        """extract_card_data работает с PDF карточкой (фоллбек extract_pdf_text)."""
        # Создаём минимальный PDF через reportlab или просто мокаем extract_pdf_text
        mock_ai_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(CARD_AI_RESPONSE)))
        ]
        pdf_path = tmp_path / "card.pdf"
        # Создаём пустой PDF через pdfplumber workaround — мокаем вместо этого
        with patch("src.contracts.extractor.extract_pdf_text", return_value="карточка текст"):
            from src.contracts.extractor import extract_card_data
            result = extract_card_data(str(pdf_path))
        assert "requisites" in result


class TestLegacyAlias:
    def test_extract_from_files_is_alias_for_legacy(self):
        """extract_from_files указывает на ту же функцию что extract_kp_data_legacy."""
        from src.contracts.extractor import extract_from_files, extract_kp_data_legacy
        assert extract_from_files is extract_kp_data_legacy
```

- [ ] **Step 3.2: Запустить тест — убедиться что они падают**

```
pytest tests/contracts/test_extractor.py -v
```

Ожидаем: ImportError на `extract_card_data` и `extract_kp_data_legacy`.

- [ ] **Step 3.3: Обновить extractor.py**

Добавить в `src/contracts/extractor.py`:

1. Добавить второй PROMPT_PATH для карточки:
```python
PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_contract_data.txt"
CARD_PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_card_data.txt"
```

2. Переименовать `extract_from_files` → `extract_kp_data_legacy`:
```python
def extract_kp_data_legacy(kp_path: str, card_path: str) -> dict:
    """
    Legacy путь: принимает пути к КП (PDF) и карточке, возвращает dict
    с 'requisites' и 'specification'. Используется только в режиме B.
    """
    kp_text = extract_kp_text(kp_path)
    if card_path.lower().endswith('.pdf'):
        card_text = extract_pdf_text(card_path)
    else:
        card_text = extract_docx_text(card_path)
    data = extract_data_via_ai(kp_text, card_text)
    return data
```

3. Добавить `extract_card_data`:
```python
def extract_card_data(card_path: str) -> dict:
    """
    Парсит только карточку контрагента через AI.
    Возвращает {"requisites": {...}} с 19 полями ЗАКАЗЧИК_*.
    Используется в режиме A (КП из базы).
    """
    if card_path.lower().endswith('.pdf'):
        card_text = extract_pdf_text(card_path)
    else:
        card_text = extract_docx_text(card_path)

    with open(CARD_PROMPT_PATH, 'r', encoding='utf-8') as f:
        system_prompt = f.read()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=st.secrets["OPENROUTER_API_KEY"],
    )
    response = client.chat.completions.create(
        model="qwen/qwen3-235b-a22b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"КАРТОЧКА КОНТРАГЕНТА:\n{card_text}"},
        ],
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw.strip())
```

4. Добавить алиас в конце файла:
```python
# Алиас для обратной совместимости
extract_from_files = extract_kp_data_legacy
```

- [ ] **Step 3.4: Запустить тесты — убедиться что все зеленеют**

```
pytest tests/contracts/test_extractor.py -v
```

Ожидаем: 5 PASS.

- [ ] **Step 3.5: Убедиться что существующие тесты не сломаны**

```
pytest tests/ -v --ignore=tests/contracts/synthetic -x -q
```

Ожидаем: все зелёные (221 прохождение).

- [ ] **Step 3.6: Commit**

```bash
git add src/contracts/extractor.py tests/contracts/test_extractor.py
git commit -m "feat(contracts): extract_card_data — парсинг только карточки контрагента (режим A)"
```

---

## Task 4: Создать src/contracts/from_kp.py

**Files:**
- Create: `tests/contracts/test_from_kp.py`
- Create: `src/contracts/from_kp.py`

- [ ] **Step 4.1: Написать failing-тесты**

```python
# tests/contracts/test_from_kp.py
"""Тесты build_specification_from_kp_snapshot."""
from __future__ import annotations
import json
from pathlib import Path


# Загружаем реальные справочники (без @st.cache_data)
def _load(fname: str) -> dict:
    return json.loads(Path(f"data/{fname}").read_text(encoding="utf-8"))


PRICES = _load("prices.json")
MODELS = _load("models.json")
PAYMENT_TERMS = _load("payment_terms.json")


def _make_kp_row(
    model_line: str = "С",
    model_max: int = 60,
    model_length: int = 18,
    model_price: int | None = None,
    options: dict | None = None,
    payment_preset: str = "split_by_items",
    payment_split_state: dict | None = None,
) -> dict:
    """Фабрика минимального kp_row для тестов."""
    return {
        "kp_number": "КП-2026-001",
        "model_id": f"vesta-{model_line.lower()}-{model_max}-{model_length}",
        "total_price": 0,
        "data": {
            "model": {"line": model_line, "max": model_max, "length": model_length, "price": model_price},
            "equipment": {"sensor_id": "zemic_dhm9b_30t", "indicator_id": "titan_3cs", "cable_m": 20},
            "options": options or {},
            "spec_overrides": {},
            "payment": {
                "preset_id": payment_preset,
                "days": 5,
                "custom_text": "",
                "split_state": payment_split_state or {"scales": {"prepay": 50, "postpay": 50}},
                "v1_prepay": 50,
                "v2_prepay": 30,
                "v2_preship": 40,
                "v3_days": 15,
                "v3_trigger_id": "after_installation",
            },
            "metadata": {"kp_valid_days": 15, "warranty_months": 36},
            "construction": {
                "beam": "Двутавр 20Б1", "beam_count": 4,
                "center_beam": "", "center_beam_count": 0,
                "deck_mm": 6, "underlining_mm": 4,
            },
            "metrology": {"is_dual_range": False},
        },
    }


class TestBuildSpecFromKpSnapshot:
    def test_minimal_has_required_keys(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        kp_row = _make_kp_row()
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)

        required = {
            "СПЕЦ_НДС", "СПЕЦ_МОДЕЛЬ_КРАТКОЕ", "СПЕЦ_МАКС_НАГРУЗКА",
            "СПЕЦ_П1_НАИМЕНОВАНИЕ", "СПЕЦ_П1_СУММА",
            "СПЕЦ_П2_ПАРАМЕТРЫ", "СПЕЦ_П2_СУММА",
            "СПЕЦ_П3_НАИМЕНОВАНИЕ", "СПЕЦ_П3_СУММА",
            "СПЕЦ_П4_НАИМЕНОВАНИЕ", "СПЕЦ_П4_СУММА",
            "СПЕЦ_П5_НАИМЕНОВАНИЕ", "СПЕЦ_П5_СУММА",
            "СПЕЦ_ИТОГО", "СПЕЦ_ИТОГО_ПРОПИСЬ",
            "СПЕЦ_ОПЛАТА_П1", "СПЕЦ_ОПЛАТА_П2", "СПЕЦ_ОПЛАТА_П3",
            "СПЕЦ_ОПЛАТА_П4", "СПЕЦ_ОПЛАТА_П5", "СПЕЦ_ОПЛАТА_П6",
            "СПЕЦ_СРОК_ПОСТАВКИ", "СПЕЦ_СРОК_ФУНДАМЕНТ", "СПЕЦ_СРОК_МОНТАЖ",
        }
        assert required.issubset(spec.keys())

    def test_minimal_nds_is_22(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_НДС"] == "22"

    def test_model_краткое_формат(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(model_line="С", model_max=60, model_length=18),
            PRICES, MODELS, PAYMENT_TERMS,
        )
        assert spec["СПЕЦ_МОДЕЛЬ_КРАТКОЕ"] == "ВЕСТА-С-60-18"

    def test_no_foundation_fields_empty(self):
        """Без фундамента П2_ПАРАМЕТРЫ и П2_СУММА пустые."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        # Нет фундаментных опций
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_П2_ПАРАМЕТРЫ"] == ""
        assert spec["СПЕЦ_П2_СУММА"] == ""

    def test_with_foundation_option(self):
        """С фундаментом П2_ПАРАМЕТРЫ и П2_СУММА заполнены."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        # Ищем реальный ключ фундамента для С-60-18 в prices.json
        foundation_key = None
        for k in PRICES.get("options", {}):
            if k.startswith("foundation_s_f_") and "18" in k:
                foundation_key = k
                break
        if foundation_key is None:
            import pytest
            pytest.skip("Foundation option for С-60-18 not found in prices.json")

        options = {
            foundation_key: {"price": 350000, "qty": 1, "customer_side": False,
                             "retail": 350000, "dealer_is_synthetic": False}
        }
        kp_row = _make_kp_row(options=options)
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)
        assert "ВЕСТА-С" in spec["СПЕЦ_П2_ПАРАМЕТРЫ"]
        assert "18м" in spec["СПЕЦ_П2_ПАРАМЕТРЫ"]
        assert spec["СПЕЦ_П2_СУММА"] != ""

    def test_итого_equals_sum_of_positions(self):
        """СПЕЦ_ИТОГО == сумма всех П*_СУММА."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        total_str = spec["СПЕЦ_ИТОГО"].replace(" ", "").replace(" ", "")
        total = int(total_str) if total_str else 0

        parts_sum = 0
        for i in range(1, 6):
            key = f"СПЕЦ_П{i}_СУММА"
            val = spec.get(key, "").replace(" ", "").replace(" ", "")
            if val:
                parts_sum += int(val)

        assert total == parts_sum, f"ИТОГО {total} ≠ sum(П1..П5) {parts_sum}"

    def test_итого_пропись_not_empty(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_ИТОГО_ПРОПИСЬ"] != ""

    def test_оплата_п1_not_empty(self):
        """Хотя бы П1 условий оплаты заполнен."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_ОПЛАТА_П1"] != ""

    def test_срок_поставки_numeric(self):
        """СПЕЦ_СРОК_ПОСТАВКИ — строка с числом."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_СРОК_ПОСТАВКИ"].isdigit()

    def test_no_заказчик_fields(self):
        """ЗАКАЗЧИК_* поля НЕ должны быть в возвращаемом dict."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        zakazchik_keys = [k for k in spec if k.startswith("ЗАКАЗЧИК_")]
        assert zakazchik_keys == []
```

- [ ] **Step 4.2: Запустить тест — убедиться что падают**

```
pytest tests/contracts/test_from_kp.py -v
```

Ожидаем: ImportError на `from_kp`.

- [ ] **Step 4.3: Создать src/contracts/from_kp.py**

```python
"""Маппинг снапшота КП из Supabase в плейсхолдеры спецификации договора."""
from __future__ import annotations

from typing import Any

from src.term_days import TERM_DAYS_DEFAULTS, calculate_term_days_per_item


def _reconstruct_state(kp_row: dict[str, Any]) -> dict[str, Any]:
    """Разворачивает kp_row["data"] JSONB → state-подобный dict для build_spec_items."""
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    payment = data.get("payment") or {}

    options = {
        key: {
            "enabled": True,
            "price": v.get("price", 0),
            "qty": v.get("qty", 1),
            "customer_side": v.get("customer_side", False),
        }
        for key, v in (data.get("options") or {}).items()
    }

    return {
        "model_id": kp_row.get("model_id", ""),
        "model_line": model.get("line", ""),
        "model_max": model.get("max"),
        "model_length": model.get("length"),
        "model_price": model.get("price"),
        "sensor_id": (data.get("equipment") or {}).get("sensor_id", ""),
        "indicator_id": (data.get("equipment") or {}).get("indicator_id", ""),
        "options": options,
        "spec_items_overrides": data.get("spec_overrides") or {},
        "total_term_days": None,
        "payment_preset_id": payment.get("preset_id", "split_by_items"),
        "payment_days": payment.get("days", 5),
        "payment_custom_text": payment.get("custom_text", ""),
        "payment_split_state": payment.get("split_state") or {},
        "payment_v1_prepay": payment.get("v1_prepay", 50),
        "payment_v2_prepay": payment.get("v2_prepay", 30),
        "payment_v2_preship": payment.get("v2_preship", 40),
        "payment_v3_days": payment.get("v3_days", 15),
        "payment_v3_trigger_id": payment.get("v3_trigger_id", "after_installation"),
    }


def _fmt(amount: int) -> str:
    """Форматирует сумму: 2835000 → '2 835 000'."""
    return f"{amount:,}".replace(",", " ") if amount else ""


def build_specification_from_kp_snapshot(
    kp_row: dict[str, Any],
    prices: dict[str, Any],
    models_json: dict[str, Any],
    payment_terms: dict[str, Any],
) -> dict[str, str]:
    """Принимает строку из Supabase, возвращает плоский dict {СПЕЦ_* → str}
    для filler.fill_template. ЗАКАЗЧИК_* поля не возвращаются.

    kp_row: строка из таблицы kps (id, kp_number, model_id, data, ...)
    prices: содержимое data/prices.json
    models_json: содержимое data/models.json
    payment_terms: содержимое data/payment_terms.json
    """
    from src.spec_builder import build_spec_items
    from src.contracts.utils import number_to_words
    from src.generators.payment_renderer import render_payment_block

    state = _reconstruct_state(kp_row)
    spec_items = build_spec_items(state, prices, models_json)

    # Группируем по смыслу
    scales = [i for i in spec_items if i.get("payment_group") == "scales"]
    foundations = [i for i in spec_items if i.get("payment_group") == "foundation"]
    install_verify = [
        i for i in spec_items
        if i.get("payment_group") == "installation_and_verification"
    ]
    delivery = [i for i in spec_items if i.get("payment_group") == "delivery"]

    scales_total = sum(i["total"] for i in scales)
    foundation_total = sum(i["total"] for i in foundations)
    install_total = sum(i["total"] for i in install_verify)
    delivery_total = sum(i["total"] for i in delivery)
    grand_total = scales_total + foundation_total + install_total + delivery_total

    # Данные модели
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    line = model.get("line", "")
    max_t = model.get("max", "")
    length = model.get("length", "")
    model_short = f"ВЕСТА-{line}-{max_t}-{length}"

    # Сроки
    item_to_days, _ = calculate_term_days_per_item(spec_items)
    model_id = state.get("model_id", "")
    scales_term = str(item_to_days.get(model_id) or TERM_DAYS_DEFAULTS.get("scales", 20))

    foundation_term = ""
    for item in foundations:
        t = item_to_days.get(item["item_key"])
        if t is not None:
            foundation_term = str(t)
            break

    install_term = ""
    inst_sum = sum(
        item_to_days.get(i["item_key"], 0) or 0
        for i in install_verify
    )
    if inst_sum:
        install_term = str(inst_sum)

    # Условия оплаты → П1..П6
    payment_text = render_payment_block(state, spec_items, payment_terms)
    lines = [ln.strip() for ln in payment_text.split("\n") if ln.strip()]
    slots = (lines + [""] * 6)[:6]

    # П1 имя — первая строка названия модели (без датчиков/терминала)
    p1_name = ""
    if scales:
        model_item = next(
            (i for i in scales if i["item_key"].startswith("vesta-")), scales[0]
        )
        p1_name = model_item["name"].split("\n")[0]

    # П2 параметры: "ВЕСТА-С, 18м"
    p2_params = f"ВЕСТА-{line}, {length}м" if foundations else ""

    return {
        "СПЕЦ_НДС": "22",
        "СПЕЦ_МОДЕЛЬ_КРАТКОЕ": model_short,
        "СПЕЦ_МАКС_НАГРУЗКА": str(max_t),
        "СПЕЦ_П1_НАИМЕНОВАНИЕ": p1_name,
        "СПЕЦ_П1_СУММА": _fmt(scales_total),
        "СПЕЦ_П2_ПАРАМЕТРЫ": p2_params,
        "СПЕЦ_П2_СУММА": _fmt(foundation_total),
        "СПЕЦ_П3_НАИМЕНОВАНИЕ": "Монтаж и поверка" if install_verify else "",
        "СПЕЦ_П3_СУММА": _fmt(install_total),
        "СПЕЦ_П4_НАИМЕНОВАНИЕ": "Доставка" if delivery else "",
        "СПЕЦ_П4_СУММА": _fmt(delivery_total),
        "СПЕЦ_П5_НАИМЕНОВАНИЕ": "",
        "СПЕЦ_П5_СУММА": "",
        "СПЕЦ_ИТОГО": _fmt(grand_total),
        "СПЕЦ_ИТОГО_ПРОПИСЬ": number_to_words(grand_total),
        "СПЕЦ_ОПЛАТА_П1": slots[0],
        "СПЕЦ_ОПЛАТА_П2": slots[1],
        "СПЕЦ_ОПЛАТА_П3": slots[2],
        "СПЕЦ_ОПЛАТА_П4": slots[3],
        "СПЕЦ_ОПЛАТА_П5": slots[4],
        "СПЕЦ_ОПЛАТА_П6": slots[5],
        "СПЕЦ_СРОК_ПОСТАВКИ": scales_term,
        "СПЕЦ_СРОК_ФУНДАМЕНТ": foundation_term,
        "СПЕЦ_СРОК_МОНТАЖ": install_term,
    }
```

- [ ] **Step 4.4: Запустить тесты from_kp — все должны зеленеть**

```
pytest tests/contracts/test_from_kp.py -v
```

Ожидаем: 10 PASS.

- [ ] **Step 4.5: Запустить полный набор**

```
pytest tests/ -v --ignore=tests/contracts/synthetic -x -q
```

Ожидаем: все зелёные.

- [ ] **Step 4.6: Commit**

```bash
git add src/contracts/from_kp.py tests/contracts/test_from_kp.py
git commit -m "feat(contracts): build_specification_from_kp_snapshot — маппинг КП снапшота в СПЕЦ_*"
```

---

## Task 5: Обновить state.py

**Files:**
- Modify: `src/contracts/state.py`
- Modify: `tests/contracts/test_state.py` (добавить тесты, не менять существующие)

- [ ] **Step 5.1: Написать failing-тесты для новых функций**

Добавить в `tests/contracts/test_state.py`:

```python
# --- Добавить в конец файла ---

class TestIsExtractedModeA:
    def test_true_when_specification_populated(self, mock_session_state):
        """Mode A: is_extracted() → True когда specification заполнена."""
        from src.contracts.state import init_contract_state, is_extracted
        init_contract_state()
        mock_session_state["contract"]["specification"]["СПЕЦ_НДС"] = "22"
        assert is_extracted() is True

    def test_false_when_specification_empty_dict(self, mock_session_state):
        """is_extracted() → False если specification = {} (пустой)."""
        from src.contracts.state import init_contract_state, is_extracted
        init_contract_state()
        assert is_extracted() is False


class TestSetSpecification:
    def test_writes_spec_to_namespace(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_specification
        init_contract_state()
        spec = {"СПЕЦ_НДС": "22", "СПЕЦ_ИТОГО": "1000000"}
        set_specification(spec)
        cs = mock_session_state["contract"]
        assert cs["specification"]["СПЕЦ_НДС"] == "22"
        assert cs["specification"]["СПЕЦ_ИТОГО"] == "1000000"

    def test_pushes_widget_keys(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_specification
        init_contract_state()
        set_specification({"СПЕЦ_НДС": "22"})
        assert mock_session_state.get("w_СПЕЦ_НДС") == "22"

    def test_none_becomes_empty_string(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_specification
        init_contract_state()
        set_specification({"СПЕЦ_ИТОГО": None})
        assert mock_session_state["contract"]["specification"]["СПЕЦ_ИТОГО"] == ""


class TestSetRequisites:
    def test_writes_requisites_to_namespace(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_requisites
        init_contract_state()
        reqs = {"ЗАКАЗЧИК_ИНН": "7701234567"}
        set_requisites(reqs)
        cs = mock_session_state["contract"]
        assert cs["requisites"]["ЗАКАЗЧИК_ИНН"] == "7701234567"

    def test_pushes_widget_keys(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_requisites
        init_contract_state()
        set_requisites({"ЗАКАЗЧИК_ИНН": "7701234567"})
        assert mock_session_state.get("w_ЗАКАЗЧИК_ИНН") == "7701234567"
```

- [ ] **Step 5.2: Запустить новые тесты — убедиться что они падают**

```
pytest tests/contracts/test_state.py::TestIsExtractedModeA -v
pytest tests/contracts/test_state.py::TestSetSpecification -v
pytest tests/contracts/test_state.py::TestSetRequisites -v
```

Ожидаем: FAIL (ImportError на set_specification и set_requisites; is_extracted не проверяет specification).

- [ ] **Step 5.3: Обновить state.py**

Добавить в `src/contracts/state.py`:

1. Обновить `is_extracted()`:
```python
def is_extracted() -> bool:
    """True если данные готовы для отображения формы.
    Режим A: specification заполнена из КП снапшота.
    Режим B: ai_raw установлен после AI-extraction.
    """
    cs = st.session_state.get("contract", {})
    return bool(cs.get("ai_raw")) or bool(cs.get("specification"))
```

2. Добавить `set_specification()`:
```python
def set_specification(spec: dict[str, str]) -> None:
    """Записать данные спецификации из КП снапшота (режим A)."""
    cs = st.session_state["contract"]
    cs["specification"] = {k: (v or "") for k, v in spec.items()}
    for key, val in cs["specification"].items():
        st.session_state[f"w_{key}"] = val
```

3. Добавить `set_requisites()`:
```python
def set_requisites(requisites: dict[str, str]) -> None:
    """Записать реквизиты из карточки контрагента (режим A)."""
    cs = st.session_state["contract"]
    cs["requisites"] = {k: (v or "") for k, v in requisites.items()}
    for key, val in cs["requisites"].items():
        st.session_state[f"w_{key}"] = val
```

- [ ] **Step 5.4: Запустить все тесты state.py — все зелёные**

```
pytest tests/contracts/test_state.py -v
```

Ожидаем: все тесты PASS (включая старые `TestIsExtracted`).

- [ ] **Step 5.5: Commit**

```bash
git add src/contracts/state.py tests/contracts/test_state.py
git commit -m "feat(contracts/state): set_specification, set_requisites, is_extracted поддерживает mode A"
```

---

## Task 6: Переписать страницу 2_Договор.py

**Files:**
- Modify: `src/pages/2_Договор.py`
- Create: `tests/contracts/test_page_dogovor.py`

- [ ] **Step 6.1: Написать failing-тест логики страницы**

```python
# tests/contracts/test_page_dogovor.py
"""Тесты вспомогательной логики страницы договора."""
from __future__ import annotations
from unittest.mock import MagicMock, patch


@patch("src.contracts.state.st")
def test_mode_a_set_specification_makes_form_ready(mock_st):
    """После set_specification is_extracted() возвращает True."""
    state = {}
    mock_st.session_state = state
    from src.contracts.state import init_contract_state, set_specification, is_extracted
    init_contract_state()
    assert not is_extracted()
    set_specification({"СПЕЦ_НДС": "22", "СПЕЦ_ИТОГО": "500000"})
    assert is_extracted()


@patch("src.contracts.state.st")
def test_mode_b_set_extracted_data_makes_form_ready(mock_st):
    """Режим B: set_extracted_data (ai_raw) тоже делает is_extracted True."""
    state = {}
    mock_st.session_state = state
    from src.contracts.state import init_contract_state, set_extracted_data, is_extracted
    init_contract_state()
    set_extracted_data({"requisites": {"ЗАКАЗЧИК_ИНН": "123"}, "specification": {}})
    assert is_extracted()


def test_extract_from_files_legacy_alias_still_importable():
    """Импорт extract_from_files из extractor работает (для pages/2_Договор.py)."""
    from src.contracts.extractor import extract_from_files, extract_kp_data_legacy
    assert extract_from_files is extract_kp_data_legacy


def test_extract_card_data_importable():
    """extract_card_data доступна для импорта в страницу."""
    from src.contracts.extractor import extract_card_data
    assert callable(extract_card_data)


def test_build_specification_importable():
    """build_specification_from_kp_snapshot доступна для импорта."""
    from src.contracts.from_kp import build_specification_from_kp_snapshot
    assert callable(build_specification_from_kp_snapshot)
```

- [ ] **Step 6.2: Запустить тест — убедиться что базовые проходят**

```
pytest tests/contracts/test_page_dogovor.py -v
```

Ожидаем: 5 PASS (они тестируют то, что уже реализовано в задачах 3-5).

- [ ] **Step 6.3: Переписать pages/2_Договор.py**

Заменить содержимое `src/pages/2_Договор.py` на:

```python
"""Страница генерации договора и спецификации."""
from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.contracts.extractor import extract_card_data, extract_kp_data_legacy  # noqa: E402
from src.contracts.filler import fill_template, get_unfilled_placeholders  # noqa: E402
from src.contracts.from_kp import build_specification_from_kp_snapshot  # noqa: E402
from src.contracts.state import (  # noqa: E402
    collect_for_template,
    init_contract_state,
    is_extracted,
    set_extracted_data,
    set_requisites,
    set_specification,
    sync_field,
    sync_manual_field,
)
from src.contracts.utils import format_date_parts  # noqa: E402
from src.data_loader import load_models, load_payment_terms, load_prices  # noqa: E402
from src.storage.supabase_client import StorageError, get_kp_by_number, list_recent_kps  # noqa: E402
from src.utils.format import sanitize_filename  # noqa: E402

CONTRACT_TEMPLATE = Path("templates/contracts/contract.docx")
SPEC_TEMPLATE = Path("templates/contracts/spec_foundation_install.docx")
OUTPUT_DIR = Path("output/contracts")

st.set_page_config(page_title="Договор", page_icon="📄", layout="wide")
init_contract_state()

# ---------------------------------------------------------------------------
# Определения полей
# ---------------------------------------------------------------------------

REQUISITE_FIELDS: list[tuple[str, str]] = [
    ("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ", "Краткое наименование"),
    ("ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ", "Полное наименование"),
    ("ЗАКАЗЧИК_ИНН", "ИНН"),
    ("ЗАКАЗЧИК_КПП", "КПП"),
    ("ЗАКАЗЧИК_ОГРН", "ОГРН"),
    ("ЗАКАЗЧИК_АДРЕС_ЮР", "Юридический адрес"),
    ("ЗАКАЗЧИК_АДРЕС_ПОЧТ", "Почтовый адрес"),
    ("ЗАКАЗЧИК_РС", "Расчётный счёт"),
    ("ЗАКАЗЧИК_БАНК", "Банк"),
    ("ЗАКАЗЧИК_КС", "Корреспондентский счёт"),
    ("ЗАКАЗЧИК_БИК", "БИК"),
    ("ЗАКАЗЧИК_ТЕЛЕФОН", "Телефон"),
    ("ЗАКАЗЧИК_EMAIL", "Email"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ", "Должность руководителя"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "ФИО руководителя"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП", "Должность (род. падеж)"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП", "ФИО (род. падеж)"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ", "Инициалы"),
    ("ЗАКАЗЧИК_ОСНОВАНИЕ", "Основание"),
]

SPEC_FIELDS: list[tuple[str, str]] = [
    ("СПЕЦ_НДС", "Ставка НДС"),
    ("СПЕЦ_МОДЕЛЬ_КРАТКОЕ", "Модель (кратко)"),
    ("СПЕЦ_МАКС_НАГРУЗКА", "Макс. нагрузка"),
    ("СПЕЦ_П1_НАИМЕНОВАНИЕ", "П1 — Наименование"),
    ("СПЕЦ_П1_СУММА", "П1 — Сумма"),
    ("СПЕЦ_П1_СРОК", "П1 — Срок"),
    ("СПЕЦ_П2_ПАРАМЕТРЫ", "П2 — Параметры"),
    ("СПЕЦ_П2_СУММА", "П2 — Сумма"),
    ("СПЕЦ_П2_СРОК", "П2 — Срок"),
    ("СПЕЦ_П3_НАИМЕНОВАНИЕ", "П3 — Наименование"),
    ("СПЕЦ_П3_СУММА", "П3 — Сумма"),
    ("СПЕЦ_П3_СРОК", "П3 — Срок"),
    ("СПЕЦ_П4_НАИМЕНОВАНИЕ", "П4 — Наименование"),
    ("СПЕЦ_П4_СУММА", "П4 — Сумма"),
    ("СПЕЦ_П4_СРОК", "П4 — Срок"),
    ("СПЕЦ_П5_НАИМЕНОВАНИЕ", "П5 — Наименование"),
    ("СПЕЦ_П5_СУММА", "П5 — Сумма"),
    ("СПЕЦ_П5_СРОК", "П5 — Срок"),
    ("СПЕЦ_ИТОГО", "Итого"),
    ("СПЕЦ_ИТОГО_ПРОПИСЬ", "Итого прописью"),
    ("СПЕЦ_ОПЛАТА_П1", "Условие оплаты 1"),
    ("СПЕЦ_ОПЛАТА_П2", "Условие оплаты 2"),
    ("СПЕЦ_ОПЛАТА_П3", "Условие оплаты 3"),
    ("СПЕЦ_ОПЛАТА_П4", "Условие оплаты 4"),
    ("СПЕЦ_ОПЛАТА_П5", "Условие оплаты 5"),
    ("СПЕЦ_ОПЛАТА_П6", "Условие оплаты 6"),
    ("СПЕЦ_СРОК_ПОСТАВКИ", "Срок поставки"),
    ("СПЕЦ_СРОК_ФУНДАМЕНТ", "Срок фундамент"),
    ("СПЕЦ_СРОК_МОНТАЖ", "Срок монтаж"),
]

WIDE_FIELDS: set[str] = {
    "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ",
    "ЗАКАЗЧИК_АДРЕС_ЮР",
    "ЗАКАЗЧИК_АДРЕС_ПОЧТ",
    "СПЕЦ_ИТОГО_ПРОПИСЬ",
    "СПЕЦ_ОПЛАТА_П1",
    "СПЕЦ_ОПЛАТА_П2",
    "СПЕЦ_ОПЛАТА_П3",
    "СПЕЦ_ОПЛАТА_П4",
    "СПЕЦ_ОПЛАТА_П5",
    "СПЕЦ_ОПЛАТА_П6",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_uploaded(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return tmp.name


def _render_field_group(
    title: str, fields: list[tuple[str, str]], section: str,
) -> None:
    st.subheader(title)
    ns = st.session_state["contract"][section]
    col1, col2 = st.columns(2)
    for i, (key, label) in enumerate(fields):
        wkey = f"w_{key}"
        st.session_state.setdefault(wkey, ns.get(key, ""))
        col = col1 if i % 2 == 0 else col2
        with col:
            if key in WIDE_FIELDS:
                st.text_area(
                    label, key=wkey, height=68,
                    on_change=sync_field, args=(section, key),
                )
            else:
                st.text_input(
                    label, key=wkey,
                    on_change=sync_field, args=(section, key),
                )


# ---------------------------------------------------------------------------
# Секция 0 — Режим источника данных
# ---------------------------------------------------------------------------

st.title("Генерация договора")

mode = st.radio(
    "Источник данных коммерческого предложения",
    options=["Из базы (по номеру)", "Из PDF файла (старый КП)"],
    captions=[
        "Основной путь — для КП, сгенерированных в этом инструменте",
        "Резервный — для старых КП до Supabase",
    ],
    horizontal=True,
    key="contract_mode",
)

st.divider()

# ---------------------------------------------------------------------------
# Секция 1 — Загрузка данных (разветвление по режиму)
# ---------------------------------------------------------------------------

if mode == "Из базы (по номеру)":
    # ---- Mode A: КП из Supabase + карточка ----
    st.subheader("Выбор КП из базы")

    # Подтягиваем список последних КП
    try:
        recent = list_recent_kps(limit=50)
    except StorageError as e:
        st.error(f"Ошибка загрузки списка КП: {e}")
        recent = []

    kp_options_labels = ["— выбрать —"]
    kp_options_map: dict[str, dict] = {}
    for r in recent:
        price_str = f"{r.get('total_price', 0):,}".replace(",", " ")
        label = f"{r['kp_number']} — {r['client_name']} — {r.get('model_id', '')} — {price_str} ₽"
        kp_options_labels.append(label)
        kp_options_map[label] = r

    selected_label = st.selectbox(
        "Последние КП", kp_options_labels, key="kp_select"
    )

    st.caption("Или введите номер вручную:")
    manual_col1, manual_col2 = st.columns([3, 1])
    with manual_col1:
        manual_kp_num = st.text_input(
            "Номер КП", placeholder="КП-2026-001", label_visibility="collapsed",
            key="kp_number_input",
        )
    with manual_col2:
        search_clicked = st.button("Найти", key="kp_search_btn")

    kp_row = None
    if selected_label != "— выбрать —":
        kp_row = kp_options_map.get(selected_label)
    elif search_clicked and manual_kp_num:
        try:
            kp_row = get_kp_by_number(manual_kp_num.strip())
            if kp_row is None:
                st.warning(f"КП «{manual_kp_num}» не найден в базе.")
        except StorageError as e:
            st.error(f"Ошибка поиска: {e}")

    if kp_row is not None:
        try:
            prices = load_prices()
            models_json = load_models()
            payment_terms = load_payment_terms()
            spec = build_specification_from_kp_snapshot(
                kp_row, prices, models_json, payment_terms
            )
            set_specification(spec)
            kp_number_display = kp_row.get("kp_number", "")
            st.success(f"КП «{kp_number_display}» загружен из базы.")
        except Exception as exc:
            st.error(f"Ошибка загрузки спецификации: {exc}")

    st.divider()
    st.subheader("Карточка контрагента")
    card_file_a = st.file_uploader(
        "PDF или DOCX карточки контрагента", type=["pdf", "docx"],
        key="upload_card_a",
    )
    if st.button("Извлечь реквизиты через AI", disabled=card_file_a is None):
        with st.spinner("AI извлекает реквизиты..."):
            try:
                card_path = _save_uploaded(card_file_a)
                card_data = extract_card_data(card_path)
                set_requisites(card_data.get("requisites", {}))
                st.success("Реквизиты извлечены.")
            except Exception as exc:
                st.error(f"Ошибка извлечения реквизитов: {exc}")

else:
    # ---- Mode B: Legacy AI парсинг PDF КП + карточки ----
    st.info(
        "Используется AI-парсинг PDF КП. Возможны неточности — "
        "проверьте форму внимательно."
    )
    st.subheader("Загрузка документов")
    up_col1, up_col2 = st.columns(2)
    with up_col1:
        kp_file = st.file_uploader(
            "PDF коммерческого предложения", type=["pdf"], key="upload_kp"
        )
    with up_col2:
        card_file_b = st.file_uploader(
            "Карточка контрагента", type=["pdf", "docx"], key="upload_card"
        )

    extract_disabled = not (kp_file and card_file_b)
    if st.button("Извлечь данные через AI", disabled=extract_disabled):
        with st.spinner("AI извлекает данные..."):
            try:
                kp_path = _save_uploaded(kp_file)
                card_path = _save_uploaded(card_file_b)
                raw = extract_kp_data_legacy(kp_path, card_path)
                set_extracted_data(raw)
                st.success("Данные извлечены")
            except Exception as exc:
                st.error(f"Ошибка извлечения: {exc}")

st.divider()

# ---------------------------------------------------------------------------
# Секция 2 — Форма проверки и правки (общая для обоих режимов)
# ---------------------------------------------------------------------------

if is_extracted():
    _render_field_group("Реквизиты заказчика", REQUISITE_FIELDS, "requisites")
    st.divider()
    _render_field_group("Из коммерческого предложения", SPEC_FIELDS, "specification")
    st.divider()

# ---------------------------------------------------------------------------
# Секция 3 — Ручной ввод (общая)
# ---------------------------------------------------------------------------

st.subheader("Параметры договора")
_manual = st.session_state["contract"]["manual"]
manual_col1, manual_col2 = st.columns(2)
with manual_col1:
    st.session_state.setdefault("w_contract_number", _manual["contract_number"])
    contract_number = st.text_input(
        "Номер договора", placeholder="1-2026",
        key="w_contract_number",
        on_change=sync_manual_field, args=("contract_number",),
    )
    st.session_state.setdefault(
        "w_contract_date", _manual["contract_date"] or date.today(),
    )
    contract_date = st.date_input(
        "Дата договора",
        key="w_contract_date",
        on_change=sync_manual_field, args=("contract_date",),
    )
with manual_col2:
    st.session_state.setdefault("w_object_address", _manual["object_address"])
    object_address = st.text_input(
        "Адрес объекта монтажа",
        key="w_object_address",
        on_change=sync_manual_field, args=("object_address",),
    )
    st.session_state.setdefault("w_spec_number", _manual["spec_number"])
    spec_number = st.text_input(
        "Номер спецификации",
        key="w_spec_number",
        on_change=sync_manual_field, args=("spec_number",),
    )

st.divider()

# ---------------------------------------------------------------------------
# Секция 4 — Генерация (общая)
# ---------------------------------------------------------------------------

cs = st.session_state["contract"]
generate_disabled = (
    not (bool(cs.get("specification")) and bool(cs.get("requisites")))
    or not contract_number
    or not object_address
)

if st.button(
    "Сгенерировать договор и спецификацию", disabled=generate_disabled
):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    data = collect_for_template()
    date_parts = format_date_parts(str(contract_date))
    data.update(date_parts)
    data["ДОГОВОР_НОМЕР"] = contract_number
    data["СПЕЦ_АДРЕС_ОБЪЕКТА"] = object_address
    data["СПЕЦ_НОМЕР"] = spec_number

    nds = data.get("СПЕЦ_НДС", "")
    if not nds or "20" in nds:
        data["СПЕЦ_НДС"] = nds.replace("20", "22") if nds else "22"

    safe_name = sanitize_filename(data.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ", ""))
    safe_number = sanitize_filename(contract_number)
    contract_fname = f"Договор_{safe_number}_{safe_name}.docx"
    spec_fname = f"Спецификация_{safe_number}_{safe_name}.docx"

    contract_path = OUTPUT_DIR / contract_fname
    spec_path = OUTPUT_DIR / spec_fname

    try:
        fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
        fill_template(str(SPEC_TEMPLATE), data, str(spec_path))

        for label, path in [("Договор", contract_path), ("Спецификация", spec_path)]:
            unfilled = get_unfilled_placeholders(str(path))
            if unfilled:
                st.warning(f"{label} — не заполнены: {', '.join(unfilled)}")

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                f"Скачать {contract_fname}",
                data=contract_path.read_bytes(),
                file_name=contract_fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        with dl_col2:
            st.download_button(
                f"Скачать {spec_fname}",
                data=spec_path.read_bytes(),
                file_name=spec_fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        st.success("Документы сгенерированы")
    except Exception as exc:
        st.error(f"Ошибка генерации: {exc}")
```

- [ ] **Step 6.4: Запустить полный набор тестов (без синтетики, без сети)**

```
pytest tests/ -v --ignore=tests/contracts/synthetic -x -q
```

Ожидаем: все зелёные (≥ 226 тестов).

- [ ] **Step 6.5: Commit**

```bash
git add src/pages/2_Договор.py tests/contracts/test_page_dogovor.py
git commit -m "feat(pages): двухрежимный UI договора — режим A (из базы) + режим B (legacy PDF)"
```

---

## Task 7: Финальный прогон и обновление STATUS.md

**Files:**
- Modify: `docs/STATUS.md`

- [ ] **Step 7.1: Запустить весь тест-набор**

```
pytest tests/ -v --ignore=tests/contracts/synthetic -q
```

Ожидаем: все зелёные. Минимум: 226 PASS, 0 FAIL.

- [ ] **Step 7.2: Убедиться что legacy-синтетика не ухудшилась**

```
pytest tests/contracts/synthetic/test_e2e_synthetic.py -v --timeout=120
```

Ожидаем: те же кейсы что и раньше (A2/A3 закрыты, остальные как были).

- [ ] **Step 7.3: Обновить STATUS.md**

В секцию "Что выполнено" добавить:
```
### Шаг 9 ✅ — Двухрежимный UI договора
- Режим A: selectbox/text_input → get_kp_by_number → build_specification_from_kp_snapshot
- Режим B: extract_kp_data_legacy (алиас extract_from_files), без изменений
- extract_card_data: только 19 ЗАКАЗЧИК_* через extract_card_data.txt
- set_specification, set_requisites, is_extracted обновлён для режима A
- Шаблоны: contract.docx и spec_foundation_install.docx — хардкод убран
- Баги A2/A3/P1.3 закрыты; P1.4 неактуален (ИНИЦИАЛЫ в шаблоне)
- 8 новых тестов extractor + 10 from_kp + 5 state + 5 page + 4 templates = +32 теста
```

Также обновить "Открытые баги" — убрать A2, A3, P1.3.

- [ ] **Step 7.4: Commit**

```bash
git add docs/STATUS.md
git commit -m "docs: Шаг 9 выполнен — двухрежимный UI договора"
```

---

## Self-Review

**Spec coverage:**
- [x] Подзадача 1: `extract_card_data` + `extract_kp_data_legacy` + алиас → Task 3
- [x] Подзадача 2: `from_kp.py` + маппинг → Task 4
- [x] Подзадача 3: `st.radio` + режимы A/B → Task 6
- [x] Подзадача 4: патч шаблонов A2/A3/P1.3 → Task 1
- [x] P1.4 — задокументировано как неактуальный баг
- [x] Тесты test_extractor + test_from_kp + test_page_dogovor → Tasks 3/4/6
- [x] Защита legacy: алиас + Mode B без изменений → Task 3/6
- [x] Не ломаем 221 существующий тест → Step 4.5

**Gaps:**
- P1.1 (строка «Ограждение» в таблице): закрывается по дизайну — в режиме A ограждение агрегируется в П1. В режиме B (legacy AI) поведение не изменилось (баг остаётся открытым как было).
- P1.2 (ТТХ статичны) — запланирован в Этапе 3, не входит в Шаг 9.
- test_e2e_synthetic B1/B3/C5 — ожидаемые падения в legacy-режиме, задокументированы в STATUS.md.

**Type consistency:**
- `build_specification_from_kp_snapshot(kp_row, prices, models_json, payment_terms) -> dict[str, str]` — используется одинаково в from_kp.py, test_from_kp.py, и page
- `extract_card_data(card_path: str) -> dict` — возвращает `{"requisites": {...}}`, используется в page через `card_data.get("requisites", {})`
- `set_specification(spec: dict[str, str])` / `set_requisites(requisites: dict[str, str])` — принимают плоские dict, одинаково в state.py и тестах
