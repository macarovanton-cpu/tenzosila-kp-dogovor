"""Тесты calculate_default_term_days — дефолт срока проекта по составу.

T_default = сумма дефолтов уникальных активных ролей. Дефолты:
весы 20, ОРИОН 5, фундамент 10, навес 25, монтаж 3, доставка 1, поверка 1.
"""
from __future__ import annotations

from src.term_days import calculate_default_term_days


def test_default_only_scales():
    """Только автовесы → 20."""
    spec = [{"item_key": "vesta-с-80-18"}]
    assert calculate_default_term_days(spec) == 20


def test_default_scales_plus_install():
    """Автовесы + монтаж → 20+3=23."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "install_default"},
    ]
    assert calculate_default_term_days(spec) == 23


def test_default_scales_plus_orion():
    """Автовесы + ОРИОН → 20+5=25."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "orion_lite"},
    ]
    assert calculate_default_term_days(spec) == 25


def test_default_scales_plus_foundation():
    """Автовесы + фундамент → 20+10=30."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "foundation_s_f_18"},
    ]
    assert calculate_default_term_days(spec) == 30


def test_default_scales_plus_canopy():
    """Автовесы + навес «под ключ» → 20+25=45."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "canopy_turnkey_18"},
    ]
    assert calculate_default_term_days(spec) == 45


def test_default_full_set_with_canopy():
    """Все 4 вариативных + 3 фикс → 20+5+10+25+3+1+1=65."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "orion_standard"},
        {"item_key": "foundation_s_f_18"},
        {"item_key": "canopy_turnkey_18"},
        {"item_key": "install_default"},
        {"item_key": "delivery_default"},
        {"item_key": "verification_default"},
    ]
    assert calculate_default_term_days(spec) == 65


def test_default_options_dont_affect():
    """Рама/ограждение/люки/закладные/калибровка не влияют (роль None)."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "frame_18"},
        {"item_key": "fence_norma_18"},
        {"item_key": "hatches_24"},
        {"item_key": "embedded_parts"},
        {"item_key": "factory_calibration"},
    ]
    assert calculate_default_term_days(spec) == 20


def test_default_empty_spec():
    """Пустой состав → 0 (никаких активных ролей)."""
    assert calculate_default_term_days([]) == 0


def test_default_verification_alone_gives_one():
    """Поверка без монтажа → 20+1=21 (отдельная роль verification)."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "verification_default"},
    ]
    assert calculate_default_term_days(spec) == 21


def test_default_construction_works_counts_as_foundation():
    """construction_works_* имеет роль foundation → +10 один раз даже с фундаментом."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "construction_works_18"},
        {"item_key": "foundation_s_f_18"},
    ]
    assert calculate_default_term_days(spec) == 30  # 20+10 (foundation один раз)


def test_default_customer_side_install_excluded():
    """install с customer_side=True не считается в дефолте."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "install_default", "customer_side": True},
    ]
    assert calculate_default_term_days(spec) == 20
