"""Страж синхронизации prices.json ↔ models.json.

Каскад строит опции ТОЛЬКО по ключам prices.json (src/filters.py), а ТХ берёт
из models.json. Модель, попавшая в прайс без записи в справочнике, остаётся
выбираемой, но молча деградирует: карточка ТХ → warning, метрология → пусто,
двухдиапазонность → задисейблена, плейсхолдеры ТТХ спецификации → пустые
в клиентском документе. Кнопка «Сгенерировать» при этом не блокируется.

Ровно так 12 моделей из дилерского прайса 01.03.2026 уехали в прод (v0.4).
Этот тест — ловушка на класс, чтобы следующее расхождение упало здесь.
"""
from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# СЛ-100 есть в дилерском PDF, но исключена справочником (changelog v10.2
# от 15.04.2025) и намеренно не заведена ни в прайс, ни в справочник.
# См. EXPECTED_NEW в tests/admin/test_price_pdf_dealer.py.


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_every_priced_model_has_tth_record():
    """Каждый ключ prices.models имеет запись в models.json.

    Нарушение = модель выбираема в каскаде, но КП/Спецификация уедут без ТХ.
    """
    prices = _load("prices.json")
    models = _load("models.json")

    priced = set(prices["models"])
    documented = {m["id"] for m in models["models"]}

    missing = priced - documented
    assert missing == set(), (
        f"модели есть в прайсе, но нет ТХ в models.json: {sorted(missing)}"
    )


def test_priced_models_are_within_declared_scope():
    """Длина и нагрузка каждой прайсовой модели заявлены в _meta.scope.

    Расхождение = запись есть, но справочник её длину/нагрузку не признаёт.
    """
    prices = _load("prices.json")
    models = _load("models.json")
    scope = models["_meta"]["scope"]
    by_id = {m["id"]: m for m in models["models"]}

    for key in prices["models"]:
        m = by_id[key]
        assert m["length_m"] in scope["lengths_m"], (
            f"{key}: длина {m['length_m']} вне _meta.scope.lengths_m"
        )
        assert m["max_load_t"] in scope["max_loads_t"][m["line"]], (
            f"{key}: нагрузка {m['max_load_t']} вне scope для линейки {m['line']}"
        )


def test_length_to_sections_agrees_with_models_json():
    """Хардкод секций в snapshot_builder не противоречит справочнику.

    _LENGTH_TO_SECTIONS дублирует поле sections из models.json (TECH_DEBT).
    Пока дубль жив — он обязан совпадать, иначе строительное задание
    подберётся не на то число секций.
    """
    from src.storage.snapshot_builder import _LENGTH_TO_SECTIONS

    models = _load("models.json")
    for m in models["models"]:
        expected = _LENGTH_TO_SECTIONS.get(m["length_m"])
        if expected is None or m["sections"] is None:
            continue
        assert m["sections"] == expected, (
            f"{m['id']}: sections={m['sections']}, "
            f"а _LENGTH_TO_SECTIONS[{m['length_m']}]={expected}"
        )
