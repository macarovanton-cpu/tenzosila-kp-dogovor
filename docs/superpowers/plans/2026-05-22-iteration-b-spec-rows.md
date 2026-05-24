# Iteration B — Spec Rows from KP Snapshot

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить функцию `build_spec_rows_from_snapshot` в `src/contracts/from_kp.py`, которая маппит снапшот КП из Supabase в список строк спецификации с каноническими формулировками, раздельными монтажом и поверкой, обработкой `customer_side` и предупреждениями для неизвестных ключей.

**Architecture:** Новая публичная функция в существующем модуле `from_kp.py`. Не использует `build_spec_items` из `spec_builder.py` — работает напрямую с `kp_row["data"]`. Канонические формулировки — внутренний маппинг-словарь. Существующая функция `build_specification_from_kp_snapshot` не трогается.

**Tech Stack:** Python 3.11+, `re`, `logging`, `pytest`.

---

## Файлы

- Modify: `src/contracts/from_kp.py` — добавить функцию `build_spec_rows_from_snapshot` и внутренний маппинг
- Modify: `tests/contracts/test_from_kp.py` — добавить класс `TestBuildSpecRowsFromSnapshot` с 6 тест-кейсами

---

### Task 1: Написать падающие тесты

**Files:**
- Modify: `tests/contracts/test_from_kp.py`

- [ ] **Step 1: Добавить тест-кейсы в конец файла `tests/contracts/test_from_kp.py`**

```python
import logging
import re


class TestBuildSpecRowsFromSnapshot:
    """Тесты build_spec_rows_from_snapshot."""

    def _make_full_kp_row(self, line="С", max_t=60, length=18, price=2835000,
                           foundation_key="foundation_s_f_18",
                           foundation_price=350000,
                           verification_customer_side=False) -> dict:
        options = {
            foundation_key: {
                "qty": 1, "price": foundation_price,
                "retail": foundation_price, "customer_side": False,
            },
            "delivery_default": {
                "qty": 1, "price": 50000,
                "retail": 50000, "customer_side": False,
            },
            "install_default": {
                "qty": 1, "price": 80000,
                "retail": 80000, "customer_side": False,
            },
            "verification_default": {
                "qty": 1, "price": 30000,
                "retail": 30000, "customer_side": verification_customer_side,
            },
        }
        return _make_kp_row(
            model_line=line, model_max=max_t, model_length=length,
            model_price=price, options=options,
        )

    def test_base_case_five_rows(self):
        """Базовый кейс: модель + фундамент + доставка + монтаж + поверка → 5 строк."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(self._make_full_kp_row())
        assert len(rows) == 5

    def test_base_case_canonical_names(self):
        """Проверка канонических формулировок всех 5 строк."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(self._make_full_kp_row())
        names = [r["name"] for r in rows]
        assert names[0] == "Весы автомобильные ВЕСТА-С-60-18-Ц, max 60т, размеры платформы 18х3м"
        assert names[1] == "Фундамент железобетонный под весы автомобильные ВЕСТА-С, 18м"
        assert names[2] == "Доставка весов до объекта"
        assert names[3] == "Монтаж автомобильных весов"
        assert names[4] == "Поверка автомобильных весов с доставкой эталонов"

    def test_customer_side_verification_price_is_zakazchik(self):
        """customer_side=True → price_display='ЗАКАЗЧИК', не учитывается в итого."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        rows = build_spec_rows_from_snapshot(
            self._make_full_kp_row(verification_customer_side=True)
        )
        assert len(rows) == 5
        verify_row = next(r for r in rows if "Поверка" in r["name"])
        assert verify_row["customer_side"] is True
        assert verify_row["price_display"] == "ЗАКАЗЧИК"
        # итого не включает поверку
        total = sum(r["price"] for r in rows if not r["customer_side"])
        assert total == 2835000 + 350000 + 50000 + 80000

    def test_qty_zero_row_skipped(self):
        """Опция с qty=0 не попадает в строки."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        kp_row = _make_kp_row(options={
            "delivery_default": {"qty": 0, "price": 50000, "retail": 50000, "customer_side": False},
        })
        rows = build_spec_rows_from_snapshot(kp_row)
        names = [r["name"] for r in rows]
        assert not any("Доставка" in n for n in names)

    def test_unknown_option_key_logged_and_included(self, caplog):
        """Неизвестный ключ → WARNING в логе, строка добавляется с raw-ключом."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        kp_row = _make_kp_row(options={
            "unknown_future_option_42": {"qty": 1, "price": 99000, "retail": 99000, "customer_side": False},
        })
        with caplog.at_level(logging.WARNING, logger="src.contracts.from_kp"):
            rows = build_spec_rows_from_snapshot(kp_row)
        assert any("unknown_future_option_42" in msg for msg in caplog.messages)
        assert any(r["name"] == "unknown_future_option_42" for r in rows)

    def test_foundation_formulations_all_three_types(self):
        """Проверка формулировок для всех 3 типов фундамента."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot

        # Тип 1: foundation_s_f_{N} для линейки С
        rows_sf = build_spec_rows_from_snapshot(
            self._make_full_kp_row(line="С", length=18, foundation_key="foundation_s_f_18")
        )
        f_names_sf = [r["name"] for r in rows_sf if "Фундамент" in r["name"]]
        assert f_names_sf == ["Фундамент железобетонный под весы автомобильные ВЕСТА-С, 18м"]

        # Тип 2: foundation_lite_sl_fl_{N} для линейки СЛ
        rows_lite = build_spec_rows_from_snapshot(
            self._make_full_kp_row(line="СЛ", length=18, foundation_key="foundation_lite_sl_fl_18")
        )
        f_names_lite = [r["name"] for r in rows_lite if "Фундамент" in r["name"]]
        assert f_names_lite == ["Фундамент пандусный «ЛАЙТ» под весы автомобильные ВЕСТА-СЛ, 18м"]

        # Тип 3: foundation_std_sl_fl_{N} для линейки ФЛ
        rows_std = build_spec_rows_from_snapshot(
            self._make_full_kp_row(line="ФЛ", length=24, foundation_key="foundation_std_sl_fl_24")
        )
        f_names_std = [r["name"] for r in rows_std if "Фундамент" in r["name"]]
        assert f_names_std == ["Фундамент пандусный «Стандарт» под весы автомобильные ВЕСТА-ФЛ, 24м"]

    def test_model_name_for_all_lines(self):
        """Формирование имени модели для всех линеек."""
        from src.contracts.from_kp import build_spec_rows_from_snapshot
        for line in ("С", "СЛ", "Ф", "ФЛ", "П"):
            kp_row = _make_kp_row(model_line=line, model_max=40, model_length=12)
            rows = build_spec_rows_from_snapshot(kp_row)
            model_row = rows[0]
            expected = f"Весы автомобильные ВЕСТА-{line}-40-12-Ц, max 40т, размеры платформы 12х3м"
            assert model_row["name"] == expected, f"Line {line}: {model_row['name']!r}"
```

