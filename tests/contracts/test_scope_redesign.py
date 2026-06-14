"""Тесты редизайна foundation_scope (docs/scope_redesign_2026-06-13.md).

Параметризованный перебор по таблице из спеки.
"""
from __future__ import annotations

import pytest


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


def _clause_ids(result: dict) -> set[str]:
    return {c.id for clauses in result.values() for c in clauses}


# ---------------------------------------------------------------------------
# contractor_supervised
# ---------------------------------------------------------------------------

class TestContractorSupervised:
    """Позиция «Курирование строительства фундамента» → scope contractor_supervised."""

    def _deal(self) -> dict:
        return {
            "items": [
                _item("weights"),
                _item("foundation", {"scope": "contractor_supervised"}),
                _item("installation", {"scope": "full"}),
            ],
            "scope_overrides": {},
            "flags": {},
            "delivery_address": "",
        }

    def test_context_scope(self):
        from src.contracts.clauses_context import build_clauses_context
        ctx = build_clauses_context(self._deal())
        assert ctx["foundation_scope"] == "contractor_supervised"

    def test_supplier_supervises_clause_present(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "supplier_supervises_foundation_construction" in ids

    def test_customer_builds_clauses_present(self):
        """Заказчик строит по Прил.№1 + фото — применимы и при курировании."""
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "customer_builds_foundation_per_spec" in ids
        assert "customer_provides_foundation_photos" in ids

    def test_dispatches_team_clause_absent(self):
        """supplier_dispatches_construction_team — НЕ применим при курировании."""
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "supplier_dispatches_construction_team" not in ids

    def test_existing_foundation_clause_absent(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "scales_for_existing_foundation" not in ids


# ---------------------------------------------------------------------------
# existing_foundation (только ручной override менеджера)
# ---------------------------------------------------------------------------

class TestExistingFoundation:
    """scope_overrides.foundation_scope='existing_foundation' → оговорка, ноль обязательств."""

    def _deal(self) -> dict:
        return {
            "items": [_item("weights")],
            "scope_overrides": {"foundation_scope": "existing_foundation"},
            "flags": {},
            "delivery_address": "",
        }

    def test_context_scope(self):
        from src.contracts.clauses_context import build_clauses_context
        ctx = build_clauses_context(self._deal())
        assert ctx["foundation_scope"] == "existing_foundation"

    def test_ogovorka_clause_present(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "scales_for_existing_foundation" in ids

    def test_customer_builds_clauses_absent(self):
        """Обязательств по стройке у заказчика нет."""
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "customer_builds_foundation_per_spec" not in ids
        assert "customer_provides_foundation_photos" not in ids

    def test_supplier_supervises_absent(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "supplier_supervises_foundation_construction" not in ids


# ---------------------------------------------------------------------------
# customer_builds (явный override)
# ---------------------------------------------------------------------------

class TestCustomerBuilds:
    def _deal(self) -> dict:
        return {
            "items": [_item("weights")],
            "scope_overrides": {"foundation_scope": "customer_builds"},
            "flags": {},
            "delivery_address": "",
        }

    def test_customer_builds_clauses_present(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "customer_builds_foundation_per_spec" in ids
        assert "customer_provides_foundation_photos" in ids

    def test_ogovorka_absent(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "scales_for_existing_foundation" not in ids

    def test_supervises_absent(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        ids = _clause_ids(build_contract_clauses(self._deal()))
        assert "supplier_supervises_foundation_construction" not in ids


# ---------------------------------------------------------------------------
# Дефолт scope гейтится монтажом
# ---------------------------------------------------------------------------

class TestDefaultScopeGating:
    def test_with_installation_gives_customer_builds(self):
        """Нет позиции фундамента + есть монтаж → дефолт customer_builds."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("installation", {"scope": "full"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "customer_builds"

    def test_without_installation_gives_none(self):
        """Нет позиции фундамента + нет монтажа (чистая поставка) → none."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [_item("weights"), _item("delivery")]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "none"

    def test_shefmontazh_gives_customer_builds(self):
        """Шеф-монтаж тоже считается монтажом для гейта."""
        from src.contracts.clauses_context import build_clauses_context
        deal = {"items": [
            _item("weights"),
            _item("installation", {"scope": "shefmontazh"}),
        ]}
        ctx = build_clauses_context(deal)
        assert ctx["foundation_scope"] == "customer_builds"

    def test_customer_builds_clauses_appear_with_install(self):
        """При монтаже без позиции фундамента — customer-клозы стройки появляются в договоре."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {
            "items": [
                _item("weights"),
                _item("installation", {"scope": "full"}),
            ],
            "scope_overrides": {},
            "flags": {},
            "delivery_address": "",
        }
        ids = _clause_ids(build_contract_clauses(deal))
        assert "customer_builds_foundation_per_spec" in ids
        assert "customer_provides_foundation_photos" in ids


# ---------------------------------------------------------------------------
# Оплаченная позиция (foundation_supervision) → клоз курирования
# ---------------------------------------------------------------------------

class TestPaidPositionContractorSupervised:
    """build_specification_items с foundation_supervision → item.scope = contractor_supervised
    → ≥1 клоз-обязательство по курированию в договоре.
    """

    def test_foundation_supervision_option_yields_supervises_clause(self):
        from src.contracts.from_kp import build_specification_items
        from src.contracts.clauses_renderer import build_contract_clauses

        kp_row = {
            "model_id": "vesta-s-100-24",
            "data": {
                "model": {"line": "С", "max": 100, "length": 24, "width": 3.0, "price": 1_000_000},
                "options": {
                    "foundation_supervision": {
                        "qty": 1, "price": 80_000, "customer_side": False,
                    },
                    "install_default": {
                        "qty": 1, "price": 50_000, "customer_side": False,
                    },
                },
            },
        }
        items = build_specification_items(kp_row)
        found = next((it for it in items if it["id"] == "foundation"), None)
        assert found is not None
        assert found["metadata"].get("scope") == "contractor_supervised"

        deal = {"items": items, "scope_overrides": {}, "flags": {}, "delivery_address": ""}
        ids = _clause_ids(build_contract_clauses(deal))
        assert "supplier_supervises_foundation_construction" in ids


# ---------------------------------------------------------------------------
# Зимний гейт (winter_surcharge_allowed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scope, expected", [
    ("contractor_full", True),
    ("contractor_with_materials", True),
    ("customer_builds", False),
    ("existing_foundation", False),
    ("contractor_supervised", False),
    ("rama", False),
    ("none", False),
])
def test_winter_surcharge_allowed(scope: str, expected: bool):
    """winter_surcharge_allowed возвращает True только для cf и cwm."""
    from src.contracts.clauses_context import winter_surcharge_allowed
    assert winter_surcharge_allowed(scope) is expected
