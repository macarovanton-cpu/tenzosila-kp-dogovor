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
        assert "20 рабочих дней" in lines[0]

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
