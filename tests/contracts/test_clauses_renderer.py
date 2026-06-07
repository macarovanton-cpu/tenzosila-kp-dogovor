"""Тесты build_contract_clauses — нумерация, фильтрация, jinja-подстановка."""
import pytest


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": id, "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100.0, "total": 100.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


def _make_montazh_deal() -> dict:
    """Сценарий: монтаж full + поверка подрядчиком, нет фундамента, нет ОРИОН."""
    return {
        "items": [
            _item("weights"),
            _item("installation", {"scope": "full"}),
            _item("verification"),
        ],
        "scope_overrides": {},
        "flags": {},
        "delivery_address": "г. Тест, ул. Промышленная",
    }


def _make_max_deal() -> dict:
    """Сценарий: фундамент+монтаж+ОРИОН (14 пунктов)."""
    return {
        "items": [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
            _item("verification"),
            _item("orion"),
            _item("orion_install"),
        ],
        "scope_overrides": {},
        "flags": {},
        "delivery_address": "г. Тест",
    }


def _make_foundation_install_deal() -> dict:
    """Сценарий: фундамент+монтаж+поверка без ОРИОН (10 пунктов)."""
    return {
        "items": [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
            _item("verification"),
        ],
        "scope_overrides": {},
        "flags": {},
        "delivery_address": "г. Тест",
    }


class TestClauseCount:
    def test_montazh_7_clauses(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_montazh_deal())
        all_ids = [c.id for section_clauses in result.values() for c in section_clauses]
        assert len(all_ids) == 7
        expected_ids = {
            "supplier_prepares_docs",
            "customer_unable_to_accept_team_delays_work",
            "customer_provides_scales_near_install_site",
            "customer_provides_crane",
            "customer_provides_test_vehicle",
            "cross_reference_to_contract",
            "delivery_address",
        }
        assert set(all_ids) == expected_ids

    def test_max_14_clauses(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_max_deal())
        all_ids = [c.id for section_clauses in result.values() for c in section_clauses]
        assert len(all_ids) == 14
        expected_ids = {
            "supplier_prepares_docs",
            "supplier_dispatches_construction_team_with_orion_poles",
            "customer_unable_to_accept_team_delays_work",
            "customer_provides_flat_area_for_construction",
            "customer_provides_scales_near_install_site",
            "customer_provides_crane",
            "customer_provides_test_vehicle",
            "customer_provides_power_220V",
            "customer_installs_high_cameras_supervised",
            "customer_provides_pc_for_orion",
            "additional_work_during_construction",
            "orion_oversized_vehicle",
            "cross_reference_to_contract",
            "delivery_address",
        }
        assert set(all_ids) == expected_ids

    def test_postavka_only_final(self):
        """Поставка без монтажа → только final секция (cross_reference + delivery)."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {"items": [_item("weights"), _item("delivery")], "delivery_address": "г. Тест"}
        result = build_contract_clauses(deal)
        all_ids = [c.id for section_clauses in result.values() for c in section_clauses]
        assert len(all_ids) == 2
        assert "cross_reference_to_contract" in all_ids
        assert "delivery_address" in all_ids


class TestAutoNumbering:
    def test_flat_numbers_start_at_4(self):
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_max_deal())

        all_clauses = [
            clause
            for section_clauses in result.values()
            for clause in section_clauses
        ]
        assert [c.auto_number for c in all_clauses] == [
            str(n) for n in range(4, 18)
        ]

        supp = result.get("obligations_supplier", [])
        assert supp[0].auto_number == "4"
        assert supp[1].auto_number == "5"

        final = result.get("final", [])
        assert final[0].auto_number == "16"

    def test_obligations_customer_ordered_by_order_field(self):
        """Пункты внутри секции отсортированы по полю order."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_montazh_deal())
        cust = result.get("obligations_customer", [])
        # customer_unable_to_accept_team_delays_work (order=5) идёт первым
        assert cust[0].id == "customer_unable_to_accept_team_delays_work"


class TestJinjaSubstitution:
    def test_scales_or_with_orion_no_orion(self):
        """Без ОРИОН: 'Весы' (не 'Весы и комплект ПАК «ОРИОН»')."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_montazh_deal())
        cust = result.get("obligations_customer", [])
        scales_clause = next(
            (c for c in cust if c.id == "customer_provides_scales_near_install_site"), None
        )
        assert scales_clause is not None
        assert "Весы" in scales_clause.text
        assert "ОРИОН" not in scales_clause.text

    def test_scales_or_with_orion_with_orion(self):
        """С ОРИОН: 'Весы и комплект ПАК «ОРИОН»' в тексте пункта."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_max_deal())
        cust = result.get("obligations_customer", [])
        scales_clause = next(
            (c for c in cust if c.id == "customer_provides_scales_near_install_site"), None
        )
        assert scales_clause is not None
        assert "ОРИОН" in scales_clause.text

    def test_obligations_range_in_cross_reference(self):
        """cross_reference_to_contract содержит рассчитанный obligations_range."""
        from src.contracts.clauses_renderer import build_contract_clauses
        result = build_contract_clauses(_make_foundation_install_deal())
        cust = result.get("obligations_customer", [])
        unable = next(
            c for c in cust if c.id == "customer_unable_to_accept_team_delays_work"
        )
        final_clauses = result.get("final", [])
        cross_ref = next(
            (c for c in final_clauses if c.id == "cross_reference_to_contract"), None
        )
        assert cross_ref is not None
        assert unable.auto_number == "6"
        assert "7-11" in cross_ref.text

    def test_delivery_address_substituted(self):
        """delivery_address_text подставляется в текст clause delivery_address."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {**_make_montazh_deal(), "delivery_address": "г. Кемерово, пр-т Кузнецкий, 15"}
        result = build_contract_clauses(deal)
        final_clauses = result.get("final", [])
        addr_clause = next(
            (c for c in final_clauses if c.id == "delivery_address"), None
        )
        assert addr_clause is not None
        assert "г. Кемерово" in addr_clause.text

    def test_foundation_term_default(self):
        """customer_builds_foundation_per_spec: дефолтный срок 60 дней если не задан в metadata."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {
            "items": [
                _item("weights"),
                _item("foundation", {"scope": "customer_builds"}),
            ],
            "delivery_address": "г. Тест",
        }
        result = build_contract_clauses(deal)
        cust = result.get("obligations_customer", [])
        found = next((c for c in cust if c.id == "customer_builds_foundation_per_spec"), None)
        assert found is not None
        assert "60" in found.text

    def test_foundation_term_from_metadata(self):
        """customer_builds_foundation_per_spec: срок из metadata.construction_term_days_by_customer."""
        from src.contracts.clauses_renderer import build_contract_clauses
        deal = {
            "items": [
                _item("weights"),
                _item("foundation", {
                    "scope": "customer_builds",
                    "construction_term_days_by_customer": 45,
                }),
            ],
            "delivery_address": "г. Тест",
        }
        result = build_contract_clauses(deal)
        cust = result.get("obligations_customer", [])
        found = next((c for c in cust if c.id == "customer_builds_foundation_per_spec"), None)
        assert found is not None
        assert "45" in found.text
