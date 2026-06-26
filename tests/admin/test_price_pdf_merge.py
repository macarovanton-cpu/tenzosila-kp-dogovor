from pathlib import Path

import pytest

from src.admin.price_pdf_dealer import parse_dealer_pdf
from src.admin.price_pdf_retail import parse_retail_pdf
from src.admin.price_pdf_merge import merge_price_items

FIXTURE_DEALER = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_дилер_экспорт.pdf"
FIXTURE_RETAIL = Path(__file__).parent / "fixtures" / "2026_03_01_Прайс_розница_Tenzosila.pdf"

_PHANTOM_KEYS = {"vesta-п-80-18", "vesta-п-80-20", "vesta-п-80-22", "vesta-п-80-24"}


@pytest.fixture(scope="module")
def parsed():
    dealer = parse_dealer_pdf(FIXTURE_DEALER)
    retail = parse_retail_pdf(FIXTURE_RETAIL)
    return dealer, retail, merge_price_items(dealer, retail)


def test_no_duplicate_keys(parsed):
    _, _, merged = parsed
    keys = [item.key for item in merged]
    assert len(keys) == len(set(keys)), f"Найдены дубли ключей"


def test_item_counts(parsed):
    _, _, merged = parsed
    models = [i for i in merged if i.item_type == "model"]
    options = [i for i in merged if i.item_type == "option"]
    assert 40 <= len(models) <= 60, f"Неожиданное число моделей: {len(models)}"
    assert 35 <= len(options) <= 55, f"Неожиданное число опций: {len(options)}"
    assert 80 <= len(merged) <= 120, f"Неожиданное общее число позиций: {len(merged)}"


def test_overlap_keys_from_dealer(parsed):
    dealer, retail, merged = parsed
    dealer_keys = {i.key for i in dealer}
    retail_keys = {i.key for i in retail}
    overlap = dealer_keys & retail_keys
    assert overlap, "Пересечение пустое — парсеры не разделяют ни одного ключа"

    by_key = {i.key: i for i in merged}
    for key in overlap:
        assert key in by_key, f"Пересечённый ключ отсутствует в merged: {key}"
        item = by_key[key]
        assert item.raw_payload.get("source") == "dealer", (
            f"{key}: ожидался источник 'dealer', получен {item.raw_payload.get('source')!r}"
        )
        assert item.price_dealer_ru is not None, (
            f"{key}: у дилерской позиции должна быть price_dealer_ru != None"
        )


def test_source_set_on_all_items(parsed):
    _, _, merged = parsed
    missing = [i.key for i in merged if "source" not in i.raw_payload]
    assert not missing, f"source отсутствует у {len(missing)} позиций: {missing[:5]}"


def test_no_phantom_keys(parsed):
    _, _, merged = parsed
    found = {i.key for i in merged} & _PHANTOM_KEYS
    assert not found, f"Фантомные ключи попали в результат: {found}"


def test_applies_to_frame_norma(parsed):
    _, _, merged = parsed
    by_key = {i.key: i for i in merged}

    frame = by_key.get("frame_18")
    assert frame is not None, "frame_18 отсутствует в merged"
    assert set(frame.applies_to_lines) == {"С", "Ф", "СЛ", "ФЛ"}, (
        f"frame_18 applies_to_lines: {frame.applies_to_lines}"
    )
    assert frame.applies_to_lengths == [18], (
        f"frame_18 applies_to_lengths: {frame.applies_to_lengths}"
    )

    norma = by_key.get("fence_norma_20")
    assert norma is not None, "fence_norma_20 отсутствует в merged"
    assert set(norma.applies_to_lines) == {"С", "Ф", "СЛ", "ФЛ", "П"}, (
        f"fence_norma_20 applies_to_lines: {norma.applies_to_lines}"
    )
    assert norma.applies_to_lengths == [20], (
        f"fence_norma_20 applies_to_lengths: {norma.applies_to_lengths}"
    )