- [ ] **Step 2: Запустить тесты — убедиться что они падают**

```
pytest tests/contracts/test_from_kp.py::TestBuildSpecRowsFromSnapshot -v
```

Ожидаем: `ImportError` или `AttributeError` — функция ещё не существует.

---

### Task 2: Реализовать `build_spec_rows_from_snapshot`

**Files:**
- Modify: `src/contracts/from_kp.py`

- [ ] **Step 1: Добавить импорты и маппинг в начало модуля**

Добавить после `from src.term_days import ...`:

```python
import logging
import re

_logger = logging.getLogger(__name__)

# Маппинг ключей опций → канонические формулировки.
# {line} и {N} подставляются динамически.
_SIMPLE_OPTION_NAMES: dict[str, str] = {
    "delivery_default": "Доставка весов до объекта",
    "install_default": "Монтаж автомобильных весов",
    "verification_default": "Поверка автомобильных весов с доставкой эталонов",
}

_FOUNDATION_PATTERNS = [
    (re.compile(r"^foundation_s_f_(\d+)$"),
     "Фундамент железобетонный под весы автомобильные ВЕСТА-{line}, {N}м"),
    (re.compile(r"^foundation_lite_sl_fl_(\d+)$"),
     "Фундамент пандусный «ЛАЙТ» под весы автомобильные ВЕСТА-{line}, {N}м"),
    (re.compile(r"^foundation_std_sl_fl_(\d+)$"),
     "Фундамент пандусный «Стандарт» под весы автомобильные ВЕСТА-{line}, {N}м"),
]
```

- [ ] **Step 2: Добавить функцию `_resolve_option_name`**

