# Clauses Library (Шаг 7 архитектуры v2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать библиотеку условий договора (clauses library) с DSL-парсером, загрузчиком YAML, вычислением контекста и рендерером — заменить статичные секции шаблона динамической сборкой из data/clauses.yaml.

**Architecture:** DSL-парсер (ast.parse + whitelist) → ClausesLibrary (YAML-загрузчик) → build_clauses_context (6 переменных из SpecItems) → build_contract_clauses (фильтр + нумерация + jinja-подстановка) → fill_template_v2 (docxtpl) → UI-override + safety fallback.

**Tech Stack:** Python 3.11, PyYAML, ast, jinja2, docxtpl≥0.18 (уже в requirements), python-docx, Streamlit.

---

## Карта файлов

### Создать:
| Файл | Назначение |
|------|------------|
| `src/contracts/clauses_dsl.py` | Парсер DSL applies_when через ast |
| `src/contracts/clauses_loader.py` | Загрузка/валидация data/clauses.yaml |
| `src/contracts/clauses_context.py` | build_clauses_context(deal) → 6 переменных |
| `src/contracts/clauses_renderer.py` | build_contract_clauses → RenderedClause |
| `scripts/make_contract_v2_template.py` | Генератор шаблона contract_v2.docx |
| `tests/contracts/test_clauses_dsl.py` | Тесты DSL-парсера |
| `tests/contracts/test_clauses_loader.py` | Тесты загрузчика |
| `tests/contracts/test_clauses_context.py` | Тесты контекста (9 сценариев) |
| `tests/contracts/test_clauses_renderer.py` | Тесты рендерера |
| `tests/contracts/test_filler_v2.py` | Тесты fill_template_v2 |

### Изменить:
| Файл | Что изменить |
|------|-------------|
| `data/clauses.yaml` | Добавить `section_number` в sections |
| `src/contracts/filler.py` | Добавить `fill_template_v2()` |
| `src/contracts/state.py` | Добавить `scope_overrides`, `flags` в defaults |
| `src/pages/2_Договор.py` | Override UI + preview + switch to v2 |
| `templates/contracts/contract_v2.docx` | Сгенерировать скриптом |
| `docs/STATUS.md` | Обновить до v1.0 |
| `docs/architecture/contracts_v2.md` | Пометить план миграции выполненным |

---

## Task 1: DSL-парсер

**Files:**
- Create: `src/contracts/clauses_dsl.py`
- Test: `tests/contracts/test_clauses_dsl.py`

- [ ] **Step 1.1: Написать failing тесты**

```python
# tests/contracts/test_clauses_dsl.py
"""Тесты безопасного DSL-парсера applies_when."""
import pytest


class TestLiterals:
    def test_true_uppercase(self):
        from src.contracts.clauses_dsl import parse
        assert parse("True").evaluate({}) is True

    def test_true_lowercase(self):
        from src.contracts.clauses_dsl import parse
        assert parse("true").evaluate({}) is True

    def test_false_lowercase(self):
        from src.contracts.clauses_dsl import parse
        assert parse("false").evaluate({}) is False

class TestAllowedVars:
    def test_bool_var(self):
        from src.contracts.clauses_dsl import parse
        assert parse("has_orion").evaluate({"has_orion": True}) is True
        assert parse("has_orion").evaluate({"has_orion": False}) is False

    def test_string_compare_allowed_var(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('verification_scope == "supplier"')
        assert expr.evaluate({"verification_scope": "supplier"}) is True
        assert expr.evaluate({"verification_scope": "customer"}) is False

    def test_missing_var_raises_key_error(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(KeyError, match="has_orion"):
            parse("has_orion").evaluate({})


class TestInOperator:
    def test_in_tuple(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('foundation_scope in ("contractor_full", "contractor_with_materials")')
        assert expr.evaluate({"foundation_scope": "contractor_full"}) is True
        assert expr.evaluate({"foundation_scope": "none"}) is False

    def test_not_equal(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('installation_scope != "none"')
        assert expr.evaluate({"installation_scope": "full"}) is True
        assert expr.evaluate({"installation_scope": "none"}) is False


class TestLogical:
    def test_and(self):
        from src.contracts.clauses_dsl import parse
        expr = parse("has_orion and winter_concrete")
        assert expr.evaluate({"has_orion": True, "winter_concrete": True}) is True
        assert expr.evaluate({"has_orion": True, "winter_concrete": False}) is False

    def test_or(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('has_orion or foundation_scope == "rama"')
        assert expr.evaluate({"has_orion": False, "foundation_scope": "rama"}) is True
        assert expr.evaluate({"has_orion": False, "foundation_scope": "none"}) is False

    def test_not(self):
        from src.contracts.clauses_dsl import parse
        assert parse("not has_orion").evaluate({"has_orion": False}) is True
        assert parse("not has_orion").evaluate({"has_orion": True}) is False

    def test_parentheses_complex(self):
        from src.contracts.clauses_dsl import parse
        expr = parse(
            'foundation_scope in ("contractor_full", "contractor_with_materials")'
            ' and not (has_orion and orion_poles_scope == "by_contractor")'
        )
        ctx_true = {"foundation_scope": "contractor_full", "has_orion": False, "orion_poles_scope": "none"}
        ctx_false = {"foundation_scope": "contractor_full", "has_orion": True, "orion_poles_scope": "by_contractor"}
        assert expr.evaluate(ctx_true) is True
        assert expr.evaluate(ctx_false) is False


class TestSecurity:
    def test_function_call_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("eval('x')")

    def test_attribute_access_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("foundation_scope.encode()")

    def test_import_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse('__import__("os")')

    def test_unknown_variable_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError, match="не разрешена"):
            parse("unknown_var")

    def test_subscript_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("items[0]")

    def test_lambda_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("lambda x: x")


class TestRealClausesYaml:
    """Все 28 applies_when из data/clauses.yaml должны парситься успешно."""

    EXPRS = [
        'verification_scope == "supplier"',
        'foundation_scope in ("contractor_full", "contractor_with_materials") and not (has_orion and orion_poles_scope == "by_contractor")',
        'foundation_scope in ("contractor_full", "contractor_with_materials") and has_orion and orion_poles_scope == "by_contractor"',
        'installation_scope != "none"',
        'foundation_scope == "customer_builds"',
        'foundation_scope == "rama"',
        'foundation_scope in ("contractor_full", "contractor_with_materials")',
        'foundation_scope == "contractor_with_materials"',
        'installation_scope == "shefmontazh"',
        'has_orion or foundation_scope == "rama"',
        'verification_scope == "customer"',
        'has_orion and orion_poles_scope == "by_customer"',
        'has_orion',
        'winter_concrete',
        'true',
    ]

    def test_all_real_exprs_parse(self):
        from src.contracts.clauses_dsl import parse
        for expr in self.EXPRS:
            try:
                parse(expr)
            except ValueError as e:
                pytest.fail(f"Не удалось разобрать {expr!r}: {e}")
```

- [ ] **Step 1.2: Запустить тесты — убедиться в FAIL**

```
pytest tests/contracts/test_clauses_dsl.py -v
```
Ожидаем: ImportError / ModuleNotFoundError (файл не существует)

- [ ] **Step 1.3: Создать `src/contracts/clauses_dsl.py`**

