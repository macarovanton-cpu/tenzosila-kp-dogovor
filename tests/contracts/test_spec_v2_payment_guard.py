"""Страж A5: fill_spec_v2 не отдаёт Спецификацию с lite-строками оплаты.

Дефект: если менеджер не тронул редактор оплаты, `_payment_lines` не задан и
fill_spec_v2 падает на fallback `_payment_lines_from_data`, читающий КП-lite
слоты СПЕЦ_ОПЛАТА_П1..6 (тире-маркер, без нумерации/сумм). Страж ловит их и
рушит генерацию, чтобы брак не уехал в клиентский документ.
"""
import os

import pytest
from docx import Document

from src.contracts.spec_v2_filler import PaymentLinesLiteError, fill_spec_v2

SPEC_V2_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'templates', 'contracts', 'spec_v2.docx'
))

# Минимальный набор плейсхолдеров (шаблон рендерится без KeyError).
_BASE_DATA = {
    "ДОГОВОР_НОМЕР": "Т-001/2026",
    "ДОГОВОР_ДАТА_ПОЛНАЯ": "15.03.2026",
    "ДОГОВОР_ДЕНЬ": "15", "ДОГОВОР_МЕСЯЦ": "марта", "ДОГОВОР_ГОД": "2026",
    "СПЕЦ_НОМЕР": "1", "СПЕЦ_НДС": "22",
    "СПЕЦ_АДРЕС_ОБЪЕКТА": "г. Тест",
    "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ": "ООО «Тест»",
    "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": "ООО «Тест»",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ": "Директор",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_КРАТКОЕ": "Тестов Т.Т.",
    "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "Т.Т. Тестов",
    "ЗАКАЗЧИК_ОСНОВАНИЕ": "Устава",
    "ДИРЕКТОР_ПРИЧАСТИЕ": "действующего",
}

# КП-lite слоты, как их кладёт build_specification_from_kp_snapshot (тире-маркер).
_LITE_SLOTS = {
    "СПЕЦ_ОПЛАТА_П1": "— Предоплата 50% стоимости весов — подписание Договора.",
    "СПЕЦ_ОПЛАТА_П2": "— Доплата 50% за весы — готовность Весов к отгрузке.",
    "СПЕЦ_ОПЛАТА_П3": "", "СПЕЦ_ОПЛАТА_П4": "",
    "СПЕЦ_ОПЛАТА_П5": "", "СПЕЦ_ОПЛАТА_П6": "",
}


def _item() -> dict:
    return {
        "id": "weights", "name": "Весы", "unit": "компл",
        "quantity": 1.0, "price_per_unit": 100_000.0, "total": 100_000.0,
        "payment_group": "scales", "is_custom": False, "source": "preset",
        "metadata": {},
    }


def _deal(items: list[dict]) -> dict:
    return {"items": items, "delivery_address": "г. Тест"}


def test_lite_slots_without_override_raise(tmp_path):
    """Негатив: снапшот КП без _payment_lines → страж рушит генерацию."""
    data = {**_BASE_DATA, **_LITE_SLOTS}
    items = [_item()]
    with pytest.raises(PaymentLinesLiteError):
        fill_spec_v2(SPEC_V2_PATH, data, items, _deal(items),
                     str(tmp_path / "lite.docx"))


def test_full_override_passes(tmp_path):
    """Позитив: нормальный путь (_payment_lines в full-формате) не ломается."""
    data = {**_BASE_DATA, **_LITE_SLOTS, "_payment_lines": [
        "2.1. Предоплата 50% в размере 50 000 рублей, в т.ч. НДС 22%.",
        "2.2. Доплата 50% в размере 50 000 рублей, в т.ч. НДС 22%.",
    ]}
    items = [_item()]
    output = str(tmp_path / "full.docx")
    fill_spec_v2(SPEC_V2_PATH, data, items, _deal(items), output)
    all_text = "\n".join(p.text for p in Document(output).paragraphs)
    assert "2.1. Предоплата 50%" in all_text
    assert "PAYMENT_SECTION" not in all_text
