"""Тесты build_specification_items."""
from __future__ import annotations

import logging
from pathlib import Path


def _make_kp_row(
    model_line: str = "С",
    model_max: int = 60,
    model_length: int = 18,
    model_price: int = 2_835_000,
    options: dict | None = None,
) -> dict:
    return {
        "kp_number": "КП-2026-001",
        "model_id": f"vesta-{model_line.lower()}-{model_max}-{model_length}",
        "data": {
            "model": {
                "line": model_line, "max": model_max,
                "length": model_length, "price": model_price,
            },
            "options": options or {},
        },
    }


class TestBuildSpecificationItems:
    def test_minimal_has_weights(self):
        """Без опций → одна позиция 'weights'."""
        from src.contracts.from_kp import build_specification_items
        items = build_specification_items(_make_kp_row())
        assert len(items) == 1
        assert items[0]["id"] == "weights"
        assert items[0]["name"].startswith("Весы автомобильные ВЕСТА-С-60-18-Ц")
        assert items[0]["total"] == 2_835_000
        assert items[0]["is_custom"] is False
        assert items[0]["source"] == "preset"

    def test_delivery_option_mapped(self):
        """delivery_default → id='delivery', не кастомная."""
        from src.contracts.from_kp import build_specification_items
        opts = {"delivery_default": {"qty": 1, "price": 50_000, "customer_side": False}}
        items = build_specification_items(_make_kp_row(options=opts))
        delivery = next(i for i in items if i["id"] == "delivery")
        assert delivery["name"] == "Доставка весов до объекта"
        assert delivery["total"] == 50_000
        assert delivery["is_custom"] is False

    def test_foundation_with_metadata_scope(self):
        """foundation_s_f_18 → id='foundation', metadata.scope='fundament_jb'."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "foundation_s_f_18": {"qty": 1, "price": 350_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        found = next(i for i in items if i["id"] == "foundation")
        assert found["metadata"]["scope"] == "fundament_jb"
        assert found["total"] == 350_000

    def test_verification_customer_side(self):
        """customer_side=True → total=0, metadata.customer_side=True."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "verification_default": {
                "qty": 1, "price": 30_000, "customer_side": True,
            },
        }
        items = build_specification_items(_make_kp_row(options=opts))
        ver = next(i for i in items if i["id"] == "verification")
        assert ver["total"] == 0.0
        assert ver["metadata"]["customer_side"] is True

    def test_unknown_key_becomes_custom(self, caplog):
        """Неизвестный ключ опции → is_custom=True, WARNING в логе."""
        from src.contracts.from_kp import build_specification_items
        opts = {"future_unknown_42": {"qty": 1, "price": 99_000, "customer_side": False}}
        with caplog.at_level(logging.WARNING, logger="src.contracts.from_kp"):
            items = build_specification_items(_make_kp_row(options=opts))
        custom = next(i for i in items if i["is_custom"])
        assert custom["id"].startswith("custom_")
        assert custom["source"] == "custom"
        assert any("future_unknown_42" in m for m in caplog.messages)

    def test_sort_order(self):
        """weights < foundation < installation < verification < delivery."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "delivery_default": {"qty": 1, "price": 50_000, "customer_side": False},
            "install_default": {"qty": 1, "price": 80_000, "customer_side": False},
            "verification_default": {"qty": 1, "price": 30_000, "customer_side": False},
            "foundation_s_f_18": {"qty": 1, "price": 350_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        ids = [i["id"] for i in items]
        assert ids.index("weights") < ids.index("foundation")
        assert ids.index("foundation") < ids.index("installation")
        assert ids.index("installation") < ids.index("verification")
        assert ids.index("verification") < ids.index("delivery")

    def test_installation_scope_with_foundation(self):
        """install_default + foundation → scope='fundament'."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "install_default": {"qty": 1, "price": 80_000, "customer_side": False},
            "foundation_s_f_18": {"qty": 1, "price": 350_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        inst = next(i for i in items if i["id"] == "installation")
        assert inst["metadata"]["scope"] == "fundament"

    def test_total_equals_price(self):
        """total == price (qty=1 always for standard options)."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "install_default": {"qty": 1, "price": 80_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        inst = next(i for i in items if i["id"] == "installation")
        assert inst["total"] == inst["quantity"] * inst["price_per_unit"]
