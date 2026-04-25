"""Сценарий Stress-max: ВЕСТА-С-100-24, dual_range, все опции, custom-оплата."""
from __future__ import annotations

from . import Scenario, ScenarioOption


_CUSTOM_PAYMENT_TEXT = (
    "— 30% предоплаты в течение 10 банковских дней с момента подписания.\n"
    "— 40% после готовности фундамента.\n"
    "— 30% по факту запуска весов и подписания акта приёмки."
)

STRESS_MAX = Scenario(
    slug="stress_max",
    client_name="ООО «Стресс-тест Макс»",
    kp_number="99999",
    model_line="С",
    model_max=100,
    model_length=24,
    dual_range=True,
    options=(
        ScenarioOption("Фундамент", "Фундамент под ВЕСТА-С/Ф/П, 24м"),
        ScenarioOption(
            "ПАК ОРИОН",
            "ПАК ОРИОН Автоматика+ (оборудование + шеф-монтаж)",
        ),
        ScenarioOption("Монтаж", "Монтаж и пусконаладка автовесов"),
        ScenarioOption("Доставка", "Доставка весов до объекта"),
        ScenarioOption("Поверка", "Первичная поверка"),
        ScenarioOption("Ограждение", "Ограждение НОРМА высота 200мм, 24м"),
        ScenarioOption("Рама", "Рама под весы ВЕСТА-С(Ф)/ФЛ(СЛ), 24м"),
        # «Навес под ключ для ВЕСТА, 24м» — on_request:true (data_loader),
        # чекбокс в UI задизейблен. См. docs/STATUS.md, открытый вопрос #4.
    ),
    payment_preset_label="Индивидуальная",
    payment_custom_text=_CUSTOM_PAYMENT_TEXT,
    verification_doer="Подрядчик",
)
