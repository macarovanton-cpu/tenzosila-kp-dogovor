"""Плейсхолдеры и утечки внутренних идентификаторов в тексте DOCX."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.contracts.filler import get_unfilled_placeholders
from tests.autoverify.docx_text import extract_text

_CUSTOM_ID_RE = re.compile(r"custom_[0-9a-f]{8}")
_NONE_RE = re.compile(r"\bNone\b|\bnan\b")


@pytest.fixture(scope="session")
def raw_option_keys() -> list[str]:
    """Сырые ключи опций из prices.json (fence_norma_20 и т.п.) — не должны
    появляться в тексте документов вместо label'ов."""
    prices = json.loads(Path("data/prices.json").read_text(encoding="utf-8"))
    return sorted(prices.get("options") or {})


def test_no_unfilled_placeholders(generated) -> None:
    """После рендера не осталось незаполненных плейсхолдеров шаблона."""
    for kind, path in generated.docx_paths.items():
        unfilled = get_unfilled_placeholders(str(path))
        assert unfilled == [], f"{generated.fixture_id}/{kind}: {unfilled}"


def test_no_internal_leaks(generated, raw_option_keys) -> None:
    """В видимом тексте нет {{…}}, custom_N-id, сырых ключей опций, None/nan."""
    for kind, path in generated.docx_paths.items():
        text = extract_text(path)
        where = f"{generated.fixture_id}/{kind}"

        assert "{{" not in text and "}}" not in text, f"{where}: остался {{{{…}}}}"

        leaked_ids = _CUSTOM_ID_RE.findall(text)
        assert not leaked_ids, f"{where}: утечка custom-id {leaked_ids}"

        leaked_keys = [k for k in raw_option_keys if k in text]
        assert not leaked_keys, f"{where}: сырые ключи опций {leaked_keys}"

        leaked_none = _NONE_RE.findall(text)
        assert not leaked_none, f"{where}: в тексте {leaked_none}"