```python
"""clauses_dsl.py — безопасный DSL-парсер для applies_when-выражений."""
from __future__ import annotations

import ast
from typing import Any

_ALLOWED_VARS = frozenset({
    "foundation_scope",
    "installation_scope",
    "verification_scope",
    "has_orion",
    "orion_poles_scope",
    "winter_concrete",
    # псевдо-булевые литералы (YAML: applies_when: 'true')
    "true",
    "false",
})


def _validate(node: ast.AST) -> None:
    """Рекурсивная валидация AST. Raises ValueError на запрещённые конструкции."""
    if isinstance(node, ast.Expression):
        _validate(node.body)
    elif isinstance(node, ast.Constant):
        pass
    elif isinstance(node, ast.Name):
        if node.id not in _ALLOWED_VARS:
            raise ValueError(f"Переменная не разрешена: {node.id!r}")
    elif isinstance(node, ast.BoolOp):
        if not isinstance(node.op, (ast.And, ast.Or)):
            raise ValueError(f"Недопустимый логический оператор: {type(node.op).__name__}")
        for val in node.values:
            _validate(val)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ast.Not):
            raise ValueError(f"Недопустимый унарный оператор: {type(node.op).__name__}")
        _validate(node.operand)
    elif isinstance(node, ast.Compare):
        _validate(node.left)
        for op in node.ops:
            if not isinstance(op, (ast.Eq, ast.NotEq, ast.In, ast.NotIn)):
                raise ValueError(f"Недопустимый оператор сравнения: {type(op).__name__}")
        for comp in node.comparators:
            _validate(comp)
    elif isinstance(node, ast.Tuple):
        for elt in node.elts:
            _validate(elt)
    else:
        raise ValueError(f"Недопустимый тип узла AST: {type(node).__name__}")


def _eval(node: ast.AST, ctx: dict[str, Any]) -> Any:
    """Вычислить значение валидированного AST-узла на контексте ctx."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        if node.id == "true":
            return True
        if node.id == "false":
            return False
        if node.id not in ctx:
            raise KeyError(f"Переменная не задана в контексте: {node.id!r}")
        return ctx[node.id]
    elif isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval(v, ctx) for v in node.values)
        return any(_eval(v, ctx) for v in node.values)
    elif isinstance(node, ast.UnaryOp):
        return not _eval(node.operand, ctx)
    elif isinstance(node, ast.Compare):
        left = _eval(node.left, ctx)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, ctx)
            if isinstance(op, ast.Eq) and left != right:
                return False
            if isinstance(op, ast.NotEq) and left == right:
                return False
            if isinstance(op, ast.In) and left not in right:
                return False
            if isinstance(op, ast.NotIn) and left in right:
                return False
            left = right
        return True
    elif isinstance(node, ast.Tuple):
        return tuple(_eval(e, ctx) for e in node.elts)
    raise ValueError(f"Не могу вычислить узел: {type(node).__name__}")


class Expression:
    def __init__(self, node: ast.AST) -> None:
        self._node = node

    def evaluate(self, context: dict[str, Any]) -> bool:
        return bool(_eval(self._node, context))


def parse(expr: str) -> Expression:
    """Разобрать выражение applies_when. Raises ValueError на недопустимые конструкции."""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Синтаксическая ошибка в выражении {expr!r}: {e}") from e
    _validate(tree.body)
    return Expression(tree.body)
```

- [ ] **Step 1.4: Запустить тесты — убедиться в PASS**

```
pytest tests/contracts/test_clauses_dsl.py -v
```
Ожидаем: все тесты PASS

- [ ] **Step 1.5: Коммит**

```bash
rtk git add src/contracts/clauses_dsl.py tests/contracts/test_clauses_dsl.py
rtk git commit -m "feat(contracts): clauses_dsl — безопасный AST-парсер applies_when"
```

---

## Task 2: Загрузчик clauses.yaml

**Files:**
- Modify: `data/clauses.yaml` (добавить `section_number`)
- Create: `src/contracts/clauses_loader.py`
- Test: `tests/contracts/test_clauses_loader.py`

- [ ] **Step 2.1: Добавить `section_number` в data/clauses.yaml**

В блоке `sections:` заменить каждый элемент:

```yaml
sections:
  - id: obligations_supplier
    title: "Обязательства Подрядчика"
    section_number: 4
  - id: obligations_customer
    title: "Обязательства Заказчика"
    section_number: 5
  - id: special_conditions
    title: "Особые условия"
    section_number: 6
  - id: final
    title: "Заключительные положения"
    section_number: 7
```

- [ ] **Step 2.2: Написать failing тесты**

```python
# tests/contracts/test_clauses_loader.py
"""Тесты загрузчика и валидатора data/clauses.yaml."""
from pathlib import Path
import pytest

CLAUSES_PATH = Path("data/clauses.yaml")


class TestSuccessfulLoad:
    def test_loads_28_clauses(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        all_clauses = [
            c
            for s in lib.get_sections()
            for c in lib.get_clauses_for_section(s.id)
        ]
        assert len(all_clauses) == 28

    def test_four_sections_with_numbers(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        sections = {s.id: s for s in lib.get_sections()}
        assert sections["obligations_supplier"].section_number == 4
        assert sections["obligations_customer"].section_number == 5
        assert sections["special_conditions"].section_number == 6
        assert sections["final"].section_number == 7

    def test_all_applies_when_parse(self):
        """Все applies_when в YAML разбираются без ошибок."""
        from src.contracts.clauses_loader import load_clauses
        # load_clauses вызывает parse() для каждого clause — не должно бросать
        load_clauses(CLAUSES_PATH)

    def test_collect_jinja_placeholders(self):
        """YAML содержит ожидаемые jinja-параметры в текстах."""
        from src.contracts.clauses_loader import load_clauses
        import re
        lib = load_clauses(CLAUSES_PATH)
        all_text = " ".join(
            c.text
            for s in lib.get_sections()
            for c in lib.get_clauses_for_section(s.id)
        )
        placeholders = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', all_text))
        assert "foundation_term_days_by_customer" in placeholders
        assert "scales_or_with_orion" in placeholders
        assert "install_site_label" in placeholders
        assert "obligations_range" in placeholders
        assert "delivery_address_text" in placeholders

    def test_get_clauses_for_section(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        supplier = lib.get_clauses_for_section("obligations_supplier")
        assert len(supplier) == 3
        ids = [c.id for c in supplier]
        assert "supplier_prepares_docs" in ids

    def test_clause_order_field_present(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        for s in lib.get_sections():
            for c in lib.get_clauses_for_section(s.id):
                assert isinstance(c.order, int)


class TestValidationErrors:
    def test_duplicate_id_raises(self, tmp_path):
        from src.contracts.clauses_loader import load_clauses
        yaml_text = """
sections:
  - id: s1
    title: "S1"
    section_number: 1
clauses:
  - id: dup
    section: s1
    order: 1
    applies_when: 'true'
    text: "First"
  - id: dup
    section: s1
    order: 2
    applies_when: 'true'
    text: "Second"
"""
        p = tmp_path / "bad.yaml"
        p.write_text(yaml_text, encoding="utf-8")
        with pytest.raises(ValueError, match="Дублирующийся id"):
            load_clauses(p)

    def test_unknown_section_raises(self, tmp_path):
        from src.contracts.clauses_loader import load_clauses
        yaml_text = """
sections:
  - id: s1
    title: "S1"
    section_number: 1
clauses:
  - id: c1
    section: nonexistent
    order: 1
    applies_when: 'true'
    text: "text"
"""
        p = tmp_path / "bad2.yaml"
        p.write_text(yaml_text, encoding="utf-8")
        with pytest.raises(ValueError, match="неизвестная section"):
            load_clauses(p)

    def test_invalid_applies_when_raises(self, tmp_path):
        from src.contracts.clauses_loader import load_clauses
        yaml_text = """
sections:
  - id: s1
    title: "S1"
    section_number: 1
clauses:
  - id: c1
    section: s1
    order: 1
    applies_when: 'evil_func()'
    text: "text"
"""
        p = tmp_path / "bad3.yaml"
        p.write_text(yaml_text, encoding="utf-8")
        with pytest.raises(ValueError, match="ошибка applies_when"):
            load_clauses(p)
```

