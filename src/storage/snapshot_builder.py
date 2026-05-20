"""Строит JSONB-снапшот session_state КП для сохранения в Supabase."""
from __future__ import annotations

from typing import Any


def build_kp_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Возвращает data-блок для колонки kps.data.

    Включает только ключи из §6.2 session_state_audit.md.
    Виджетные ключи (opt_*, split_*), вычисляемые (spec_items, totals)
    и legacy (payment_percents) исключены.
    Для options хранятся только enabled=True записи с полями
    price/qty/customer_side/retail/dealer_is_synthetic.
    """
    opts = state.get("options") or {}
    enabled_options = {
        key: {
            "price": opt.get("price", 0),
            "qty": opt.get("qty", 1),
            "customer_side": opt.get("customer_side", False),
            "retail": opt.get("retail", 0),
            "dealer_is_synthetic": opt.get("dealer_is_synthetic", False),
        }
        for key, opt in opts.items()
        if opt.get("enabled", False)
    }

    return {
        "metadata": {
            "kp_valid_days": state.get("kp_valid_days"),
            "warranty_months": state.get("warranty_months"),
        },
        "model": {
            "line": state.get("model_line"),
            "max": state.get("model_max"),
            "length": state.get("model_length"),
            "price": state.get("model_price"),
        },
        "equipment": {
            "sensor_id": state.get("sensor_id"),
            "indicator_id": state.get("indicator_id"),
            "cable_m": state.get("cable_m"),
        },
        "construction": {
            "beam": state.get("construction_beam"),
            "beam_count": state.get("construction_beam_count"),
            "center_beam": state.get("construction_center_beam"),
            "center_beam_count": state.get("construction_center_beam_count"),
            "deck_mm": state.get("construction_deck_mm"),
            "underlining_mm": state.get("construction_underlining_mm"),
        },
        "metrology": {
            "is_dual_range": state.get("is_dual_range"),
        },
        "options": enabled_options,
        "spec_overrides": state.get("spec_items_overrides") or {},
        "payment": {
            "preset_id": state.get("payment_preset_id"),
            "days": state.get("payment_days"),
            "custom_text": state.get("payment_custom_text", ""),
            "split_state": state.get("payment_split_state") or {},
            "v1_prepay": state.get("payment_v1_prepay"),
            "v2_prepay": state.get("payment_v2_prepay"),
            "v2_preship": state.get("payment_v2_preship"),
            "v3_days": state.get("payment_v3_days"),
            "v3_trigger_id": state.get("payment_v3_trigger_id"),
        },
    }
