"""Тесты: override-флаги и scope_overrides → корректные clauses в предпросмотре."""
from __future__ import annotations


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


def _clause_ids(result: dict) -> set[str]:
    return {c.id for clauses in result.values() for c in clauses}


class TestWinterConcreteFlag:
    def test_winter_concrete_true_adds_surcharge(self):
        """flags.winter_concrete=True → clause winter_concrete_surcharge появляется."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [_item("weights"), _item("foundation", {"scope": "contractor_full"})],
            "scope_overrides": {},
            "flags": {"winter_concrete": True},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "winter_concrete_surcharge" in _clause_ids(result)

    def test_winter_concrete_false_no_surcharge(self):
        """flags.winter_concrete=False → clause winter_concrete_surcharge отсутствует."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [_item("weights"), _item("foundation", {"scope": "contractor_full"})],
            "scope_overrides": {},
            "flags": {"winter_concrete": False},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "winter_concrete_surcharge" not in _clause_ids(result)


class TestFoundationScopeOverride:
    def test_foundation_scope_rama_override(self):
        """scope_overrides.foundation_scope='rama' → clause customer_provides_flat_area_for_rama."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],  # нет items → используется override
            "scope_overrides": {"foundation_scope": "rama"},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "customer_provides_flat_area_for_rama" in _clause_ids(result)

    def test_foundation_scope_none_by_default(self):
        """Без items и overrides → foundation_scope='none', rama-clause отсутствует."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],
            "scope_overrides": {},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "customer_provides_flat_area_for_rama" not in _clause_ids(result)


class TestVerificationScopeOverride:
    def test_verification_scope_customer_override(self):
        """scope_overrides.verification_scope='customer' → clause customer_organizes_verification."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],
            "scope_overrides": {"verification_scope": "customer"},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "customer_organizes_verification" in _clause_ids(result)

    def test_verification_scope_supplier_override(self):
        """scope_overrides.verification_scope='supplier' → clause supplier_prepares_docs."""
        from src.contracts.clauses_renderer import build_contract_clauses

        deal = {
            "items": [],
            "scope_overrides": {"verification_scope": "supplier"},
            "flags": {},
            "delivery_address": "",
        }
        result = build_contract_clauses(deal)
        assert "supplier_prepares_docs" in _clause_ids(result)
