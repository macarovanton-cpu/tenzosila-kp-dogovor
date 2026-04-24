"""Единый формат денежных сумм."""
from __future__ import annotations


def fmt_rub(amount: int | float) -> str:
    """Форматирует сумму как '1 234 567 ₽' (неразрывный пробел как разделитель тысяч)."""
    return f"{int(amount):,}".replace(",", "\u00A0") + "\u00A0₽"
