"""Сроки исполнения проекта: per-role дефолты и пропорциональный скейл.

Чистая бизнес-логика, без зависимости от Streamlit/state.

Модель:
    TERM_DAYS_DEFAULTS — дефолтный срок по каждой роли.
    VARIABLE_ROLES — роли, которые скейлятся пропорционально при правке T_общий.
    FIXED_ROLES   — сервисные позиции (монтаж/доставка/поверка), срок не меняется.

T_default = сумма дефолтов уникальных активных ролей. Если T_общий ≠ T_default —
вариативные скейлятся пропорционально:

    variable_target = T_общий − T_фикс
    scaled[r] = max(1, round(default[r] * variable_target / variable_default_total))
    дельту округления добавляем к scales (или к первой активной вариативной).

Минимум T_общий = T_фикс + len(active_variable). Меньше → TermDaysTooSmallError.

Опции весов (frame_, fence_, ramp_, hatches_, embedded_parts, rubber_,
factory_calibration, cable_, extra_, …) → role=None: своей строки сроков
нет, в DOCX сливаются по vMerge с весами.
"""
from __future__ import annotations

from typing import Any

# Дефолтные сроки по ролям, рабочих дней
TERM_DAYS_DEFAULTS: dict[str, int] = {
    "scales": 20,
    "orion": 5,
    "foundation": 10,
    "canopy": 25,
    "install": 3,
    "delivery": 1,
    "verification": 1,
}

# Вариативные роли — скейлятся пропорционально при правке T_общий
VARIABLE_ROLES: frozenset[str] = frozenset({"scales", "orion", "foundation", "canopy"})

# Фиксированные роли — сервисные позиции, срок не меняется
FIXED_ROLES: frozenset[str] = frozenset({"install", "delivery", "verification"})

# Куда направить дельту округления (приоритет, если scales не активна)
_VARIABLE_DELTA_PRIORITY: tuple[str, ...] = ("scales", "orion", "foundation", "canopy")

# (prefix-or-exact-key, role) — порядок матчинга важен
_ROLE_RULES: list[tuple[str, str]] = [
    ("install_default",        "install"),
    ("verification_default",   "verification"),
    ("delivery_default",       "delivery"),
    ("foundation_lite_",       "foundation"),
    ("foundation_std_",        "foundation"),
    ("foundation_s_f_",        "foundation"),
    ("foundation_supervision", "foundation"),
    ("construction_works_",    "foundation"),
    ("concrete_base_on_frame", "foundation"),
    ("canopy_turnkey_",        "canopy"),
    ("orion_",                 "orion"),
]


def resolve_term_role(item_key: str) -> str | None:
    """item_key → роль для расчёта срока. None — опция весов (vMerge с scales)."""
    if not item_key:
        return None
    if item_key.startswith("vesta-"):
        return "scales"
    for prefix, role in _ROLE_RULES:
        if item_key == prefix or item_key.startswith(prefix):
            return role
    return None


class TermDaysTooSmallError(ValueError):
    """T_общий ниже минимума — невозможно уместить в проект.

    Атрибут ``details``: dict с разбивкой ({"total","min","fixed_total",
    "variable_count","install","verification","delivery"}) для UI.
    """

    def __init__(self, details: dict[str, int]) -> None:
        self.details = details
        super().__init__(
            f"term_days_too_small: total={details['total']} < "
            f"min={details['min']} (fixed={details['fixed_total']}, "
            f"variable_count={details['variable_count']})"
        )


def _is_active(item: dict[str, Any]) -> bool:
    """Сервисная позиция активна, если НЕ помечена customer_side."""
    return not bool(item.get("customer_side", False))


def _collect_active_pairs(spec_items: list[dict]) -> list[tuple[str, str | None]]:
    """item_key → role, исключая customer_side для FIXED_ROLES."""
    pairs: list[tuple[str, str | None]] = []
    for it in spec_items:
        key = it.get("item_key", "")
        role = resolve_term_role(key)
        if role in FIXED_ROLES and not _is_active(it):
            continue
        pairs.append((key, role))
    return pairs


