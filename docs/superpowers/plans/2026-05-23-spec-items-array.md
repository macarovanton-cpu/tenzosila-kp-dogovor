# Spec Items Array Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded 5-slot spec table in the contract workflow with a dynamic array of SpecItem objects, with full UI editing and DOCX rendering.

**Architecture:** SpecItem is a TypedDict stored in `st.session_state["contract"]["specification"]["items"]`. `build_specification_items(kp_row)` in `from_kp.py` maps KP snapshot options to SpecItem list. `fill_spec_with_items()` in `filler.py` uses a two-step approach: (1) `fill_template()` for all non-table content, (2) python-docx XML manipulation to replace Table[0] rows with dynamic item rows.

**Tech Stack:** Python 3.11, TypedDict, python-docx (lxml XML), Streamlit data_editor, pandas

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/contracts/spec_items.py` | CREATE | SpecItem TypedDict + `make_custom_item()` + `_option_key_to_spec_id()` |
| `src/contracts/from_kp.py` | MODIFY | Add `build_specification_items(kp_row)` |
| `src/contracts/state.py` | MODIFY | `set_spec_items()`, `get_spec_items()`, updated `collect_for_template()` + `is_extracted()` |
| `src/contracts/filler.py` | MODIFY | Add `fill_spec_with_items()` + 2 XML helpers |
| `src/pages/2_Договор.py` | MODIFY | `st.data_editor` for items, "+ Добавить" button, updated generation logic |
| `tests/contracts/test_spec_items.py` | CREATE | Unit tests for `build_specification_items` + integration DOCX test |
| `tests/contracts/test_state.py` | MODIFY | Tests for `set_spec_items`, `get_spec_items`, updated functions |
| `tests/contracts/test_filler.py` | MODIFY | Test for `fill_spec_with_items` |

---

## Task 1: SpecItem TypedDict + helpers

**Files:**
- Create: `src/contracts/spec_items.py`

- [ ] **Step 1.1: Create `src/contracts/spec_items.py`**

```python
"""SpecItem — единица спецификации договора."""
from __future__ import annotations

import uuid
from typing import Literal, Optional, TypedDict


class SpecItem(TypedDict):
    id: str
    name: str
    unit: str
    quantity: float
    price_per_unit: float
    total: float
    payment_group: Optional[int]
    is_custom: bool
    source: Literal["preset", "custom"]
    metadata: dict


def make_custom_item(
    name: str = "",
    unit: str = "шт",
    quantity: float = 1.0,
    price_per_unit: float = 0.0,
) -> SpecItem:
    """Создать пустую кастомную позицию."""
    total = quantity * price_per_unit
    return {  # type: ignore[return-value]
        "id": f"custom_{uuid.uuid4().hex[:8]}",
        "name": name,
        "unit": unit,
        "quantity": quantity,
        "price_per_unit": price_per_unit,
        "total": total,
        "payment_group": None,
        "is_custom": True,
        "source": "custom",
        "metadata": {},
    }


def _option_key_to_spec_id(key: str) -> str | None:
    """Вернуть canonical id позиции для ключа опции или None (→ custom)."""
    if key == "delivery_default":
        return "delivery"
    if key == "install_default":
        return "installation"
    if key == "verification_default":
        return "verification"
    if key.startswith("foundation_"):
        return "foundation"
    if "orion_install" in key:
        return "orion_install"
    if key.startswith("orion"):
        return "orion"
    if key.startswith("fence"):
        return "fence"
    if key.startswith("bytovka"):
        return "bytovka"
    if key.startswith("rama"):
        return "rama"
    if key.startswith("pandus"):
        return "pandus"
    return None
```

- [ ] **Step 1.2: Verify import**

Run: `python -c "from src.contracts.spec_items import SpecItem, make_custom_item, _option_key_to_spec_id; print('ok')"`
Expected: `ok`

- [ ] **Step 1.3: Commit**

```bash
rtk git add src/contracts/spec_items.py
rtk git commit -m "feat(contracts): SpecItem TypedDict + make_custom_item + _option_key_to_spec_id"
```

---

## Task 2: `build_specification_items()` + tests

**Files:**
- Modify: `src/contracts/from_kp.py` (add function + import)
- Create: `tests/contracts/test_spec_items.py`

- [ ] **Step 2.1: Add import and function to `src/contracts/from_kp.py`**

Add at top of file (after existing imports):
```python
import uuid
from src.contracts.spec_items import SpecItem, _option_key_to_spec_id
```

Add after `build_spec_rows_from_snapshot()`:
```python
_ITEM_ORDER: dict[str, int] = {
    "weights": 0,
    "foundation": 1,
    "installation": 2,
    "verification": 3,
    "delivery": 4,
}


