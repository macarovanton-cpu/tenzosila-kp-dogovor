"""Тесты supply_filler: маппинг реквизитов, ТТХ, автовыбор типа, тексты оплаты."""
from __future__ import annotations

import pytest

from src.contracts.payment_line import (
    PaymentTrigger,
    build_lines_from_snapshot,
    format_payment_line,
)
from src.contracts.supplier import SUPPLIER
from src.contracts.supply_filler import (
    SUPPLY_TRIGGER_TEXTS,
    _buyer_context,
    build_supply_tth,
    decide_contract_type,
)


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

def _ooo_ctx() -> dict:
    """Плоский ctx для ООО (с КПП)."""
    return {
        "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ":  "ООО «Тест»",
        "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ":   "Общество с ограниченной ответственностью «Тест»",
        "ЗАКАЗЧИК_ИНН":                   "7701234567",
        "ЗАКАЗЧИК_КПП":                   "770101001",
        "ЗАКАЗЧИК_ОГРН":                  "1027700000000",
        "ЗАКАЗЧИК_АДРЕС_ЮР":             "г. Москва, ул. Тестовая, 1",
        "ЗАКАЗЧИК_РС":                    "40702810000000000001",
        "ЗАКАЗЧИК_КС":                    "30101810400000000225",
        "ЗАКАЗЧИК_БИК":                   "044525225",
        "ЗАКАЗЧИК_БАНК":                  "ПАО «Сбербанк России»",
        "ЗАКАЗЧИК_EMAIL":                 "test@test.ru",
        "ЗАКАЗЧИК_ДИРЕКТОР_ФИО":         "Иванов Иван Иванович",
        "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ":   "Генеральный директор",
    }


def _ip_ctx() -> dict:
    """Плоский ctx для ИП (без КПП)."""
    return {
        "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ":  "ИП Петров А. В.",
        "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ":   "",
        "ЗАКАЗЧИК_ИНН":                   "771234567890",
        "ЗАКАЗЧИК_ОГРН":                  "316770000050000",
        "ЗАКАЗЧИК_АДРЕС_ЮР":             "г. Москва, пер. Частный, 5",
        "ЗАКАЗЧИК_РС":                    "40802810000000000002",
        "ЗАКАЗЧИК_КС":                    "30101810400000000225",
        "ЗАКАЗЧИК_БИК":                   "044525225",
        "ЗАКАЗЧИК_БАНК":                  "ПАО «Сбербанк России»",
        "ЗАКАЗЧИК_EMAIL":                 "ip@test.ru",
        "ЗАКАЗЧИК_ДИРЕКТОР_ФИО":         "Петров А. В.",
        "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ":   "Индивидуальный предприниматель",
    }


def _model() -> dict:
    return {
        "max_load_t": 80,
        "axle_loads_t": {"single": 11},
        "length_m": 18,
        "width_m": 3,
        "verification_division_kg": 20,
    }


def _sensor() -> dict:
    return {"temperature_min_c": -30, "temperature_max_c": 40}


def _v2_payment() -> dict:
    """Снапшот v2_prepay_preship_postpay с дефолтными 30/40/30."""
    return {"preset_id": "v2_prepay_preship_postpay", "days": 5}


def _prepay100_payment() -> dict:
    return {"preset_id": "prepay_100", "days": 5}


def _spec_items(total: int = 2_000_000) -> list[dict]:
    return [{"name": "Весы", "item_key": "vesta-sl-80", "total": total, "payment_group": "scales"}]


# ---------------------------------------------------------------------------
# Тест 1 — _buyer_context: ООО маппит все ПОКУПАТЕЛЬ_* и ПОСТАВЩИК_*
# ---------------------------------------------------------------------------

