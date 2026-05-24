# Сохранение КП в Supabase после генерации DOCX

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** После нажатия кнопки «Сгенерировать КП» автоматически сохранять снапшот session_state в таблицу `kps` Supabase через `save_kp()`.

**Architecture:** Новый хелпер `src/storage/snapshot_builder.py` строит JSONB-словарь из session_state по структуре §6.2 аудита. В `src/ui/sidebar.py` return-value `st.download_button` служит guard'ом против повторных вызовов на rerune. `save_kp()` не блокирует генерацию: ошибки показываются через `st.warning`.

**Tech Stack:** Python 3.11, Streamlit, `src.storage.supabase_client.save_kp` (уже готов), pytest.

---

## Файлы

| Действие | Путь | Ответственность |
|----------|------|-----------------|
| Create   | `src/storage/snapshot_builder.py` | Чистая функция `build_kp_snapshot(state) -> dict` |
| Create   | `tests/storage/test_snapshot_builder.py` | 5 тестов без сети |
| Modify   | `src/ui/sidebar.py` | Thread `totals`, вызов `_save_kp_to_storage` по клику |

---

## Task 1: Написать падающие тесты для snapshot_builder

**Files:**
- Create: `tests/storage/test_snapshot_builder.py`

- [ ] **Step 1: Написать тесты**

```python
"""Тесты build_kp_snapshot — без сети, без Supabase."""
from __future__ import annotations

import pytest
from datetime import date

from src.storage.snapshot_builder import build_kp_snapshot


def _base_state() -> dict:
    return {
        "kp_number": "КП-2026-001",
        "kp_date": date(2026, 5, 20),
        "kp_valid_days": 15,
        "warranty_months": 36,
        "client_name": "ООО Ромашка",
        "manager_id": "ivanov",
        "model_line": "С",
        "model_max": 60,
        "model_length": 18,
        "model_id": "vesta-с-60-18",
        "model_price": None,
        "sensor_id": "zemic_dhm9b_30t",
        "indicator_id": "titan_3cs",
        "cable_m": 20,
        "is_dual_range": False,
        "construction_beam": "Двутавр 20Б1",
        "construction_beam_count": 4,
        "construction_center_beam": "",
        "construction_center_beam_count": 0,
        "construction_deck_mm": 6,
        "construction_underlining_mm": 4,
        "options": {},
        "spec_items_overrides": {},
        "payment_preset_id": "split_by_items",
        "payment_days": 5,
        "payment_custom_text": "",
        "payment_split_state": {"scales": {"prepay": 50, "postpay": 50}},
        "payment_v1_prepay": 50,
        "payment_v2_prepay": 30,
        "payment_v2_preship": 40,
        "payment_v3_days": 15,
        "payment_v3_trigger_id": "after_installation",
    }


def test_builds_full_snapshot_from_minimal_state():
    snap = build_kp_snapshot(_base_state())

    assert snap["metadata"]["kp_valid_days"] == 15
    assert snap["metadata"]["warranty_months"] == 36

    assert snap["model"]["line"] == "С"
    assert snap["model"]["max"] == 60
    assert snap["model"]["length"] == 18
    assert snap["model"]["price"] is None

    assert snap["equipment"]["sensor_id"] == "zemic_dhm9b_30t"
    assert snap["equipment"]["indicator_id"] == "titan_3cs"
    assert snap["equipment"]["cable_m"] == 20

    assert snap["construction"]["beam"] == "Двутавр 20Б1"
    assert snap["construction"]["beam_count"] == 4
    assert snap["construction"]["deck_mm"] == 6

    assert snap["metrology"]["is_dual_range"] is False

    assert snap["options"] == {}
    assert snap["spec_overrides"] == {}

    assert snap["payment"]["preset_id"] == "split_by_items"
    assert snap["payment"]["days"] == 5
    assert snap["payment"]["v1_prepay"] == 50
    assert snap["payment"]["v3_trigger_id"] == "after_installation"


def test_excludes_widget_keys():
    state = _base_state()
    # Виджетные ключи Streamlit — НЕ должны попасть в снапшот
    state["opt_frame_std_с_enabled__vesta-с-60-18"] = True
    state["opt_frame_std_с_price__vesta-с-60-18"] = 85000
    state["split_scales_prepay"] = 50
    snap = build_kp_snapshot(state)
    flat = str(snap)
    assert "opt_" not in flat
    assert "split_scales" not in flat


def test_excludes_computed_values():
    state = _base_state()
    # Вычисляемые ключи — не должны попасть в снапшот
    state["spec_items"] = [{"label": "Базовый блок", "price": 2450000}]
    state["total_term_days_user_set"] = True
    state["payment_percents"] = {"p1": 50}
    snap = build_kp_snapshot(state)
    assert "spec_items" not in snap
    assert "total_term_days_user_set" not in snap
    assert "payment_percents" not in snap


def test_handles_missing_optional_keys():
    # Минимальный state — только обязательные ключи, нет options/overrides/payment_custom_text
    state = {
        "kp_valid_days": 15,
        "warranty_months": 24,
        "model_line": "Ф",
        "model_max": 30,
        "model_length": 12,
        "model_price": None,
        "sensor_id": "s1",
        "indicator_id": "i1",
        "cable_m": 10,
        "is_dual_range": False,
        "construction_beam": "20Б1",
        "construction_beam_count": 2,
        "construction_center_beam": "",
        "construction_center_beam_count": 0,
        "construction_deck_mm": 5,
        "construction_underlining_mm": 3,
        "payment_preset_id": "prepay_100",
        "payment_days": 3,
    }
    snap = build_kp_snapshot(state)
    assert snap["options"] == {}
    assert snap["spec_overrides"] == {}
    assert snap["payment"]["custom_text"] == ""
    assert snap["payment"]["split_state"] == {}


def test_options_preserve_retail_and_dealer_flag():
    state = _base_state()
    state["options"] = {
        "frame_std_с": {
            "enabled": True,
            "price": 85000,
            "qty": 2,
            "customer_side": False,
            "is_on_request": False,
            "retail": 90000,
            "dealer_is_synthetic": True,
            "block": "ramps",
        },
        "lighting": {
            "enabled": False,   # отключена — не должна попасть
            "price": 15000,
            "qty": 1,
            "customer_side": False,
            "is_on_request": False,
            "retail": 15000,
            "dealer_is_synthetic": False,
            "block": "extras",
        },
    }
    snap = build_kp_snapshot(state)
    # Только enabled опции
    assert "frame_std_с" in snap["options"]
    assert "lighting" not in snap["options"]
    # Проверяем поля снапшота
    opt = snap["options"]["frame_std_с"]
    assert opt["price"] == 85000
    assert opt["qty"] == 2
    assert opt["customer_side"] is False
    assert opt["retail"] == 90000
    assert opt["dealer_is_synthetic"] is True
    # Служебные поля прайса не хранятся
    assert "is_on_request" not in opt
    assert "block" not in opt
    assert "enabled" not in opt
```

