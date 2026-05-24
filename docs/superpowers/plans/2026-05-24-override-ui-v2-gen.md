# Override UI + v2 Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить UI для override-флагов и зимнего периода на странице Договор, предпросмотр пунктов, переключить генерацию спецификации на fill_spec_v2 с fallback.

**Architecture:** Task 6 — три новых UI-блока внутри `if is_extracted()` в 2_Договор.py; state.py расширяется defaults'ами для `flags`/`scope_overrides`. Task 7 — в блоке генерации пробуем fill_spec_v2, при ошибке — старый fill_spec_with_items. Task 8 — pytest + docs + git tag v1.0.

**Tech Stack:** Python 3.11, Streamlit, docxtpl, pytest, src.contracts.clauses_renderer.build_contract_clauses, src.contracts.spec_v2_filler.fill_spec_v2

---

## File Map

| Файл | Действие | Зона ответственности |
|------|----------|----------------------|
| `src/contracts/state.py` | Изменить | Добавить `flags` и `scope_overrides` в `_CONTRACT_DEFAULTS` |
| `src/pages/2_Договор.py` | Изменить | Новый UI "Особые условия" + импорт + генерация v2 + fallback |
| `tests/contracts/test_page_dogovor_overrides.py` | Создать | 3 теста: override через flags и scope_overrides |
| `docs/STATUS.md` | Изменить | Пометить Шаг 7 ✅, v1.0 |
| `docs/architecture/contracts_v2.md` | Изменить | Пометить migration как реализованный |

---

## Task 1: Добавить flags и scope_overrides в state.py

**Files:**
- Modify: `src/contracts/state.py:9-24`

### Состояние до:

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

- [ ] **Step 1: Добавить flags и scope_overrides в _CONTRACT_DEFAULTS**

В `src/contracts/state.py` после `"generated": None,` добавить два новых ключа:

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
    "flags": {"winter_concrete": False},
    "scope_overrides": {
        "foundation_scope": None,
        "installation_scope": None,
        "verification_scope": None,
        "orion_poles_scope": None,
    },
}
```

- [ ] **Step 2: Запустить существующие тесты state**

```bash
pytest tests/contracts/test_state.py -v
```

Ожидаем: все тесты PASS. Новые ключи — additive, существующие тесты проверяют только `requisites/specification/manual/uploads/ai_raw`.

- [ ] **Step 3: Commit**

```bash
git add src/contracts/state.py
git commit -m "feat(contracts): state.py — flags + scope_overrides в defaults"
```

---

## Task 2: Написать тесты test_page_dogovor_overrides.py (TDD)

**Files:**
- Create: `tests/contracts/test_page_dogovor_overrides.py`

Тесты проверяют, что `build_contract_clauses(deal)` возвращает нужные clauses при использовании `flags` и `scope_overrides` в deal-объекте. Логика уже реализована в `clauses_context.py` — тесты добавляют покрытие этих сценариев.

- [ ] **Step 1: Написать тест-файл**

```python
"""Тесты: override-флаги и scope_overrides → корректные clauses в предпросмотре."""
from __future__ import annotations


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


def _clause_ids(result: dict) -> set[str]:
    return {c.id for clauses in result.values() for c in clauses}


class TestWinterConcreteFlag:
    def test_winter_concrete_true_adds_surcharge(self):
        """flags.winter_concrete=True → clause winter_concrete_surcharge появляется."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [_item("weights"), _item("foundation", {"scope": "contractor_full"})],
            "scope_overrides": {},
            "flags": {"winter_concrete": True},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "winter_concrete_surcharge" in _clause_ids(result)

    def test_winter_concrete_false_no_surcharge(self):
        """flags.winter_concrete=False → clause winter_concrete_surcharge отсутствует."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [_item("weights"), _item("foundation", {"scope": "contractor_full"})],
            "scope_overrides": {},
            "flags": {"winter_concrete": False},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "winter_concrete_surcharge" not in _clause_ids(result)


