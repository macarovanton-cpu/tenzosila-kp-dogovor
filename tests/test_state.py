"""Тесты инициализации и колбэков состояния КП."""
from __future__ import annotations

from src import state as state_module


def test_platform_width_default_is_standard_3m():
    """По умолчанию ширина платформы стандартная — 3.0 м."""
    state = state_module.initial_state()

    assert state["platform_width_m"] == 3.0


def test_platform_width_change_resets_model_price_and_price_override(monkeypatch):
    """Смена ширины сбрасывает цену модели и только price override модели."""
    fake_state = {
        "model_id": "vesta-с-60-18",
        "model_price": 1_906_000,
        "spec_items_overrides": {
            "vesta-с-60-18": {"price": 1_800_000, "qty": 2},
            "install_default": {"price": 200_000},
        },
    }
    monkeypatch.setattr(state_module.st, "session_state", fake_state)

    state_module.on_platform_width_change()

    assert fake_state["model_price"] is None
    assert fake_state["spec_items_overrides"]["vesta-с-60-18"] == {"qty": 2}
    assert fake_state["spec_items_overrides"]["install_default"] == {"price": 200_000}


def test_platform_width_change_removes_empty_model_override(monkeypatch):
    """Если override модели содержал только price, он удаляется полностью."""
    fake_state = {
        "model_id": "vesta-с-60-18",
        "model_price": 1_906_000,
        "spec_items_overrides": {
            "vesta-с-60-18": {"price": 1_800_000},
        },
    }
    monkeypatch.setattr(state_module.st, "session_state", fake_state)

    state_module.on_platform_width_change()

    assert fake_state["model_price"] is None
    assert fake_state["spec_items_overrides"] == {}