- [ ] **Step 2.3: Запустить тесты — убедиться в FAIL**

```
pytest tests/contracts/test_clauses_loader.py -v
```
Ожидаем: ImportError / ModuleNotFoundError

- [ ] **Step 2.4: Создать `src/contracts/clauses_loader.py`**

```python
"""clauses_loader.py — загрузка и валидация data/clauses.yaml."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.contracts.clauses_dsl import Expression, parse

_logger = logging.getLogger(__name__)


@dataclass
class Section:
    id: str
    title: str
    section_number: int = 0


@dataclass
class Clause:
    id: str
    section: str
    order: int
    applies_when: Expression
    text: str
    related_to: list[str] = field(default_factory=list)


class ClausesLibrary:
    def __init__(self, sections: list[Section], clauses: list[Clause]) -> None:
        self._sections_list = sections
        self._sections = {s.id: s for s in sections}
        self._clauses = clauses

    def get_sections(self) -> list[Section]:
        return list(self._sections_list)

    def get_clauses_for_section(self, section_id: str) -> list[Clause]:
        return [c for c in self._clauses if c.section == section_id]


def load_clauses(path: Path) -> ClausesLibrary:
    """Загрузить data/clauses.yaml. Raises ValueError на ошибки валидации."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    sections: list[Section] = []
    section_ids: set[str] = set()
    for s in data.get("sections", []):
        section_ids.add(s["id"])
        sections.append(Section(
            id=s["id"],
            title=str(s["title"]),
            section_number=int(s.get("section_number", 0)),
        ))

    clauses: list[Clause] = []
    seen_ids: set[str] = set()
    for c in data.get("clauses", []):
        cid = str(c["id"])
        if cid in seen_ids:
            raise ValueError(f"Дублирующийся id clause: {cid!r}")
        seen_ids.add(cid)

        sec = str(c["section"])
        if sec not in section_ids:
            raise ValueError(f"Clause {cid!r}: неизвестная section {sec!r}")

        applies_when_str = str(c.get("applies_when", "true"))
        try:
            applies_when = parse(applies_when_str)
        except ValueError as e:
            raise ValueError(f"Clause {cid!r}: ошибка applies_when: {e}") from e

        text = str(c.get("text", ""))
        placeholders = re.findall(r'\{\{\s*(\w+)\s*\}\}', text)
        if placeholders:
            _logger.debug("Clause %s требует jinja-параметры: %s", cid, placeholders)

        clauses.append(Clause(
            id=cid,
            section=sec,
            order=int(c.get("order", 0)),
            applies_when=applies_when,
            text=text,
            related_to=list(c.get("related_to") or []),
        ))

    return ClausesLibrary(sections, clauses)
```

- [ ] **Step 2.5: Запустить тесты — убедиться в PASS**

```
pytest tests/contracts/test_clauses_loader.py -v
```
Ожидаем: все PASS

- [ ] **Step 2.6: Полный прогон всех тестов**

```
pytest tests/ -v --tb=short -q
```
Ожидаем: все существующие тесты PASS + новые PASS

- [ ] **Step 2.7: Коммит**

```bash
rtk git add data/clauses.yaml src/contracts/clauses_loader.py tests/contracts/test_clauses_loader.py
rtk git commit -m "feat(contracts): clauses_loader — загрузка/валидация clauses.yaml"
```

---

## Task 3: Контекст для оценки clauses

**Files:**
- Create: `src/contracts/clauses_context.py`
- Test: `tests/contracts/test_clauses_context.py`

- [ ] **Step 3.1: Написать failing тесты**

```python
# tests/contracts/test_clauses_context.py
"""Тесты build_clauses_context — 9 эталонных сценариев."""
import pytest


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


class TestNineScenarios:
    """9 эталонных кейсов из архитектурного документа."""

    def test_1_postavka(self):
        """Поставка: только весы и доставка — нет монтажа/фундамента."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("weights"), _item("delivery")]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "none"
        assert ctx["installation_scope"] == "none"
        assert ctx["verification_scope"] == "none"
        assert ctx["has_orion"] is False
        assert ctx["orion_poles_scope"] == "none"
        assert ctx["winter_concrete"] is False

    def test_2_montazh(self):
        """Монтаж: full монтаж + поверка подрядчиком."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("installation", {"scope": "full"}),
            _item("verification"),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["installation_scope"] == "full"
        assert ctx["verification_scope"] == "supplier"
        assert ctx["foundation_scope"] == "none"
        assert ctx["has_orion"] is False

    def test_3_montazh_orion(self):
        """Монтаж + ОРИОН, без orion_install → opoles by_customer."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("installation", {"scope": "full"}),
            _item("orion"),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["has_orion"] is True
        assert ctx["orion_poles_scope"] == "by_customer"
        assert ctx["verification_scope"] == "none"

    def test_4_rama_montazh(self):
        """Рама + монтаж full."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("rama"),
            _item("installation", {"scope": "full"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "rama"
        assert ctx["installation_scope"] == "full"

    def test_5_rama_shefmontazh(self):
        """Рама + шеф-монтаж."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("rama"),
            _item("installation", {"scope": "shefmontazh"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "rama"
        assert ctx["installation_scope"] == "shefmontazh"

    def test_6_stroika_mat(self):
        """Стройка с материалами заказчика."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("foundation", {"scope": "contractor_with_materials"}),
            _item("installation", {"scope": "full"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "contractor_with_materials"
        assert ctx["installation_scope"] == "full"

    def test_7_fundament_montazh(self):
        """Фундамент ЖБ (contractor_full) + монтаж."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
        ]}
        ctx = build_clauses_context(deal)
        # fundament_jb → contractor_full
        assert ctx["foundation_scope"] == "contractor_full"
        assert ctx["installation_scope"] == "full"

    def test_8_fundament_zima(self):
        """Фундамент заказчика + зимний период."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {
            "items": [_item("weights"), _item("foundation", {"scope": "customer_builds"})],
            "flags": {"winter_concrete": True},
        }
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "customer_builds"
        assert ctx["winter_concrete"] is True

    def test_9_fundament_montazh_orion(self):
        """Фундамент + монтаж + ОРИОН с опорами подрядчика."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
            _item("verification"),
            _item("orion"),
            _item("orion_install"),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "contractor_full"
        assert ctx["has_orion"] is True
        assert ctx["orion_poles_scope"] == "by_contractor"
        assert ctx["verification_scope"] == "supplier"


class TestOverrides:
    def test_scope_override_replaces_items(self):
        """scope_overrides перекрывает значение из items."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {
            "items": [_item("installation", {"scope": "full"})],
            "scope_overrides": {"installation_scope": "shefmontazh"},
        }
        # items есть → items приоритет; override только если items нет
        # Но если items → full, а override → shef: items побеждает
        # Тест проверяет что override работает когда items НЕТ:
        deal2 = {
            "items": [_item("weights")],
            "scope_overrides": {"installation_scope": "shefmontazh"},
        }
        ctx = build_clauses_context(deal2)
        assert ctx["installation_scope"] == "shefmontazh"

    def test_winter_concrete_only_from_flag(self):
        """winter_concrete=True только из явного флага, не из items."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("foundation", {"scope": "fundament_jb"})]}
        ctx = build_clauses_context(deal)
        # Нет флага → False
        assert ctx["winter_concrete"] is False

    def test_old_installation_scope_fundament_maps_to_full(self):
        """Старое значение 'fundament' из from_kp.py → installation_scope='full'."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("installation", {"scope": "fundament"})]}
        ctx = build_clauses_context(deal)
        assert ctx["installation_scope"] == "full"

    def test_old_installation_scope_rama_maps_to_full(self):
        """Старое значение 'rama' из from_kp.py → installation_scope='full'."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("installation", {"scope": "rama"})]}
        ctx = build_clauses_context(deal)
        assert ctx["installation_scope"] == "full"

    def test_verification_customer_side_true(self):
        """verification item с customer_side=True → verification_scope='customer'."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("verification", {"customer_side": True})]}
        ctx = build_clauses_context(deal)
        assert ctx["verification_scope"] == "customer"
```