- [ ] **Step 2: Запустить тесты, убедиться что падают**

```
pytest tests/storage/test_snapshot_builder.py -v
```

Ожидаем: `ImportError: cannot import name 'build_kp_snapshot' from 'src.storage.snapshot_builder'` (файл не существует).

---

## Task 2: Реализовать `src/storage/snapshot_builder.py`

**Files:**
- Create: `src/storage/snapshot_builder.py`

- [ ] **Step 1: Написать реализацию**

```python
"""Строит JSONB-снапшот session_state КП для сохранения в Supabase."""
from __future__ import annotations

from typing import Any


def build_kp_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Возвращает data-блок для колонки kps.data.

    Включает только ключи из §6.2 session_state_audit.md.
    Виджетные ключи (opt_*, split_*), вычисляемые (spec_items, totals)
    и legacy (payment_percents) исключены.
    """
    opts = state.get("options") or {}
    enabled_options = {
        key: {
            "price": opt.get("price", 0),
            "qty": opt.get("qty", 1),
            "customer_side": opt.get("customer_side", False),
            "retail": opt.get("retail", 0),
            "dealer_is_synthetic": opt.get("dealer_is_synthetic", False),
        }
        for key, opt in opts.items()
        if opt.get("enabled", False)
    }

    return {
        "metadata": {
            "kp_valid_days": state.get("kp_valid_days"),
            "warranty_months": state.get("warranty_months"),
        },
        "model": {
            "line": state.get("model_line"),
            "max": state.get("model_max"),
            "length": state.get("model_length"),
            "price": state.get("model_price"),
        },
        "equipment": {
            "sensor_id": state.get("sensor_id"),
            "indicator_id": state.get("indicator_id"),
            "cable_m": state.get("cable_m"),
        },
        "construction": {
            "beam": state.get("construction_beam"),
            "beam_count": state.get("construction_beam_count"),
            "center_beam": state.get("construction_center_beam"),
            "center_beam_count": state.get("construction_center_beam_count"),
            "deck_mm": state.get("construction_deck_mm"),
            "underlining_mm": state.get("construction_underlining_mm"),
        },
        "metrology": {
            "is_dual_range": state.get("is_dual_range"),
        },
        "options": enabled_options,
        "spec_overrides": state.get("spec_items_overrides") or {},
        "payment": {
            "preset_id": state.get("payment_preset_id"),
            "days": state.get("payment_days"),
            "custom_text": state.get("payment_custom_text", ""),
            "split_state": state.get("payment_split_state") or {},
            "v1_prepay": state.get("payment_v1_prepay"),
            "v2_prepay": state.get("payment_v2_prepay"),
            "v2_preship": state.get("payment_v2_preship"),
            "v3_days": state.get("payment_v3_days"),
            "v3_trigger_id": state.get("payment_v3_trigger_id"),
        },
    }
```

- [ ] **Step 2: Запустить тесты — должны пройти**

```
pytest tests/storage/test_snapshot_builder.py -v
```

