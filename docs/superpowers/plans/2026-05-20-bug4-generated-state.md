# Bug 4 — Сохранение сгенерированных файлов в session_state

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Сохранять байты сгенерированных документов в `st.session_state["contract"]["generated"]`, чтобы кнопки скачивания не исчезали после rerun при нажатии на одну из них.

**Architecture:** Добавить ключ `"generated"` в namespace `contract` в state.py. После успешной генерации записать байты и имена файлов в этот ключ. В странице 2_Договор.py разделить UI на два взаимоисключающих блока: (1) кнопка «Сгенерировать» — показывается когда `generated` пуст; (2) кнопки скачивания + «Сгенерировать заново» — показываются когда `generated` есть. `init_contract_state` идемпотентна (`setdefault`), поэтому `generated` сохраняется между рерами.

**Tech Stack:** Python 3.11, Streamlit, pytest, unittest.mock

---

## Анализ текущего состояния

### Где хранятся данные сейчас (проблема)

В `src/pages/2_Договор.py:331-382` блок генерации:
```python
if st.button("Сгенерировать договор и спецификацию", disabled=generate_disabled):
    # ... генерация ...
    # Байты только в локальных переменных:
    data=contract_path.read_bytes()   # исчезает после rerun
    data=spec_path.read_bytes()       # исчезает после rerun
```
Кнопки скачивания находятся ВНУТРИ `if st.button(...)`. При нажатии на кнопку скачивания Streamlit делает rerun, `st.button("Сгенерировать...")` возвращает `False`, блок не выполняется, кнопки исчезают.

### Что изменится

- `src/contracts/state.py` — `_CONTRACT_DEFAULTS` получает `"generated": None`; новая функция `clear_generated()`
- `src/pages/2_Договор.py` — Section 4 реструктурируется: кнопка генерации в `if not generated:`, блок скачивания в `if generated:`
- `tests/test_page_dogovor.py` — 3 новых теста + `mock_session_state` фикстура

---

## Task 1: Добавить `generated` в state.py

**Files:**
- Modify: `src/contracts/state.py`

- [ ] **Step 1: Написать упавший тест** в `tests/contracts/test_state.py` — убедиться что ключ `generated` ожидается

```python
# Добавить в конец файла tests/contracts/test_state.py

class TestGeneratedKey:
    def test_init_creates_generated_none(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        assert "generated" in cs
        assert cs["generated"] is None

    def test_idempotent_does_not_clear_generated(self, mock_session_state):
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["generated"] = {"contract_bytes": b"x", "spec_bytes": b"y"}
        init_contract_state()  # симулируем rerun
        assert cs["generated"] is not None
        assert cs["generated"]["contract_bytes"] == b"x"

    def test_clear_generated_sets_none(self, mock_session_state):
        from src.contracts.state import init_contract_state, clear_generated
        init_contract_state()
        mock_session_state["contract"]["generated"] = {
            "contract_bytes": b"x",
            "contract_filename": "a.docx",
            "spec_bytes": b"y",
            "spec_filename": "b.docx",
        }
        clear_generated()
        assert mock_session_state["contract"]["generated"] is None
```

- [ ] **Step 2: Запустить тест, убедиться что падает**

```
pytest tests/contracts/test_state.py::TestGeneratedKey -v
```

Ожидаем: `FAILED` — `KeyError: 'generated'` и `ImportError: cannot import name 'clear_generated'`

- [ ] **Step 3: Изменить `src/contracts/state.py`**

В `_CONTRACT_DEFAULTS` добавить строку `"generated": None` (после `"ai_raw"`):

```python
_CONTRACT_DEFAULTS: dict[str, Any] = {
    "requisites": {},
    "specification": {},
    "manual": {
        "contract_number": "",
        "contract_date": None,
        "object_address": "",
        "spec_number": "1",
    },
    "uploads": {
        "kp": None,
        "card": None,
    },
    "ai_raw": None,
    "generated": None,
}
```

В конец файла добавить функцию `clear_generated`:

```python
def clear_generated() -> None:
    """Очистить сгенерированные файлы — вернуть страницу к форме генерации."""
    st.session_state["contract"]["generated"] = None
```

- [ ] **Step 4: Запустить тест, убедиться что зелёный**

```
pytest tests/contracts/test_state.py::TestGeneratedKey -v
```

Ожидаем: 3x `PASSED`

- [ ] **Step 5: Запустить полный suite state.py — убедиться ничего не сломалось**

```
pytest tests/contracts/test_state.py -v
```

Ожидаем: все `PASSED`

- [ ] **Step 6: Коммит**

```
rtk git add src/contracts/state.py tests/contracts/test_state.py
rtk git commit -m "feat(contracts/state): добавить generated в namespace и clear_generated()"
```

---

## Task 2: Добавить тесты в test_page_dogovor.py

**Files:**
- Modify: `tests/test_page_dogovor.py`

- [ ] **Step 1: Добавить фикстуру и 3 теста в конец `tests/test_page_dogovor.py`**

