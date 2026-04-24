"""Фильтрация моделей и опций по каскаду линейка → нагрузка → длина."""
from __future__ import annotations

from typing import Any

from src.config import BLOCK_KEY_PREFIXES


def model_id_from_cascade(line: str, max_load: int, length: int) -> str:
    """Собрать id модели в том же формате, что в prices.json."""
    return f"vesta-{line.lower()}-{max_load}-{length}"


def _iter_models_in_prices(prices: dict) -> list[str]:
    return list(prices.get("models", {}).keys())


def available_max_loads(models_json: dict, line: str, prices: dict) -> list[int]:
    """Вернуть отсортированный список max_load_t для линейки,
    скрывая нагрузки без записей в prices.json (напр. 40т)."""
    price_keys = _iter_models_in_prices(prices)
    line_lower = line.lower()
    result: set[int] = set()
    for key in price_keys:
        parts = key.split("-")
        if len(parts) != 4:
            continue
        if parts[1] != line_lower:
            continue
        try:
            result.add(int(parts[2]))
        except ValueError:
            continue
    return sorted(result)


def available_lengths(
    models_json: dict, line: str, max_load: int, prices: dict
) -> list[int]:
    """Длины, доступные для (линейка, нагрузка) — по наличию модели в prices."""
    price_keys = _iter_models_in_prices(prices)
    line_lower = line.lower()
    result: set[int] = set()
    for key in price_keys:
        parts = key.split("-")
        if len(parts) != 4:
            continue
        if parts[1] != line_lower:
            continue
        try:
            if int(parts[2]) != max_load:
                continue
            result.add(int(parts[3]))
        except ValueError:
            continue
    return sorted(result)


def model_exists_in_prices(model_id: str, prices: dict) -> bool:
    return model_id in prices.get("models", {})


def is_option_applicable(entry: dict[str, Any], line: str, length: int) -> bool:
    """Проверка applies_to_lines и applies_to_lengths."""
    lines = entry.get("applies_to_lines")
    if lines is not None and line not in lines:
        return False
    lengths = entry.get("applies_to_lengths")
    if lengths is not None and length not in lengths:
        return False
    return True


def _key_matches_block(key: str, block_id: str) -> bool:
    prefixes = BLOCK_KEY_PREFIXES.get(block_id, ())
    return any(key.startswith(p) or key == p for p in prefixes)


def get_visible_options(
    prices_options: dict[str, Any],
    line: str,
    length: int,
    block_id: str,
) -> list[tuple[str, dict]]:
    """Опции указанного блока, отфильтрованные по линейке и длине.
    Порядок — как в prices.options."""
    result: list[tuple[str, dict]] = []
    for key, entry in prices_options.items():
        if not _key_matches_block(key, block_id):
            continue
        if not is_option_applicable(entry, line, length):
            continue
        result.append((key, entry))
    return result
