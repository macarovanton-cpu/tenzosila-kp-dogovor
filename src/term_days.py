"""Сроки исполнения проекта: общий, дефолт по составу, и per-item с vMerge.

Чистая бизнес-логика — без зависимости от Streamlit/state. UI и генератор
DOCX используют этот модуль через функции верхнего уровня.

Параллельная модель сроков:
    T_фиксированных = T_монтаж (4) + T_поверка (1) + T_доставка (1)
                      — каждое слагаемое только если позиция включена и
                        НЕ помечена customer_side.
    T_осталось = T_общий − T_фиксированных
    T_весы = T_фундамент = T_parallel_aux = T_осталось

Если T_осталось ≤ 0 — расчёт невозможен, поднимается TermDaysTooSmallError.
"""
from __future__ import annotations

from typing import Any

# Фиксированные сроки сервисных позиций, рабочих дней
TERM_INSTALL: int = 4
TERM_VERIFICATION: int = 1
TERM_DELIVERY: int = 1

# (prefix-or-exact-key, role) — порядок матчинга важен. Точные ключи и
# длинные префиксы должны идти раньше коротких.
TERM_ROLE_MAP: list[tuple[str, str]] = [
    ("install_default",        "install"),
    ("verification_default",   "verification"),
    ("delivery_default",       "delivery"),
    ("foundation_lite_",       "foundation"),
    ("foundation_std_",        "foundation"),
    ("foundation_s_f_",        "foundation"),
    ("foundation_supervision", "foundation"),
    ("canopy_turnkey_",        "parallel_aux"),
    ("construction_works_",    "parallel_aux"),
    ("concrete_base_on_frame", "parallel_aux"),
    ("ramp_set_",              "scales_aux"),
    ("frame_",                 "scales_aux"),
    ("fence_",                 "scales_aux"),
    ("hatches_",               "scales_aux"),
    ("embedded_parts",         "scales_aux"),
    ("rubber_",                "scales_aux"),
    ("factory_calibration",    "scales_aux"),
    ("orion_",                 "scales_aux"),
]


def classify_term_role(item_key: str) -> str:
    """item_key → роль для расчёта срока и vMerge.

    Возможные роли: scales_main, scales_aux, parallel_aux, foundation,
    install, verification, delivery.
    """
    if item_key.startswith("vesta-"):
        return "scales_main"
    for prefix, role in TERM_ROLE_MAP:
        if item_key == prefix or item_key.startswith(prefix):
            return role
    return "scales_aux"


class TermDaysTooSmallError(ValueError):
    """T_общий ≤ T_фиксированных — невозможно уместить производство.

    Атрибут ``details``: dict с разбивкой ({"total", "min", "install",
    "verification", "delivery"}) для UI-сообщения.
    """

    def __init__(self, details: dict[str, int]) -> None:
        self.details = details
        super().__init__(
            f"term_days_too_small: total={details['total']} "
            f"<= fixed={details['min']} (install={details['install']}, "
            f"verification={details['verification']}, "
            f"delivery={details['delivery']})"
        )


def calculate_default_term_days(spec_items: list[dict]) -> int:
    """Дефолтный срок проекта по составу спецификации.

    База 20 + 5 (монтаж/поверка) + 5 (ОРИОН) + 10 (фундамент).
    Доставка и опции (рамы/ограждения/навес/...) на срок не влияют.
    """
    days = 20
    has_install_or_verification = False
    has_orion = False
    has_foundation = False
    for it in spec_items:
        key = it.get("item_key", "")
        if key in ("install_default", "verification_default"):
            has_install_or_verification = True
        if key.startswith("orion_"):
            has_orion = True
        if key.startswith("foundation_"):
            has_foundation = True
    if has_install_or_verification:
        days += 5
    if has_orion:
        days += 5
    if has_foundation:
        days += 10
    return days


def resolve_term_days(spec_items: list[dict], state: dict) -> int:
    """Срок проекта: ручной из state (если задан), иначе дефолт по составу."""
    manual = state.get("total_term_days")
    if manual is not None:
        return int(manual)
    return calculate_default_term_days(spec_items)


def _is_active_service(item: dict[str, Any]) -> bool:
    """Сервисная позиция «активна» (вычитается из общего срока) только если
    НЕ помечена customer_side."""
    return not bool(item.get("customer_side", False))


def calculate_term_days_per_item(
    spec_items: list[dict],
    total_days: int,
) -> list[dict[str, str | None]]:
    """Срок исполнения по каждой позиции спецификации.

    Возвращает список той же длины и в том же порядке, что spec_items.
    Каждый элемент:
        {"item_key": str, "value": str, "merge": "restart" | "continue" | None}

    - value: текст для подстановки в ячейку («24», «4», «», ...).
    - merge: маркер vMerge для пост-процессинга DOCX.

    Бросает TermDaysTooSmallError если T_общий ≤ T_фиксированных.
    """
    install_days = 0
    verification_days = 0
    delivery_days = 0
    for it in spec_items:
        role = classify_term_role(it.get("item_key", ""))
        if not _is_active_service(it):
            continue
        if role == "install":
            install_days = TERM_INSTALL
        elif role == "verification":
            verification_days = TERM_VERIFICATION
        elif role == "delivery":
            delivery_days = TERM_DELIVERY

    fixed = install_days + verification_days + delivery_days
    if total_days <= fixed:
        raise TermDaysTooSmallError({
            "total": int(total_days),
            "min": int(fixed) + 1,  # минимум, чтобы T_осталось >= 1
            "install": install_days,
            "verification": verification_days,
            "delivery": delivery_days,
        })

    remaining = int(total_days) - fixed

    result: list[dict[str, str | None]] = []
    in_scales_merge = False
    for it in spec_items:
        key = it.get("item_key", "")
        role = classify_term_role(key)
        customer_side = bool(it.get("customer_side", False))

        if role == "scales_main":
            result.append({
                "item_key": key,
                "value": str(remaining),
                "merge": "restart",
            })
            in_scales_merge = True
        elif role == "scales_aux":
            if in_scales_merge:
                result.append({
                    "item_key": key, "value": "", "merge": "continue",
                })
            else:
                # Нет предшествующих весов в merge-группе — открываем
                # новую (одиночная ячейка с T_осталось).
                result.append({
                    "item_key": key,
                    "value": str(remaining),
                    "merge": "restart",
                })
                in_scales_merge = True
        elif role == "parallel_aux":
            result.append({
                "item_key": key,
                "value": str(remaining),
                "merge": None,
            })
            in_scales_merge = False
        elif role == "foundation":
            result.append({
                "item_key": key,
                "value": str(remaining),
                "merge": None,
            })
            in_scales_merge = False
        elif role == "install":
            result.append({
                "item_key": key,
                "value": "" if customer_side else str(TERM_INSTALL),
                "merge": None,
            })
            in_scales_merge = False
        elif role == "verification":
            result.append({
                "item_key": key,
                "value": "" if customer_side else str(TERM_VERIFICATION),
                "merge": None,
            })
            in_scales_merge = False
        elif role == "delivery":
            result.append({
                "item_key": key,
                "value": "" if customer_side else str(TERM_DELIVERY),
                "merge": None,
            })
            in_scales_merge = False
        else:  # неизвестная роль — безопасно: пустое значение
            result.append({
                "item_key": key, "value": "", "merge": None,
            })
            in_scales_merge = False

    return result
