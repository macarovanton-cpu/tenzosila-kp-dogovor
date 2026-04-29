"""Тесты calculate_term_days_per_item — per-item срок исполнения с vMerge."""
from __future__ import annotations

import pytest

from src.term_days import (
    TermDaysTooSmallError,
    calculate_term_days_per_item,
    classify_term_role,
)


def _item(key: str, customer_side: bool = False) -> dict:
    return {"item_key": key, "customer_side": customer_side}


def test_full_set_30_days() -> None:
    """Модель + рама + ограждение + фундамент + монтаж + поверка + доставка.

    Total=30, fixed=4+1+1=6, remaining=24.
    Весы → restart/24, frame/fence → continue/"", фундамент 24, monтаж 4,
    поверка 1, доставка 1.
    """
    spec = [
        _item("vesta-с-80-18"),
        _item("frame_18"),
        _item("fence_norma_18"),
        _item("foundation_s_f_18"),
        _item("install_default"),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    out = calculate_term_days_per_item(spec, 30)
    assert out[0] == {"item_key": "vesta-с-80-18", "value": "24", "merge": "restart"}
    assert out[1] == {"item_key": "frame_18", "value": "", "merge": "continue"}
    assert out[2] == {"item_key": "fence_norma_18", "value": "", "merge": "continue"}
    assert out[3] == {"item_key": "foundation_s_f_18", "value": "24", "merge": None}
    assert out[4] == {"item_key": "install_default", "value": "4", "merge": None}
    assert out[5] == {"item_key": "verification_default", "value": "1", "merge": None}
    assert out[6] == {"item_key": "delivery_default", "value": "1", "merge": None}


def test_no_foundation() -> None:
    """Без фундамента T_осталось не меняется (фундамент шёл параллельно)."""
    spec = [
        _item("vesta-с-80-18"),
        _item("frame_18"),
        _item("install_default"),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    out = calculate_term_days_per_item(spec, 30)
    assert out[0]["value"] == "24"
    assert out[0]["merge"] == "restart"
    assert out[1]["merge"] == "continue"
    # Поверки фундамента в out нет — это ок, фундамент не в spec.


def test_no_verification_in_spec() -> None:
    """Нет позиции «поверка» в спеке → fixed=4+1=5, remaining=25."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("delivery_default"),
    ]
    out = calculate_term_days_per_item(spec, 30)
    assert out[0]["value"] == "25"


def test_no_install_in_spec() -> None:
    """Нет «монтажа» (силами заказчика убрали из спеки) → fixed=1+1=2, remaining=28."""
    spec = [
        _item("vesta-с-80-18"),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    out = calculate_term_days_per_item(spec, 30)
    assert out[0]["value"] == "28"


def test_no_delivery_in_spec() -> None:
    """Нет «доставки» → fixed=4+1=5, remaining=25."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("verification_default"),
    ]
    out = calculate_term_days_per_item(spec, 30)
    assert out[0]["value"] == "25"


def test_customer_side_install_not_subtracted() -> None:
    """install_default с customer_side=True — не вычитается из общего, в ячейке пусто."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default", customer_side=True),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    out = calculate_term_days_per_item(spec, 30)
    # fixed = 0 (install customer) + 1 + 1 = 2 → remaining = 28
    assert out[0]["value"] == "28"
    install_row = out[1]
    assert install_row["item_key"] == "install_default"
    assert install_row["value"] == ""
    assert install_row["merge"] is None


def test_customer_side_delivery_not_subtracted() -> None:
    """delivery_default customer_side → пустая ячейка, не учитывается."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("verification_default"),
        _item("delivery_default", customer_side=True),
    ]
    out = calculate_term_days_per_item(spec, 30)
    # fixed = 4 + 1 + 0 = 5 → remaining = 25
    assert out[0]["value"] == "25"
    assert out[3]["value"] == ""


def test_total_equals_fixed_raises() -> None:
    """T_общий == T_фиксированных → ValueError, расчёт невозможен."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    with pytest.raises(TermDaysTooSmallError) as exc_info:
        calculate_term_days_per_item(spec, 6)  # 6 == 4+1+1
    d = exc_info.value.details
    assert d["total"] == 6
    assert d["min"] == 7  # минимум, чтобы T_осталось >= 1
    assert d["install"] == 4
    assert d["verification"] == 1
    assert d["delivery"] == 1


def test_total_less_than_fixed_raises() -> None:
    """T_общий < T_фиксированных → ValueError."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    with pytest.raises(TermDaysTooSmallError):
        calculate_term_days_per_item(spec, 3)


def test_parallel_aux_canopy_separate_cell() -> None:
    """canopy_turnkey_18 → отдельная ячейка с T_осталось, без merge."""
    spec = [
        _item("vesta-с-80-18"),
        _item("frame_18"),
        _item("canopy_turnkey_18"),
        _item("install_default"),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    out = calculate_term_days_per_item(spec, 30)
    assert out[0]["merge"] == "restart"
    assert out[1]["merge"] == "continue"
    canopy_row = out[2]
    assert canopy_row["item_key"] == "canopy_turnkey_18"
    assert canopy_row["value"] == "24"
    assert canopy_row["merge"] is None


def test_classify_term_role_typical_keys() -> None:
    """Маппинг item_key → роль для 8 типичных ключей."""
    assert classify_term_role("vesta-с-80-18") == "scales_main"
    assert classify_term_role("frame_18") == "scales_aux"
    assert classify_term_role("fence_norma_20") == "scales_aux"
    assert classify_term_role("ramp_set_fl_sl") == "scales_aux"
    assert classify_term_role("orion_lite") == "scales_aux"
    assert classify_term_role("orion_cable_poles") == "scales_aux"
    assert classify_term_role("foundation_s_f_18") == "foundation"
    assert classify_term_role("foundation_supervision") == "foundation"
    assert classify_term_role("canopy_turnkey_22") == "parallel_aux"
    assert classify_term_role("construction_works_18") == "parallel_aux"
    assert classify_term_role("concrete_base_on_frame") == "parallel_aux"
    assert classify_term_role("install_default") == "install"
    assert classify_term_role("verification_default") == "verification"
    assert classify_term_role("delivery_default") == "delivery"
    assert classify_term_role("embedded_parts") == "scales_aux"
    assert classify_term_role("rubber_t_6m") == "scales_aux"
    assert classify_term_role("factory_calibration") == "scales_aux"


def test_total_one_more_than_fixed_passes() -> None:
    """T_общий = fixed+1 → remaining=1, расчёт проходит."""
    spec = [
        _item("vesta-с-80-18"),
        _item("install_default"),
        _item("verification_default"),
        _item("delivery_default"),
    ]
    out = calculate_term_days_per_item(spec, 7)  # fixed=6, remaining=1
    assert out[0]["value"] == "1"
