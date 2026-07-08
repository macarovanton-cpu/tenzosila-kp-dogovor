"""Валидация реквизитов договора: жёсткие errors (блокируют генерацию) и warnings.

Чистая функция без Streamlit. Проверяет результат парсинга/ручного ввода,
данные НЕ восстанавливает — только флагает проблемы для менеджера.
"""
from __future__ import annotations

import re

from src.contracts.requisites_parser import _valid_inn

# КПП: 4 цифры (код ИФНС) + код причины (цифры или заглавные латинские) + 3 цифры
_KPP_RE = re.compile(r"^\d{4}[\dA-Z]{2}\d{3}$")


def _valid_ogrn(digits: str) -> bool:
    """Проверить контрольную цифру ОГРН (13 цифр) или ОГРНИП (15 цифр).

    13-значный: остаток первых 12 цифр по mod 11, младший разряд = 13-я цифра.
    15-значный: остаток первых 14 цифр по mod 13, младший разряд = 15-я цифра.
    """
    if not digits.isdigit():
        return False
    if len(digits) == 13:
        return int(digits[:12]) % 11 % 10 == int(digits[12])
    if len(digits) == 15:
        return int(digits[:14]) % 13 % 10 == int(digits[14])
    return False


# Веса контрольного ключа счёта (23 позиции): префикс(3) + номер счёта(20)
_ACCOUNT_WEIGHTS = [7, 1, 3] * 7 + [7, 1]


def _valid_account(account: str, bik: str) -> bool:
    """Проверить контрольный ключ расчётного счёта (20 цифр) вместе с БИК.

    Строка для проверки (23 цифры) = префикс + account, где префикс для
    расчётного счёта — последние 3 цифры БИК (bik[6:9]). Валиден, если
    взвешенная по _ACCOUNT_WEIGHTS сумма цифр кратна 10.
    Предполагает, что длины уже проверены (account 20, bik 9, обе цифры).
    """
    if not (account.isdigit() and bik.isdigit()):
        return False
    digits = bik[6:9] + account
    checksum = sum(int(d) * w for d, w in zip(digits, _ACCOUNT_WEIGHTS)) % 10
    return checksum == 0


def validate_requisites(fields: dict[str, str]) -> tuple[list[str], list[str]]:
    """Вернуть (errors, warnings). errors блокируют «Сгенерировать договор»."""
    errors: list[str] = []
    warnings: list[str] = []

    def _val(key: str) -> str:
        return str(fields.get(key, "") or "").strip()

    name = _val("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ")
    inn = _val("ЗАКАЗЧИК_ИНН")
    ogrn = _val("ЗАКАЗЧИК_ОГРН")
    kpp = _val("ЗАКАЗЧИК_КПП")
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

    # Контрольный ключ р/с считается вместе с БИК — только при валидных длинах
    # обоих (нет опорного БИК — не считаем, длина р/с проверена выше).
    if (
        rs and bik
        and rs.isdigit() and len(rs) == 20
        and bik.isdigit() and len(bik) == 9
        and not _valid_account(rs, bik)
    ):
        errors.append(
            "Расчётный счёт не проходит проверку контрольного ключа с БИК — "
            "проверьте цифры"
        )

    if ogrn and not _valid_ogrn(ogrn):
        errors.append(
            "ОГРН/ОГРНИП не проходит проверку контрольной цифры — проверьте цифры"
        )

    # Сверка БИК ↔ к/с: последние 3 цифры к/с (в Банке России) совпадают с БИК
    if (
        bik and ks
        and bik.isdigit() and len(bik) == 9
        and ks.isdigit() and len(ks) == 20
        and ks[-3:] != bik[-3:]
    ):
        errors.append(
            "БИК и корреспондентский счёт не согласованы: последние 3 цифры "
            "к/с должны совпадать с последними 3 цифрами БИК"
        )

    # --- WARNINGS ---
    # Соответствие форм: ИНН 10 знаков (юрлицо) ↔ ОГРН 13, ИНН 12 (ИП) ↔ ОГРНИП 15
    if inn.isdigit() and ogrn.isdigit():
        if len(inn) == 10 and len(ogrn) == 15:
            warnings.append(
                "ИНН юрлица (10 цифр) при ОГРНИП (15 цифр) — проверьте форму контрагента"
            )
        elif len(inn) == 12 and len(ogrn) == 13:
            warnings.append(
                "ИНН ИП (12 цифр) при ОГРН юрлица (13 цифр) — проверьте форму контрагента"
            )

    if kpp and not _KPP_RE.match(kpp):
        warnings.append(
            "КПП не соответствует формату (9 знаков, позиции 5-6 — код причины)"
        )

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