def _role_breakdown(
    spec_items: list[dict],
) -> tuple[list[tuple[str, str | None]], set[str], set[str], set[str]]:
    pairs = _collect_active_pairs(spec_items)
    unique_roles = {r for _, r in pairs if r is not None}
    return (
        pairs,
        unique_roles,
        unique_roles & VARIABLE_ROLES,
        unique_roles & FIXED_ROLES,
    )


def calculate_term_days_per_item(
    spec_items: list[dict],
    total_days_user: int | None = None,
) -> tuple[dict[str, int | None], int]:
    """Сроки по каждой позиции.

    Возвращает (item_key → days|None, total_days).

    - days|None: число для подстановки в ячейку DOCX. None = опция весов
      (рама/ограждение/…), сливается с весами по vMerge.
    - total_days: сумма по уникальным активным ролям (после скейла).

    Если total_days_user задан и < min_total — TermDaysTooSmallError.
    """
    pairs, unique_roles, active_variable, active_fixed = _role_breakdown(spec_items)

    fixed_total = sum(TERM_DAYS_DEFAULTS[r] for r in active_fixed)
    variable_default_total = sum(TERM_DAYS_DEFAULTS[r] for r in active_variable)
    t_default = fixed_total + variable_default_total

    use_default = total_days_user is None or int(total_days_user) == t_default

    if use_default:
        role_to_days: dict[str, int] = {r: TERM_DAYS_DEFAULTS[r] for r in unique_roles}
        total = t_default
    else:
        total_user = int(total_days_user)
        min_total = fixed_total + len(active_variable)
        if total_user < min_total:
            raise TermDaysTooSmallError({
                "total": total_user,
                "min": min_total,
                "fixed_total": fixed_total,
                "variable_count": len(active_variable),
                "install": (
                    TERM_DAYS_DEFAULTS["install"] if "install" in active_fixed else 0
                ),
                "verification": (
                    TERM_DAYS_DEFAULTS["verification"]
                    if "verification" in active_fixed else 0
                ),
                "delivery": (
                    TERM_DAYS_DEFAULTS["delivery"] if "delivery" in active_fixed else 0
                ),
            })

        role_to_days = {r: TERM_DAYS_DEFAULTS[r] for r in active_fixed}
        if active_variable and variable_default_total > 0:
            variable_target = total_user - fixed_total
            scaled: dict[str, int] = {}
            for r in active_variable:
                raw = TERM_DAYS_DEFAULTS[r] * variable_target / variable_default_total
                scaled[r] = max(1, round(raw))
            delta = variable_target - sum(scaled.values())
            if delta != 0:
                for r in _VARIABLE_DELTA_PRIORITY:
                    if r in scaled:
                        scaled[r] = max(1, scaled[r] + delta)
                        break
            role_to_days.update(scaled)
        total = sum(role_to_days.values())

    item_to_days: dict[str, int | None] = {}
    for key, role in pairs:
        item_to_days[key] = role_to_days.get(role) if role else None

    return item_to_days, total


def calculate_default_term_days(spec_items: list[dict]) -> int:
    """Дефолтный срок по составу = T_default из новой модели."""
    _, total = calculate_term_days_per_item(spec_items, total_days_user=None)
    return total


def resolve_term_days(spec_items: list[dict], state: dict) -> int:
    """Срок проекта: ручной из state (если задан), иначе дефолт по составу."""
    manual = state.get("total_term_days")
    if manual is not None:
        return int(manual)
    return calculate_default_term_days(spec_items)


def calculate_min_term_days(spec_items: list[dict]) -> int:
    """Минимально допустимый T_общий для текущего состава.

    = T_фикс_активных + len(active_variable). При len(active_variable)==0 =
    T_фикс_активных (если ничего нет — 0).
    """
    _, _, active_variable, active_fixed = _role_breakdown(spec_items)
    fixed_total = sum(TERM_DAYS_DEFAULTS[r] for r in active_fixed)
    return fixed_total + len(active_variable)
