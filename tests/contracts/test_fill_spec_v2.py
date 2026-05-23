"""Тесты fill_spec_v2 — спецификация с динамическими clauses."""
import os

import pytest
from docx import Document

from src.contracts.spec_v2_filler import fill_spec_v2

SPEC_V2_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'templates', 'contracts', 'spec_v2.docx'
))

MOCK_DATA = {
    "ДОГОВОР_НОМЕР": "Т-001/2026",
    "ДОГОВОР_ДАТА_ПОЛНАЯ": "15.03.2026",
    "ДОГОВОР_ДЕНЬ": "15",
    "ДОГОВОР_МЕСЯЦ": "марта",
    "ДОГОВОР_ГОД": "2026",
    "СПЕЦ_НОМЕР": "1",
    "СПЕЦ_НДС": "22",
    "СПЕЦ_ОПЛАТА_П1": "Предоплата 30%",
    "СПЕЦ_ОПЛАТА_П2": "Оплата по отгрузке 70%",
    "СПЕЦ_ОПЛАТА_П3": "",
    "СПЕЦ_ОПЛАТА_П4": "",
    "СПЕЦ_ОПЛАТА_П5": "",
    "СПЕЦ_ОПЛАТА_П6": "",
    "СПЕЦ_СРОК_ПОСТАВКИ": "30",
    "СПЕЦ_СРОК_ФУНДАМЕНТ": "20",
    "СПЕЦ_СРОК_МОНТАЖ": "10",
    "СПЕЦ_АДРЕС_ОБЪЕКТА": "г. Тест",
    "СПЕЦ_МОДЕЛЬ_КРАТКОЕ": "ВЕСТА-С-60-18",
    "СПЕЦ_МАКС_НАГРУЗКА": "60",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "Директор",
    "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": "ООО «Тест»",
    "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "ООО «Тест»",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_КРАТКОЕ": "Тестов Т.Т.",
    "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "Т.Т. Тестов",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП": "директора",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП": "Тестова Тимофея Тимофеевича",
    "ЗАКАЗЧИК_ОСНОВАНИЕ": "Устава",
    "ДИРЕКТОР_ПРИЧАСТИЕ": "действующего",
}


def _item(id: str, metadata: dict | None = None) -> dict:
    return {
        "id": id, "name": f"Позиция {id}", "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100_000.0, "total": 100_000.0,
        "payment_group": None, "is_custom": False, "source": "preset",
        "metadata": metadata or {},
    }


class TestFillSpecV2Minimal:
    """Минимальный кейс: поставка без монтажа → только секция 7 (final)."""

    def test_only_final_section(self, tmp_path):
        items = [_item("weights"), _item("delivery")]
        deal = {"items": items, "delivery_address": "г. Тест"}
        output = str(tmp_path / "spec_v2_min.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        all_text = "\n".join(p.text for p in doc.paragraphs)

        assert "7. Заключительные положения" in all_text
        assert "7.1." in all_text
        assert "7.2." in all_text

        assert "4. Обязательства Подрядчика" not in all_text
        assert "5. Обязательства Заказчика" not in all_text
        assert "6. Особые условия" not in all_text

    def test_markers_removed(self, tmp_path):
        items = [_item("weights")]
        deal = {"items": items, "delivery_address": "г. Тест"}
        output = str(tmp_path / "spec_v2_markers.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "CLAUSE_SECTION" not in all_text

    def test_items_table_has_correct_rows(self, tmp_path):
        items = [_item("weights"), _item("delivery")]
        deal = {"items": items, "delivery_address": "г. Тест"}
        output = str(tmp_path / "spec_v2_table.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        table = doc.tables[0]
        # header + 2 items + total = 4
        assert len(table.rows) == 4


class TestFillSpecV2Medium:
    """Средний кейс: монтаж → секции 4, 5, 7 (7 пунктов)."""

    def _make_deal(self):
        items = [
            _item("weights"),
            _item("installation", {"scope": "full"}),
            _item("verification"),
        ]
        return {
            "items": items,
            "scope_overrides": {},
            "flags": {},
            "delivery_address": "г. Кемерово, пр-т Кузнецкий, 15",
        }, items

    def test_three_sections_present(self, tmp_path):
        deal, items = self._make_deal()
        output = str(tmp_path / "spec_v2_med.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        all_text = "\n".join(p.text for p in doc.paragraphs)

        assert "4. Обязательства Подрядчика" in all_text
        assert "5. Обязательства Заказчика" in all_text
        assert "7. Заключительные положения" in all_text
        assert "6. Особые условия" not in all_text

    def test_seven_clause_numbers(self, tmp_path):
        deal, items = self._make_deal()
        output = str(tmp_path / "spec_v2_med_cnt.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        all_text = "\n".join(p.text for p in doc.paragraphs)

        assert "4.1." in all_text
        assert "5.1." in all_text
        assert "5.4." in all_text
        assert "7.1." in all_text
        assert "7.2." in all_text
        # 5.5 не должно быть в этом сценарии
        assert "5.5." not in all_text

    def test_delivery_address_substituted(self, tmp_path):
        deal, items = self._make_deal()
        output = str(tmp_path / "spec_v2_med_addr.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "г. Кемерово" in all_text


class TestFillSpecV2Max:
    """Максимальный кейс: фундамент+монтаж+ОРИОН → все 4 секции, 14 пунктов."""

    def _make_deal(self):
        items = [
            _item("weights"),
            _item("foundation", {"scope": "fundament_jb"}),
            _item("installation", {"scope": "full"}),
            _item("verification"),
            _item("orion"),
            _item("orion_install"),
        ]
        return {
            "items": items,
            "scope_overrides": {},
            "flags": {},
            "delivery_address": "г. Тест",
        }, items

    def test_all_four_sections(self, tmp_path):
        deal, items = self._make_deal()
        output = str(tmp_path / "spec_v2_max.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        all_text = "\n".join(p.text for p in doc.paragraphs)

        assert "4. Обязательства Подрядчика" in all_text
        assert "5. Обязательства Заказчика" in all_text
        assert "6. Особые условия" in all_text
        assert "7. Заключительные положения" in all_text

    def test_fourteen_clauses(self, tmp_path):
        deal, items = self._make_deal()
        output = str(tmp_path / "spec_v2_max_cnt.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        import re
        # Ищем параграфы вида "N.M. текст" (auto_number + точка)
        clause_paras = [
            p for p in doc.paragraphs
            if re.match(r'^\d+\.\d+\.', p.text.strip())
        ]
        assert len(clause_paras) == 14

    def test_key_clause_texts(self, tmp_path):
        deal, items = self._make_deal()
        output = str(tmp_path / "spec_v2_max_txt.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        all_text = "\n".join(p.text for p in doc.paragraphs)

        assert "Подрядчик обеспечивает подготовку" in all_text
        assert "автокран" in all_text
        assert "ОРИОН" in all_text
        assert "4.1-6.2" in all_text

    def test_items_table_intact(self, tmp_path):
        deal, items = self._make_deal()
        output = str(tmp_path / "spec_v2_max_tbl.docx")

        fill_spec_v2(SPEC_V2_PATH, MOCK_DATA, items, deal, output)

        doc = Document(output)
        table = doc.tables[0]
        # header + 6 items + total = 8
        assert len(table.rows) == 8
