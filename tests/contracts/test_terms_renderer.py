"""Тесты terms_renderer — динамические строки сроков."""
from src.contracts.terms_renderer import render_terms_section


def _make_spec_items(*keys: str) -> list[dict]:
    """Создать spec_items с item_key для term_days."""
    return [{"item_key": k, "customer_side": False} for k in keys]


def _make_deal(items_ids: list[dict], overrides: dict | None = None) -> dict:
    return {
        "items": items_ids,
        "scope_overrides": overrides or {},
        "flags": {},
        "delivery_address": "г. Тест",
    }


class TestDeliveryOnly:
    """Только поставка → 1 строка (scales)."""

    def test_one_line(self):
        spec_items = _make_spec_items("vesta-sl-40-18", "delivery_default")
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
        ])
        lines = render_terms_section(deal, spec_items)
        assert len(lines) == 1

    def test_contains_days(self):
        spec_items = _make_spec_items("vesta-sl-40-18")
        deal = _make_deal([{"id": "weights", "metadata": {}}])
        lines = render_terms_section(deal, spec_items)
        assert "20 (двадцати) рабочих дней" in lines[0]

    def test_delivery_refers_only_to_payment_2_1_without_foundation(self):
        spec_items = _make_spec_items("vesta-sl-40-18")
        deal = _make_deal([{"id": "weights", "metadata": {}}])
        lines = render_terms_section(deal, spec_items)

        assert "в соответствии с п.2.1 настоящей Спецификации" in lines[0]
        assert "п.2.2" not in lines[0]

    def test_no_foundation_line(self):
        spec_items = _make_spec_items("vesta-sl-40-18")
        deal = _make_deal([{"id": "weights", "metadata": {}}])
        lines = render_terms_section(deal, spec_items)
        assert not any("фундамент" in ln for ln in lines)


class TestFoundationAndInstall:
    """Фундамент + монтаж → 3 строки."""

    def test_three_lines(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "foundation_std_jb",
            "install_default", "verification_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "foundation", "metadata": {"scope": "fundament_jb"}},
            {"id": "installation", "metadata": {"scope": "full"}},
            {"id": "verification", "metadata": {}},
        ])
        lines = render_terms_section(deal, spec_items)
        assert len(lines) == 3

    def test_rows_order_is_foundation_delivery_install(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "foundation_std_jb",
            "install_default", "verification_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "foundation", "metadata": {"scope": "fundament_jb"}},
            {"id": "installation", "metadata": {"scope": "full"}},
            {"id": "verification", "metadata": {}},
        ])

        lines = render_terms_section(deal, spec_items)

        assert "строительство фундамента" in lines[0]
        assert "поставка Весов" in lines[1]
        assert "монтаж Весов" in lines[2]

    def test_foundation_line_present(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "foundation_std_jb", "install_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "foundation", "metadata": {"scope": "fundament_jb"}},
            {"id": "installation", "metadata": {"scope": "full"}},
        ])
        lines = render_terms_section(deal, spec_items)
        assert any("фундамент" in ln.lower() for ln in lines)

    def test_foundation_line_has_plus_five_temperature_condition(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "foundation_std_jb", "install_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "foundation", "metadata": {"scope": "fundament_jb"}},
            {"id": "installation", "metadata": {"scope": "full"}},
        ])

        lines = render_terms_section(deal, spec_items)

        assert (
            "Работы по строительству фундамента Весов проводятся при условии "
            "среднесуточной температуры выше +5 °С."
        ) in lines[0]

    def test_delivery_refers_to_payment_2_1_and_2_2_with_foundation(self):
        spec_items = _make_spec_items("vesta-c-80-18", "foundation_std_jb")
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "foundation", "metadata": {"scope": "fundament_jb"}},
        ])

        lines = render_terms_section(deal, spec_items)

        assert "п.2.1 и п.2.2 настоящей Спецификации" in lines[1]

    def test_install_line_present(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "install_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "installation", "metadata": {"scope": "full"}},
        ])
        lines = render_terms_section(deal, spec_items)
        assert any("монтаж" in ln.lower() for ln in lines)

    def test_install_line_has_team_departure_condition(self):
        spec_items = _make_spec_items("vesta-c-80-18", "install_default")
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "installation", "metadata": {"scope": "full"}},
        ])

        lines = render_terms_section(deal, spec_items)

        assert (
            "Выезд монтажной бригады на Объект работ осуществляется при соблюдении "
            "вышеперечисленных условий и получения Подрядчиком письменного "
            "уведомления от Заказчика о готовности принять на площадку монтажа "
            "специалистов Подрядчика."
        ) in lines[1]

    def test_term_days_are_written_with_genitive_words(self, monkeypatch):
        monkeypatch.setattr(
            "src.contracts.terms_renderer._role_days",
            lambda spec_items: {"scales": 30, "foundation": 14, "install": 3},
        )
        spec_items = _make_spec_items(
            "vesta-c-80-18", "foundation_std_jb", "install_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "foundation", "metadata": {"scope": "fundament_jb"}},
            {"id": "installation", "metadata": {"scope": "full"}},
        ])

        lines = render_terms_section(deal, spec_items)

        assert "14 (четырнадцати) рабочих дней" in lines[0]
        assert "30 (тридцати) рабочих дней" in lines[1]


class TestCustomerBuilds:
    """Заказчик строит фундамент → нет строки фундамента."""

    def test_no_foundation_line(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "install_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "installation", "metadata": {"scope": "full"}},
        ], overrides={"foundation_scope": "customer_builds"})
        lines = render_terms_section(deal, spec_items)
        assert not any("фундамент" in ln.lower() for ln in lines)

    def test_two_lines_delivery_and_install(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "install_default", "verification_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "installation", "metadata": {"scope": "full"}},
            {"id": "verification", "metadata": {}},
        ], overrides={"foundation_scope": "customer_builds"})
        lines = render_terms_section(deal, spec_items)
        assert len(lines) == 2

    def test_rows_order_is_delivery_install_without_contractor_foundation(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "install_default", "verification_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "installation", "metadata": {"scope": "full"}},
            {"id": "verification", "metadata": {}},
        ], overrides={"foundation_scope": "customer_builds"})

        lines = render_terms_section(deal, spec_items)

        assert "поставка Весов" in lines[0]
        assert "монтаж Весов" in lines[1]


class TestVerificationScopeInTerms:
    """B11: сроки не обещают поверку, которую организует заказчик."""

    def test_customer_scope_omits_verification(self):
        spec_items = _make_spec_items("vesta-c-80-18", "install_default")
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "installation", "metadata": {"scope": "full"}},
        ], overrides={"foundation_scope": "customer_builds", "verification_scope": "customer"})

        lines = render_terms_section(deal, spec_items)

        assert "монтаж Весов" in lines[1]
        assert "поверка Весов" not in lines[1]

    def test_supplier_scope_keeps_verification(self):
        spec_items = _make_spec_items(
            "vesta-c-80-18", "install_default", "verification_default",
        )
        deal = _make_deal([
            {"id": "weights", "metadata": {}},
            {"id": "installation", "metadata": {"scope": "full"}},
            {"id": "verification", "metadata": {}},
        ], overrides={"foundation_scope": "customer_builds"})

        lines = render_terms_section(deal, spec_items)

        assert "монтаж Весов и поверка Весов" in lines[1]
