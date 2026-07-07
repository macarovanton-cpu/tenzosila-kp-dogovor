"""Валидация реквизитов договора: жёсткие errors (блокируют генерацию) и warnings.

Чистая функция без Streamlit. Проверяет результат парсинга/ручного ввода,
данные НЕ восстанавливает — только флагает проблемы для менеджера.
"""
from __future__ import annotations

from src.contracts.requisites_parser import _valid_inn


def validate_requisites(fields: dict[str, str]) -> tuple[list[str], list[str]]:
    """Вернуть (errors, warnings). errors блокируют «Сгенерировать договор»."""
    errors: list[str] = []
    warnings: list[str] = []

    def _val(key: str) -> str:
        return str(fields.get(key, "") or "").strip()

    name = _val("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ")
    inn = _val("ЗАКАЗЧИК_ИНН")
    rs = _val("ЗАКАЗЧИК_РС")
    ks = _val("ЗАКАЗЧИК_КС")
    bik = _val("ЗАКАЗЧИК_БИК")

    # --- ERRORS ---
    if not name:
        errors.append("Не заполнено наименование заказчика")
    if not inn:
        errors.append("Не заполнен ИНН заказчика")
    if not rs:
        errors.append("Не заполнен расчётный счёт")

    if inn and not (inn.isdigit() and _valid_inn(inn)):
        errors.append(
            "ИНН не проходит проверку контрольной суммы — проверьте цифры"
        )
    if rs and not (rs.isdigit() and len(rs) == 20):
        errors.append("Расчётный счёт должен состоять из 20 цифр")
    if ks and not (ks.isdigit() and len(ks) == 20):
        errors.append("Корреспондентский счёт должен состоять из 20 цифр")
    if bik and not (bik.isdigit() and len(bik) == 9):
        errors.append("БИК должен состоять из 9 цифр")

    # --- WARNINGS ---
    warn_empty = [
        ("ЗАКАЗЧИК_БИК", "Не заполнен БИК"),
        ("ЗАКАЗЧИК_КС", "Не заполнен корреспондентский счёт"),
        ("ЗАКАЗЧИК_БАНК", "Не заполнен банк"),
        ("ЗАКАЗЧИК_АДРЕС_ЮР", "Не заполнен юридический адрес"),
        ("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "Не заполнено ФИО руководителя"),
        ("ЗАКАЗЧИК_ОСНОВАНИЕ", "Не заполнено основание полномочий"),
    ]
    for key, message in warn_empty:
        if not _val(key):
            warnings.append(message)

    return errors, warnings
