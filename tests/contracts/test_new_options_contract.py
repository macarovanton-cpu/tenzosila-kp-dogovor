"""Д06: новые опции прайса 28.09 в договоре — КБУ, навес, «Горыныч», ППР."""
from __future__ import annotations

from pathlib import Path

from src.contracts.clauses_context import build_clauses_context
from src.contracts.clauses_renderer import build_contract_clauses
from src.contracts.from_kp import build_specification_items
from src.contracts.fundament_lookup import (
    kbu_build_task_files,
    kbu_build_task_reason,
    snapshot_has_kbu,
)
from src.contracts.supply_filler import _supply_spec_rows, decide_contract_type
from src.data_loader import load_models, load_prices
from src.payment_wording import installation_object
from src.spec_builder import build_spec_items
from src.storage.snapshot_builder import build_kp_snapshot
from tests.test_kp_restore import _kp_row
from tests.test_validation import _valid_state

PRICES = load_prices()


def _opt(price: int) -> dict:
    return {"enabled": True, "price": price, "qty": 1, "customer_side": False}


def _deal(options: dict, line: str = "С") -> tuple[dict, list[dict], dict]:
    state = _valid_state()
    state.update(model_line=line, model_id=f"vesta-{line.lower()}-60-18", options=options)
    row = _kp_row(state)
    items = build_specification_items(row, PRICES)
    kp_total = sum(it["total"] for it in build_spec_items(state, PRICES, load_models()))
    assert sum(it["total"] for it in items) == kp_total  # Σ договора = Σ КП
    return row, items, build_clauses_context({"items": items})


def _clause_texts(items: list[dict]) -> dict[str, str]:
    clauses = build_contract_clauses({"items": items})
    return {c.id: c.text for section in clauses.values() for c in section}


def test_kbu_with_install_is_spec_like_rama():
    _, items, ctx = _deal({"kbu_p06_44_18": _opt(400_000), "install_default": _opt(180_000)})
    assert [it["id"] for it in items if it["id"] == "kbu"] == ["kbu"]
    assert ctx["foundation_scope"] == "rama" and ctx["installation_scope"] == "full"
    assert decide_contract_type(ctx["installation_scope"], ctx["foundation_scope"], ctx["has_orion"]) == "spec"
    texts = _clause_texts(items)
    assert "customer_provides_flat_area_for_rama" in texts
    assert any("220В" in t for t in texts.values())
    assert any("месту установки" in t for t in texts.values())


def test_kbu_without_install_is_supply_in_scales_row():
    _, items, ctx = _deal({"kbu_p06_35_l_18": _opt(300_000)}, line="СЛ")
    assert decide_contract_type(ctx["installation_scope"], ctx["foundation_scope"], ctx["has_orion"]) == "supply"
    total, rows = _supply_spec_rows(items, "Весы")
    assert len(rows) == 1 and total == sum(it["total"] for it in items)


def test_kbu_build_task_choice():
    row, _, _ = _deal({"kbu_p06_44_18": _opt(400_000), "install_default": _opt(180_000)})
    snapshot = row["data"]
    assert snapshot_has_kbu(snapshot) and snapshot["foundation_sections"] == 3
    names = [p.name for p in kbu_build_task_files(snapshot["foundation_sections"])]
    assert names and all(n.startswith("rama_") and n.endswith("_3скц.docx") for n in names)
    assert "на 3 скц" in kbu_build_task_reason(3)
    assert not snapshot_has_kbu(build_kp_snapshot(_valid_state()))


def test_canopy_parts_and_gorynych_not_foundation():
    options = {
        "canopy_18": _opt(2_800_000),
        "foundation_under_canopy_18": _opt(1_100_000),
        "canopy_installation_18": _opt(1_600_000),
        "foundation_heating_gorynych_5": _opt(90_000),
        "orion_standard": _opt(PRICES["options"]["orion_standard"]["price_retail"]),
        "install_default": _opt(180_000),
    }
    _, items, ctx = _deal(options)
    assert "foundation" not in {it["id"] for it in items}
    assert ctx["foundation_scope"] == "customer_builds"  # как без фундамента
    orion_install = next(it for it in items if it["id"] == "orion_install")
    assert orion_install["name"] == "Монтаж ПАК «ОРИОН»"


def test_ppr_with_install_payment_object_and_clauses():
    base = {"install_default": _opt(180_000)}
    _, items, _ = _deal(dict(base, ppr_documentation=_opt(50_000)))
    _, items_no_ppr, _ = _deal(base)
    iv = [it for it in items if it["payment_group"] == "installation_and_verification"]
    assert {it["id"] for it in iv} == {"installation", "ppr_documentation"}
    assert installation_object("full", iv, False) == "монтажных работ"
    assert set(_clause_texts(items)) == set(_clause_texts(items_no_ppr))
    assert Path(kbu_build_task_files(3)[0]).exists()
