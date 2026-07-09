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
        """weights < foundation < delivery < installation < verification (FIX_SPEC E3a)."""
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
        assert ids.index("foundation") < ids.index("delivery")
        assert ids.index("delivery") < ids.index("installation")
        assert ids.index("installation") < ids.index("verification")

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


class TestRecalculateTotals:
    def test_price_change_recalculates_total(self):
        """Изменение price_per_unit → total пересчитывается как quantity * price_per_unit."""
        from src.contracts.spec_items import recalculate_totals

        items = [
            {"id": "weights", "name": "Весы", "unit": "компл",
             "quantity": 2.0, "price_per_unit": 150_000.0, "total": 100_000.0,
             "payment_group": None, "is_custom": False, "source": "preset", "metadata": {}},
        ]
        result = recalculate_totals(items)
        assert result[0]["total"] == 300_000.0


class TestCustomItemFlow:
    def test_add_custom_item_appears_in_items(self):
        """Симуляция нажатия '+ Добавить позицию': кастомная позиция появляется в state."""
        from src.contracts.spec_items import make_custom_item

        initial_items = [
            {"id": "weights", "name": "Весы ВЕСТА-С-60-18",
             "unit": "компл", "quantity": 1.0,
             "price_per_unit": 2_835_000.0, "total": 2_835_000.0,
             "payment_group": None, "is_custom": False,
             "source": "preset", "metadata": {}},
        ]
        items = list(initial_items)
        items.append(make_custom_item(name="Тестовая позиция", price_per_unit=10_000.0))

        custom = next(i for i in items if i["is_custom"])
        assert custom["id"].startswith("custom_")
        assert custom["name"] == "Тестовая позиция"
        assert custom["source"] == "custom"
        assert len(items) == 2

    def test_custom_item_appears_in_docx(self, tmp_path):
        """Кастомная позиция попадает в Table[0] DOCX."""
        import os
        from docx import Document
        from src.contracts.spec_items import make_custom_item
        from src.contracts.filler import fill_spec_with_items
        from tests.contracts.test_filler import SPEC_MOCK_DATA, SPEC_TEMPLATE_PATH

        items = [
            {"id": "weights", "name": "Весы автомобильные ВЕСТА-С-60-18-Ц",
             "unit": "компл", "quantity": 1.0,
             "price_per_unit": 2_835_000.0, "total": 2_835_000.0,
             "payment_group": None, "is_custom": False,
             "source": "preset", "metadata": {}},
            make_custom_item(name="Кастомное оборудование", price_per_unit=100_000.0),
        ]

        template = os.path.normpath(SPEC_TEMPLATE_PATH)
        output = str(tmp_path / "spec_custom.docx")

        fill_spec_with_items(template, SPEC_MOCK_DATA, items, output)

        doc = Document(output)
        table = doc.tables[0]
        all_text = " ".join(c.text for row in table.rows for c in row.cells)
        assert "Кастомное оборудование" in all_text
        assert len(table.rows) == 1 + len(items) + 1  # header + 2 + total


class TestNewFoundationKeyMapping:
    """construction_works_* и concrete_base_on_frame → spec_id='foundation'."""

    def test_construction_works_maps_to_foundation(self):
        """construction_works_18 → id='foundation', не кастомная."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "construction_works_18": {"qty": 1, "price": 400_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        found = next(i for i in items if i["id"] == "foundation")
        assert found["is_custom"] is False
        assert found["metadata"]["scope"] == "contractor_with_materials"
        assert found["total"] == 400_000

    def test_concrete_base_maps_to_foundation(self):
        """concrete_base_on_frame → id='foundation', scope='rama_concrete'."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "concrete_base_on_frame": {"qty": 1, "price": 550_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        found = next(i for i in items if i["id"] == "foundation")
        assert found["is_custom"] is False
        assert found["metadata"]["scope"] == "rama_concrete"
        assert found["total"] == 550_000

    def test_foundation_supervision_maps_to_foundation(self):
        """foundation_supervision → id='foundation', scope='contractor_supervised'."""
        from src.contracts.from_kp import build_specification_items
        opts = {
            "foundation_supervision": {"qty": 1, "price": 120_000, "customer_side": False},
        }
        items = build_specification_items(_make_kp_row(options=opts))
        found = next(i for i in items if i["id"] == "foundation")
        assert found["is_custom"] is False
        assert found["metadata"]["scope"] == "contractor_supervised"
