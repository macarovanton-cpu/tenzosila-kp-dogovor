"""Юниты секции BUCKETS golden-дампа (видимость B9/B12)."""

from __future__ import annotations

from tests.golden.dump_buckets import buckets_section

_SCALES = {"id": "weights", "name": "Весы", "payment_group": "scales"}
_FOUNDATION = {"id": "foundation", "name": "Фундамент", "payment_group": "foundation"}
_DELIVERY = {"id": "delivery", "name": "Доставка", "payment_group": "delivery"}
_INSTALL = {"id": "installation", "name": "Монтаж", "payment_group": "installation_and_verification"}
_VERIF = {"id": "verification", "name": "Поверка", "payment_group": "installation_and_verification"}
_CUSTOM = {
    "id": "custom_1", "name": "Доп.работы", "payment_group": "scales",
    "custom_scope": "other",
}


def test_items_section_lists_id_name_group():
    section = buckets_section([_SCALES, _FOUNDATION])
    assert "weights | Весы | scales" in section
    assert "foundation | Фундамент | foundation" in section


def test_items_section_shows_custom_scope_when_present():
    section = buckets_section([_CUSTOM])
    assert "custom_1 | Доп.работы | scales | custom_scope=other" in section


def test_items_section_omits_custom_scope_when_absent():
    section = buckets_section([_SCALES])
    assert "custom_scope" not in section.split("[GROUPS]")[0]


def test_groups_section_lists_members_per_bucket():
    section = buckets_section([_SCALES, _FOUNDATION, _DELIVERY, _INSTALL])
    groups = section.split("[GROUPS]")[1].split("[IV]")[0]
    assert "scales: weights" in groups
    assert "foundation: foundation" in groups
    assert "delivery: delivery" in groups
    assert "installation_and_verification: installation" in groups


def test_groups_section_marks_empty_bucket():
    section = buckets_section([_SCALES])
    assert "foundation: (пусто)" in section


def test_iv_flags_composed_bucket_no_guard():
    """Монтаж + поверка — бакет опознан целиком, guard не срабатывает."""
    section = buckets_section([_INSTALL, _VERIF])
    assert "has_install=True has_verification=True has_orion_install=False" in section
    assert "guard_triggered=False" in section


def test_iv_flags_unrecognized_item_triggers_guard():
    """Неопознанная позиция в iv-бакете (B11) — guard срабатывает."""
    unrecognized = {
        "id": "custom_2", "name": "Прочее", "payment_group": "installation_and_verification",
    }
    section = buckets_section([unrecognized])
    assert "guard_triggered=True" in section


def test_iv_flags_no_iv_bucket_triggers_guard():
    """Пустой iv-бакет — та же формула, что installation_object([])."""
    section = buckets_section([_SCALES])
    assert "guard_triggered=True" in section
