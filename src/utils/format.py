"""Единый формат чисел и денежных сумм."""
from __future__ import annotations

import re

_PHONE_RE = re.compile(
    r"^\+7[\s-]*(\d{3})[\s-]?(\d{3})[\s-]?(\d{2})[\s-]?(\d{2})$"
)


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


def format_phone(raw: str) -> str:
    """'+7 903 651-85-77' → '+7 (903) 651-85-77'.

    При несоответствии шаблону возвращает raw без изменений.
    """
    if not raw:
        return ""
    m = _PHONE_RE.match(raw.strip())
    if not m:
        return raw
    return f"+7 ({m.group(1)}) {m.group(2)}-{m.group(3)}-{m.group(4)}"