def test_buyer_context_ooo_maps_all_keys():
    ctx = _buyer_context(_ooo_ctx())

    # ПОКУПАТЕЛЬ_* — ключи присутствуют и не None
    assert ctx["ПОКУПАТЕЛЬ_НАИМЕНОВАНИЕ"] == "Общество с ограниченной ответственностью «Тест»"
    assert ctx["ПОКУПАТЕЛЬ_ИНН"] == "7701234567"
    assert ctx["ПОКУПАТЕЛЬ_КПП"] == "770101001"
    assert ctx["ПОКУПАТЕЛЬ_ОГРН"] == "1027700000000"
    assert ctx["ПОКУПАТЕЛЬ_ЮР_АДРЕС"] == "г. Москва, ул. Тестовая, 1"
    assert ctx["ПОКУПАТЕЛЬ_РС"] == "40702810000000000001"
    assert ctx["ПОКУПАТЕЛЬ_КС"] == "30101810400000000225"
    assert ctx["ПОКУПАТЕЛЬ_БИК"] == "044525225"
    assert ctx["ПОКУПАТЕЛЬ_БАНК"] == "ПАО «Сбербанк России»"
    assert ctx["ПОКУПАТЕЛЬ_EMAIL"] == "test@test.ru"
    assert ctx["ПОКУПАТЕЛЬ_ДИРЕКТОР_ФИО"] == "Иванов Иван Иванович"
    assert ctx["ПОКУПАТЕЛЬ_ДИРЕКТОР_ДОЛЖНОСТЬ"] == "Генеральный директор"

    # ПОСТАВЩИК_* подтянулись из SUPPLIER
    assert ctx["ПОСТАВЩИК_ИНН"] == SUPPLIER["ПОСТАВЩИК_ИНН"]
    assert ctx["ПОСТАВЩИК_ДИРЕКТОР_ФИО"] == SUPPLIER["ПОСТАВЩИК_ДИРЕКТОР_ФИО"]


def test_buyer_context_ip_no_kpp():
    """ИП без КПП — ПОКУПАТЕЛЬ_КПП пусто, без исключений."""
    ctx = _buyer_context(_ip_ctx())
    assert ctx["ПОКУПАТЕЛЬ_КПП"] == ""
    assert ctx["ПОКУПАТЕЛЬ_НАИМЕНОВАНИЕ"] == "ИП Петров А. В."  # fallback к краткому


def test_buyer_context_naimenovanie_fallback():
    """Если ПОЛНОЕ_НАИМЕНОВАНИЕ пусто — берём КРАТКОЕ_НАИМЕНОВАНИЕ."""
    data = _ooo_ctx()
    data["ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ"] = ""
    ctx = _buyer_context(data)
    assert ctx["ПОКУПАТЕЛЬ_НАИМЕНОВАНИЕ"] == "ООО «Тест»"


# ---------------------------------------------------------------------------
# Тест 2 — SUPPLIER: реквизиты непусты
# ---------------------------------------------------------------------------

def test_supplier_non_empty():
    assert SUPPLIER["ПОСТАВЩИК_ИНН"] == "3662257349"
    assert SUPPLIER["ПОСТАВЩИК_ДИРЕКТОР_ФИО"] == "О. А. Сенаторов"
    assert SUPPLIER["ПОСТАВЩИК_ДИРЕКТОР_ФИО_РП"] == "Сенаторова Олега Александровича"
    assert SUPPLIER["ПОСТАВЩИК_ДИРЕКТОР_ДОЛЖНОСТЬ"] == "Директор"
    assert SUPPLIER["ПОСТАВЩИК_БАНК"]
    assert SUPPLIER["ПОСТАВЩИК_РС"]
    assert SUPPLIER["ПОСТАВЩИК_БИК"]
    assert SUPPLIER["ПОСТАВЩИК_КС"]
    assert SUPPLIER["ПОСТАВЩИК_ОГРН"]


# ---------------------------------------------------------------------------
# Тест 3 — build_supply_tth: корректный ремаппинг + константы
# ---------------------------------------------------------------------------

def test_build_supply_tth_keys():
    tth = build_supply_tth(_model(), _sensor())
    assert tth["ТТХ_MAX"] == "80"
    assert tth["ТТХ_ОСЬ"] == "11"
    assert "не более" in tth["ТТХ_РАССТОЯНИЕ_ТЕРМИНАЛ"]
    assert tth["ТТХ_ДИСКРЕТНОСТЬ"] == "20"  # нет dual_range → только _1
    assert "18×3" in tth["ТТХ_ГАБАРИТЫ"]
    assert "30" in tth["ТТХ_ТЕМПЕРАТУРА"] and "40" in tth["ТТХ_ТЕМПЕРАТУРА"]
    # Константы
    assert tth["ТТХ_СВЯЗЬ"] == "RS 232/485"
    assert tth["ТТХ_ПИТАНИЕ"] == "220 ±15"
    assert tth["ТТХ_МОЩНОСТЬ"] == "15"
    assert "ГОСТ" in tth["ТТХ_ГОСТ_СТРОКА"]