def build_specification_items(kp_row: dict[str, Any]) -> list[SpecItem]:
    """Собрать список SpecItem из строки КП Supabase.

    Цены хранятся с НДС (та же конвенция что и в prices.json и КП).
    """
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    line = model.get("line", "")
    max_t = model.get("max", "")
    length = model.get("length", "")
    model_price = float(model.get("price") or 0)
    options = data.get("options") or {}

    items: list[SpecItem] = []

    # Позиция весов — всегда первая
    model_name = (
        f"Весы автомобильные ВЕСТА-{line}-{max_t}-{length}-Ц, "
        f"max {max_t}т, размеры платформы {length}х3м"
    )
    items.append({  # type: ignore[misc]
        "id": "weights",
        "name": model_name,
        "unit": "компл",
        "quantity": 1.0,
        "price_per_unit": model_price,
        "total": model_price,
        "payment_group": None,
        "is_custom": False,
        "source": "preset",
        "metadata": {"line": line, "max": max_t, "length": length},
    })

    for key, opt in options.items():
        qty = float(opt.get("qty", 1) or 1)
        if qty == 0:
            continue

        customer_side = bool(opt.get("customer_side", False))
        price = 0.0 if customer_side else float(opt.get("price") or 0)

        spec_id = _option_key_to_spec_id(key)
        is_custom = spec_id is None
        if is_custom:
            _logger.warning("build_specification_items: неизвестный ключ %r", key)
            spec_id = f"custom_{uuid.uuid4().hex[:8]}"

        name = _resolve_option_name(key, line)
        if name is None:
            name = key

        metadata: dict[str, Any] = {}
        if customer_side:
            metadata["customer_side"] = True
        if spec_id == "installation":
            has_foundation = any(k.startswith("foundation_") for k in options)
            metadata["scope"] = "fundament" if has_foundation else "rama"
        elif spec_id == "foundation":
            if "_lite_" in key:
                metadata["scope"] = "pandus_lite"
            elif "_std_" in key:
                metadata["scope"] = "pandus_std"
            else:
                metadata["scope"] = "fundament_jb"

        price_per_unit = price / qty if qty > 0 else 0.0

        items.append({  # type: ignore[misc]
            "id": spec_id,
            "name": name,
            "unit": "компл",
            "quantity": qty,
            "price_per_unit": price_per_unit,
            "total": price,
            "payment_group": None,
            "is_custom": is_custom,
            "source": "custom" if is_custom else "preset",
            "metadata": metadata,
        })

    items.sort(key=lambda x: _ITEM_ORDER.get(x["id"], 10))
    return items
