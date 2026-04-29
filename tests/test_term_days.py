"""Тесты calculate_default_term_days — дефолт срока проекта по составу."""
from __future__ import annotations

from src.term_days import calculate_default_term_days


def test_default_term_days_only_scales():
    """Только автовесы → 20."""
    spec = [{"item_key": "vesta-с-80-18"}]
    assert calculate_default_term_days(spec) == 20


def test_default_term_days_scales_plus_install():
    """Автовесы + монтаж → 25."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "install_default"},
    ]
    assert calculate_default_term_days(spec) == 25


def test_default_term_days_scales_plus_orion():
    """Автовесы + ОРИОН без монтажа → 25."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "orion_lite"},
    ]
    assert calculate_default_term_days(spec) == 25


def test_default_term_days_scales_plus_foundation():
    """Автовесы + фундамент без монтажа → 30."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "foundation_s_f_18"},
    ]
    assert calculate_default_term_days(spec) == 30


def test_default_term_days_full_set():
    """Автовесы + монтаж + фундамент + ОРИОН → 40."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "install_default"},
        {"item_key": "foundation_s_f_18"},
        {"item_key": "orion_standard"},
    ]
    assert calculate_default_term_days(spec) == 40


def test_default_term_days_delivery_and_fences_dont_affect():
    """Доставка и ограждения не влияют на срок."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "delivery_default"},
        {"item_key": "fence_norma_18"},
    ]
    assert calculate_default_term_days(spec) == 20


def test_default_term_days_empty_spec():
    """Пустой состав → 20 (база)."""
    assert calculate_default_term_days([]) == 20


def test_default_term_days_verification_counts_as_install():
    """Поверка отдельно (без монтажа) тоже даёт +5."""
    spec = [
        {"item_key": "vesta-с-80-18"},
        {"item_key": "verification_default"},
    ]
    assert calculate_default_term_days(spec) == 25