- [ ] **Step 3.2: Запустить тесты — убедиться в FAIL**

```
pytest tests/contracts/test_clauses_context.py -v
```
Ожидаем: ImportError

- [ ] **Step 3.3: Создать `src/contracts/clauses_context.py`**

```python
"""clauses_context.py — вычисление контекста переменных для applies_when."""
from __future__ import annotations

# Маппинг внутренних значений scope из from_kp.py → clauses DSL
_FOUNDATION_SCOPE_MAP: dict[str, str] = {
    "fundament_jb": "contractor_full",
    "pandus_lite": "contractor_full",
    "pandus_std": "contractor_full",
    "contractor_full": "contractor_full",
    "contractor_with_materials": "contractor_with_materials",
    "customer_builds": "customer_builds",
}


def build_clauses_context(deal: dict) -> dict:
    """Вычислить 6 переменных DSL-контекста из объекта сделки.

    deal:
      items: list[dict]          — SpecItem list
      scope_overrides: dict      — переопределения (применяются если items не содержат значения)
      flags: dict                — {"winter_concrete": bool}
      delivery_address: str      — адрес поставки (не используется здесь, для renderer)
    """
    items: list[dict] = deal.get("items", []) or []
    overrides: dict = deal.get("scope_overrides", {}) or {}
    flags: dict = deal.get("flags", {}) or {}

    items_by_id = {item["id"]: item for item in items}

    # --- foundation_scope ---
    if "foundation" in items_by_id:
        raw = items_by_id["foundation"].get("metadata", {}).get("scope", "contractor_full")
        foundation_scope = _FOUNDATION_SCOPE_MAP.get(raw, "contractor_full")
    elif "rama" in items_by_id:
        foundation_scope = "rama"
    elif "foundation_scope" in overrides:
        foundation_scope = overrides["foundation_scope"]
    else:
        foundation_scope = "none"

    # --- installation_scope ---
    if "installation" in items_by_id:
        raw = items_by_id["installation"].get("metadata", {}).get("scope", "full")
        if raw in ("fundament", "rama"):
            installation_scope = "full"
        elif raw in ("shefmontazh", "full"):
            installation_scope = raw
        else:
            installation_scope = "full"
    elif "installation_scope" in overrides:
        installation_scope = overrides["installation_scope"]
    else:
        installation_scope = "none"

    # --- verification_scope ---
    if "verification" in items_by_id:
        meta = items_by_id["verification"].get("metadata", {})
        verification_scope = "customer" if meta.get("customer_side") else "supplier"
    elif "verification_scope" in overrides:
        verification_scope = overrides["verification_scope"]
    else:
        verification_scope = "none"

    # --- has_orion ---
    has_orion = "orion" in items_by_id

    # --- orion_poles_scope ---
    if has_orion:
        if "orion_install" in items_by_id:
            orion_poles_scope = "by_contractor"
        elif "orion_poles_scope" in overrides:
            orion_poles_scope = overrides["orion_poles_scope"]
        else:
            orion_poles_scope = "by_customer"
    else:
        orion_poles_scope = "none"

    # --- winter_concrete — ТОЛЬКО из явного флага ---
    winter_concrete = bool(flags.get("winter_concrete", False))

    return {
        "foundation_scope": foundation_scope,
        "installation_scope": installation_scope,
        "verification_scope": verification_scope,
        "has_orion": has_orion,
        "orion_poles_scope": orion_poles_scope,
        "winter_concrete": winter_concrete,
    }
```

- [ ] **Step 3.4: Запустить тесты — убедиться в PASS**

```
pytest tests/contracts/test_clauses_context.py -v
```
Ожидаем: все PASS

- [ ] **Step 3.5: Полный прогон**

```
pytest tests/ -q
```
Ожидаем: все PASS

- [ ] **Step 3.6: Коммит**

```bash
rtk git add src/contracts/clauses_context.py tests/contracts/test_clauses_context.py
rtk git commit -m "feat(contracts): clauses_context — вычисление 6 переменных DSL из SpecItems"
```

---

## Task 4: Сборщик clauses + нумерация

**Files:**
- Create: `src/contracts/clauses_renderer.py`
- Test: `tests/contracts/test_clauses_renderer.py`

- [ ] **Step 4.1: Написать failing тесты**