```python
def _resolve_option_name(key: str, line: str) -> str | None:
    """Вернуть каноническое имя для ключа опции или None если неизвестный."""
    if key in _SIMPLE_OPTION_NAMES:
        return _SIMPLE_OPTION_NAMES[key]
    for pattern, template in _FOUNDATION_PATTERNS:
        m = pattern.match(key)
        if m:
            return template.format(line=line, N=m.group(1))
    return None
```

- [ ] **Step 3: Добавить функцию `build_spec_rows_from_snapshot`**

```python
def build_spec_rows_from_snapshot(kp_row: dict[str, Any]) -> list[dict[str, Any]]:
    """Список строк спецификации из снапшота КП.

    Каждая строка: {name, qty, price, price_display, customer_side}.
    customer_side=True → price_display='ЗАКАЗЧИК', price=0 (не в итого).
    qty=0 → строка пропускается.
    Неизвестный ключ → WARNING в логе, добавляется с raw-ключом.
    """
    data = kp_row.get("data") or {}
    model = data.get("model") or {}
    line = model.get("line", "")
    max_t = model.get("max", "")
    length = model.get("length", "")
    model_price = int(model.get("price") or 0)

    rows: list[dict[str, Any]] = []

    # Первая строка — модель весов
    model_name = (
        f"Весы автомобильные ВЕСТА-{line}-{max_t}-{length}-Ц, "
        f"max {max_t}т, размеры платформы {length}х3м"
    )
    rows.append({
        "name": model_name,
        "qty": 1,
        "price": model_price,
        "price_display": _fmt(model_price),
        "customer_side": False,
    })

    # Строки опций
    options = data.get("options") or {}
    for key, opt in options.items():
        qty = int(opt.get("qty", 1))
        if qty == 0:
            continue
        customer_side = bool(opt.get("customer_side", False))
        price = 0 if customer_side else int(opt.get("price", 0))
        price_display = "ЗАКАЗЧИК" if customer_side else _fmt(price)

        name = _resolve_option_name(key, line)
        if name is None:
            _logger.warning("build_spec_rows_from_snapshot: неизвестный ключ опции %r", key)
            name = key

        rows.append({
            "name": name,
            "qty": qty,
            "price": price,
            "price_display": price_display,
            "customer_side": customer_side,
        })

    return rows
```

- [ ] **Step 4: Запустить новые тесты**

```
pytest tests/contracts/test_from_kp.py::TestBuildSpecRowsFromSnapshot -v
```

Ожидаем: все 7 тестов зелёные.

- [ ] **Step 5: Запустить все тесты модуля, убедиться что старые не сломались**

```
pytest tests/contracts/test_from_kp.py -v
```

Ожидаем: все тесты зелёные.

- [ ] **Step 6: Запустить полный pytest**

```
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Ожидаем: зелёный.

- [ ] **Step 7: Коммит**

```
git add src/contracts/from_kp.py tests/contracts/test_from_kp.py
git commit -m "feat(contracts): Итерация B — build_spec_rows_from_snapshot, канонические формулировки"
```

---

## Self-Review

**Spec coverage:**
- ✅ Маппинг модели → «Весы автомобильные ВЕСТА-{line}-{max}-{length}-Ц, max {max}т, ...»
- ✅ delivery_default → «Доставка весов до объекта»
- ✅ install_default → «Монтаж автомобильных весов»
- ✅ verification_default → «Поверка автомобильных весов с доставкой эталонов»
- ✅ foundation_s_f_{N} → «Фундамент железобетонный...»
- ✅ foundation_lite_sl_fl_{N} → «Фундамент пандусный «ЛАЙТ»...»
- ✅ foundation_std_sl_fl_{N} → «Фундамент пандусный «Стандарт»...»
- ✅ Отдельные строки для монтажа и поверки (не схлопываются)
- ✅ customer_side=True → price_display="ЗАКАЗЧИК", price=0
- ✅ qty=0 → строка пропускается
- ✅ Неизвестный ключ → WARNING + raw-ключ в name
- ✅ Существующие тесты test_from_kp.py не трогаются

**Placeholder scan:** нет TBD/TODO/«аналогично».

**Type consistency:** `build_spec_rows_from_snapshot` использует `_fmt` (уже есть в модуле). Все поля `price_display`, `customer_side`, `price`, `name`, `qty` одинаковы в реализации и тестах.