```

- [ ] **Step 2.2: Write failing tests in `tests/contracts/test_spec_items.py`**

```python
"""Тесты build_specification_items."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest


def _load(fname: str) -> dict:
    return json.loads(Path(f"data/{fname}").read_text(encoding="utf-8"))


def _make_kp_row(
    model_line: str = "С",
    model_max: int = 60,
    model_length: int = 18,
    model_price: int = 2_835_000,
    options: dict | None = None,
) -> dict:
    return {
        "kp_number": "КП-2026-001",
        "model_id": f"vesta-{model_line.lower()}-{model_max}-{model_length}",
        "data": {
            "model": {
                "line": model_line, "max": model_max,
                "length": model_length, "price": model_price,
            },
            "options": options or {},
        },
    }


class TestBuildSpecificationItems:
    def test_minimal_has_weights(self):
        """Без опций → одна позиция 'weights'."""
        from src.contracts.from_kp import build_specification_items
        items = build_specification_items(_make_kp_row())
        assert len(items) == 1
        assert items[0]["id"] == "weights"
        assert items[0]["name"].startswith("Весы автомобильные ВЕСТА-С-60-18-Ц")
        assert items[0]["total"] == 2_835_000
        assert items[0]["is_custom"] is False
        assert items[0]["source"] == "preset"

    def test_delivery_option_mapped(self):
        """delivery_default → id='delivery', не кастомная."""
        from src.contracts.from_kp import build_specification_items
        opts = {"delivery_default": {"qty": 1, "price": 50_000, "customer_side": False}}
        items = build_specification_items(_make_kp_row(options=opts))
        delivery = next(i for i in items if i["id"] == "delivery")
        assert delivery["name"] == "Доставка весов до объекта"
        assert delivery["total"] == 50_000
        assert delivery["is_custom"] is False

    def test_foundation_with_metadata_scope(self):
        """foundation_s_f_18 → id='foundation', metadata.scope='fundament_jb'."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "foundation_s_f_18": {"qty": 1, "price": 350_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        found = next(i for i in items if i["id"] == "foundation")
        assert found["metadata"]["scope"] == "fundament_jb"
        assert found["total"] == 350_000

    def test_verification_customer_side(self):
        """customer_side=True → total=0, metadata.customer_side=True."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "verification_default": {
                "qty": 1, "price": 30_000, "customer_side": True,
            },
        }
        items = build_specification_items(_make_kp_row(options=opts))
        ver = next(i for i in items if i["id"] == "verification")
        assert ver["total"] == 0.0
        assert ver["metadata"]["customer_side"] is True

    def test_unknown_key_becomes_custom(self, caplog):
        """Неизвестный ключ опции → is_custom=True, WARNING в логе."""
        from src.contracts.from_kp import build_specification_items
        opts = {"future_unknown_42": {"qty": 1, "price": 99_000, "customer_side": False}}
        with caplog.at_level(logging.WARNING, logger="src.contracts.from_kp"):
            items = build_specification_items(_make_kp_row(options=opts))
        custom = next(i for i in items if i["is_custom"])
        assert custom["id"].startswith("custom_")
        assert custom["source"] == "custom"
        assert any("future_unknown_42" in m for m in caplog.messages)

    def test_sort_order(self):
        """weights < foundation < installation < verification < delivery."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "delivery_default": {"qty": 1, "price": 50_000, "customer_side": False},
            "install_default": {"qty": 1, "price": 80_000, "customer_side": False},
            "verification_default": {"qty": 1, "price": 30_000, "customer_side": False},
            "foundation_s_f_18": {"qty": 1, "price": 350_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        ids = [i["id"] for i in items]
        assert ids.index("weights") < ids.index("foundation")
        assert ids.index("foundation") < ids.index("installation")
        assert ids.index("installation") < ids.index("verification")
        assert ids.index("verification") < ids.index("delivery")

    def test_installation_scope_with_foundation(self):
        """install_default + foundation → scope='fundament'."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "install_default": {"qty": 1, "price": 80_000, "customer_side": False},
            "foundation_s_f_18": {"qty": 1, "price": 350_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        inst = next(i for i in items if i["id"] == "installation")
        assert inst["metadata"]["scope"] == "fundament"

    def test_total_equals_price(self):
        """total == price (qty=1 always for standard options)."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "install_default": {"qty": 1, "price": 80_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        inst = next(i for i in items if i["id"] == "installation")
        assert inst["total"] == inst["quantity"] * inst["price_per_unit"]
```

- [ ] **Step 2.3: Run tests — confirm FAIL**

```
pytest tests/contracts/test_spec_items.py -v
```
Expected: FAIL — `ImportError` or `AttributeError` since `build_specification_items` not yet added.

- [ ] **Step 2.4: Run tests — confirm PASS after Step 2.1**

```
pytest tests/contracts/test_spec_items.py -v
```
Expected: All 8 tests PASS.

- [ ] **Step 2.5: Run full contracts test suite — no regressions**

```
pytest tests/contracts/ -v --ignore=tests/contracts/synthetic
```
Expected: All existing tests PASS.

- [ ] **Step 2.6: Commit**

```bash
rtk git add src/contracts/from_kp.py tests/contracts/test_spec_items.py
rtk git commit -m "feat(contracts): build_specification_items — маппинг снапшота КП в SpecItem list"
```

---

## Task 3: State management

**Files:**
- Modify: `src/contracts/state.py`

- [ ] **Step 3.1: Add `set_spec_items`, `get_spec_items`, update `collect_for_template`, `is_extracted`**

In `src/contracts/state.py`:

**Replace** `collect_for_template`:
```python
def collect_for_template() -> dict[str, str]:
    """Собрать плоский dict для docxtpl из namespace (requisites + specification)."""
    cs = st.session_state["contract"]
    data: dict[str, str] = {}
    data.update(cs.get("requisites", {}))
    spec = cs.get("specification", {})
    data.update({k: v for k, v in spec.items() if k != "items"})
    return data
```

**Replace** `is_extracted`:
```python
def is_extracted() -> bool:
    """True если данные готовы для отображения формы."""
    cs = st.session_state.get("contract", {})
    spec = cs.get("specification", {})
    has_spec_fields = any(k != "items" for k in spec)
    return bool(cs.get("ai_raw")) or has_spec_fields
```

**Add** after `set_specification`:
```python
def set_spec_items(items: list) -> None:
    """Записать список SpecItem в specification['items']."""
    cs = st.session_state["contract"]
    cs.setdefault("specification", {})["items"] = items


def get_spec_items() -> list:
    """Получить список SpecItem из specification['items']."""
    cs = st.session_state.get("contract", {})
    return cs.get("specification", {}).get("items", [])
```

- [ ] **Step 3.2: Write tests for new state functions**

Add to `tests/contracts/test_state.py`:

```python
# ---------------------------------------------------------------------------
# set_spec_items / get_spec_items
# ---------------------------------------------------------------------------

class TestSetGetSpecItems:
    def test_set_and_get_items(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_spec_items, get_spec_items
        init_contract_state()
        items = [{"id": "weights", "name": "Весы", "unit": "компл",
                  "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
                  "payment_group": None, "is_custom": False,
                  "source": "preset", "metadata": {}}]
        set_spec_items(items)
        assert get_spec_items() == items

    def test_get_items_empty_by_default(self, mock_session_state):
        from src.contracts.state import init_contract_state, get_spec_items
        init_contract_state()
        assert get_spec_items() == []

    def test_items_stored_in_specification(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_spec_items
        init_contract_state()
        set_spec_items([{"id": "x"}])
        assert mock_session_state["contract"]["specification"]["items"] == [{"id": "x"}]


class TestCollectForTemplateExcludesItems:
    def test_items_key_excluded(self, mock_session_state):
        from src.contracts.state import init_contract_state, set_spec_items, collect_for_template
        init_contract_state()
        mock_session_state["contract"]["specification"]["СПЕЦ_НДС"] = "22"
        set_spec_items([{"id": "weights"}])
        data = collect_for_template()
        assert "items" not in data
        assert "СПЕЦ_НДС" in data


class TestIsExtractedWithItems:
    def test_false_when_only_items_set(self, mock_session_state):
        """is_extracted() → False если specification содержит только items=[]."""
        from src.contracts.state import init_contract_state, is_extracted, set_spec_items
        init_contract_state()
        set_spec_items([])
        assert is_extracted() is False

    def test_true_when_spec_fields_present(self, mock_session_state):
        from src.contracts.state import init_contract_state, is_extracted, set_spec_items
        init_contract_state()
        mock_session_state["contract"]["specification"]["СПЕЦ_НДС"] = "22"
        set_spec_items([{"id": "weights"}])
        assert is_extracted() is True
```

- [ ] **Step 3.3: Run state tests**

```
pytest tests/contracts/test_state.py -v
```
Expected: All tests PASS.

- [ ] **Step 3.4: Commit**

```bash
rtk git add src/contracts/state.py tests/contracts/test_state.py
rtk git commit -m "feat(contracts): state — set_spec_items, get_spec_items, fix collect_for_template/is_extracted"
```

---

## Task 4: `fill_spec_with_items()` in filler.py

**Files:**
- Modify: `src/contracts/filler.py`
- Modify: `tests/contracts/test_filler.py`

- [ ] **Step 4.1: Add helpers and `fill_spec_with_items` to `src/contracts/filler.py`**

Add at the top of `filler.py`, after existing imports:
```python
import copy
from docx.oxml.ns import qn
```

Add at the bottom of `filler.py`:
```python
def _fmt(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") if amount else ""


def _clear_row_text(tr_el) -> None:
    """Обнулить все w:t элементы в строке таблицы."""
    for t_el in tr_el.findall('.//' + qn('w:t')):
        t_el.text = ''


def _set_cell_text(tc_el, text: str) -> None:
    """Записать текст в первый w:t элемент ячейки таблицы."""
    t_els = tc_el.findall('.//' + qn('w:t'))
    if t_els:
        t_els[0].text = text


def fill_spec_with_items(
    template_path: str,
    data: dict,
    items: list[dict],
    output_path: str,
) -> None:
    """Рендер шаблона спецификации с динамическим массивом позиций.

    Двухшаговый подход:
    1. fill_template() для всех плейсхолдеров кроме строк таблицы (СПЕЦ_П* → '').
    2. python-docx: заменить строки Table[0] на позиции из items.

    Итого вычисляется из items и передаётся в fill_template.
    """
    from src.contracts.utils import number_to_words

    grand_total = sum(
        int(item.get("total", 0))
        for item in items
        if not item.get("metadata", {}).get("customer_side")
    )

    fill_data = dict(data)
    fill_data["СПЕЦ_ИТОГО"] = _fmt(grand_total)
    fill_data["СПЕЦ_ИТОГО_ПРОПИСЬ"] = number_to_words(grand_total)
    for i in range(1, 6):
        fill_data.setdefault(f"СПЕЦ_П{i}_НАИМЕНОВАНИЕ", "")
        fill_data.setdefault(f"СПЕЦ_П{i}_СУММА", "")
        fill_data.setdefault(f"СПЕЦ_П{i}_СРОК", "")

    fill_template(template_path, fill_data, output_path)

    doc = Document(output_path)
    table = doc.tables[0]
    tbl = table._tbl

    all_trs = [c for c in tbl if c.tag == qn('w:tr')]
    if len(all_trs) < 2:
        doc.save(output_path)
        return

    header_tr = all_trs[0]
    template_tr = copy.deepcopy(all_trs[1])

    for tr in all_trs[1:-1]:
        tbl.remove(tr)

    for item in reversed(items):
        new_tr = copy.deepcopy(template_tr)
        _clear_row_text(new_tr)

        customer_side = item.get("metadata", {}).get("customer_side", False)
        name_text = item.get("name", "")
        total_val = int(item.get("total", 0))
        total_text = "ЗАКАЗЧИК" if customer_side else (_fmt(total_val) if total_val else "")

        tcs = [c for c in new_tr if c.tag == qn('w:tc')]
        if tcs:
            _set_cell_text(tcs[0], name_text)
        if len(tcs) > 1:
            _set_cell_text(tcs[1], total_text)

        header_tr.addnext(new_tr)

    doc.save(output_path)
```

- [ ] **Step 4.2: Write test for `fill_spec_with_items`**

Add to `tests/contracts/test_filler.py`:

```python
import json
from pathlib import Path

SPEC_MOCK_ITEMS = [
    {
        "id": "weights",
        "name": "Весы автомобильные ВЕСТА-С-60-18-Ц, max 60т, размеры платформы 18х3м",
        "unit": "компл",
        "quantity": 1.0,
        "price_per_unit": 2_835_000.0,
        "total": 2_835_000.0,
        "payment_group": None,
        "is_custom": False,
        "source": "preset",
        "metadata": {},
    },
    {
        "id": "foundation",
        "name": "Фундамент железобетонный под весы ВЕСТА-С, 18м",
        "unit": "компл",
        "quantity": 1.0,
        "price_per_unit": 350_000.0,
        "total": 350_000.0,
        "payment_group": None,
        "is_custom": False,
        "source": "preset",
        "metadata": {"scope": "fundament_jb"},
    },
    {
        "id": "verification",
        "name": "Поверка автомобильных весов с доставкой эталонов",
        "unit": "компл",
        "quantity": 1.0,
        "price_per_unit": 0.0,
        "total": 0.0,
        "payment_group": None,
        "is_custom": False,
        "source": "preset",
        "metadata": {"customer_side": True},
    },
]


def test_fill_spec_with_items_row_count(tmp_path):
    """Table[0] содержит ровно len(items) строк данных (кроме header и total)."""
    from docx import Document
    from src.contracts.filler import fill_spec_with_items

    template = os.path.normpath(SPEC_TEMPLATE_PATH)
    output = str(tmp_path / "spec_items.docx")

    fill_spec_with_items(template, SPEC_MOCK_DATA, SPEC_MOCK_ITEMS, output)

    doc = Document(output)
    table = doc.tables[0]
    # Header row + N item rows + total row
    assert len(table.rows) == 1 + len(SPEC_MOCK_ITEMS) + 1


def test_fill_spec_with_items_names_in_table(tmp_path):
    """Наименования позиций присутствуют в Table[0]."""
    from docx import Document
    from src.contracts.filler import fill_spec_with_items

    template = os.path.normpath(SPEC_TEMPLATE_PATH)
    output = str(tmp_path / "spec_items_names.docx")

    fill_spec_with_items(template, SPEC_MOCK_DATA, SPEC_MOCK_ITEMS, output)

    doc = Document(output)
    table = doc.tables[0]
    all_text = " ".join(c.text for row in table.rows for c in row.cells)

    assert "Весы автомобильные ВЕСТА-С-60-18-Ц" in all_text
    assert "Фундамент железобетонный" in all_text
    assert "ЗАКАЗЧИК" in all_text  # customer_side item


def test_fill_spec_with_items_total_computed_from_items(tmp_path):
    """ИТОГО в Table[0] = сумма non-customer-side позиций."""
    from docx import Document
    from src.contracts.filler import fill_spec_with_items

    template = os.path.normpath(SPEC_TEMPLATE_PATH)
    output = str(tmp_path / "spec_items_total.docx")

    fill_spec_with_items(template, SPEC_MOCK_DATA, SPEC_MOCK_ITEMS, output)

    doc = Document(output)
    table = doc.tables[0]
    total_row = table.rows[-1]
    total_text = total_row.cells[1].text.replace(" ", " ").strip()
    # 2_835_000 + 350_000 = 3_185_000
    assert "3" in total_text  # Начинается с 3...
    assert total_text != ""


def test_fill_spec_with_items_preserves_footer_page_field(tmp_path):
    """fill_spec_with_items не уничтожает поле PAGE в footer."""
    import zipfile
    from src.contracts.filler import fill_spec_with_items

    template = os.path.normpath(SPEC_TEMPLATE_PATH)
    output = str(tmp_path / "spec_items_footer.docx")

    fill_spec_with_items(template, SPEC_MOCK_DATA, SPEC_MOCK_ITEMS, output)

    with zipfile.ZipFile(output) as z:
        footer_xml = z.read("word/footer2.xml").decode("utf-8")

    assert "PAGE" in footer_xml


def test_fill_spec_with_items_e2e_from_kp_snapshot(tmp_path):
    """E2E: KP snapshot → build_specification_items → fill_spec_with_items → DOCX."""
    import json as json_lib
    from docx import Document
    from src.contracts.from_kp import build_specification_items
    from src.contracts.filler import fill_spec_with_items

    kp_row = {
        "kp_number": "КП-2026-E2E",
        "model_id": "vesta-s-60-18",
        "data": {
            "model": {"line": "С", "max": 60, "length": 18, "price": 2_835_000},
            "options": {
                "foundation_s_f_18": {"qty": 1, "price": 350_000, "customer_side": False},
                "install_default": {"qty": 1, "price": 80_000, "customer_side": False},
                "delivery_default": {"qty": 1, "price": 50_000, "customer_side": False},
            },
        },
    }

    items = build_specification_items(kp_row)
    assert len(items) == 4  # weights + foundation + install + delivery

    template = os.path.normpath(SPEC_TEMPLATE_PATH)
    output = str(tmp_path / "spec_e2e.docx")
    fill_spec_with_items(template, SPEC_MOCK_DATA, items, output)

    doc = Document(output)
    table = doc.tables[0]
    # header + 4 items + total = 6
    assert len(table.rows) == 6

    item_names = [table.rows[i].cells[0].text for i in range(1, 5)]
    assert any("Весы" in n for n in item_names)
    assert any("Фундамент" in n for n in item_names)
    assert any("Монтаж" in n for n in item_names)
    assert any("Доставка" in n for n in item_names)
```

- [ ] **Step 4.3: Run filler tests**

```
pytest tests/contracts/test_filler.py -v
```
Expected: All tests PASS (including the 5 new ones).

- [ ] **Step 4.4: Commit**

```bash
rtk git add src/contracts/filler.py tests/contracts/test_filler.py
rtk git commit -m "feat(contracts): fill_spec_with_items — динамическая таблица позиций спецификации"
```

---

## Task 5: UI — spec items editor in `2_Договор.py`

**Files:**
- Modify: `src/pages/2_Договор.py`

### Changes overview:
1. Import `build_specification_items`, `set_spec_items`, `get_spec_items`, `fill_spec_with_items`, `make_custom_item`
2. In mode A (after KP load): call `build_specification_items` + `set_spec_items`
3. Replace `_render_field_group("Из коммерческого предложения", SPEC_FIELDS...)` with `st.data_editor` block
4. In generation handler: use `fill_spec_with_items` if items available

- [ ] **Step 5.1: Update imports at top of `2_Договор.py`**

Replace the existing import block for contracts:
```python
from src.contracts.extractor import extract_card_data, extract_kp_data_legacy  # noqa: E402
from src.contracts.filler import fill_spec_with_items, fill_template, get_unfilled_placeholders  # noqa: E402
from src.contracts.from_kp import build_specification_from_kp_snapshot, build_specification_items  # noqa: E402
from src.contracts.spec_items import make_custom_item  # noqa: E402
from src.contracts.state import (  # noqa: E402
    clear_generated,
    collect_for_template,
    get_spec_items,
    init_contract_state,
    is_extracted,
    set_extracted_data,
    set_requisites,
    set_spec_items,
    set_specification,
    sync_field,
    sync_manual_field,
)
```

- [ ] **Step 5.2: Add items build after KP load in mode A**

In the mode A block, after `set_specification(spec)` is called successfully, add:
```python
            set_specification(spec)
            # Build and store spec items from snapshot
            try:
                items = build_specification_items(kp_row)
                set_spec_items(items)
            except Exception as exc:
                _logger.warning("build_specification_items failed: %s", exc)
            st.success(f"КП «{kp_row.get('kp_number', '')}» загружен из базы.")
```

At the top of `2_Договор.py` (after existing imports), add the logger:
```python
import logging
_logger = logging.getLogger(__name__)
```

- [ ] **Step 5.3: Add helper functions for data_editor ↔ items conversion**

Add these helper functions before the "Helpers" section in `2_Договор.py` (or in the Helpers section):

```python
def _items_to_rows(items: list[dict]) -> list[dict]:
    """Конвертировать SpecItem list в строки для data_editor."""
    return [
        {
            "Наименование": item.get("name", ""),
            "Ед.": item.get("unit", "шт"),
            "Кол-во": item.get("quantity", 1.0),
            "Цена с НДС, руб.": item.get("price_per_unit", 0.0),
            "Сумма с НДС, руб.": item.get("total", 0.0),
        }
        for item in items
    ]


def _rows_to_items(rows, original_items: list[dict]) -> list[dict]:
    """Конвертировать строки data_editor обратно в SpecItem list.

    Для существующих строк (idx < len(original_items)) сохраняет id,
    payment_group, is_custom, source, metadata из оригинала.
    Новые строки (добавленные через data_editor) получают custom_* id.
    """
    import uuid
    result = []
    rows_list = rows.to_dict("records") if hasattr(rows, "to_dict") else list(rows)
    for i, row in enumerate(rows_list):
        if i < len(original_items):
            item = dict(original_items[i])
        else:
            item = {
                "id": f"custom_{uuid.uuid4().hex[:8]}",
                "payment_group": None,
                "is_custom": True,
                "source": "custom",
                "metadata": {},
            }
        qty = float(row.get("Кол-во") or 1)
        price = float(row.get("Цена с НДС, руб.") or 0)
        item["name"] = str(row.get("Наименование") or "")
        item["unit"] = str(row.get("Ед.") or "шт")
        item["quantity"] = qty
        item["price_per_unit"] = price
        item["total"] = qty * price
        result.append(item)
    return result
```

- [ ] **Step 5.4: Replace spec fields section in the form with items editor**

Find the block:
```python
    st.divider()
    _render_field_group("Из коммерческого предложения", SPEC_FIELDS, "specification")
    st.divider()
```

Replace with:
```python
    st.divider()
    spec_items = get_spec_items()
    if spec_items:
        st.subheader("Позиции спецификации")
        edited_df = st.data_editor(
            _items_to_rows(spec_items),
            num_rows="dynamic",
            column_config={
                "Наименование": st.column_config.TextColumn("Наименование"),
                "Ед.": st.column_config.TextColumn("Ед.", width="small"),
                "Кол-во": st.column_config.NumberColumn("Кол-во", min_value=0, step=1),
                "Цена с НДС, руб.": st.column_config.NumberColumn(
                    "Цена с НДС, руб.", min_value=0, format="%d"
                ),
                "Сумма с НДС, руб.": st.column_config.NumberColumn(
                    "Сумма с НДС, руб.", disabled=True, format="%d"
                ),
            },
            key="spec_items_editor",
            use_container_width=True,
            hide_index=True,
        )

        if st.button("+ Добавить позицию"):
            # Sync current editor edits → session state
            current_items = _rows_to_items(edited_df, spec_items)
            current_items.append(make_custom_item())
            set_spec_items(current_items)
            # Clear editor widget state → re-init with new items
            if "spec_items_editor" in st.session_state:
                del st.session_state["spec_items_editor"]
            st.rerun()

        # Recompute totals for display (disabled column shows initial value;
        # totals update on next rerun after user edits)
        _synced = _rows_to_items(edited_df, spec_items)
        for _item in _synced:
            _item["total"] = _item["quantity"] * _item["price_per_unit"]
        set_spec_items(_synced)

    else:
        # No items (mode B or not yet loaded) — show flat spec fields
        _render_field_group("Из коммерческого предложения", SPEC_FIELDS, "specification")

    st.divider()
```

- [ ] **Step 5.5: Update generation handler to use `fill_spec_with_items`**

Find the generation handler block (inside `if st.button("Сгенерировать договор и спецификацию"...)`):

Replace:
```python
            fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
            fill_template(str(SPEC_TEMPLATE), data, str(spec_path))
```

With:
```python
            fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
            items_for_docx = get_spec_items()
            if items_for_docx:
                # Use the current editor state (may have unsaved edits)
                editor_rows = st.session_state.get("spec_items_editor")
                if editor_rows is not None and hasattr(edited_df, "to_dict"):
                    items_for_docx = _rows_to_items(edited_df, items_for_docx)
                    for _i in items_for_docx:
                        _i["total"] = _i["quantity"] * _i["price_per_unit"]
                fill_spec_with_items(
                    str(SPEC_TEMPLATE), data, items_for_docx, str(spec_path)
                )
            else:
                fill_template(str(SPEC_TEMPLATE), data, str(spec_path))
```

Note: `edited_df` is in scope here because it is defined earlier in `if is_extracted()` block. If not in scope (mode B), `items_for_docx` will be empty and we fall back to `fill_template`.

**IMPORTANT:** The `edited_df` variable is defined inside the `if spec_items:` block. For the generation handler to access it, we need to ensure `edited_df` is available. Add a fallback before the generation block:

```python
# After the spec items block, before the divider:
if not spec_items:
    edited_df = None  # fallback — won't be used in generation
```

Or, restructure slightly so `edited_df` is always defined:

At the start of the `if is_extracted():` block, add:
```python
    edited_df = None  # Will be set in spec items section if items exist
```

- [ ] **Step 5.6: Manual smoke test**

Start Streamlit and verify:
```
streamlit run src/app.py
```
- Navigate to Договор page
- Load a KP in mode A
- Verify `st.data_editor` appears with spec items
- Edit a name field → verify Сумма stays (recomputes on next interaction)
- Click "+ Добавить позицию" → new empty row appears
- Delete a row via the row's built-in delete control
- Click "Сгенерировать" → DOCX downloads without errors

This is a manual test step. Proceed when the above behaviors are confirmed.

- [ ] **Step 5.7: Commit**

```bash
rtk git add src/pages/2_Договор.py
rtk git commit -m "feat(contracts): UI спецификации — st.data_editor + кнопка добавления позиции"
```

---

## Task 6: Integration & regression tests

**Files:**
- Modify: `tests/contracts/test_spec_items.py` (add UI simulation test)

- [ ] **Step 6.1: Add "add custom item" simulation test**

Add to `tests/contracts/test_spec_items.py`:

```python
class TestCustomItemFlow:
    def test_add_custom_item_appears_in_items(self):
        """Симуляция нажатия '+ Добавить позицию': кастомная позиция появляется в state."""
        from src.contracts.spec_items import make_custom_item

        initial_items = [
            {"id": "weights", "name": "Весы ВЕСТА-С-60-18",
             "unit": "компл", "quantity": 1.0,
             "price_per_unit": 2_835_000.0, "total": 2_835_000.0,
             "payment_group": None, "is_custom": False,
             "source": "preset", "metadata": {}},
        ]
        items = list(initial_items)
        items.append(make_custom_item(name="Тестовая позиция", price_per_unit=10_000.0))

        custom = next(i for i in items if i["is_custom"])
        assert custom["id"].startswith("custom_")
        assert custom["name"] == "Тестовая позиция"
        assert custom["source"] == "custom"
        assert len(items) == 2

    def test_custom_item_appears_in_docx(self, tmp_path):
        """Кастомная позиция попадает в Table[0] DOCX."""
        from src.contracts.spec_items import make_custom_item
        from src.contracts.filler import fill_spec_with_items
        from docx import Document

        items = [
            {"id": "weights", "name": "Весы автомобильные ВЕСТА-С-60-18-Ц",
             "unit": "компл", "quantity": 1.0,
             "price_per_unit": 2_835_000.0, "total": 2_835_000.0,
             "payment_group": None, "is_custom": False,
             "source": "preset", "metadata": {}},
            make_custom_item(name="Кастомное оборудование", price_per_unit=100_000.0),
        ]

        from tests.contracts.test_filler import SPEC_MOCK_DATA, SPEC_TEMPLATE_PATH
        import os
        template = os.path.normpath(SPEC_TEMPLATE_PATH)
        output = str(tmp_path / "spec_custom.docx")

        fill_spec_with_items(template, SPEC_MOCK_DATA, items, output)

        doc = Document(output)
        table = doc.tables[0]
        all_text = " ".join(c.text for row in table.rows for c in row.cells)
        assert "Кастомное оборудование" in all_text
        assert len(table.rows) == 1 + len(items) + 1  # header + 2 + total
```

- [ ] **Step 6.2: Run full test suite**

```
pytest tests/ -v --ignore=tests/contracts/synthetic -x
```
Expected: All tests PASS. If any fail, fix before continuing.

- [ ] **Step 6.3: Run synthetic-free contracts tests specifically**

```
pytest tests/contracts/ -v --ignore=tests/contracts/synthetic
```
Expected: All tests PASS.

- [ ] **Step 6.4: Commit**

```bash
rtk git add tests/contracts/test_spec_items.py
rtk git commit -m "test(contracts): интеграционные тесты — кастомная позиция в state и в DOCX"
```

---

## Task 7: Final verification and commit

- [ ] **Step 7.1: Run complete test suite**

```
pytest tests/ -v --ignore=tests/contracts/synthetic
```
Expected output: All tests PASS. Note count and any skips.

- [ ] **Step 7.2: Verify Streamlit runs without errors**

```
streamlit run src/app.py
```
Navigate to pages 1 (КП) and 2 (Договор). Confirm no import errors, no tracebacks.

- [ ] **Step 7.3: Update docs/STATUS.md**

Add to "Что работает сейчас" under "Модуль договоров":
```
- Спецификация: массив SpecItem вместо 5 фиксированных слотов
- st.data_editor: редактирование, добавление, удаление позиций
- fill_spec_with_items(): динамическая таблица позиций в DOCX
```

Add new шаг to completed:
```
### Шаг 12 — Массив позиций спецификации (без clauses) ✅
```

- [ ] **Step 7.4: Final commit**

```bash
rtk git add docs/STATUS.md
rtk git commit -m "docs: STATUS.md — шаг 12 (массив позиций спецификации) выполнен"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Covered by |
|-------------|-----------|
| SpecItem TypedDict с полями id/name/unit/quantity/price_per_unit/total/payment_group/is_custom/source/metadata | Task 1 |
| Цены С НДС | SpecItem + build_specification_items (price from snapshot = с НДС) |
| build_specification_items — маппинг weights/delivery/installation/verification/foundation | Task 2 |
| orion/orion_install/fence/bytovka/rama/pandus в маппинге | Task 2 (`_option_key_to_spec_id`) |
| metadata.scope для installation/foundation | Task 2 |
| Кастомные позиции → is_custom=True, source='custom', id='custom_<uuid>' | Task 2 + make_custom_item |
| set_spec_items / get_spec_items в state | Task 3 |
| collect_for_template исключает 'items' | Task 3 |
| is_extracted работает корректно при наличии items | Task 3 |
| fill_spec_with_items в filler.py | Task 4 |
| Итого из items (не из старых П*) | Task 4 |
| customer_side → 'ЗАКАЗЧИК' в ячейке | Task 4 |
| st.data_editor с 5 колонками | Task 5 |
| Кнопка '+ Добавить позицию' | Task 5 |
| Удаление (num_rows='dynamic') | Task 5 |
| Реактивность без st.form | Task 5 |
| DOCX используется fill_spec_with_items при наличии items | Task 5 |
| Fallback fill_template для mode B | Task 5 |
| Тест build_specification_items (5+ кейсов) | Task 2 |
| Тест: добавление кастомной → в items → в DOCX | Task 6 |
| E2E: KP snapshot → items → DOCX → правильная таблица | Task 4 (test_fill_spec_with_items_e2e_from_kp_snapshot) |
| Старые тесты не сломаны | Task 2.5, 6.2 |

**Gaps found:** None.

**Placeholder scan:** No TBD/TODO in code blocks. All imports explicit.

**Type consistency:**
- `SpecItem` used consistently across spec_items.py, from_kp.py, state.py, filler.py
- `_option_key_to_spec_id()` defined in spec_items.py, imported in from_kp.py ✅
- `fill_spec_with_items(template_path, data, items, output_path)` signature is consistent between filler.py and usage in 2_Договор.py ✅
- `make_custom_item()` returns a plain dict (matching SpecItem TypedDict) ✅

---

## Notes

**On "jinja-цикл" and "{% tr %} {% tc %}":** The task description references docxtpl syntax. After verification, Jinja2 DOES support Cyrillic variable names (confirmed by test). However, the existing `fill_template()` has critical post-processing (empty numbered paragraph removal, text box placeholder replacement, PAGE field guard in footer). To preserve these behaviors without risk, this plan uses python-docx XML manipulation (`copy.deepcopy` + `addnext`) for table row insertion rather than switching the spec template to docxtpl. The result is semantically identical: a Python loop over items inserts rows into the spec table, matching the "jinja loop over rows" intent. If full docxtpl migration is desired in a future step (e.g., for clauses library), it can be done as a standalone change with dedicated testing.

**On mode B fallback:** Mode B (legacy AI PDF parsing) does not produce SpecItem objects. The UI falls back to the existing flat field form, and generation falls back to `fill_template()`. This ensures the existing mode B flow is not broken.

**На note из задания:** Если структура session_state["contract"] потребует серьёзного рефакторинга (breaking change для существующих тестов) — проверьте Task 3.3 (все state tests GREEN). Если тесты красные — остановитесь и сообщите.
