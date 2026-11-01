"""Д13 / N4, N6: второй диапазон ТТХ — только при двухдиапазонности КП; габариты — с шириной КП."""
from __future__ import annotations

import json
from pathlib import Path

from src.contracts.spec_v2_filler import _load_model_and_deps
from src.contracts.supply_filler import build_supply_tth
from src.contracts.tth_context import build_tth_data, deal_tth_opts

_MODELS = json.loads(Path("data/models.json").read_text(encoding="utf-8"))["models"]
_DUAL = next(m for m in _MODELS if m.get("dual_range"))
_SENSOR: dict = {}


def test_dual_model_without_kp_dual_gives_single_range():
    t = build_tth_data(_DUAL, _SENSOR, is_dual=False)
    assert t["ТТХ_ДИСКРЕТНОСТЬ_2"] == "" and t["ТТХ_ГРАНИЦА_2"] == ""
    assert t["ТТХ_ГРАНИЦА_1"] == str(_DUAL["max_load_t"])


def test_dual_model_with_kp_dual_gives_two_ranges():
    t = build_tth_data(_DUAL, _SENSOR, is_dual=True)
    assert t["ТТХ_ДИСКРЕТНОСТЬ_2"] and t["ТТХ_ГРАНИЦА_2"]


def test_width_from_kp():
    length = _DUAL["length_m"]
    assert build_tth_data(_DUAL, _SENSOR, width=3.5)["ТТХ_ГАБАРИТЫ"] == f"{length}×3.5"
    assert build_tth_data(_DUAL, _SENSOR, width=3.0)["ТТХ_ГАБАРИТЫ"] == f"{length}×3"
    assert build_supply_tth(_DUAL, _SENSOR, width=3.5)["ТТХ_ГАБАРИТЫ"] == f"{length}×3.5"


def test_deal_tth_opts():
    deal = {"is_dual_range": True, "items": [{"metadata": {"width": 3.5}}]}
    assert deal_tth_opts(deal) == {"is_dual": True, "width": 3.5}
    assert deal_tth_opts({"items": []}) == {"is_dual": False, "width": None}


def test_deal_to_model_lookup_still_works():
    m = _DUAL
    deal = {"items": [{"metadata": {"line": m["line"], "max": m["max_load_t"], "length": m["length_m"]}}]}
    assert _load_model_and_deps(deal) is not None


def _spec_text(path: str) -> str:
    from docx import Document
    d = Document(path)
    return "\n".join(p.text for t in d.tables for r in t.rows for c in r.cells for p in c.paragraphs)


def test_spec_single_range_has_no_second_range_paragraphs(tmp_path):
    from src.contracts.filler import fill_template
    from src.contracts.spec_v2_filler import _template_without_second_range
    tpl = "templates/contracts/spec_v2.docx"
    single = build_tth_data(_DUAL, _SENSOR, is_dual=False)
    dual = build_tth_data(_DUAL, _SENSOR, is_dual=True)
    out1, out2 = str(tmp_path / "a.docx"), str(tmp_path / "b.docx")
    fill_template(_template_without_second_range(tpl), single, out1)
    fill_template(tpl, dual, out2)
    t1, t2 = _spec_text(out1), _spec_text(out2)
    assert f"- от 0 до {single['ТТХ_ГРАНИЦА_1']}т" in t1
    assert " до т" not in t1
    assert len(t1.splitlines()) == len(t2.splitlines()) - 2  # ушли ровно два абзаца
    assert f"до {dual['ТТХ_ГРАНИЦА_2']}т" in t2 and dual["ТТХ_ДИСКРЕТНОСТЬ_2"] in t2
