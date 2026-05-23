"""Сценарий Кирова: ВЕСТА-ФЛ-80-18, без ОРИОН и фундамента.

Два варианта: с поверкой и без — для покрытия обоих источников истины
(спека пользователя 1.6 vs. scripts/generate_test_kp.py reference).
"""
from __future__ import annotations

from . import Scenario, ScenarioOption


_BASE_OPTIONS = (
    ScenarioOption("Монтаж", "Монтаж и пусконаладка автовесов"),
    ScenarioOption("Доставка", "Доставка весов до объекта"),
)

KIROVA_WITH_VERIFICATION = Scenario(
    slug="kirova_with_verification",
    client_name="АО «Совхоз имени Кирова»",
    kp_number="47215-A",
    model_line="ФЛ",
    model_max=80,
    model_length=18,
    dual_range=True,
    options=_BASE_OPTIONS + (
        ScenarioOption("Поверка", "Первичная поверка"),
    ),
    payment_preset_label="50% / 50%",
    verification_doer="Подрядчик",
)

KIROVA_WITHOUT_VERIFICATION = Scenario(
    slug="kirova_without_verification",
    client_name="АО «Совхоз имени Кирова»",
    kp_number="47215-B",
    model_line="ФЛ",
    model_max=80,
    model_length=18,
    dual_range=True,
    options=_BASE_OPTIONS,
    payment_preset_label="50% / 50%",
)
