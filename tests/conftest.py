"""Фикстуры pytest: загрузка реальных справочников из data/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Сделать `src` импортируемым при запуске `pytest tests/`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def models_json() -> dict:
    return _read(DATA / "models.json")


@pytest.fixture(scope="session")
def prices() -> dict:
    return _read(DATA / "prices.json")


@pytest.fixture(scope="session")
def payment_terms() -> dict:
    return _read(DATA / "payment_terms.json")
