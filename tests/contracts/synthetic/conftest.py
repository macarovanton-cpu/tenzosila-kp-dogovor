"""conftest.py — патч st.secrets для тестов без Streamlit-рантайма."""

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
OUTPUT_DIR = Path(__file__).parent / "output"


class _SecretsDict(dict):
    """dict с поддержкой attribute-доступа, как у st.secrets."""

    def __getattr__(self, key: str):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


@pytest.fixture(scope="session", autouse=True)
def patch_st_secrets():
    """Подменяет st.secrets на dict из .streamlit/secrets.toml."""
    if not SECRETS_PATH.exists():
        pytest.skip("Нет .streamlit/secrets.toml — пропуск AI-тестов")

    with open(SECRETS_PATH, "rb") as f:
        raw = tomllib.load(f)

    secrets = _SecretsDict(raw)

    import streamlit as st
    original = getattr(st, "secrets", None)
    st.secrets = secrets
    yield
    if original is not None:
        st.secrets = original


@pytest.fixture(scope="session", autouse=True)
def ensure_dirs():
    """Создаёт каталоги fixtures/ и output/."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