```python
# --- В начало файла добавить импорты ---
from unittest.mock import patch

# --- В конец файла добавить ---

@pytest.fixture()
def mock_session_state():
    """Мокаем st.session_state как обычный dict для тестов страницы."""
    state: dict = {}
    with patch("src.contracts.state.st") as mock_st:
        mock_st.session_state = state
        yield state


class TestGeneratedStatePage:
    def test_generated_contains_both_files(self, mock_session_state):
        """После генерации cs['generated'] содержит байты обоих документов."""
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["generated"] = {
            "contract_bytes": b"contract_content",
            "contract_filename": "Договор_1_ООО.docx",
            "spec_bytes": b"spec_content",
            "spec_filename": "Спецификация_1_ООО.docx",
        }
        gen = cs["generated"]
        assert gen["contract_bytes"] == b"contract_content"
        assert gen["spec_bytes"] == b"spec_content"
        assert gen["contract_filename"] == "Договор_1_ООО.docx"
        assert gen["spec_filename"] == "Спецификация_1_ООО.docx"

    def test_rerun_does_not_lose_bytes(self, mock_session_state):
        """Повторный rerun (init_contract_state) не затирает generated."""
        from src.contracts.state import init_contract_state
        init_contract_state()
        cs = mock_session_state["contract"]
        cs["generated"] = {
            "contract_bytes": b"contract_data",
            "contract_filename": "Договор.docx",
            "spec_bytes": b"spec_data",
            "spec_filename": "Спецификация.docx",
        }
        init_contract_state()  # симуляция rerun
        assert cs["generated"] is not None
        assert cs["generated"]["contract_bytes"] == b"contract_data"
        assert cs["generated"]["spec_bytes"] == b"spec_data"

    def test_clear_generated_resets_to_none(self, mock_session_state):
        """Кнопка 'Сгенерировать заново' очищает generated через clear_generated()."""
        from src.contracts.state import clear_generated, init_contract_state
        init_contract_state()
        mock_session_state["contract"]["generated"] = {
            "contract_bytes": b"x",
            "contract_filename": "a.docx",
            "spec_bytes": b"y",
            "spec_filename": "b.docx",
        }
        clear_generated()
        assert mock_session_state["contract"]["generated"] is None
```

Также добавить `import pytest` в начало файла если его нет.

- [ ] **Step 2: Запустить новые тесты**

```
pytest tests/test_page_dogovor.py -v
```

Ожидаем: 5x `PASSED` (2 старых + 3 новых)

- [ ] **Step 3: Коммит**

```
rtk git add tests/test_page_dogovor.py
rtk git commit -m "test(page_dogovor): тесты на сохранение generated в session_state"
```

---

## Task 3: Реструктурировать Section 4 в 2_Договор.py

**Files:**
- Modify: `src/pages/2_Договор.py`

Текущая Section 4 (строки 324-382) полностью заменяется.

- [ ] **Step 1: Обновить импорт `clear_generated` в начале файла**

Найти строку (строки 18-27):
```python
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
```

Заменить на:
```python
from src.contracts.state import (  # noqa: E402
    clear_generated,
    collect_for_template,
    init_contract_state,
    is_extracted,
    set_extracted_data,
    set_requisites,
    set_specification,
    sync_field,
    sync_manual_field,
)
```

- [ ] **Step 2: Заменить Section 4 в `src/pages/2_Договор.py`**

Найти весь блок Section 4 (строки 324-382) — от `cs = st.session_state["contract"]` до конца файла — и заменить на:

```python
# ---------------------------------------------------------------------------
# Секция 4 — Генерация (общая)
# ---------------------------------------------------------------------------

cs = st.session_state["contract"]
generated = cs.get("generated")

if not generated:
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

            cs["generated"] = {
                "contract_bytes": contract_path.read_bytes(),
                "contract_filename": contract_fname,
                "spec_bytes": spec_path.read_bytes(),
                "spec_filename": spec_fname,
            }
            generated = cs["generated"]
        except Exception as exc:
            st.error(f"Ошибка генерации: {exc}")

if generated:
    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            f"Скачать {generated['contract_filename']}",
            data=generated["contract_bytes"],
            file_name=generated["contract_filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with dl_col2:
        st.download_button(
            f"Скачать {generated['spec_filename']}",
            data=generated["spec_bytes"],
            file_name=generated["spec_filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    st.success("Документы сгенерированы")
    if st.button("Сгенерировать заново"):
        clear_generated()
        st.rerun()
```

- [ ] **Step 3: Запустить полный тестовый suite**

```
pytest tests/ -v --ignore=tests/test_e2e_synthetic.py
```

Ожидаем: все `PASSED` (без новых падений)

- [ ] **Step 4: Коммит**

```
rtk git add src/pages/2_Договор.py
rtk git commit -m "fix(pages/договор): байты документов в session_state — кнопки скачивания не теряются при rerun (баг 4)"
```

---

## Self-Review

**Spec coverage:**
- ✅ Байты сохраняются в `cs["generated"]` после генерации
- ✅ Кнопки скачивания рендерятся из `cs["generated"]` — выживают любой rerun
- ✅ Кнопка «Сгенерировать заново» вызывает `clear_generated()` + `st.rerun()`
- ✅ Legacy-режим B не тронут (та же логика генерации, только изменён блок сохранения/отображения)
- ✅ Форма проверки данных не тронута (Section 2, 3)
- ✅ 3 новых теста в `test_page_dogovor.py`
- ✅ `test_state.py` получает `TestGeneratedKey` (3 теста)

**Placeholder scan:** Нет TBD/TODO/placeholder в плане.

**Type consistency:**
- `clear_generated` — определена в Task 1, импортируется в Task 3 ✅
- `cs["generated"]` — структура `{contract_bytes, contract_filename, spec_bytes, spec_filename}` одинакова во всех местах ✅
- `generated` локальная переменная переназначается после успешной генерации (`generated = cs["generated"]`) чтобы `if generated:` сработал в том же рендер-цикле ✅