Ожидаем: 5 passed.

- [ ] **Step 3: Запустить весь suite — убедиться, что ничего не сломали**

```
pytest tests/ -v --ignore=tests/contracts/synthetic
```

Ожидаем: все зелёные (234 + 5 новых = 239).

- [ ] **Step 4: Коммит**

```
git add src/storage/snapshot_builder.py tests/storage/test_snapshot_builder.py
git commit -m "test: snapshot_builder — 5 тестов на сборку снапшота КП"
```

---

## Task 3: Интегрировать save_kp в sidebar.py

**Files:**
- Modify: `src/ui/sidebar.py:14-160`

Текущая сигнатура `_render_generate_button(state, spec_items, errors, prices)` — добавить `totals: dict`.

Текущий вызов в `render_sidebar`: `_render_generate_button(state, spec_items, errors, prices)` — добавить `totals`.

- [ ] **Step 1: Добавить helper `_save_kp_to_storage` и обновить `_render_generate_button`**

Добавить импорты в начало файла (после существующих):

```python
from src.pricing import calc_totals
from src.storage.snapshot_builder import build_kp_snapshot
from src.storage.supabase_client import StorageError, save_kp
```

Добавить функцию `_save_kp_to_storage` перед `_render_generate_button`:

```python
def _save_kp_to_storage(state: dict, total_price: int) -> None:
    """Сохраняет снапшот КП в Supabase. Ошибки не блокируют генерацию."""
    try:
        save_kp(
            kp_number=state["kp_number"],
            kp_date=state["kp_date"],
            client_name=state["client_name"],
            model_id=state["model_id"],
            total_price=total_price,
            manager_id=state["manager_id"],
            data=build_kp_snapshot(state),
        )
        st.success("КП сохранён в базу")
    except StorageError as e:
        st.warning(f"Не удалось сохранить в базу: {e}")
```

В `_render_generate_button` — внутри try-блока заменить:

```python
    try:
        docx_bytes = generate_kp(dict(state), prices)
        st.download_button(
            label,
            data=docx_bytes,
            file_name=build_filename(dict(state)),
            mime=mime,
            width="stretch",
            type="primary",
        )
```

на:

```python
    try:
        docx_bytes = generate_kp(dict(state), prices)
        total_price = calc_totals(spec_items)["with_vat"]
        clicked = st.download_button(
            label,
            data=docx_bytes,
            file_name=build_filename(dict(state)),
            mime=mime,
            width="stretch",
            type="primary",
        )
        if clicked:
            _save_kp_to_storage(dict(state), total_price)
```

- [ ] **Step 2: Убедиться что тесты всё ещё зелёные**

```
pytest tests/ -v --ignore=tests/contracts/synthetic
```

Ожидаем: 239 passed.

- [ ] **Step 3: Коммит**

```
git add src/ui/sidebar.py src/storage/snapshot_builder.py
git commit -m "feat: сохранение КП в Supabase после генерации DOCX (Шаг 8)"
```

---

## Task 4: Обновить docs/STATUS.md

**Files:**
- Modify: `docs/STATUS.md`

- [ ] **Step 1: Отметить Шаг 8 выполненным**

В разделе «Что выполнено» добавить:

```markdown
### Шаг 8 ✅ — Интеграция save_kp в страницу КП
- src/storage/snapshot_builder.py: build_kp_snapshot(state) → JSONB по §6.2
- sidebar.py: download_button-click guard + _save_kp_to_storage
- 5 новых тестов (test_snapshot_builder.py), итого 239 тестов зелёные
```

В разделе «Что делаем дальше» изменить заголовок Шага 8 на «(выполнен)» и пометить Шаг 9 как текущий.

- [ ] **Step 2: Обновить строку «Текущая фаза»**

```
Текущая фаза: 2.x — Шаг 9, двухрежимный UI договора
```

- [ ] **Step 3: Коммит**

```
git add docs/STATUS.md
git commit -m "docs: Шаг 8 выполнен, обновить STATUS.md"
```

---

## Self-Review

**Spec coverage:**

| Требование | Task |
|------------|------|
| build_kp_snapshot в отдельном файле | Task 2 |
| Только ключи из §6.2 (не widget, не computed) | Task 2 |
| save_kp с распакованными аргументами | Task 3 |
| Успех: st.success | Task 3 |
| Ошибка: st.warning, не блокирует DOCX | Task 3 |
| Один вызов при нажатии, не на каждый rerun | Task 3 (download_button guard) |
| 5 тестов по именам из задачи | Task 1 |
| options: retail + dealer_is_synthetic | Task 1 + Task 2 |
| Существующие 234 теста остаются зелёными | Task 2 Step 3 |

**Gaps:** Нет. Все требования покрыты.

**Type consistency:** `build_kp_snapshot(state: dict) -> dict` используется одинаково в Task 1 (импорт в тестах) и Task 3 (импорт в sidebar.py).

**Placeholders:** Нет TBD/TODO. Все шаги содержат реальный код.
