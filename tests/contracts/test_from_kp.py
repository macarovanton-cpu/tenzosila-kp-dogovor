"""Тесты build_specification_from_kp_snapshot."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _load(fname: str) -> dict:
    return json.loads(Path(f"data/{fname}").read_text(encoding="utf-8"))


PRICES = _load("prices.json")
MODELS = _load("models.json")
PAYMENT_TERMS = _load("payment_terms.json")


def _make_kp_row(
    model_line: str = "С",
    model_max: int = 60,
    model_length: int = 18,
    model_price: int | None = 2835000,
    options: dict | None = None,
    payment_preset: str = "split_by_items",
    payment_split_state: dict | None = None,
) -> dict:
    return {
        "kp_number": "КП-2026-001",
        "model_id": f"vesta-{model_line.lower()}-{model_max}-{model_length}",
        "total_price": 0,
        "data": {
            "model": {"line": model_line, "max": model_max, "length": model_length, "price": model_price},
            "equipment": {"sensor_id": "zemic_dhm9b_30t", "indicator_id": "titan_3cs", "cable_m": 20},
            "options": options or {},
            "spec_overrides": {},
            "payment": {
                "preset_id": payment_preset,
                "days": 5,
                "custom_text": "",
                "split_state": payment_split_state or {"scales": {"prepay": 50, "postpay": 50}},
                "v1_prepay": 50,
                "v2_prepay": 30,
                "v2_preship": 40,
                "v3_days": 15,
                "v3_trigger_id": "after_installation",
            },
            "metadata": {"kp_valid_days": 15, "warranty_months": 36},
            "construction": {
                "beam": "Двутавр 20Б1", "beam_count": 4,
                "center_beam": "", "center_beam_count": 0,
                "deck_mm": 6, "underlining_mm": 4,
            },
            "metrology": {"is_dual_range": False},
        },
    }


class TestBuildSpecFromKpSnapshot:
    def test_minimal_has_required_keys(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        kp_row = _make_kp_row()
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)

        required = {
            "СПЕЦ_НДС", "СПЕЦ_МОДЕЛЬ_КРАТКОЕ", "СПЕЦ_МАКС_НАГРУЗКА",
            "СПЕЦ_П1_НАИМЕНОВАНИЕ", "СПЕЦ_П1_СУММА",
            "СПЕЦ_П2_ПАРАМЕТРЫ", "СПЕЦ_П2_СУММА",
            "СПЕЦ_П3_НАИМЕНОВАНИЕ", "СПЕЦ_П3_СУММА",
            "СПЕЦ_П4_НАИМЕНОВАНИЕ", "СПЕЦ_П4_СУММА",
            "СПЕЦ_П5_НАИМЕНОВАНИЕ", "СПЕЦ_П5_СУММА",
            "СПЕЦ_ИТОГО", "СПЕЦ_ИТОГО_ПРОПИСЬ",
            "СПЕЦ_ОПЛАТА_П1", "СПЕЦ_ОПЛАТА_П2", "СПЕЦ_ОПЛАТА_П3",
            "СПЕЦ_ОПЛАТА_П4", "СПЕЦ_ОПЛАТА_П5", "СПЕЦ_ОПЛАТА_П6",
            "СПЕЦ_СРОК_ПОСТАВКИ", "СПЕЦ_СРОК_ФУНДАМЕНТ", "СПЕЦ_СРОК_МОНТАЖ",
        }
        assert required.issubset(spec.keys())

    def test_minimal_nds_is_22(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_НДС"] == "22"

    def test_model_краткое_формат(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(model_line="С", model_max=60, model_length=18),
            PRICES, MODELS, PAYMENT_TERMS,
        )
        assert spec["СПЕЦ_МОДЕЛЬ_КРАТКОЕ"] == "ВЕСТА-С-60-18"

    def test_no_foundation_fields_empty(self):
        """Без фундамента П2_ПАРАМЕТРЫ и П2_СУММА пустые."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_П2_ПАРАМЕТРЫ"] == ""
        assert spec["СПЕЦ_П2_СУММА"] == ""

    def test_with_foundation_option(self):
        """С фундаментом П2_ПАРАМЕТРЫ и П2_СУММА заполнены."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        # foundation_s_f_* — для линий С/Ф; foundation_lite_sl_fl_* — для СЛ/ФЛ
        foundation_key = None
        for k in PRICES.get("options", {}):
            if k.startswith("foundation_s_f_") and "18" in k:
                foundation_key = k
                break
        if foundation_key is None:
            pytest.skip("foundation_s_f_18 not found in prices.json")

        options = {
            foundation_key: {"price": 350000, "qty": 1, "customer_side": False,
                             "retail": 350000, "dealer_is_synthetic": False}
        }
        kp_row = _make_kp_row(options=options)
        spec = build_specification_from_kp_snapshot(kp_row, PRICES, MODELS, PAYMENT_TERMS)
        assert spec["СПЕЦ_П2_ПАРАМЕТРЫ"] != ""
        assert spec["СПЕЦ_П2_СУММА"] != ""

    def test_итого_equals_sum_of_positions(self):
        """СПЕЦ_ИТОГО == сумма всех П*_СУММА."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        total_str = spec["СПЕЦ_ИТОГО"].replace(" ", "").replace("\xa0", "")
        total = int(total_str) if total_str else 0

        parts_sum = 0
        for i in range(1, 6):
            key = f"СПЕЦ_П{i}_СУММА"
            val = spec.get(key, "").replace(" ", "").replace("\xa0", "")
            if val:
                parts_sum += int(val)

        assert total == parts_sum, f"ИТОГО {total} != sum(П1..П5) {parts_sum}"

    def test_итого_пропись_not_empty(self):
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_ИТОГО_ПРОПИСЬ"] != ""

    def test_оплата_п1_not_empty(self):
        """Хотя бы П1 условий оплаты заполнен."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_ОПЛАТА_П1"] != ""

    def test_срок_поставки_numeric(self):
        """СПЕЦ_СРОК_ПОСТАВКИ — строка с числом."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        assert spec["СПЕЦ_СРОК_ПОСТАВКИ"].isdigit()

    def test_no_заказчик_fields(self):
        """ЗАКАЗЧИК_* поля НЕ должны быть в возвращаемом dict."""
        from src.contracts.from_kp import build_specification_from_kp_snapshot
        spec = build_specification_from_kp_snapshot(
            _make_kp_row(), PRICES, MODELS, PAYMENT_TERMS
        )
        zakazchik_keys = [k for k in spec if k.startswith("ЗАКАЗЧИК_")]
        assert zakazchik_keys == []