class TestFoundationScopeOverride:
    def test_foundation_scope_rama_override(self):
        """scope_overrides.foundation_scope='rama' → clause customer_provides_flat_area_for_rama."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],  # нет items → используется override
            "scope_overrides": {"foundation_scope": "rama"},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "customer_provides_flat_area_for_rama" in _clause_ids(result)

    def test_foundation_scope_none_by_default(self):
        """Без items и overrides → foundation_scope='none', rama-clause отсутствует."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],
            "scope_overrides": {},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "customer_provides_flat_area_for_rama" not in _clause_ids(result)


class TestVerificationScopeOverride:
    def test_verification_scope_customer_override(self):
        """scope_overrides.verification_scope='customer' → clause customer_organizes_verification."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],
            "scope_overrides": {"verification_scope": "customer"},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "customer_organizes_verification" in _clause_ids(result)

    def test_verification_scope_supplier_override(self):
        """scope_overrides.verification_scope='supplier' → clause supplier_prepares_docs."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],
            "scope_overrides": {"verification_scope": "supplier"},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "supplier_prepares_docs" in _clause_ids(result)
```

- [ ] **Step 2: Запустить тесты — убедиться что проходят**

```bash
pytest tests/contracts/test_page_dogovor_overrides.py -v
```

Ожидаем: 5 тестов PASS. Логика clauses_context.py уже обрабатывает override-сценарии.

Если RED — значит что-то сломалось в clauses_context.py. Проверить `_FOUNDATION_SCOPE_MAP` и ветки `elif "foundation_scope" in overrides`.

- [ ] **Step 3: Commit**

```bash
git add tests/contracts/test_page_dogovor_overrides.py
git commit -m "test(contracts): test_page_dogovor_overrides — scope_overrides и winter_concrete"
```

---

## Task 3: UI "Особые условия" в 2_Договор.py

**Files:**
- Modify: `src/pages/2_Договор.py`

Блок "Особые условия" вставляется в `if is_extracted():` после первого `st.divider()` (строка ≈349), перед `spec_items = get_spec_items()`.

- [ ] **Step 1: Добавить импорт build_contract_clauses в блок импортов**

В начале файла (после `from src.contracts.filler import ...`), добавить строку:

```python
from src.contracts.clauses_renderer import build_contract_clauses  # noqa: E402
```

Вставить после строки ~18 (рядом с остальными imports из src.contracts):

```python
from src.contracts.clauses_renderer import build_contract_clauses  # noqa: E402
from src.contracts.extractor import extract_card_data, extract_kp_data_legacy  # noqa: E402
from src.contracts.filler import fill_spec_with_items, fill_template, get_unfilled_placeholders  # noqa: E402
from src.contracts.from_kp import build_specification_from_kp_snapshot, build_specification_items  # noqa: E402
from src.contracts.spec_items import make_custom_item, recalculate_totals  # noqa: E402
```

- [ ] **Step 2: Добавить константы section labels и mapping-словари**

Сразу после блока `WIDE_FIELDS` (после строки ~115), добавить:

```python
_SECTION_LABELS: dict[str, str] = {
    "obligations_supplier": "4. Обязательства Подрядчика",
    "obligations_customer": "5. Обязательства Заказчика",
    "special_conditions": "6. Особые условия",
    "final": "7. Заключительные положения",
}

_FOUND_OPTS = [
    "Авто (из позиций)", "Заказчик строит", "Подрядчик строит",
    "Подрядчик с материалами Заказчика", "Рама", "Без фундамента",
]
_FOUND_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Заказчик строит": "customer_builds",
    "Подрядчик строит": "contractor_full",
    "Подрядчик с материалами Заказчика": "contractor_with_materials",
    "Рама": "rama", "Без фундамента": "none",
}
_FOUND_RMAP = {v: k for k, v in _FOUND_MAP.items()}

_INST_OPTS = ["Авто (из позиций)", "Полный монтаж", "Шеф-монтаж", "Без монтажа"]
_INST_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Полный монтаж": "full",
    "Шеф-монтаж": "shefmontazh", "Без монтажа": "none",
}
_INST_RMAP = {v: k for k, v in _INST_MAP.items()}

_VERIF_OPTS = ["Авто (из позиций)", "Подрядчик", "Заказчик", "Без поверки"]
_VERIF_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Подрядчик": "supplier",
    "Заказчик": "customer", "Без поверки": "none",
}
_VERIF_RMAP = {v: k for k, v in _VERIF_MAP.items()}

