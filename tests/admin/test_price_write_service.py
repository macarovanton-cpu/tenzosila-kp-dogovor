"""Тесты сервиса записи прайса: three-way merge, backup, atomic, rollback.

Всё на временном каталоге (tmp_path). Боевой data/prices.json только читается.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from src.admin.price_models import PriceItem
from src.admin.price_normalizer import normalize_prices
from src.admin.price_write_service import (
    build_merged_prices,
    rollback_prices,
    write_prices,
)
from src.config import PRICES_JSON

# JSON-only позиции: которых нет в PDF-снимке, обязаны прийти через carryover.
_JSON_ONLY_EXACT = {
    "install_default", "delivery_default", "verification_default", "bytovka_weigh_room",
}
_JSON_ONLY_PREFIX = ("road_slabs_", "pag_slabs_", "vesta-п-80-")


def _is_json_only(key: str) -> bool:
    return key in _JSON_ONLY_EXACT or any(key.startswith(p) for p in _JSON_ONLY_PREFIX)


def _pdf_model(key: str, retail: int, dealer: int) -> PriceItem:
    """PDF-снимок модели (raw_payload с маркером source, как у парсеров)."""
    return PriceItem(
        item_type="model", key=key, label=key,
        price_retail=retail, price_dealer_ru=dealer, discount_pct=8,
        price_class="A_retail_and_dealer", on_request=False, allow_customer_value=False,
        range_min=None, range_max=None, applies_to_lines=[], applies_to_lengths=[],
        raw_payload={"source": "dealer"},
    )


def _pdf_option(key: str, retail: int, dealer: int) -> PriceItem:
    return PriceItem(
        item_type="option", key=key, label=f"label-{key}",
        price_retail=retail, price_dealer_ru=dealer, discount_pct=8,
        price_class="A_retail_and_dealer", on_request=False, allow_customer_value=False,
        range_min=None, range_max=None, applies_to_lines=["Ф"], applies_to_lengths=[18],
        raw_payload={"source": "dealer"},
    )


def _fake_current() -> dict[str, Any]:
    """Минимальный текущий прайс: пересекающиеся ключи + JSON-only позиции."""
    return {
        "_meta": {"version": "test", "updated_at": "2026-06-27"},
        "models": {
            "vesta-фл-60-18": {"retail": 100, "dealer_ru": 92, "dealer_discount_pct": 8},
            "vesta-п-80-18": {
                "retail": 200, "dealer_ru": 184, "dealer_discount_pct": 8,
                "data_incomplete": True,
            },
        },
        "options": {
            "ramp_set_f_s": {
                "label": "old", "applies_to_lines": ["Ф"], "applies_to_lengths": [18],
                "price_retail": 380000, "price_dealer_ru": 349600,
                "discount_pct": 8, "price_class": "A_retail_and_dealer",
            },
            "install_default": {
                "label": "Монтаж", "applies_to_lines": [], "applies_to_lengths": [],
                "price_retail": 180000, "price_dealer_ru": 165600, "discount_pct": 8,
                "price_class": "C_manual_range", "range_min": 100000, "range_max": 1000000,
                "notes": "ручной диапазон",
            },
            "road_slabs_18": {
                "label": "плиты", "applies_to_lengths": [18],
                "price_retail": 300000, "price_dealer_ru": 276000, "discount_pct": 8,
                "price_class": "B_retail_only", "dealer_note": "скидка -8%",
            },
        },
    }


def _write_current(tmp_path: Path, current: dict[str, Any]) -> Path:
    prices_path = tmp_path / "prices.json"
    prices_path.write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return prices_path


# ──────────────────── 1. three-way merge ────────────────────

def test_three_way_merge_overwrites_pdf_keeps_json_only(tmp_path: Path) -> None:
    current = _fake_current()
    prices_path = _write_current(tmp_path, current)

    # PDF-снимок: новые значения только пересекающихся ключей.
    merge_result = [
        _pdf_model("vesta-фл-60-18", retail=111, dealer=101),
        _pdf_option("ramp_set_f_s", retail=400000, dealer=368000),
    ]

    write_prices(merge_result, prices_path=prices_path,
                 backup_path=tmp_path / "prices.backup.json", clear_cache=False)
    written = json.loads(prices_path.read_text(encoding="utf-8"))

    # Пересекающиеся ключи взяты из снимка.
    assert written["models"]["vesta-фл-60-18"]["retail"] == 111
    assert written["options"]["ramp_set_f_s"]["price_retail"] == 400000

    # JSON-only позиции присутствуют и не изменены (вербатим).
    assert written["models"]["vesta-п-80-18"] == current["models"]["vesta-п-80-18"]
    assert written["options"]["install_default"] == current["options"]["install_default"]
    assert written["options"]["road_slabs_18"] == current["options"]["road_slabs_18"]

    # Merge-маркер source не протёк в схему.
    assert "source" not in written["models"]["vesta-фл-60-18"]
    assert "source" not in written["options"]["ramp_set_f_s"]


def test_pdf_covered_entry_keeps_current_metadata(tmp_path: Path) -> None:
    """PDF-снимок обновляет цену covered-ключа, но не теряет его метаданные.

    Парсеры не выдают notes/dealer_note/components — они должны сохраниться из
    текущего прайса (raw_payload PDF-позиции их не содержит).
    """
    current = _fake_current()
    current["options"]["orion_standard"] = {
        "label": "ПАК ОРИОН Стандарт", "applies_to_lines": ["Ф"], "applies_to_lengths": [18],
        "price_retail": 299900, "price_dealer_ru": 275908, "discount_pct": 8,
        "price_class": "A_retail_and_dealer",
        "notes": "цена справочная", "dealer_note": "individual_calc",
        "components": [{"name": "оборудование"}, {"name": "шеф-монтаж"}],
    }
    prices_path = _write_current(tmp_path, current)

    # PDF-позиция с новой ценой и БЕЗ метаданных (как реальный парсер).
    pdf_item = _pdf_option("orion_standard", retail=310000, dealer=285200)
    write_prices([pdf_item], prices_path=prices_path,
                 backup_path=tmp_path / "prices.backup.json", clear_cache=False)
    written = json.loads(prices_path.read_text(encoding="utf-8"))["options"]["orion_standard"]

    # Цена обновлена из снимка.
    assert written["price_retail"] == 310000
    # Метаданные сохранены вербатим.
    assert written["notes"] == "цена справочная"
    assert written["dealer_note"] == "individual_calc"
    assert written["components"] == current["options"]["orion_standard"]["components"]
    assert "source" not in written


# ──────────────────── 2. backup + валидный json ────────────────────

def test_write_creates_backup_and_valid_json(tmp_path: Path) -> None:
    current = _fake_current()
    prices_path = _write_current(tmp_path, current)
    old_text = prices_path.read_text(encoding="utf-8")
    backup_path = tmp_path / "prices.backup.json"

    result = write_prices([_pdf_option("ramp_set_f_s", 400000, 368000)],
                          prices_path=prices_path, backup_path=backup_path,
                          clear_cache=False)

    assert result.backup_path == backup_path
    # Бэкап = прежнее содержимое.
    assert backup_path.read_text(encoding="utf-8") == old_text
    # Новый прайс — валидный JSON с финальным переводом строки.
    new_text = prices_path.read_text(encoding="utf-8")
    assert new_text.endswith("}\n")
    json.loads(new_text)


# ──────────────────── 3. round-trip + carryover (главный тест) ────────────────────

def test_roundtrip_carryover_preserves_json_only_verbatim(
    tmp_path: Path, prices: dict
) -> None:
    # Копируем реальный прайс на temp (боевой не трогаем).
    src_text = PRICES_JSON.read_text(encoding="utf-8")
    original = json.loads(src_text)
    prices_path = tmp_path / "prices.json"
    prices_path.write_text(src_text, encoding="utf-8")

    # merge_result = ТОЛЬКО PDF-покрываемое подмножество (без JSON-only).
    all_items = normalize_prices(original)
    merge_result = [it for it in all_items if not _is_json_only(it.key)]
    assert any(_is_json_only(it.key) for it in all_items), "в данных должны быть JSON-only"

    write_prices(merge_result, prices_path=prices_path,
                 backup_path=tmp_path / "prices.backup.json", clear_cache=False)
    written = json.loads(prices_path.read_text(encoding="utf-8"))

    # Carryover (главное): каждая JSON-only позиция вербатим равна исходной.
    for key, entry in original["models"].items():
        if _is_json_only(key):
            assert written["models"][key] == entry, f"модель {key} потеряна/изменена"
    for key, entry in original["options"].items():
        if _is_json_only(key):
            assert written["options"][key] == entry, f"опция {key} потеряна/изменена"

    # Поимённая проверка ключевых JSON-only позиций с их полями.
    assert written["options"]["install_default"]["range_min"] == \
        original["options"]["install_default"]["range_min"]
    assert written["options"]["road_slabs_18"]["dealer_note"] == \
        original["options"]["road_slabs_18"]["dealer_note"]
    assert written["models"]["vesta-п-80-18"]["data_incomplete"] is True

    # Round-trip: множества ключей не изменились (carryover + снимок = всё).
    assert set(written["models"]) == set(original["models"])
    assert set(written["options"]) == set(original["options"])

    # Выборочный serialized-ключ сохранил схему и price_class.
    ramp = written["options"]["ramp_set_f_s"]
    assert ramp["price_class"] == original["options"]["ramp_set_f_s"]["price_class"]
    assert "price_retail" in ramp and "label" in ramp


# ──────────────────── 4. rollback ────────────────────

def test_rollback_restores_previous(tmp_path: Path) -> None:
    current = _fake_current()
    prices_path = _write_current(tmp_path, current)
    backup_path = tmp_path / "prices.backup.json"

    write_prices([_pdf_option("ramp_set_f_s", 400000, 368000)],
                 prices_path=prices_path, backup_path=backup_path, clear_cache=False)
    backup_text = backup_path.read_text(encoding="utf-8")

    # Портим прайс, затем откатываем.
    prices_path.write_text("{ broken", encoding="utf-8")
    assert rollback_prices(prices_path=prices_path, backup_path=backup_path,
                           clear_cache=False) is True
    assert prices_path.read_text(encoding="utf-8") == backup_text


# ──────────────────── 5. имитация сбоя ────────────────────

def test_write_failure_keeps_original_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = _fake_current()
    prices_path = _write_current(tmp_path, current)
    original_text = prices_path.read_text(encoding="utf-8")
    backup_path = tmp_path / "prices.backup.json"

    real_replace = os.replace

    def boom(src: str, dst: str, *a: Any, **k: Any) -> None:
        # Бэкап проходит; падаем именно на записи нового прайса.
        if Path(dst) == prices_path:
            raise OSError("имитация сбоя записи")
        return real_replace(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(OSError):
        write_prices([_pdf_option("ramp_set_f_s", 400000, 368000)],
                     prices_path=prices_path, backup_path=backup_path, clear_cache=False)

    # Исходный прайс цел: байты не изменились, json валиден, не пуст.
    assert prices_path.read_text(encoding="utf-8") == original_text
    json.loads(prices_path.read_text(encoding="utf-8"))
    # Temp-файлов не осталось.
    leftovers = [p for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


# ──────────────────── 6. нет бэкапа → rollback недоступен ────────────────────

def test_rollback_without_backup_returns_false(tmp_path: Path) -> None:
    current = _fake_current()
    prices_path = _write_current(tmp_path, current)
    before = prices_path.read_text(encoding="utf-8")

    assert rollback_prices(prices_path=prices_path,
                           backup_path=tmp_path / "prices.backup.json",
                           clear_cache=False) is False
    # Прайс не тронут.
    assert prices_path.read_text(encoding="utf-8") == before


# ──────────────────── build_merged_prices: _meta вербатим ────────────────────

def test_meta_carried_verbatim(tmp_path: Path) -> None:
    current = _fake_current()
    merged = build_merged_prices([_pdf_option("ramp_set_f_s", 1, 1)], current)
    assert merged["_meta"] == current["_meta"]