def test_build_supply_tth_dual_range():
    """dual_range → ДИСКРЕТНОСТЬ включает оба диапазона через ' / '."""
    model = dict(_model())
    model["dual_range"] = {
        "w1": {"e_kg": 20, "max_load_t": 40},
        "w2": {"e_kg": 50, "max_load_t": 80},
    }
    tth = build_supply_tth(model, _sensor())
    assert tth["ТТХ_ДИСКРЕТНОСТЬ"] == "20 / 50"


# ---------------------------------------------------------------------------
# Тест 4 — decide_contract_type: 4 комбинации
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("install_scope,foundation_scope,has_orion,expected", [
    ("none", "none", False, "supply"),                     # чистая поставка
    ("none", "existing_foundation", False, "supply"),      # существующий фундамент
    ("full", "none", False, "spec"),                       # есть монтаж → spec
    ("none", "none", True, "spec"),                        # есть ОРИОН → spec
    ("none", "customer_builds", False, "spec"),            # клиент строит фундамент → spec
    ("full", "existing_foundation", True, "spec"),         # всё вместе → spec
])
def test_decide_contract_type(install_scope, foundation_scope, has_orion, expected):
    assert decide_contract_type(install_scope, foundation_scope, has_orion) == expected


# ---------------------------------------------------------------------------
# Тест 5 — SUPPLY_TRIGGER_TEXTS: тексты не ссылаются на «Спецификацию»
# ---------------------------------------------------------------------------

def _fmt(line, idx, trigger_texts=None):
    return format_payment_line(line, idx, trigger_texts)


def test_supply_trigger_texts_no_spec_references():
    """v2-пресет с SUPPLY_TRIGGER_TEXTS не содержит 'Спецификации'/'Акта выполненных работ'."""
    items = _spec_items(2_000_000)
    lines = build_lines_from_snapshot(_v2_payment(), items)
    assert len(lines) >= 2, "v2 должен дать ≥2 строки"

    texts = [_fmt(line, f"4.2.{i + 1}", SUPPLY_TRIGGER_TEXTS) for i, line in enumerate(lines)]
    full_text = " ".join(texts)

    assert "Спецификации" not in full_text
    assert "Акта выполненных работ" not in full_text


def test_supply_v2_trigger_texts_content():
    """Строки v2-пресета содержат 'настоящего Договора' и 'поставки Весов'."""
    items = _spec_items(2_000_000)
    lines = build_lines_from_snapshot(_v2_payment(), items)
    texts = [_fmt(line, f"4.2.{i + 1}", SUPPLY_TRIGGER_TEXTS) for i, line in enumerate(lines)]

    # Первая строка — предоплата по подписанию Договора
    assert "настоящего Договора" in texts[0]
    # Последняя строка (доплата после монтажа в spec → "поставки Весов" для supply)
    assert any("поставки Весов Покупателю" in t for t in texts)


def test_supply_prepay100_trigger_texts():
    """prepay_100: строка ссылается на 'настоящего Договора'."""
    items = _spec_items(1_500_000)
    lines = build_lines_from_snapshot(_prepay100_payment(), items)
    assert len(lines) == 1
    text = _fmt(lines[0], "4.2.1", SUPPLY_TRIGGER_TEXTS)
    assert "настоящего Договора" in text
    assert "Спецификации" not in text


def test_spec_flow_trigger_texts_unchanged():
    """Spec-флоу (без trigger_texts) всё ещё ссылается на 'настоящей Спецификации'."""
    items = _spec_items(1_000_000)
    lines = build_lines_from_snapshot(_prepay100_payment(), items)
    text = _fmt(lines[0], "2.1")  # без trigger_texts — дефолт TRIGGER_TEXTS
    assert "Спецификации" in text