_ORION_OPTS = ["Авто (из позиций)", "Заказчик", "Подрядчик"]
_ORION_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Заказчик": "by_customer", "Подрядчик": "by_contractor",
}
_ORION_RMAP = {v: k for k, v in _ORION_MAP.items()}
```

- [ ] **Step 3: Вставить UI "Особые условия" в блок is_extracted()**

Найти место вставки: строка ~349 — первый `st.divider()` внутри блока `if is_extracted():`.

Текущий код (строки ~349-352):
```python
    st.divider()
    spec_items = get_spec_items()
    if spec_items:
```

Заменить на:
```python
    st.divider()

    # ------------------------------------------------------------------
    # Секция 2.5 — Особые условия (override-флаги + clauses preview)
    # ------------------------------------------------------------------
    _cs_flags = st.session_state["contract"]["flags"]
    _cs_ovr = st.session_state["contract"]["scope_overrides"]

    st.subheader("Особые условия")
    st.session_state.setdefault("w_winter_concrete", _cs_flags.get("winter_concrete", False))
    _winter_val = st.checkbox(
        "Зимний период (бетонные работы при +5 °C и ниже)",
        key="w_winter_concrete",
    )
    _cs_flags["winter_concrete"] = _winter_val

    with st.expander("Override-флаги (для нестандартных случаев)", expanded=False):
        st.caption(
            "По умолчанию scope вычисляется из позиций спецификации. "
            "Здесь можно вручную переопределить."
        )
        _cur_f = _cs_ovr.get("foundation_scope")
        st.session_state.setdefault("w_foundation_scope", _FOUND_RMAP.get(_cur_f, "Авто (из позиций)"))
        _sel_f = st.selectbox("Тип фундамента", _FOUND_OPTS, key="w_foundation_scope")
        _cs_ovr["foundation_scope"] = _FOUND_MAP[_sel_f]

        _cur_i = _cs_ovr.get("installation_scope")
        st.session_state.setdefault("w_installation_scope", _INST_RMAP.get(_cur_i, "Авто (из позиций)"))
        _sel_i = st.selectbox("Тип монтажа", _INST_OPTS, key="w_installation_scope")
        _cs_ovr["installation_scope"] = _INST_MAP[_sel_i]

        _cur_v = _cs_ovr.get("verification_scope")
        st.session_state.setdefault("w_verification_scope", _VERIF_RMAP.get(_cur_v, "Авто (из позиций)"))
        _sel_v = st.selectbox("Поверку организует", _VERIF_OPTS, key="w_verification_scope")
        _cs_ovr["verification_scope"] = _VERIF_MAP[_sel_v]

        _items_check = get_spec_items()
        _has_orion = any(item.get("id") == "orion" for item in _items_check)
        if _has_orion:
            _cur_o = _cs_ovr.get("orion_poles_scope")
            st.session_state.setdefault("w_orion_poles_scope", _ORION_RMAP.get(_cur_o, "Авто (из позиций)"))
            _sel_o = st.selectbox("Опоры ПАК ОРИОН", _ORION_OPTS, key="w_orion_poles_scope")
            _cs_ovr["orion_poles_scope"] = _ORION_MAP[_sel_o]

    with st.expander("Предпросмотр пунктов договора", expanded=False):
        _preview_deal = {
            "items": get_spec_items(),
            "scope_overrides": _cs_ovr,
            "flags": _cs_flags,
            "delivery_address": st.session_state["contract"].get("manual", {}).get("object_address", ""),
        }
        _clauses_preview = build_contract_clauses(_preview_deal)
        _total_count = sum(len(v) for v in _clauses_preview.values())
        for _sec_id, _sec_clauses in _clauses_preview.items():
            st.markdown(f"**{_SECTION_LABELS.get(_sec_id, _sec_id)}**")
            for _clause in _sec_clauses:
                st.text(f"  {_clause.auto_number}. {_clause.text[:60]}...")
        st.caption(f"Всего пунктов: {_total_count}")

    st.divider()
    spec_items = get_spec_items()
    if spec_items:
