"""Единый формат чисел и денежных сумм."""
from __future__ import annotations


def fmt_rub(amount: int | float) -> str:
    """Форматирует сумму как '1 234 567 ₽' (неразрывный пробел как разделитель тысяч)."""
    return f"{int(amount):,}".replace(",", "\u00A0") + "\u00A0₽"


def fmt_int_spaces(n: int | float) -> str:
    """Форматирует число с обычным пробелом: 2450000 → '2 450 000'.

    Для DOCX используем обычный пробел (не nbsp) — Word корректно отрисовывает.
    """
    return f"{int(n):,}".replace(",", " ")


def pluralize(n: int, forms: tuple[str, str, str]) -> str:
    """Русское склонение по числу: pluralize(15, ('день','дня','дней')) → '15 дней'.

    forms = (для 1, для 2-4, для 5-20).
    """
    n_abs = abs(int(n))
    if n_abs % 10 == 1 and n_abs % 100 != 11:
        return f"{n_abs} {forms[0]}"
    if 2 <= n_abs % 10 <= 4 and (n_abs % 100 < 10 or n_abs % 100 >= 20):
        return f"{n_abs} {forms[1]}"
    return f"{n_abs} {forms[2]}"