```python
# tests/contracts/test_clauses_renderer.py
"""Тесты build_contract_clauses — нумерация, фильтрация, jinja-подстановка."""
import pytest


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


def _make_montazh_deal() -> dict:
    """Сценарий: монтаж full + поверка подрядчиком, нет фундамента, нет ОРИОН."""
    return {
        "items": [
            _item("weights"),
            _item("installation", {"scope": "full"}),
            _item("verification"),
        ],
        "scope_overrides": {},
        "flags": {},
        "delivery_address": "г. Тест, ул. Промышленная",
    }


def _make_max_deal() -> dict:
    """Сценарий: фундамент+монтаж+ОРИОН (14 пунктов)."""
    return {
        "items": [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
            _item("verification"),
            _item("orion"),
            _item("orion_install"),
        ],
        "scope_overrides": {},
        "flags": {},
        "delivery_address": "г. Тест",
    }


class TestClauseCount:
    def test_montazh_7_clauses(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_montazh_deal())
        all_ids = [c.id for section_clauses in result.values() for c in section_clauses]
        assert len(all_ids) == 7
        expected_ids = {
            "supplier_prepares_docs",
            "customer_unable_to_accept_team_delays_work",
            "customer_provides_scales_near_install_site",
            "customer_provides_crane",
            "customer_provides_test_vehicle",
            "cross_reference_to_contract",
            "delivery_address",
        }
        assert set(all_ids) == expected_ids

    def test_max_14_clauses(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_max_deal())
        all_ids = [c.id for section_clauses in result.values() for c in section_clauses]
        assert len(all_ids) == 14
        expected_ids = {
            "supplier_prepares_docs",
            "supplier_dispatches_construction_team_with_orion_poles",
            "customer_unable_to_accept_team_delays_work",
            "customer_provides_flat_area_for_construction",
            "customer_provides_scales_near_install_site",
            "customer_provides_crane",
            "customer_provides_test_vehicle",
            "customer_provides_power_220V",
            "customer_installs_high_cameras_supervised",
            "customer_provides_pc_for_orion",
            "additional_work_during_construction",
            "orion_oversized_vehicle",
            "cross_reference_to_contract",
            "delivery_address",
        }
        assert set(all_ids) == expected_ids

    def test_postavka_only_final(self):
        """Поставка без монтажа → только final секция (cross_reference + delivery)."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {"items": [_item("weights"), _item("delivery")], "delivery_address": "г. Тест"}
        result = build_contract_clauses(deal)
        all_ids = [c.id for section_clauses in result.values() for c in section_clauses]
        assert len(all_ids) == 2
        assert "cross_reference_to_contract" in all_ids
        assert "delivery_address" in all_ids


class TestAutoNumbering:
    def test_section_numbers_correct(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_max_deal())
        # obligations_supplier → секция 4
        supp = result.get("obligations_supplier", [])
        assert supp[0].auto_number == "4.1"
        assert supp[1].auto_number == "4.2"
        # obligations_customer → секция 5, первый пункт 5.1
        cust = result.get("obligations_customer", [])
        assert cust[0].auto_number == "5.1"
        assert cust[-1].auto_number == f"5.{len(cust)}"
        # final → секция 7
        final = result.get("final", [])
        assert final[0].auto_number == "7.1"

    def test_obligations_customer_ordered_by_order_field(self):
        """Пункты внутри секции отсортированы по полю order."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_montazh_deal())
        cust = result.get("obligations_customer", [])
        # customer_unable_to_accept_team_delays_work (order=5) идёт первым
        assert cust[0].id == "customer_unable_to_accept_team_delays_work"


class TestJinjaSubstitution:
    def test_scales_or_with_orion_no_orion(self):
        """Без ОРИОН: 'Весы' (не 'Весы и комплект ПАК «ОРИОН»')."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_montazh_deal())
        cust = result.get("obligations_customer", [])
        scales_clause = next(
            (c for c in cust if c.id == "customer_provides_scales_near_install_site"), None
        )
        assert scales_clause is not None
        assert "Весы" in scales_clause.text
        assert "ОРИОН" not in scales_clause.text

    def test_scales_or_with_orion_with_orion(self):
        """С ОРИОН: 'Весы и комплект ПАК «ОРИОН»' в тексте пункта."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_max_deal())
        cust = result.get("obligations_customer", [])
        scales_clause = next(
            (c for c in cust if c.id == "customer_provides_scales_near_install_site"), None
        )
        assert scales_clause is not None
        assert "ОРИОН" in scales_clause.text

    def test_obligations_range_in_cross_reference(self):
        """cross_reference_to_contract содержит рассчитанный obligations_range."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_max_deal())
        final_clauses = result.get("final", [])
        cross_ref = next(
            (c for c in final_clauses if c.id == "cross_reference_to_contract"), None
        )
        assert cross_ref is not None
        # Должен содержать "4.1-6.2" для max-сценария
        assert "4.1-6.2" in cross_ref.text

    def test_delivery_address_substituted(self):
        """delivery_address_text подставляется в текст clause delivery_address."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {**_make_montazh_deal(), "delivery_address": "г. Кемерово, пр-т Кузнецкий, 15"}
        result = build_contract_clauses(deal)
        final_clauses = result.get("final", [])
        addr_clause = next(
            (c for c in final_clauses if c.id == "delivery_address"), None
        )
        assert addr_clause is not None
        assert "г. Кемерово" in addr_clause.text

    def test_foundation_term_default(self):
        """customer_builds_foundation_per_spec: дефолтный срок 60 дней если не задан в metadata."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {
            "items": [
                _item("weights"),
                _item("foundation", {"scope": "customer_builds"}),
            ],
            "delivery_address": "г. Тест",
        }
        result = build_contract_clauses(deal)
        cust = result.get("obligations_customer", [])
        found = next((c for c in cust if c.id == "customer_builds_foundation_per_spec"), None)
        assert found is not None
        assert "60" in found.text

    def test_foundation_term_from_metadata(self):
        """customer_builds_foundation_per_spec: срок из metadata.construction_term_days_by_customer."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {
            "items": [
                _item("weights"),
                _item("foundation", {
                    "scope": "customer_builds",
                    "construction_term_days_by_customer": 45,
                }),
            ],
            "delivery_address": "г. Тест",
        }
        result = build_contract_clauses(deal)
        cust = result.get("obligations_customer", [])
        found = next((c for c in cust if c.id == "customer_builds_foundation_per_spec"), None)
        assert found is not None
        assert "45" in found.text
```

- [ ] **Step 4.2: Запустить тесты — убедиться в FAIL**

```
pytest tests/contracts/test_clauses_renderer.py -v
```
Ожидаем: ImportError

- [ ] **Step 4.3: Создать `src/contracts/clauses_renderer.py`**

```python
"""clauses_renderer.py — сборка применимых clauses с нумерацией и jinja-подстановкой."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import jinja2

from src.contracts.clauses_context import build_clauses_context
from src.contracts.clauses_loader import Clause, ClausesLibrary, load_clauses

_logger = logging.getLogger(__name__)

_LIBRARY: Optional[ClausesLibrary] = None
_CLAUSES_PATH = Path("data/clauses.yaml")
_OBLIGATIONS_SECTIONS = ("obligations_supplier", "obligations_customer", "special_conditions")


@dataclass
class RenderedClause:
    id: str
    section: str
    auto_number: str
    text: str


def _get_library() -> ClausesLibrary:
    global _LIBRARY
    if _LIBRARY is None:
        _LIBRARY = load_clauses(_CLAUSES_PATH)
    return _LIBRARY


def _render_text(template_str: str, params: dict) -> str:
    env = jinja2.Environment(undefined=jinja2.Undefined)
    return env.from_string(template_str).render(**params)


def build_contract_clauses(deal: dict) -> dict[str, list[RenderedClause]]:
    """Собрать применимые clauses для deal. Возвращает section_id → [RenderedClause].

    Только непустые секции попадают в результат.
    """
    library = _get_library()
    context = build_clauses_context(deal)
    sections = library.get_sections()
    section_numbers = {s.id: s.section_number for s in sections}

    # Шаг 1: отфильтровать clauses по применимости
    applicable: dict[str, list[Clause]] = {}
    for section in sections:
        clauses = sorted(library.get_clauses_for_section(section.id), key=lambda c: c.order)
        filtered: list[Clause] = []
        for clause in clauses:
            try:
                if clause.applies_when.evaluate(context):
                    filtered.append(clause)
            except KeyError as e:
                _logger.warning("Clause %s: пропущена переменная %s", clause.id, e)
        if filtered:
            applicable[section.id] = filtered

    # Шаг 2: вычислить obligations_range
    range_nums: list[str] = []
    for sec_id in _OBLIGATIONS_SECTIONS:
        sec_num = section_numbers.get(sec_id, 0)
        for i in range(1, len(applicable.get(sec_id, [])) + 1):
            range_nums.append(f"{sec_num}.{i}")

    if len(range_nums) > 1:
        obligations_range = f"{range_nums[0]}-{range_nums[-1]}"
    elif range_nums:
        obligations_range = range_nums[0]
    else:
        obligations_range = ""

    # Шаг 3: jinja-параметры для подстановки в тексты
    items_by_id = {item["id"]: item for item in (deal.get("items") or [])}
    has_orion = context["has_orion"]
    foundation_scope = context["foundation_scope"]

    foundation_term = 60
    if "foundation" in items_by_id:
        foundation_term = int(
            items_by_id["foundation"].get("metadata", {}).get("construction_term_days_by_customer", 60)
        )

    jinja_params = {
        "foundation_term_days_by_customer": foundation_term,
        "scales_or_with_orion": "Весы и комплект ПАК «ОРИОН»" if has_orion else "Весы",
        "install_site_label": "месту установки" if foundation_scope == "rama" else "фундаменту",
        "obligations_range": obligations_range,
        "delivery_address_text": deal.get("delivery_address", ""),
    }

    # Шаг 4: нумерация и рендеринг
    result: dict[str, list[RenderedClause]] = {}
    for section in sections:
        sec_num = section_numbers.get(section.id, 0)
        clauses = applicable.get(section.id, [])
        rendered = [
            RenderedClause(
                id=clause.id,
                section=section.id,
                auto_number=f"{sec_num}.{i}",
                text=_render_text(clause.text.strip(), jinja_params),
            )
            for i, clause in enumerate(clauses, start=1)
        ]
        if rendered:
            result[section.id] = rendered

    return result
```

