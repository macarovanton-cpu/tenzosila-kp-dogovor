"""Задача 3: парсер розничного PDF — сверка ключей и точечных цен."""
import json
from pathlib import Path

import pytest

from src.admin.price_pdf_retail import parse_retail_pdf

FIXTURE_RETAIL = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_розница_Tenzosila.pdf"
PRICES_JSON = Path(__file__).resolve().parents[2] / "data" / "prices.json"

_ORION_LEVEL_KEYS = {
    "orion_lite", "orion_standard", "orion_standard_plus",
    "orion_auto", "orion_auto_plus",
}

# Новые ключи, которых нет в prices.json, но которые парсер обязан создать.
EXPECTED_NEW = {
    "shef_montazh_s_f",
    "heating_gorynych",
}


@pytest.fixture(scope="module")
def items():
    return parse_retail_pdf(FIXTURE_RETAIL)


@pytest.fixture(scope="module")
def prices():
    return json.loads(PRICES_JSON.read_text(encoding="utf-8"))


def _by_key(items):
    return {i.key: i for i in items}


def test_counts(items):
    assert 38 <= len(items) <= 52


def test_key_deltas(items, prices):
    """Парсер покрывает все retail-ключи из prices.json (кроме ожидаемых исключений)
    и генерирует ровно EXPECTED_NEW новых ключей — не больше, не меньше."""
    parser_keys = {i.key for i in items}

    not_scope = (
        {"bytovka_weigh_room", "delivery_default", "verification_default",
         "install_default"}  # C_manual_range — range/price задаются вручную в JSON
        | {k for k in prices["options"] if k.endswith("_22")}
        | {k for k in prices["options"] if k.startswith("road_slabs_")}
        | {k for k in prices["options"] if k.startswith("pag_slabs_")}
        | {"canopy_turnkey_24"}  # 24м отсутствует в PDF (по запросу, строчки нет)
    )
    expected_from_json = set(prices["options"]) - not_scope

    missing = expected_from_json - parser_keys
    assert missing == set(), f"не распознаны ключи из prices.json: {missing}"

    extra = parser_keys - (set(prices["options"]) | EXPECTED_NEW)
    assert extra == set(), f"неожиданные новые ключи: {extra}"


def test_spot_prices(items):
    d = _by_key(items)
    assert d["foundation_s_f_18"].price_retail == 1_500_000
    assert d["orion_standard"].price_retail == 464_900        # 299 900 + 165 000
    assert d["canopy_turnkey_22"].price_retail == 6_380_000   # 3 200 000 + 1 480 000 + 1 700 000
    assert d["factory_calibration"].price_retail == 120_000


def test_orion_individual_calc(items):
    orion_items = [i for i in items if i.key in _ORION_LEVEL_KEYS]
    assert len(orion_items) == 5, f"ожидаем 5 ОРИОН позиций, получили {len(orion_items)}"
    assert all(i.raw_payload.get("individual_calc") is True for i in orion_items)


def test_on_request(items):
    d = _by_key(items)
    assert d["shef_montazh_s_f"].on_request is True
    assert d["shef_montazh_s_f"].price_retail is None
    assert d["heating_gorynych"].on_request is True
    assert d["heating_gorynych"].price_retail is None


def test_no_dealer_prices(items):
    assert all(i.price_dealer_ru is None for i in items)
