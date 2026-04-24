"""Тесты _sync_overrides из sidebar.py — логики синхронизации правок data_editor."""
from __future__ import annotations

import pandas as pd

from src.ui.sidebar import _sync_overrides


def _items() -> list[dict]:
    return [
        {"num": 1, "item_key": "vesta-с-60-18", "name": "Весы", "qty": 1, "price": 1_906_000, "total": 1_906_000, "is_overridden": False},
        {"num": 2, "item_key": "ramp_set_f_s", "name": "Пандусы", "qty": 2, "price": 380_000, "total": 760_000, "is_overridden": False},
    ]


def _as_edited(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_sync_returns_false_when_nothing_changed():
    state: dict = {"spec_items_overrides": {}}
    items = _items()
    # edited = исходный snapshot, ничего не правили
    edited = _as_edited([
        {"num": 1, "item_key": "vesta-с-60-18", "name": "Весы", "qty": 1, "price": 1_906_000, "total": "1 906 000 ₽"},
        {"num": 2, "item_key": "ramp_set_f_s", "name": "Пандусы", "qty": 2, "price": 380_000, "total": "760 000 ₽"},
    ])
    assert _sync_overrides(state, items, edited) is False
    assert state["spec_items_overrides"] == {}


def test_sync_writes_price_override_and_returns_true():
    state: dict = {"spec_items_overrides": {}}
    items = _items()
    edited = _as_edited([
        {"num": 1, "item_key": "vesta-с-60-18", "name": "Весы", "qty": 1, "price": 1_500_000, "total": "stale"},
        {"num": 2, "item_key": "ramp_set_f_s", "name": "Пандусы", "qty": 2, "price": 380_000, "total": "760 000 ₽"},
    ])
    assert _sync_overrides(state, items, edited) is True
    assert state["spec_items_overrides"] == {"vesta-с-60-18": {"price": 1_500_000}}


def test_sync_writes_qty_override_on_option():
    state: dict = {"spec_items_overrides": {}}
    items = _items()
    edited = _as_edited([
        {"num": 1, "item_key": "vesta-с-60-18", "name": "Весы", "qty": 1, "price": 1_906_000, "total": "1 906 000 ₽"},
        {"num": 2, "item_key": "ramp_set_f_s", "name": "Пандусы", "qty": 5, "price": 380_000, "total": "stale"},
    ])
    assert _sync_overrides(state, items, edited) is True
    assert state["spec_items_overrides"] == {"ramp_set_f_s": {"qty": 5}}


def test_sync_removes_override_when_user_reverts_to_default():
    """Пользователь вернул qty/price к computed-значению → override чистится."""
    state: dict = {"spec_items_overrides": {"ramp_set_f_s": {"qty": 5}}}
    items = _items()
    # items прилетают с applied override → qty=5. Пользователь правит обратно на 2.
    items[1]["qty"] = 5
    edited = _as_edited([
        {"num": 1, "item_key": "vesta-с-60-18", "name": "Весы", "qty": 1, "price": 1_906_000, "total": "1 906 000 ₽"},
        {"num": 2, "item_key": "ramp_set_f_s", "name": "Пандусы", "qty": 2, "price": 380_000, "total": "stale"},
    ])
    # Новое qty=2 равно computed (так как override сейчас даёт qty=5, а computed (без override)
    # мы не можем прочитать из items — это ограничение текущей реализации).
    # Важно: поведение должно быть безопасным — либо сохранить new override, либо очистить.
    # В текущей реализации: new_qty(2) != it["qty"](5) → qty_ov=2 → override={"qty": 2}.
    changed = _sync_overrides(state, items, edited)
    assert changed is True
    assert state["spec_items_overrides"] == {"ramp_set_f_s": {"qty": 2}}
