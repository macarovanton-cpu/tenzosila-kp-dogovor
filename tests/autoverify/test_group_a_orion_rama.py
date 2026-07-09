"""Ловушки группы A/БАГ из FIX_SPEC_generation_2026-07-08.md.

БАГ-1a: рама (frame_18) без foundation-опции даёт клаузы «фундамент своими
силами» вместо клаузы площадки 30х4м — рассинхрон префикса в
`_option_key_to_spec_id` (frame_* не матчится, есть только rama*).

E4: та же причина — пандусы (ramp_set_*) получают custom_xxxx id вместо
собственного spec_id.

A1: бандл ОРИОН расщепляется на ПАК + «Монтаж ОРИОН» (2 позиции). Опоры —
обычная опция: попадают в договор ТОЛЬКО если включены в КП (тогда 3-я позиция),
не авто по факту фундамента.
"""
from __future__ import annotations

import re

_CUSTOM_ID_RE = re.compile(r"^custom_[0-9a-f]{8}$")

# fixture_id -> ожидаемое количество ОРИОН-позиций (FIX_SPEC A1)
_ORION_POSITION_COUNT = {
    "orion": 2,               # фундамент+ОРИОН, опор в КП НЕТ: ПАК + монтаж ОРИОН
    "orion_poles": 3,         # фундамент+ОРИОН+опоры в КП: ПАК + монтаж ОРИОН + опоры
    "montazh_orion": 2,       # монтаж+ОРИОН, без фундамента: ПАК + монтаж ОРИОН
}


def test_bag1a_rama_clauses_not_foundation(generated) -> None:
    """рама+монтаж → клауза площадки 30х4м, НЕ клаузы фундамента-заказчиком."""
    if generated.fixture_id != "rama_ploshadka_montazh":
        return
    ids = {c.id for c in generated.clauses.get("obligations_customer", [])}
    where = generated.fixture_id

    assert "customer_provides_flat_area_for_rama" in ids, (
        f"{where}: нет клаузы площадки 30х4м (customer_provides_flat_area_for_rama)"
    )
    flat_area = next(
        c for c in generated.clauses["obligations_customer"]
        if c.id == "customer_provides_flat_area_for_rama"
    )
    assert "30х4м" in flat_area.text or "30х4 м" in flat_area.text, (
        f"{where}: клауза площадки не содержит «30х4м»: {flat_area.text!r}"
    )
    assert "customer_builds_foundation_per_spec" not in ids, (
        f"{where}: лишняя клауза «изготовить фундамент своими силами»"
    )
    assert "customer_provides_foundation_photos" not in ids, (
        f"{where}: лишняя клауза контрольного листа/стройзадания на фундамент"
    )


def test_e4_pandus_has_real_spec_id(generated) -> None:
    """Позиция пандусов должна иметь собственный spec_id, не custom_xxxxxxxx."""
    if generated.fixture_id != "rama_ploshadka_montazh":
        return
    pandus_item = next(
        (it for it in generated.items if "пандус" in it["name"].lower()), None
    )
    assert pandus_item is not None, f"{generated.fixture_id}: позиция пандусов не найдена"
    assert not _CUSTOM_ID_RE.match(pandus_item["id"]), (
        f"{generated.fixture_id}: пандусы получили custom-id {pandus_item['id']!r} "
        f"вместо собственного spec_id"
    )


def test_a1_orion_position_count(generated) -> None:
    """Количество ОРИОН-позиций по сценарию (см. _ORION_POSITION_COUNT)."""
    orion_items = [it for it in generated.items if "ОРИОН" in it["name"]]
    expected = _ORION_POSITION_COUNT.get(generated.fixture_id, 0)
    assert len(orion_items) == expected, (
        f"{generated.fixture_id}: ОРИОН-позиций {len(orion_items)}, ожидалось "
        f"{expected} ({[it['name'] for it in orion_items]})"
    )
