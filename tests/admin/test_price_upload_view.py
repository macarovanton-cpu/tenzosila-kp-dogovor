"""Тесты безопасной проверки загруженного JSON-прайса."""
from __future__ import annotations

import json
from pathlib import Path

from src.admin.price_upload_view import analyze_uploaded_price_json


FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_valid_uploaded_price_gets_diff_and_download() -> None:
    current = _read_fixture("price_upload_current.json")
    candidate = _read_fixture("price_upload_valid_changed.json")

    result = analyze_uploaded_price_json(
        json.dumps(candidate, ensure_ascii=False).encode("utf-8"),
        current_prices=current,
    )

    assert result.parse_error is None
    assert result.error_count == 0
    assert result.can_download is True
    assert result.download_json is not None
    assert result.diff_summary == {
        "added": 0,
        "removed": 0,
        "changed": 1,
    }
    assert result.diff is not None
    assert result.diff.changed[0].item_key == "test_option"


def test_invalid_uploaded_price_blocks_download() -> None:
    current = _read_fixture("price_upload_current.json")
    candidate = _read_fixture("price_upload_invalid.json")

    result = analyze_uploaded_price_json(
        json.dumps(candidate, ensure_ascii=False).encode("utf-8"),
        current_prices=current,
    )

    assert result.parse_error is None
    assert result.can_download is False
    assert result.download_json is None
    assert result.error_count == 1
    assert result.errors[0].item_key == "test_option"
    assert result.errors[0].field == "price_retail"


def test_same_uploaded_price_has_empty_diff() -> None:
    current = _read_fixture("price_upload_current.json")

    result = analyze_uploaded_price_json(
        json.dumps(current, ensure_ascii=False).encode("utf-8"),
        current_prices=current,
    )

    assert result.can_download is True
    assert result.diff_summary == {
        "added": 0,
        "removed": 0,
        "changed": 0,
    }


def test_invalid_json_returns_parse_error() -> None:
    current = _read_fixture("price_upload_current.json")

    result = analyze_uploaded_price_json(
        b"{not-json",
        current_prices=current,
    )

    assert result.parse_error is not None
    assert result.can_download is False
    assert result.download_json is None
