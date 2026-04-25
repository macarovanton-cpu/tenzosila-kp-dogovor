"""Сценарий Гипсобетон: ВЕСТА-С-80-18, dual_range, фундамент, ОРИОН."""
from __future__ import annotations

from . import Scenario, ScenarioOption


GIPSOBETON = Scenario(
    slug="gipsobeton",
    client_name="АО «Гипсобетон»",
    kp_number="47141",
    model_line="С",
    model_max=80,
    model_length=18,
    dual_range=True,
    options=(
        ScenarioOption("Фундамент", "Фундамент под ВЕСТА-С/Ф/П, 18м"),
        ScenarioOption(
            "ПАК ОРИОН",
            "ПАК ОРИОН Стандарт+ (оборудование + шеф-монтаж)",
        ),
        ScenarioOption("Монтаж", "Монтаж и пусконаладка автовесов"),
        ScenarioOption("Доставка", "Доставка весов до объекта"),
        ScenarioOption("Поверка", "Первичная поверка"),
    ),
    payment_preset_label="Расщеплённая по позициям",
    verification_doer="Подрядчик",
)
