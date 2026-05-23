"""Тесты загрузчика и валидатора data/clauses.yaml."""
from pathlib import Path
import pytest

CLAUSES_PATH = Path("data/clauses.yaml")


class TestSuccessfulLoad:
    def test_loads_28_clauses(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        all_clauses = [
            c
            for s in lib.get_sections()
            for c in lib.get_clauses_for_section(s.id)
        ]
        assert len(all_clauses) == 28

    def test_four_sections_with_numbers(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        sections = {s.id: s for s in lib.get_sections()}
        assert sections["obligations_supplier"].section_number == 4
        assert sections["obligations_customer"].section_number == 5
        assert sections["special_conditions"].section_number == 6
        assert sections["final"].section_number == 7

    def test_all_applies_when_parse(self):
        """Все applies_when в YAML разбираются без ошибок."""
        from src.contracts.clauses_loader import load_clauses
        load_clauses(CLAUSES_PATH)

    def test_collect_jinja_placeholders(self):
        """YAML содержит ожидаемые jinja-параметры в текстах."""
        from src.contracts.clauses_loader import load_clauses
        import re
        lib = load_clauses(CLAUSES_PATH)
        all_text = " ".join(
            c.text
            for s in lib.get_sections()
            for c in lib.get_clauses_for_section(s.id)
        )
        placeholders = set(re.findall(r'\{\{\s*(\w+)\s*\}\}', all_text))
        assert "foundation_term_days_by_customer" in placeholders
        assert "scales_or_with_orion" in placeholders
        assert "install_site_label" in placeholders
        assert "obligations_range" in placeholders
        assert "delivery_address_text" in placeholders

    def test_get_clauses_for_section(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        supplier = lib.get_clauses_for_section("obligations_supplier")
        assert len(supplier) == 3
        ids = [c.id for c in supplier]
        assert "supplier_prepares_docs" in ids

    def test_clause_order_field_present(self):
        from src.contracts.clauses_loader import load_clauses
        lib = load_clauses(CLAUSES_PATH)
        for s in lib.get_sections():
            for c in lib.get_clauses_for_section(s.id):
                assert isinstance(c.order, int)


class TestValidationErrors:
    def test_duplicate_id_raises(self, tmp_path):
        from src.contracts.clauses_loader import load_clauses
        yaml_text = """
sections:
  - id: s1
    title: "S1"
    section_number: 1
clauses:
  - id: dup
    section: s1
    order: 1
    applies_when: 'true'
    text: "First"
  - id: dup
    section: s1
    order: 2
    applies_when: 'true'
    text: "Second"
"""
        p = tmp_path / "bad.yaml"
        p.write_text(yaml_text, encoding="utf-8")
        with pytest.raises(ValueError, match="Дублирующийся id"):
            load_clauses(p)

    def test_unknown_section_raises(self, tmp_path):
        from src.contracts.clauses_loader import load_clauses
        yaml_text = """
sections:
  - id: s1
    title: "S1"
    section_number: 1
clauses:
  - id: c1
    section: nonexistent
    order: 1
    applies_when: 'true'
    text: "text"
"""
        p = tmp_path / "bad2.yaml"
        p.write_text(yaml_text, encoding="utf-8")
        with pytest.raises(ValueError, match="неизвестная section"):
            load_clauses(p)

    def test_invalid_applies_when_raises(self, tmp_path):
        from src.contracts.clauses_loader import load_clauses
        yaml_text = """
sections:
  - id: s1
    title: "S1"
    section_number: 1
clauses:
  - id: c1
    section: s1
    order: 1
    applies_when: 'evil_func()'
    text: "text"
"""
        p = tmp_path / "bad3.yaml"
        p.write_text(yaml_text, encoding="utf-8")
        with pytest.raises(ValueError, match="ошибка applies_when"):
            load_clauses(p)
