"""Тесты term_days: per-role дефолты, пропорциональный скейл, валидация."""
from __future__ import annotations

import pytest

from src.term_days import (
    TermDaysTooSmallError,
    calculate_default_term_days,
    calculate_min_term_days,
    calculate_term_days_per_item,
    resolve_term_role,
)


def _item(key: str, customer_side: bool = False) -> dict:
    return {"item_key": key, "customer_side": customer_side}


def test_full_set_default_no_user_override() -> None:
    """Все 4 вариативных + 3 фикс. Дефолтный T_default = 65."""
    spec = [
        _item("vesta-с-80-18"),
        _item("frame_18"),
        _item("fence_norma_18"),
        _item("orion_standard"),
        _item("foundation_s_f_18"),
        _item("canopy_turnkey_18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, total_days_user=None)
    assert days["vesta-с-80-18"] == 20
    assert days["frame_18"] is None  # опция весов
    assert days["fence_norma_18"] is None
    assert days["orion_standard"] == 5
    assert days["foundation_s_f_18"] == 10
    assert days["canopy_turnkey_18"] == 25
    assert days["install_default"] == 3
    assert days["delivery_default"] == 1
    assert days["verification_default"] == 1
    assert total == 65


def test_no_foundation_default() -> None:
    """scales+orion+install+delivery+verification → 20+5+3+1+1 = 30."""
    spec = [
        _item("vesta-с-80-18"),
        _item("orion_standard"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, None)
    assert total == 30
    assert days["orion_standard"] == 5
    assert days["install_default"] == 3


def test_no_orion_default() -> None:
    """scales+foundation+install+delivery+verification → 20+10+3+1+1 = 35."""
    spec = [
        _item("vesta-с-80-18"),
        _item("foundation_s_f_18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    _, total = calculate_term_days_per_item(spec, None)
    assert total == 35


def test_scales_only_with_services_default() -> None:
    """scales+install+delivery+verification → 20+3+1+1 = 25."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, None)
    assert total == 25
    assert days["vesta-с-80-18"] == 20


def test_user_override_up_proportional_scale() -> None:
    """T_default=40, user=50. fixed=5, variable_target=45, variable_default=35.
    scales=26, foundation=13, orion=6. Сумма = 50.
    """
    spec = [
        _item("vesta-с-80-18"),
        _item("foundation_s_f_18"),
        _item("orion_standard"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, total_days_user=50)
    assert days["vesta-с-80-18"] == 26
    assert days["foundation_s_f_18"] == 13
    assert days["orion_standard"] == 6
    assert days["install_default"] == 3
    assert days["delivery_default"] == 1
    assert days["verification_default"] == 1
    assert total == 50


def test_user_override_down_proportional_scale() -> None:
    """T_default=40, user=30. variable_target=25, variable_default=35.
    scales=14, foundation=7, orion=4. Сумма = 30.
    """
    spec = [
        _item("vesta-с-80-18"),
        _item("foundation_s_f_18"),
        _item("orion_standard"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, total_days_user=30)
    assert days["vesta-с-80-18"] == 14
    assert days["foundation_s_f_18"] == 7
    assert days["orion_standard"] == 4
    assert total == 30


def test_user_override_at_minimum() -> None:
    """min_total = fixed_total + len(active_variable). Для scales+install+delivery+verification: 5+1=6."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, total_days_user=6)
    assert days["vesta-с-80-18"] == 1
    assert days["install_default"] == 3
    assert days["delivery_default"] == 1
    assert days["verification_default"] == 1
    assert total == 6


def test_user_override_below_minimum_raises() -> None:
    """user < min_total → TermDaysTooSmallError с разбивкой."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    with pytest.raises(TermDaysTooSmallError) as exc_info:
        calculate_term_days_per_item(spec, total_days_user=4)
    d = exc_info.value.details
    assert d["total"] == 4
    assert d["min"] == 6
    assert d["fixed_total"] == 5
    assert d["variable_count"] == 1
    assert d["install"] == 3
    assert d["delivery"] == 1
    assert d["verification"] == 1


def test_user_override_total_always_matches() -> None:
    """Дельта округления гарантирует sum(role_days) == user_total для любого user >= min."""
    spec = [
        _item("vesta-с-80-18"),
        _item("foundation_s_f_18"),
        _item("orion_standard"),
        _item("canopy_turnkey_18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    for user in (10, 15, 20, 33, 47, 65, 80, 99, 120):
        _, total = calculate_term_days_per_item(spec, total_days_user=user)
        assert total == user, f"user={user}: total={total}"


def test_construction_works_and_foundation_share_role() -> None:
    """construction_works_* и foundation_* обе с role=foundation.

    Обе позиции получают одинаковый T_foundation, в total роль учитывается один раз.
    """
    spec = [
        _item("vesta-с-80-18"),
        _item("construction_works_18"),
        _item("foundation_s_f_18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, None)
    assert days["construction_works_18"] == 10
    assert days["foundation_s_f_18"] == 10
    assert total == 35  # 20+10+3+1+1 (foundation один раз)


def test_customer_side_install_excluded() -> None:
    """customer_side=True для install — позиция не активна, в days_map отсутствует."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default", customer_side=True),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    days, total = calculate_term_days_per_item(spec, None)
    assert "install_default" not in days
    assert total == 22  # 20+1+1


def test_resolve_term_role_typical_keys() -> None:
    """Маппинг item_key → роль для основных ключей."""
    assert resolve_term_role("vesta-с-80-18") == "scales"
    # Опции весов → None
    assert resolve_term_role("frame_18") is None
    assert resolve_term_role("fence_norma_20") is None
    assert resolve_term_role("ramp_set_fl_sl") is None
    assert resolve_term_role("hatches_24") is None
    assert resolve_term_role("embedded_parts") is None
    assert resolve_term_role("rubber_t_6m") is None
    assert resolve_term_role("factory_calibration") is None
    # ОРИОН
    assert resolve_term_role("orion_lite") == "orion"
    assert resolve_term_role("orion_cable_poles") == "orion"
    # Фундамент (включая stone-works/concrete)
    assert resolve_term_role("foundation_s_f_18") == "foundation"
    assert resolve_term_role("foundation_lite_sl_fl_20") == "foundation"
    assert resolve_term_role("foundation_supervision") == "foundation"
    assert resolve_term_role("construction_works_22") == "foundation"
    assert resolve_term_role("concrete_base_on_frame") == "foundation"
    # Навес
    assert resolve_term_role("canopy_turnkey_22") == "canopy"
    # Сервисные
    assert resolve_term_role("install_default") == "install"
    assert resolve_term_role("verification_default") == "verification"
    assert resolve_term_role("delivery_default") == "delivery"
    assert resolve_term_role("") is None


def test_calculate_min_term_days() -> None:
    """min = fixed_total + len(active_variable)."""
    spec = [
        _item("vesta-с-80-18"),
        _item("foundation_s_f_18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    # fixed=3+1+1=5, variable={scales,foundation}=2 → min=7
    assert calculate_min_term_days(spec) == 7


def test_calculate_default_term_days_matches_total() -> None:
    """calculate_default_term_days == total из calculate_term_days_per_item(None)."""
    spec = [
        _item("vesta-с-80-18"),
        _item("foundation_s_f_18"),
        _item("orion_standard"),
        _item("canopy_turnkey_18"),
        _item("install_default"),
        _item("delivery_default"),
        _item("verification_default"),
    ]
    assert calculate_default_term_days(spec) == 65