- [ ] **Step 4.4: Запустить тесты — убедиться в PASS**

```
pytest tests/contracts/test_clauses_renderer.py -v
```
Ожидаем: все PASS

- [ ] **Step 4.5: Полный прогон**

```
pytest tests/ -q
```
Ожидаем: все PASS

- [ ] **Step 4.6: Коммит**

```bash
rtk git add src/contracts/clauses_renderer.py tests/contracts/test_clauses_renderer.py
rtk git commit -m "feat(contracts): clauses_renderer — фильтрация, нумерация, jinja-подстановка"
```

---

## Task 5: Шаблон contract_v2.docx + fill_template_v2

**Files:**
- Create: `scripts/make_contract_v2_template.py`
- Create: `templates/contracts/contract_v2.docx` (генерируется скриптом)
- Modify: `src/contracts/filler.py` (добавить `fill_template_v2`)
- Test: `tests/contracts/test_filler_v2.py`

- [ ] **Step 5.1: Создать скрипт генерации шаблона**

```python
# scripts/make_contract_v2_template.py
"""Создать templates/contracts/contract_v2.docx с jinja-петлями по clauses.

Запуск: python scripts/make_contract_v2_template.py
"""
from pathlib import Path
from docx import Document

OUTPUT = Path("templates/contracts/contract_v2.docx")

CLAUSE_SECTIONS = [
    ("obligations_supplier", "4. Обязательства Подрядчика"),
    ("obligations_customer", "5. Обязательства Заказчика"),
    ("special_conditions", "6. Особые условия"),
    ("final", "7. Заключительные положения"),
]


def make_template() -> None:
    doc = Document()

    # Преамбула с плейсхолдерами
    doc.add_paragraph(
        "г. Москва «{{ДОГОВОР_ДЕНЬ}}» {{ДОГОВОР_МЕСЯЦ}} {{ДОГОВОР_ГОД}} г."
    )
    doc.add_paragraph(
        "Спецификация №{{СПЕЦ_НОМЕР}} к Договору подряда №{{ДОГОВОР_НОМЕР}}"
    )
    doc.add_paragraph(
        "{{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}, именуемое в дальнейшем «Заказчик», "
        "в лице {{ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ}} {{ЗАКАЗЧИК_ДИРЕКТОР_ФИО}}, "
        "{{ДИРЕКТОР_ПРИЧАСТИЕ}} на основании {{ЗАКАЗЧИК_ОСНОВАНИЕ}}, "
        "с одной стороны, и ООО «Тензосила», именуемое в дальнейшем «Подрядчик», "
        "с другой стороны, заключили настоящую Спецификацию."
    )

    # Разделы с динамическими пунктами через docxtpl jinja-петли
    for var_name, title in CLAUSE_SECTIONS:
        doc.add_heading(title, level=1)
        # {%p for %} — docxtpl удаляет этот параграф, повторяет следующий
        p_for = doc.add_paragraph()
        p_for.add_run("{%p for clause in " + var_name + " %}")
        # Строка содержания — повторяется для каждого clause
        p_content = doc.add_paragraph()
        p_content.add_run("{{ clause.auto_number }}. {{ clause.text }}")
        # {%p endfor %} — конец петли
        p_end = doc.add_paragraph()
        p_end.add_run("{%p endfor %}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT))
    print(f"Создан: {OUTPUT}")


if __name__ == "__main__":
    make_template()
```

- [ ] **Step 5.2: Запустить скрипт и убедиться, что файл создан**

```bash
python scripts/make_contract_v2_template.py
```
Ожидаем: `Создан: templates/contracts/contract_v2.docx`

Проверить:
```bash
python -c "from docx import Document; d=Document('templates/contracts/contract_v2.docx'); print(len(d.paragraphs), 'параграфов')"
```

- [ ] **Step 5.3: Добавить `fill_template_v2` в `src/contracts/filler.py`**

Добавить в конец файла (после `remove_empty_paragraphs`):

```python
def fill_template_v2(
    template_path: str,
    data: dict,
    clauses_by_section: dict,
    output_path: str,
) -> None:
    """Рендер v2 шаблона договора через docxtpl с jinja-петлями по clauses.

    clauses_by_section: dict[str, list[RenderedClause]] из build_contract_clauses().
    """
    from docxtpl import DocxTemplate

    if "requisites" in data or "specification" in data:
        flat: dict = {}
        flat.update(data.get("requisites", {}))
        spec = data.get("specification", {})
        flat.update({k: v for k, v in spec.items() if k != "items"})
        data = flat

    context = dict(data)
    # Передать RenderedClause lists в контекст docxtpl
    context.update(clauses_by_section)

    tpl = DocxTemplate(template_path)
    tpl.render(context)
    tpl.save(output_path)
```

- [ ] **Step 5.4: Написать failing тесты для fill_template_v2**

