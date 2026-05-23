"""Тесты build_clauses_context — 9 эталонных сценариев."""
import pytest


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


class TestNineScenarios:
    """9 эталонных кейсов из архитектурного документа."""

    def test_1_postavka(self):
        """Поставка: только весы и доставка — нет монтажа/фундамента."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("weights"), _item("delivery")]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "none"
        assert ctx["installation_scope"] == "none"
        assert ctx["verification_scope"] == "none"
        assert ctx["has_orion"] is False
        assert ctx["orion_poles_scope"] == "none"
        assert ctx["winter_concrete"] is False

    def test_2_montazh(self):
        """Монтаж: full монтаж + поверка подрядчиком."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("installation", {"scope": "full"}),
            _item("verification"),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["installation_scope"] == "full"
        assert ctx["verification_scope"] == "supplier"
        assert ctx["foundation_scope"] == "none"
        assert ctx["has_orion"] is False

    def test_3_montazh_orion(self):
        """Монтаж + ОРИОН, без orion_install → orion_poles by_customer."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("installation", {"scope": "full"}),
            _item("orion"),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["has_orion"] is True
        assert ctx["orion_poles_scope"] == "by_customer"
        assert ctx["verification_scope"] == "none"

    def test_4_rama_montazh(self):
        """Рама + монтаж full."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("rama"),
            _item("installation", {"scope": "full"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "rama"
        assert ctx["installation_scope"] == "full"

    def test_5_rama_shefmontazh(self):
        """Рама + шеф-монтаж."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("rama"),
            _item("installation", {"scope": "shefmontazh"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "rama"
        assert ctx["installation_scope"] == "shefmontazh"

    def test_6_stroika_mat(self):
        """Стройка с материалами заказчика."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("foundation", {"scope": "contractor_with_materials"}),
            _item("installation", {"scope": "full"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "contractor_with_materials"
        assert ctx["installation_scope"] == "full"

    def test_7_fundament_montazh(self):
        """Фундамент ЖБ (contractor_full) + монтаж."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
        ]}
        ctx = build_clauses_context(deal)
        # fundament_jb → contractor_full
        assert ctx["foundation_scope"] == "contractor_full"
        assert ctx["installation_scope"] == "full"

    def test_8_fundament_zima(self):
        """Фундамент заказчика + зимний период."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {
            "items": [_item("weights"), _item("foundation", {"scope": "customer_builds"})],
            "flags": {"winter_concrete": True},
        }
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "customer_builds"
        assert ctx["winter_concrete"] is True

    def test_9_fundament_montazh_orion(self):
        """Фундамент + монтаж + ОРИОН с опорами подрядчика."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
            _item("verification"),
            _item("orion"),
            _item("orion_install"),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "contractor_full"
        assert ctx["has_orion"] is True
        assert ctx["orion_poles_scope"] == "by_contractor"
        assert ctx["verification_scope"] == "supplier"


class TestOverrides:
    def test_scope_override_replaces_items(self):
        """scope_overrides применяется когда items не содержат значения."""
        from src.contracts.clauses_context import build_clauses_context
        deal2 = {
            "items": [_item("weights")],
            "scope_overrides": {"installation_scope": "shefmontazh"},
        }
        ctx = build_clauses_context(deal2)
        assert ctx["installation_scope"] == "shefmontazh"

    def test_winter_concrete_only_from_flag(self):
        """winter_concrete=True только из явного флага, не из items."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("foundation", {"scope": "fundament_jb"})]}
        ctx = build_clauses_context(deal)
        # Нет флага → False
        assert ctx["winter_concrete"] is False

    def test_old_installation_scope_fundament_maps_to_full(self):
        """Старое значение 'fundament' из from_kp.py → installation_scope='full'."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("installation", {"scope": "fundament"})]}
        ctx = build_clauses_context(deal)
        assert ctx["installation_scope"] == "full"

    def test_old_installation_scope_rama_maps_to_full(self):
        """Старое значение 'rama' из from_kp.py → installation_scope='full'."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("installation", {"scope": "rama"})]}
        ctx = build_clauses_context(deal)
        assert ctx["installation_scope"] == "full"

    def test_verification_customer_side_true(self):
        """verification item с customer_side=True → verification_scope='customer'."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("verification", {"customer_side": True})]}
        ctx = build_clauses_context(deal)
        assert ctx["verification_scope"] == "customer"
