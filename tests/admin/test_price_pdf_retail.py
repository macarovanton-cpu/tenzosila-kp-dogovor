"""Задача 3: парсер розничного PDF — сверка ключей и точечных цен."""
import json
from pathlib import Path

import pytest

from src.admin.price_pdf_retail import parse_retail_pdf

FIXTURE_RETAIL = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_розница_Tenzosila.pdf"
PRICES_JSON = Path(__file__).resolve().parents[2] / "data" / "prices.json"

# Суммарные ОРИОН-позиции в prices.json — парсер их НЕ генерирует (это агрегаты).
_SUMMARY_ORION = {
    "orion_lite", "orion_standard", "orion_standard_plus",
    "orion_auto", "orion_auto_plus",
}

# Новые ключи, которых нет в prices.json, но которые парсер обязан создать.
EXPECTED_NEW = {
    "canopy_18", "canopy_20", "canopy_22",
    "canopy_foundation_18", "canopy_foundation_20", "canopy_foundation_22",
    "canopy_install_18", "canopy_install_20", "canopy_install_22",
    "canopy_lighting",
    "orion_lite_equipment", "orion_lite_shef_montazh",
    "orion_standard_equipment", "orion_standard_shef_montazh",
    "orion_standard_plus_equipment", "orion_standard_plus_shef_montazh",
    "orion_auto_equipment", "orion_auto_shef_montazh",
    "orion_auto_plus_equipment", "orion_auto_plus_shef_montazh",
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
    assert 50 <= len(items) <= 65


def test_key_deltas(items, prices):
    """Парсер покрывает все retail-ключи из prices.json (кроме ожидаемых исключений)
    и генерирует ровно EXPECTED_NEW новых ключей — не больше, не меньше."""
    parser_keys = {i.key for i in items}

    not_scope = (
        _SUMMARY_ORION
        | {"bytovka_weigh_room", "delivery_default", "verification_default"}
        | {k for k in prices["options"] if k.endswith("_22")}
        | {k for k in prices["options"] if k.startswith("road_slabs_")}
        | {k for k in prices["options"] if k.startswith("pag_slabs_")}
        | {k for k in prices["options"] if k.startswith("canopy_turnkey_")}
    )
    expected_from_json = set(prices["options"]) - not_scope

    missing = expected_from_json - parser_keys
    assert missing == set(), f"не распознаны ключи из prices.json: {missing}"

    extra = parser_keys - (set(prices["options"]) | EXPECTED_NEW)
    assert extra == set(), f"неожиданные новые ключи: {extra}"


def test_spot_prices(items):
    d = _by_key(items)
    assert d["foundation_s_f_18"].price_retail == 1_500_000
    assert d["canopy_install_22"].price_retail == 1_700_000
    assert d["orion_standard_equipment"].price_retail == 299_900
    assert d["factory_calibration"].price_retail == 120_000


def test_orion_individual_calc(items):
    orion_comp = [
        i for i in items
        if i.key.endswith("_equipment") or i.key.endswith("_shef_montazh")
    ]
    assert len(orion_comp) == 10, f"ожидаем 10 ОРИОН компонентов, получили {len(orion_comp)}"
    assert all(i.raw_payload.get("individual_calc") is True for i in orion_comp)


def test_on_request(items):
    d = _by_key(items)
    assert d["shef_montazh_s_f"].on_request is True
    assert d["shef_montazh_s_f"].price_retail is None
    assert d["heating_gorynych"].on_request is True
    assert d["heating_gorynych"].price_retail is None


def test_no_dealer_prices(items):
    assert all(i.price_dealer_ru is None for i in items)