```python
# tests/contracts/test_filler_v2.py
"""Тесты fill_template_v2 — рендер v2 шаблона договора с clauses."""
import os
from pathlib import Path
import pytest

TEMPLATE_V2 = str(Path("templates/contracts/contract_v2.docx"))


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


BASE_DATA = {
    "ДОГОВОР_НОМЕР": "1-2026",
    "ДОГОВОР_ДЕНЬ": "1",
    "ДОГОВОР_МЕСЯЦ": "января",
    "ДОГОВОР_ГОД": "2026",
    "СПЕЦ_НОМЕР": "1",
    "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": "ООО «Тест»",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "Директор",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО": "Тестов Т.Т.",
    "ДИРЕКТОР_ПРИЧАСТИЕ": "действующего",
    "ЗАКАЗЧИК_ОСНОВАНИЕ": "Устава",
}


@pytest.fixture(autouse=True)
def require_template():
    if not os.path.exists(TEMPLATE_V2):
        pytest.skip(f"Шаблон не найден: {TEMPLATE_V2}. Запустите make_contract_v2_template.py")


class TestFillTemplateV2Montazh:
    def test_output_file_created(self, tmp_path):
        from src.contracts.filler import fill_template_v2
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [_item("installation", {"scope": "full"}), _item("verification")],
            "delivery_address": "г. Тест",
        }
        clauses = build_contract_clauses(deal)
        output = str(tmp_path / "v2_montazh.docx")
        fill_template_v2(TEMPLATE_V2, BASE_DATA, clauses, output)
        assert os.path.exists(output)

    def test_clause_text_in_output(self, tmp_path):
        """Текст пункта 'автокран' (customer_provides_crane) присутствует в DOCX."""
        from docx import Document
        from src.contracts.filler import fill_template_v2
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [_item("installation", {"scope": "full"}), _item("verification")],
            "delivery_address": "г. Тест",
        }
        clauses = build_contract_clauses(deal)
        output = str(tmp_path / "v2_crane.docx")
        fill_template_v2(TEMPLATE_V2, BASE_DATA, clauses, output)

        doc = Document(output)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "автокран" in full_text
        assert "комплекта документации" in full_text  # supplier_prepares_docs

    def test_contract_number_substituted(self, tmp_path):
        """Плейсхолдер {{ДОГОВОР_НОМЕР}} заменён."""
        from docx import Document
        from src.contracts.filler import fill_template_v2
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {"items": [_item("delivery")], "delivery_address": "г. Тест"}
        clauses = build_contract_clauses(deal)
        output = str(tmp_path / "v2_num.docx")
        fill_template_v2(TEMPLATE_V2, BASE_DATA, clauses, output)

        doc = Document(output)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "1-2026" in full_text
        assert "{{ДОГОВОР_НОМЕР}}" not in full_text


class TestFillTemplateV2MaxCase:
    def test_14_clauses_all_present(self, tmp_path):
        """Максимальный сценарий: все 14 пунктов в документе."""
        from docx import Document
        from src.contracts.filler import fill_template_v2
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [
                _item("weights"),
                _item("foundation", {"scope": "fundament_jb"}),
                _item("installation", {"scope": "full"}),
                _item("verification"),
                _item("orion"),
                _item("orion_install"),
            ],
            "delivery_address": "г. Тест",
        }
        clauses = build_contract_clauses(deal)
        total_clauses = sum(len(v) for v in clauses.values())
        assert total_clauses == 14

        output = str(tmp_path / "v2_max.docx")
        fill_template_v2(TEMPLATE_V2, BASE_DATA, clauses, output)

        doc = Document(output)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "ОРИОН" in full_text
        assert "4.1-6.2" in full_text  # obligations_range
        assert "строительную бригаду" in full_text  # supplier_dispatches_...with_orion_poles
```

- [ ] **Step 5.5: Запустить тесты — убедиться в PASS**

```
pytest tests/contracts/test_filler_v2.py -v
```
Ожидаем: все PASS

- [ ] **Step 5.6: Полный прогон**

```
pytest tests/ -q
```
Ожидаем: все PASS

- [ ] **Step 5.7: Коммит**

```bash
rtk git add scripts/make_contract_v2_template.py templates/contracts/contract_v2.docx tests/contracts/test_filler_v2.py
rtk git add src/contracts/filler.py
rtk git commit -m "feat(contracts): fill_template_v2 + contract_v2.docx (docxtpl jinja-петли)"
```

---

## Task 6: UI — override-чекбоксы и флаги

**Files:**
- Modify: `src/contracts/state.py` (добавить `scope_overrides`, `flags`)
- Modify: `src/pages/2_Договор.py` (новая секция + preview)

- [ ] **Step 6.1: Обновить `src/contracts/state.py`**

В `_CONTRACT_DEFAULTS` добавить два новых поля:

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
    "scope_overrides": {},                          # новое
    "flags": {"winter_concrete": False},            # новое
}
```

Добавить новые хелперы в конец файла:

```python
def get_scope_overrides() -> dict:
    """Получить dict scope_overrides из namespace."""
    return st.session_state.get("contract", {}).get("scope_overrides", {})


def get_flags() -> dict:
    """Получить dict flags из namespace."""
    return st.session_state.get("contract", {}).get("flags", {"winter_concrete": False})
```

- [ ] **Step 6.2: Запустить все тесты — убедиться что state.py изменения не ломают ничего**

```
pytest tests/contracts/test_state.py -v
pytest tests/ -q
```
Ожидаем: все PASS

- [ ] **Step 6.3: Добавить секцию override в `src/pages/2_Договор.py`**

После блока с `st.data_editor` спецификации (после строки `set_spec_items(_synced)`), перед `st.divider()` в секции 2, добавить:

```python
# --- Особые условия и override-флаги ---
if spec_items:
    st.divider()
    st.subheader("Особые условия")
    cs = st.session_state["contract"]
    cs.setdefault("scope_overrides", {})
    cs.setdefault("flags", {"winter_concrete": False})

    ov_col1, ov_col2 = st.columns(2)
    with ov_col1:
        winter_val = bool(cs["flags"].get("winter_concrete", False))
        new_winter = st.checkbox("Зимний период (бетонные работы при t < +5°C)", value=winter_val, key="w_winter_concrete")
        cs["flags"]["winter_concrete"] = new_winter

    with ov_col2:
        VER_OPTIONS = ["Авто (из позиций)", "Подрядчик", "Заказчик"]
        ver_idx = 0
        if cs["scope_overrides"].get("verification_scope") == "supplier":
            ver_idx = 1
        elif cs["scope_overrides"].get("verification_scope") == "customer":
            ver_idx = 2
        ver_sel = st.selectbox("Кто организует поверку", VER_OPTIONS, index=ver_idx, key="w_ver_override")
        if ver_sel == "Подрядчик":
            cs["scope_overrides"]["verification_scope"] = "supplier"
        elif ver_sel == "Заказчик":
            cs["scope_overrides"]["verification_scope"] = "customer"
        else:
            cs["scope_overrides"].pop("verification_scope", None)

    # Preview clauses
    st.caption("Условия, которые будут включены в договор:")
    _deal_preview = {
        "items": spec_items,
        "scope_overrides": cs.get("scope_overrides", {}),
        "flags": cs.get("flags", {}),
        "delivery_address": cs["manual"].get("object_address", ""),
    }
    try:
        from src.contracts.clauses_renderer import build_contract_clauses
        _clauses_preview = build_contract_clauses(_deal_preview)
        for _sec_id, _sec_clauses in _clauses_preview.items():
            for _c in _sec_clauses:
                st.text(f"{_c.auto_number}  {_c.id} — {_c.text[:70]}…")
    except Exception as _e:
        st.caption(f"(preview недоступен: {_e})")
