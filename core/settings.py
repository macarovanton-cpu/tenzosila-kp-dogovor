"""Настройки core: секреты только из переменных окружения (И-5, P0-06).

Streamlit при старте сервера продвигает top-level ключи secrets.toml
в os.environ (web/bootstrap.py → load_if_toml_exists) — работает
и локально, и на Streamlit Cloud без дополнительного кода.
"""
import os


def get_secret(name: str) -> str:
    """Секрет из окружения; пустой/отсутствующий → RuntimeError с именем ключа."""
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Секрет {name} не задан в переменных окружения")
    return value
