"""Тесты UI-контракта блока «Фундамент и основание под раму»."""
from __future__ import annotations

from src.ui.options_section import (
    FOUNDATION_EXECUTION_CHOICES,
    _disable_other_orion_packages,
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


def test_orion_package_toggle_disables_others_and_clears_overrides():
    """Включение второго пакета ОРИОН выключает первый, чистит его override."""
    sfx = "__vesta-с-60-18"
    session = {
        f"opt_orion_standard_enabled{sfx}": True,
        f"opt_orion_auto_enabled{sfx}": True,  # активный, только что включён
        "options": {
            "orion_standard": {"enabled": True, "price": 464_900},
            "orion_auto": {"enabled": True, "price": 620_000},
        },
        "spec_items_overrides": {
            "orion_standard": {"price": 400_000},
            "orion_install": {"price": 100_000},
        },
    }
    _disable_other_orion_packages(session, "orion_auto", sfx)

    assert session[f"opt_orion_standard_enabled{sfx}"] is False
    assert session[f"opt_orion_auto_enabled{sfx}"] is True
    assert "orion_standard" not in session["options"]
    assert "orion_standard" not in session["spec_items_overrides"]
    assert "orion_install" not in session["spec_items_overrides"]


def test_orion_package_uncheck_leaves_others_untouched():
    """Снятие галочки пакета не должно трогать остальные (страж вкл. только on)."""
    sfx = "__x"
    session = {
        f"opt_orion_auto_enabled{sfx}": False,  # активный сняли
        f"opt_orion_standard_enabled{sfx}": True,
        "options": {"orion_standard": {"enabled": True}},
    }
    _disable_other_orion_packages(session, "orion_auto", sfx)
    assert session[f"opt_orion_standard_enabled{sfx}"] is True
    assert "orion_standard" in session["options"]