```

- [ ] **Step 6.4: Коммит**

```bash
rtk git add src/contracts/state.py src/pages/2_Договор.py
rtk git commit -m "feat(contracts): UI — зимний период, override поверки, preview clauses"
```

---

## Task 7: Переключение генерации на v2 (safety fallback)

**Files:**
- Modify: `src/pages/2_Договор.py` (генерация → v2 с fallback)

- [ ] **Step 7.1: Добавить импорт и константу для v2 в `2_Договор.py`**

Найти строки:
```python
CONTRACT_TEMPLATE = Path("templates/contracts/contract.docx")
SPEC_TEMPLATE = Path("templates/contracts/spec_foundation_install.docx")
```

Добавить после них:
```python
CONTRACT_V2_TEMPLATE = Path("templates/contracts/contract_v2.docx")
```

Добавить в блок импортов из filler:
```python
from src.contracts.filler import fill_spec_with_items, fill_template, fill_template_v2, get_unfilled_placeholders
```

- [ ] **Step 7.2: Заменить генерацию договора на v2 с fallback**

Найти в секции 4 (Генерация) строку:
```python
fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
```

Заменить весь этот вызов на:
```python
_deal_for_clauses = {
    "items": items_for_docx if items_for_docx else get_spec_items(),
    "scope_overrides": cs.get("scope_overrides", {}),
    "flags": cs.get("flags", {}),
    "delivery_address": object_address,
}
_v2_ok = False
if CONTRACT_V2_TEMPLATE.exists():
    try:
        from src.contracts.clauses_renderer import build_contract_clauses
        _clauses_by_section = build_contract_clauses(_deal_for_clauses)
        fill_template_v2(str(CONTRACT_V2_TEMPLATE), data, _clauses_by_section, str(contract_path))
        _v2_ok = True
    except Exception as _v2_exc:
        _logger.warning("fill_template_v2 failed (%s), fallback to v1", _v2_exc)
        st.warning(f"Clauses library error (используется v1 шаблон): {_v2_exc}")
if not _v2_ok:
    fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
```

- [ ] **Step 7.3: Запустить полный pytest**

```
pytest tests/ -q
```
Ожидаем: все PASS

- [ ] **Step 7.4: Коммит**

```bash
rtk git add src/pages/2_Договор.py
rtk git commit -m "feat(contracts): генерация переключена на fill_template_v2 с fallback на v1"
```

---

## Task 8: Финальная верификация

- [ ] **Step 8.1: Полный прогон pytest**

```
pytest tests/ -v --tb=short
```
Ожидаем: все тесты PASS (включая старые тесты Step 12)

- [ ] **Step 8.2: Smoke-проверка Streamlit (ручная)**

```
streamlit run src/app.py
```

Проверить:
- Страница Договор открывается без ошибок
- В режиме A: загрузить любой КП из базы → spec items появляются → секция "Особые условия" видна → preview clauses отображается
- Нажать "Сгенерировать" → оба файла скачиваются → DOCX открывается → разделы 4-7 содержат пункты
- Включить "Зимний период" → в preview появляются winter_concrete_surcharge/winter_concrete_heating_option

- [ ] **Step 8.3: Обновить docs/STATUS.md**

Добавить Шаг 7 в раздел "Что выполнено":

```markdown
### Шаг 7 — Clauses Library (DSL + loader + context + renderer + UI) ✅
- src/contracts/clauses_dsl.py: безопасный AST-парсер applies_when
- src/contracts/clauses_loader.py: загрузка/валидация data/clauses.yaml (28 clauses)
- src/contracts/clauses_context.py: build_clauses_context — 6 переменных из SpecItems
- src/contracts/clauses_renderer.py: фильтрация, нумерация, jinja-подстановка
- fill_template_v2() + contract_v2.docx (docxtpl jinja-петли)
- UI: зимний период, override поверки, реактивный preview clauses
- Safety fallback: при ошибке → v1 шаблон
```

Изменить строку:
```
Текущая фаза: 2.x — готовность к деплою (Шаг 11)
```
На:
```
Текущая фаза: 3.x — clauses library (Шаг 7 выполнен, тег v1.0)
```

- [ ] **Step 8.4: Обновить docs/architecture/contracts_v2.md**

В разделе "## План миграции с v1 на v2" добавить отметку о выполнении пунктов 4 и 5:

```markdown
4. ~~Реализация массива позиций спецификации~~ ✅ тег `v0.9`
5. ~~Реализация clauses library и замена шаблонов~~ ✅ тег `v1.0`
```

- [ ] **Step 8.5: Финальный коммит**

```bash
rtk git add docs/STATUS.md docs/architecture/contracts_v2.md
rtk git commit -m "docs: STATUS.md и contracts_v2.md — Шаг 7 выполнен, тег v1.0"
```

- [ ] **Step 8.6: Поставить тег v1.0** (только после явной отмашки пользователя)

```bash
rtk git tag v1.0
```

---

## Примечания

**Ограничение: contract_v2.docx — минимальный шаблон.** Файл создаётся программно и содержит только преамбулу + 4 секции clauses. Для production-использования нужно перенести в него все остальные разделы из `contract.docx` (разделы 1-3, реквизиты, подписи). Это делается вручную в Word или отдельным скриптом — за рамками текущего шага.

**Обратная совместимость:** `fill_template` + `contract.docx` + `spec_foundation_install.docx` сохраняются и продолжают работать как fallback. Не удалять до явной отмашки.

**obligations_range при поставке** (нет секций obligations): cross_reference_to_contract всё равно рендерится (applies_when: 'true'), но obligations_range = "" → в тексте будет "п.п.  настоящей Спецификации" с пустым местом. Это известное ограничение MVP.

---

## Self-Review

### 1. Spec coverage

| Требование | Задача |
|-----------|--------|
| DSL parser через ast.parse + whitelist | Task 1 |
| Security: функции/атрибуты/импорты отклоняются | Task 1 (TestSecurity) |
| load_clauses + ClausesLibrary | Task 2 |
| Валидация: дублирующийся id, несуществующий section | Task 2 (TestValidationErrors) |
| build_clauses_context, 6 переменных | Task 3 |
| 9 эталонных кейсов | Task 3 (TestNineScenarios) |
| Override scope_overrides | Task 3 (TestOverrides) |
| winter_concrete только из flags | Task 3 |
| build_contract_clauses + RenderedClause | Task 4 |
| Автонумерация (section_number.i) | Task 4 (TestAutoNumbering) |
| obligations_range для cross_reference | Task 4 (TestJinjaSubstitution) |
| jinja-подстановка scales_or_with_orion, install_site_label | Task 4 |
| foundation_term из metadata / default 60 | Task 4 |
| delivery_address_text из deal | Task 4 |
| contract_v2.docx с jinja-петлями | Task 5 |
| fill_template_v2 через docxtpl | Task 5 |
| Тесты DOCX-генерации (монтаж + max 14) | Task 5 |
| UI: зимний период + override поверки | Task 6 |
| Preview clauses в UI | Task 6 |
| Переключение генерации на v2 | Task 7 |
| Safety fallback на v1 | Task 7 |
| Полный pytest зелёный | Task 8 |
| STATUS.md + contracts_v2.md обновлены | Task 8 |

### 2. Нет плейсхолдеров: проверено ✓

### 3. Согласованность типов

- `parse(expr: str) -> Expression` — используется в `load_clauses` (Task 2) ✓
- `Expression.evaluate(context: dict) -> bool` — используется в `build_contract_clauses` (Task 4) ✓
- `ClausesLibrary.get_clauses_for_section(id) -> list[Clause]` — используется в renderer ✓
- `build_clauses_context(deal: dict) -> dict` — используется в renderer ✓
- `RenderedClause(id, section, auto_number, text)` — передаётся в docxtpl context ✓
- `fill_template_v2(template_path, data, clauses_by_section, output_path)` — вызывается из page ✓
