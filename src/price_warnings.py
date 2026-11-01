"""Предупреждения о свободной цене: ниже дилерской и вне коридора прайса."""
from __future__ import annotations

from src.pricing import SliderParams
from src.utils.format import fmt_int_spaces


def price_warnings(name: str, value: int, params: SliderParams) -> list[str]:
    """Вернуть тексты предупреждений; условия независимы, может быть два сразу.

    price_below_dealer — value < dealer (не проверяется, если dealer is None);
    price_out_of_corridor — value вне min_v…max_v.
    """
    result: list[str] = []
    if params.dealer is not None and value < params.dealer:
        result.append(
            f"Цена «{name}» {fmt_int_spaces(value)} ₽ ниже дилерской "
            f"{fmt_int_spaces(params.dealer)} ₽."
        )
    if not params.min_v <= value <= params.max_v:
        result.append(
            f"Цена «{name}» {fmt_int_spaces(value)} ₽ вне коридора "
            f"{fmt_int_spaces(params.min_v)}–{fmt_int_spaces(params.max_v)} ₽."
        )
    return result
