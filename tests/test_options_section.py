"""Тесты UI-контракта блока «Фундамент и основание под раму»."""
from __future__ import annotations

from src.ui.options_section import (
    FOUNDATION_EXECUTION_CHOICES,
    _requires_foundation_execution_choice,
)


def test_foundation_execution_choices_match_snapshot_contract():
    """UI предлагает ровно те типы, которые менеджер выбирает для вариантов 1-3."""
    assert FOUNDATION_EXECUTION_CHOICES == [
        "пандусный",
        "приямок",
        "монолитная_плита",
    ]


def test_foundation_execution_choice_required_for_variants_1_2_3_only():
    """Варианты 1-3 требуют UI-выбор, рамные варианты имеют фиксированный тип."""
    assert _requires_foundation_execution_choice("foundation_s_f_18")
    assert _requires_foundation_execution_choice("foundation_lite_sl_fl_18")
    assert _requires_foundation_execution_choice("foundation_supervision")
    assert _requires_foundation_execution_choice("construction_works_18")

    assert not _requires_foundation_execution_choice("concrete_base_on_frame")
    assert not _requires_foundation_execution_choice("road_slabs_18")
    assert not _requires_foundation_execution_choice("pag_slabs_18")