```

- [ ] **Step 4: Запустить полный pytest**

```bash
pytest tests/ -v
```

Ожидаем: все существующие тесты + 5 новых PASS. Если есть RED — исправить перед коммитом.

- [ ] **Step 5: Commit**

```bash
git add src/pages/2_Договор.py
git commit -m "feat(contracts): UI override-флаги + предпросмотр пунктов в странице Договор"
```

---

## Task 4: Переключить генерацию спецификации на v2 + fallback

**Files:**
- Modify: `src/pages/2_Договор.py`

- [ ] **Step 1: Добавить импорт fill_spec_v2 в блок импортов**

В начале файла добавить после других импортов из `src.contracts`:

```python
from src.contracts.spec_v2_filler import fill_spec_v2  # noqa: E402
```

- [ ] **Step 2: Добавить константу SPEC_V2_TEMPLATE**

После строки `SPEC_TEMPLATE = Path("templates/contracts/spec_foundation_install.docx")` добавить:

```python
SPEC_V2_TEMPLATE = Path("templates/contracts/spec_v2.docx")
```

Итоговый блок констант:
```python
CONTRACT_TEMPLATE = Path("templates/contracts/contract.docx")
SPEC_TEMPLATE = Path("templates/contracts/spec_foundation_install.docx")
SPEC_V2_TEMPLATE = Path("templates/contracts/spec_v2.docx")
OUTPUT_DIR = Path("output/contracts")
```

- [ ] **Step 3: Заменить вызов fill_spec_with_items на v2 + fallback**

Найти в блоке генерации (строки ~478-487):

```python
        items_for_docx = get_spec_items()
        if items_for_docx:
            if edited_df is not None and hasattr(edited_df, "to_dict"):
                items_for_docx = _rows_to_items(edited_df, items_for_docx)
                for _i in items_for_docx:
                    _i["total"] = _i["quantity"] * _i["price_per_unit"]
            fill_spec_with_items(str(SPEC_TEMPLATE), data, items_for_docx, str(spec_path))
        else:
            fill_template(str(SPEC_TEMPLATE), data, str(spec_path))
```

Заменить на:

```python
        items_for_docx = get_spec_items()
        if items_for_docx:
            if edited_df is not None and hasattr(edited_df, "to_dict"):
                items_for_docx = _rows_to_items(edited_df, items_for_docx)
                for _i in items_for_docx:
                    _i["total"] = _i["quantity"] * _i["price_per_unit"]
            _gen_cs = st.session_state["contract"]
            _gen_deal = {
                "items": items_for_docx,
                "scope_overrides": _gen_cs.get("scope_overrides", {}),
                "flags": _gen_cs.get("flags", {}),
                "delivery_address": _gen_cs.get("manual", {}).get("object_address", ""),
            }
            try:
                fill_spec_v2(str(SPEC_V2_TEMPLATE), data, items_for_docx, _gen_deal, str(spec_path))
            except Exception as exc_v2:
                st.warning(
                    f"Не удалось сгенерировать v2-спецификацию: {exc_v2}. "
                    "Использую старый шаблон."
                )
                fill_spec_with_items(str(SPEC_TEMPLATE), data, items_for_docx, str(spec_path))
        else:
            fill_template(str(SPEC_TEMPLATE), data, str(spec_path))
```

- [ ] **Step 4: Запустить полный pytest**

```bash
pytest tests/ -v
```

Ожидаем: все тесты PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pages/2_Договор.py
git commit -m "feat(contracts): генерация спецификации переключена на v2 + fallback на старый шаблон"
```

---

## Task 5: Финальная верификация + docs + тег v1.0

**Files:**
- Modify: `docs/STATUS.md`
- Modify: `docs/architecture/contracts_v2.md`

- [ ] **Step 1: Полный pytest с отчётом**

```bash
pytest tests/ -v
```

Ожидаем: все тесты GREEN. Количество тестов >= 390 (было 385/390 перед началом).

Если есть FAIL — исправить до продолжения. Не коммитить с красными тестами.

- [ ] **Step 2: Обновить docs/STATUS.md**

В разделе "Где мы сейчас" изменить на:

