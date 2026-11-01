"""Д12 / N3: датчик, индикатор и кабель договора берутся из снапшота КП."""
from __future__ import annotations

import json
import os
from datetime import date

from docx import Document

from src.contracts.from_kp import build_spec_v2_data
from src.contracts.spec_v2_filler import _load_model_and_deps, fill_spec_v2
from src.contracts.supply_filler import build_supply_context
from tests.contracts.test_spec_v2_integration import (
    _REQUISITES,
    DATA_DIR,
    SPEC_V2_PATH,
    _make_kp,
)

_ITEMS = [{
    "name": "Весы автомобильные ВЕСТА-С-60-18", "quantity": 1, "total": 2_000_000,
    "id": "weights", "payment_group": "scales", "metadata": {"line": "С", "max": 60, "length": 18},
}]
_EQ = {"sensor_id": "keli_zsfy_d_30t", "indicator_id": "titan_12", "cable_m": 30}



def _kit_text(rows: list[dict]) -> str:
    return "\n".join(f"{r['name']}|{r['qty']}" for r in rows)


def test_load_deps_uses_snapshot_equipment():
    model, ld, sensor, indicator = _load_model_and_deps({"items": _ITEMS, "equipment": _EQ})
    assert sensor["model"] == "ZSFY-D"  # не «ZSFY»: берётся самое длинное совпадение
    assert indicator["model"] == "ТИТАН 12"
    assert ld["default_cable_length_m"] == 30


def test_load_deps_without_equipment_is_line_defaults():
    for deal in ({"items": _ITEMS}, {"items": _ITEMS, "equipment": {}},
                 {"items": _ITEMS, "equipment": {"sensor_id": "", "indicator_id": None, "cable_m": None}},
                 {"items": _ITEMS, "equipment": {"sensor_id": "нет_такого"}}):
        _, ld, sensor, indicator = _load_model_and_deps(deal)
        assert sensor["model"] == "DHM9B"
        assert indicator["model"] == "ТИТАН 3ЦС"
        assert ld["default_cable_length_m"] == 20


def test_supply_context_kit_and_tth_from_kp():
    ctx = {"ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "ООО «Тест»"}
    res = build_supply_context(
        ctx, _ITEMS, {"items": _ITEMS, "equipment": _EQ}, [],
        {"contract_number": "1"}, date(2026, 1, 1),
    )
    text = _kit_text(res["kit_rows"])
    assert "ZSFY-D-30t" in text and "ТИТАН 12" in text
    assert "Кабель сигнальный, м|30" in text
    assert "40" in res["ТТХ_ТЕМПЕРАТУРА"] and "30" not in res["ТТХ_ТЕМПЕРАТУРА"]  # Keli −40
    base = build_supply_context(
        ctx, _ITEMS, {"items": _ITEMS}, [], {"contract_number": "1"}, date(2026, 1, 1),
    )
    assert "Кабель сигнальный, м|20" in _kit_text(base["kit_rows"])
    assert "DHM9B-30t" in _kit_text(base["kit_rows"])
    assert "30" in base["ТТХ_ТЕМПЕРАТУРА"]


def test_fill_spec_v2_kit_from_kp(tmp_path):
    out = str(tmp_path / "spec.docx")
    data = {**_REQUISITES}
    fill_spec_v2(SPEC_V2_PATH, data, _ITEMS, {"items": _ITEMS, "equipment": _EQ}, out)
    doc = Document(out)
    cells = [c.text for t in doc.tables for r in t.rows for c in r.cells]
    assert any("ZSFY-D-30t" in c for c in cells)
    assert any("ТИТАН 12" in c for c in cells)
    assert "30" in cells


def test_build_spec_v2_data_kit_from_kp():
    with open(os.path.join(DATA_DIR, "models.json"), encoding="utf-8") as f:
        models = json.load(f)
    with open(os.path.join(DATA_DIR, "prices.json"), encoding="utf-8") as f:
        prices = json.load(f)
    with open(os.path.join(DATA_DIR, "payment_terms.json"), encoding="utf-8") as f:
        pt = json.load(f)
    with open(os.path.join(DATA_DIR, "equipment_specs.json"), encoding="utf-8") as f:
        es = json.load(f)
    kp = _make_kp("vesta-с-60-18", "С", 60, 18, 2_000_000)
    kp["data"]["equipment"] = dict(_EQ)
    data, _, _ = build_spec_v2_data(kp, prices, models, pt, es)
    text = _kit_text(data["_kit_items"])
    assert "ZSFY-D-30t" in text and "ТИТАН 12" in text
    assert "Кабель сигнальный, м|30" in text
    # без полей — умолчания линейки
    kp["data"]["equipment"] = {}
    data, _, _ = build_spec_v2_data(kp, prices, models, pt, es)
    text = _kit_text(data["_kit_items"])
    assert "DHM9B-30t" in text and "ТИТАН 3ЦС" in text and "Кабель сигнальный, м|20" in text
