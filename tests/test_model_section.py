"""Тесты UI-секции выбора модели."""
from __future__ import annotations

from src.state import on_platform_width_change
from src.pricing import SliderParams
from src.ui import model_section


def test_platform_width_control_uses_segmented_control(monkeypatch):
    """Ширина платформы выбирается segmented_control с тремя вариантами."""
    calls = []

    def fake_segmented_control(
        label: str,
        options: list[float],
        *,
        key: str,
        on_change,
        format_func,
        help: str,
    ) -> float:
        calls.append({
            "label": label,
            "options": options,
            "key": key,
            "on_change": on_change,
            "help": help,
        })
        assert format_func(3.5) == "3.5м"
        return 3.5

    monkeypatch.setattr(model_section.st, "segmented_control", fake_segmented_control)

    model_section._render_platform_width_control()

    assert calls == [{
        "label": "Ширина платформы",
        "options": [3.0, 3.5, 4.0],
        "key": "platform_width_m",
        "on_change": on_platform_width_change,
        "help": "Нестандартная ширина масштабирует цену модели пропорционально 3.0 м",
    }]


def test_model_price_slider_passes_platform_width_to_pricing(monkeypatch):
    """Ценовой виджет модели рассчитывает параметры с учётом выбранной ширины."""
    state = {
        "model_id": "vesta-с-60-18",
        "platform_width_m": 4.0,
        "model_price": None,
    }
    calls = []

    def fake_get_model_slider_params(price: dict, *, platform_width_m: float):
        calls.append({"price": price, "platform_width_m": platform_width_m})
        return SliderParams(
            min_v=1_000,
            max_v=10_000,
            default_v=5_000,
            step=1_000,
            dealer=1_000,
            retail=5_000,
            is_on_request=False,
            dealer_is_synthetic=False,
            allow_customer_value=False,
        )

    monkeypatch.setattr(
        model_section, "get_model_slider_params", fake_get_model_slider_params
    )
    monkeypatch.setattr(model_section.st, "number_input", lambda *a, **k: 5_000)
    monkeypatch.setattr(model_section.st, "caption", lambda *a, **k: None)

    price = {"retail": 1_906_544, "dealer_ru": 1_754_021}
    model_section._render_model_price_slider(state, price)

    assert calls == [{"price": price, "platform_width_m": 4.0}]
    assert state["model_price"] == 5_000
