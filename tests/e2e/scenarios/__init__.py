"""Сценарии для e2e — общий dataclass и набор фикстур-конфигов."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScenarioOption:
    block_label: str  # текст expander'а в UI («Фундамент», «ПАК ОРИОН», ...)
    option_label: str  # точная подпись чекбокса опции


@dataclass(frozen=True)
class Scenario:
    slug: str  # «gipsobeton», «kirova_with_verif», ...
    client_name: str
    kp_number: str
    model_line: str  # «С», «СЛ», «Ф», «ФЛ», «П»
    model_max: int
    model_length: int
    dual_range: bool
    options: tuple[ScenarioOption, ...] = field(default_factory=tuple)
    payment_preset_label: str = "Расщеплённая по позициям"
    payment_custom_text: str | None = None
    verification_doer: str | None = None  # «Подрядчик» / «Заказчик»

    @property
    def model_full_name(self) -> str:
        return f"ВЕСТА-{self.model_line}-{self.model_max}-{self.model_length}"
