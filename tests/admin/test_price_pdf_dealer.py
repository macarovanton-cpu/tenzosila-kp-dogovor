"""Задача 2: парсер дилерского PDF — сверка цен и дельт ключей с prices.json."""
import json
from pathlib import Path

import pytest

from src.admin.price_pdf_dealer import parse_dealer_pdf

FIXTURE_DEALER = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_дилер_экспорт.pdf"
PRICES_JSON = Path(__file__).resolve().parents[2] / "data" / "prices.json"

# Документированные дельты PDF ↔ prices.json (Задача 2, ARCHITECTURE п.1a).
# Есть в prices.json (ошибочные дубли п-100), в PDF отсутствуют:
EXPECTED_PHANTOM = {
    "vesta-п-80-18", "vesta-п-80-20", "vesta-п-80-22", "vesta-п-80-24",
}
# Есть в PDF, в prices.json НАМЕРЕННО нет: СЛ-100 исключена справочником
# (changelog v10.2 от 15.04.2025), отдел продаж её всё ещё прайсует.
# Решение Антона 2026-07-16 — в конфигуратор не заводить. Дельта постоянная.
EXPECTED_NEW = {
    "vesta-сл-100-18", "vesta-сл-100-20", "vesta-сл-100-22", "vesta-сл-100-24",
}


@pytest.fixture(scope="module")
def items():
    return parse_dealer_pdf(FIXTURE_DEALER)


@pytest.fixture(scope="module")
def prices():
    return json.loads(PRICES_JSON.read_text(encoding="utf-8"))


def _models(items):
    return {i.key: i for i in items if i.item_type == "model"}


def _options(items):
    return {i.key: i for i in items if i.item_type == "option"}


def test_counts(items):
    assert 50 <= len(_models(items)) <= 55
    assert len(_options(items)) == 19


def test_model_key_deltas(items, prices):
    """Точное совпадение множеств с учётом задокументированных дельт.

    Любой иной дрейф (напр. латиница вместо кириллицы) изменит дельту → FAIL.
    """
    parser_keys = set(_models(items))
    json_keys = set(prices["models"])
    assert json_keys - parser_keys == EXPECTED_PHANTOM
    assert parser_keys - json_keys == EXPECTED_NEW


def test_intersection_values(items, prices):
    models = _models(items)
    pm = prices["models"]
    for key in set(models) & set(pm):
        assert models[key].price_retail == pm[key]["retail"], key
        # дилер из PDF — источник правды; ±1 руб из-за округления (п.1a)
        assert abs(models[key].price_dealer_ru - pm[key]["dealer_ru"]) <= 1, key


def test_model_spot_prices(items):
    models = _models(items)
    assert models["vesta-фл-60-12"].price_retail == 1140296
    assert models["vesta-фл-60-12"].price_dealer_ru == 1049072
    # page-break Ф/С: строки С не приклеились к Ф (метка С на 3х-строке стр.2)
    assert models["vesta-с-60-18"].price_retail == 1906544
    assert models["vesta-ф-60-18"].price_retail == 1792719


def test_option_spot_price(items):
    options = _options(items)
    assert options["ramp_set_f_s"].price_retail == 380000
    assert options["ramp_set_f_s"].price_dealer_ru == 349600


def test_options_match_prices_json(items, prices):
    options = _options(items)
    po = prices["options"]
    for key, item in options.items():
        assert key in po, key
        assert item.price_retail == po[key]["price_retail"], key
        assert item.price_dealer_ru == po[key]["price_dealer_ru"], key
        assert item.price_class == po[key]["price_class"], key


def test_no_3x_variants(items):
    """3х выведен из продаж с 2026; парсер должен явно пропускать эти строки.

    Проверяем через список items (до dict-свёртки):
    - нет дублирующихся ключей моделей (значит 3х-строки не попали в items);
    - vesta-сл-60-20 имеет цены 4х, а не 3х.
    """
    model_items = [i for i in items if i.item_type == "model"]
    keys = [i.key for i in model_items]
    assert len(keys) == len(set(keys)), "дублирующиеся ключи — 3х-строки попали в результат"

    models = _models(items)
    assert models["vesta-сл-60-20"].price_retail == 2_078_323
    assert models["vesta-сл-60-20"].price_dealer_ru == 1_912_057


def test_sb_line_excluded(items):
    assert not any("-сб-" in i.key for i in items)


def test_no_on_request_in_dealer_section(items):
    assert all(not i.on_request for i in items)