```markdown
## Где мы сейчас

**v1.0 — clauses library + override UI. Задачи 6, 7, 8 выполнены.**

Последний тег: **v1.0** (clauses library, override UI, spec_v2 генерация).
```

В разделе "Что закрыто за последние сессии" добавить:

```markdown
**Шаг 7 архитектуры v2 — задачи 6, 7, 8 (закрыто, тег v1.0):**
- `src/contracts/state.py` — flags + scope_overrides в `_CONTRACT_DEFAULTS`
- UI "Особые условия": checkbox зимний период, expander override-флаги (4 selectbox), expander предпросмотр пунктов
- `src/pages/2_Договор.py` — генерация спецификации переключена на fill_spec_v2 + fallback
- `tests/contracts/test_page_dogovor_overrides.py` — 5 тестов (winter_concrete, foundation_scope, verification_scope overrides)
```

Удалить раздел "Открытая работа: план Code сохранён" (уже выполнено).

Заменить в разделе "Следующие задачи" содержимое на ссылку на backlog.

- [ ] **Step 3: Обновить docs/architecture/contracts_v2.md**

Найти раздел плана миграции или статуса — добавить пометку "✅ Реализовано (v1.0, 2026-05-24)".

- [ ] **Step 4: Commit docs**

```bash
git add docs/STATUS.md docs/architecture/contracts_v2.md
git commit -m "docs(status): Шаг 7 ✅ — v1.0 готов, обновлён STATUS.md и contracts_v2.md"
```

- [ ] **Step 5: Финальный release commit + тег**

```bash
git add -A
git commit -m "chore(release): v1.0 — clauses library + override UI"
git tag v1.0
```

> **Важно:** `git push` и `git push --tags` — только по явному запросу пользователя.

---

## Чек-лист проверки (Task 8 smoke)

После завершения всех задач:

```
[ ] pytest tests/ -v — все GREEN, 0 failed
[ ] Streamlit: страница "Договор" открывается без ошибок
[ ] Streamlit: загрузить КП из базы → is_extracted() = True
[ ] Streamlit: чекбокс "Зимний период" переключается, сохраняется в session_state
[ ] Streamlit: expander "Override-флаги" открывается, selectbox-ы работают
[ ] Streamlit: expander "Предпросмотр пунктов" обновляется реактивно при смене override
[ ] Streamlit: кнопка "Сгенерировать" → скачать спецификацию → открыть DOCX в Word
```

---

## Self-Review

**Spec coverage:**
- ✅ `st.subheader("Особые условия")` — Task 3
- ✅ `st.checkbox "Зимний период"` → `flags.winter_concrete` — Task 3
- ✅ expander override-флаги с 4 selectbox (foundation, installation, verification, orion) — Task 3
- ✅ orion_poles_scope показывается только если `has_orion` — Task 3
- ✅ expander предпросмотр clauses с нумерацией — Task 3
- ✅ Тест winter_concrete=True → winter_concrete_surcharge — Task 2
- ✅ Тест foundation_scope="rama" → customer_provides_flat_area_for_rama — Task 2
- ✅ Тест verification_scope="customer" → customer_organizes_verification — Task 2
- ✅ Генерация v2 + fallback в кнопке — Task 4
- ✅ Старый spec_foundation_install.docx НЕ удаляется — Task 4 (используется как fallback)
- ✅ payment_renderer / term_days / snapshot_builder / supabase_client — НЕ тронуты
- ✅ docs/STATUS.md — Task 5
- ✅ docs/architecture/contracts_v2.md — Task 5
- ✅ git tag v1.0 — Task 5

**Placeholder scan:** Все шаги содержат конкретный код.

**Type consistency:**
- `_FOUND_MAP` / `_INST_MAP` / `_VERIF_MAP` / `_ORION_MAP` — `dict[str, str | None]` ✓
- `_cs_flags["winter_concrete"]` — `bool` ✓
- `_cs_ovr["foundation_scope"]` — `str | None` ✓
- `_gen_deal` в Task 4 совпадает со структурой `deal` ожидаемой `fill_spec_v2` и `build_contract_clauses` ✓
- `fill_spec_v2(template_path, data, items, deal, output_path)` — подпись совпадает ✓
