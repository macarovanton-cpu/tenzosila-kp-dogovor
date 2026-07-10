"""Тесты build_kp_payload — атомарная сборка данных КП для страницы Договор."""
from __future__ import annotations

import pytest

from src.contracts.kp_load import build_kp_payload
from tests.contracts.test_from_kp import MODELS, PAYMENT_TERMS, PRICES, _make_kp_row


class TestBuildKpPayload:
    def test_valid_snapshot_full_payload(self):
        kp_row = _make_kp_row(options={
            "delivery_default": {"price": 100000, "qty": 1},
        })
        payload = build_kp_payload(kp_row, PRICES, MODELS, PAYMENT_TERMS)

        assert payload["spec"].get("СПЕЦ_МОДЕЛЬ_КРАТКОЕ") == "ВЕСТА-С-60-18"
        assert payload["items"][0]["id"] == "weights"
        assert any(i["id"] == "delivery" for i in payload["items"])
        assert payload["snapshot"] == kp_row["data"]
        assert payload["payment"]["preset_id"] == "split_by_items"

    def test_malformed_option_raises(self):
        # Кривой снапшот обязан кидать, а не возвращать частичный payload —
        # на этом контракте держится атомарный коммит state на странице.
        kp_row = _make_kp_row(options={
            "delivery_default": {"price": 100000, "qty": "не число"},
        })
        with pytest.raises(Exception):
            build_kp_payload(kp_row, PRICES, MODELS, PAYMENT_TERMS)

    def test_non_dict_option_raises(self):
        kp_row = _make_kp_row(options={"delivery_default": 100000})
        with pytest.raises(Exception):
            build_kp_payload(kp_row, PRICES, MODELS, PAYMENT_TERMS)
