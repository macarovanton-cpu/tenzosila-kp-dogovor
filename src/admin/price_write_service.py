"""Безопасная запись `data/prices.json`: three-way merge + backup + atomic + rollback.

Самый ответственный модуль трека: пишет на диск живой прайс, на котором считаются
реальные КП. Принципы:
- three-way merge: PDF-снимок перезаписывает свои ключи, JSON-only позиции переносятся
  вербатим из текущего прайса (ничего не теряется);
- backup делается ДО записи (guard): не удался — запись не начинается;
- atomic write через temp-файл + os.replace (сбой не оставляет половинчатый файл);
- после записи и отката — сброс кэша load_prices (R4).
"""
from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.admin.price_models import UNKNOWN_PRICE_CLASS, PriceItem
from src.config import PRICES_JSON

# Канонические поля схемы prices.json, которые сериализуются из полей PriceItem.
# Всё, чего тут нет (data_incomplete, notes, dealer_note, components), переносится
# из raw_payload как extra-поле.
_MODEL_CANONICAL = frozenset({"retail", "dealer_ru", "dealer_discount_pct"})
_OPTION_CANONICAL = frozenset({
    "label", "applies_to_lines", "applies_to_lengths",
    "price_retail", "price_dealer_ru", "discount_pct", "price_class",
    "on_request", "allow_customer_value", "range_min", "range_max",
})


@dataclass(frozen=True)
class WriteResult:
    """Результат успешной записи: пути к записанному прайсу и его бэкапу."""

    prices_path: Path
    backup_path: Path


def write_prices(
    merge_result: list[PriceItem],
    *,
    prices_path: Path = PRICES_JSON,
    backup_path: Path | None = None,
    clear_cache: bool = True,
) -> WriteResult:
    """Записать прайс: backup → three-way merge → atomic write → сброс кэша.

    merge_result — PDF-снимок (модели + опции из парсеров). JSON-only позиции
    текущего прайса (которых в снимке нет) переносятся как есть.
    """
    backup_path = _default_backup_path(prices_path) if backup_path is None else backup_path

    # 1. BACKUP (guard): читаем текущий прайс; если нечитаем — не начинаем запись.
    current_text = prices_path.read_text(encoding="utf-8")
    current = json.loads(current_text)
    _atomic_write_text(backup_path, current_text)

    # 2. THREE-WAY MERGE и atomic-запись нового прайса.
    merged = build_merged_prices(merge_result, current)
    _atomic_write_json(prices_path, merged)

    # 3. CACHE CLEAR (R4): иначе КП/договор считают по старому прайсу до TTL.
    if clear_cache:
        _clear_prices_cache()

    return WriteResult(prices_path=prices_path, backup_path=backup_path)


def rollback_prices(
    *,
    prices_path: Path = PRICES_JSON,
    backup_path: Path | None = None,
    clear_cache: bool = True,
) -> bool:
    """Откатить прайс из бэкапа. Вернуть True если восстановлено, False если бэкапа нет."""
    backup_path = _default_backup_path(prices_path) if backup_path is None else backup_path
    if not backup_path.exists():
        return False

    backup_text = backup_path.read_text(encoding="utf-8")
    _atomic_write_text(prices_path, backup_text)
    if clear_cache:
        _clear_prices_cache()
    return True


# ──────────────────── three-way merge ────────────────────

def build_merged_prices(
    merge_result: list[PriceItem],
    current: dict[str, Any],
) -> dict[str, Any]:
    """Финальный прайс = PDF-снимок (перезапись) + JSON-only позиции (как есть).

    Схема результата — точная схема prices.json: _meta / models / options.
    _meta переносится из current вербатим (вне scope записи).
    """
    result: dict[str, Any] = {
        "_meta": deepcopy(current.get("_meta", {})),
        "models": {},
        "options": {},
    }

    # 1. PDF-снимок: сериализуем и перезаписываем свои ключи. Метаданные текущей
    #    записи (notes/dealer_note/components), которых нет в выводе парсеров,
    #    сохраняем — обновляются только ценовые поля.
    covered: dict[str, set[str]] = {"models": set(), "options": set()}
    for item in merge_result:
        section = "models" if item.item_type == "model" else "options"
        current_entry = current.get(section, {}).get(item.key)
        _, key, entry = _serialize_item(item, current_entry)
        result[section][key] = entry
        covered[section].add(key)

    # 2. Carryover: JSON-only позиции, которых нет в снимке, — вербатим из current.
    for section in ("models", "options"):
        for key, entry in current.get(section, {}).items():
            if key not in covered[section]:
                result[section][key] = deepcopy(entry)

    return result


def _serialize_item(
    item: PriceItem,
    current_entry: dict[str, Any] | None = None,
) -> tuple[str, str, dict[str, Any]]:
    """PriceItem → (section, key, entry схемы prices.json) для PDF-позиций.

    Ценовые (канонические) поля берутся из PriceItem. Не-ценовые метаданные схемы
    (notes/dealer_note/components/data_incomplete) сохраняются: сначала из raw_payload
    парсера, затем из текущей записи прайса (current_entry) — парсеры их не выдают.
    """
    if item.item_type == "model":
        entry = _model_entry(item)
        canonical = _MODEL_CANONICAL
        section = "models"
    else:
        entry = _option_entry(item)
        canonical = _OPTION_CANONICAL
        section = "options"

    # Extra-поля из raw_payload парсера (не протаскивая merge-маркер `source`).
    _preserve_extras(entry, item.raw_payload, canonical, skip={"source"})
    # Extra-поля из текущей записи (метаданные, которых нет в выводе парсеров).
    if current_entry:
        _preserve_extras(entry, current_entry, canonical, skip=set())

    return section, item.key, entry


def _preserve_extras(
    entry: dict[str, Any],
    source: dict[str, Any],
    canonical: frozenset[str],
    skip: set[str],
) -> None:
    """Перенести в entry не-канонические поля source (setdefault, deepcopy значений)."""
    for src_key, src_value in source.items():
        if src_key not in canonical and src_key not in skip:
            entry.setdefault(src_key, deepcopy(src_value))


def _model_entry(item: PriceItem) -> dict[str, Any]:
    entry: dict[str, Any] = {}
    if item.price_retail is not None:
        entry["retail"] = item.price_retail
    if item.price_dealer_ru is not None:
        entry["dealer_ru"] = item.price_dealer_ru
    if item.discount_pct is not None:
        entry["dealer_discount_pct"] = item.discount_pct
    return entry


def _option_entry(item: PriceItem) -> dict[str, Any]:
    entry: dict[str, Any] = {"label": item.label}
    if item.applies_to_lines:
        entry["applies_to_lines"] = list(item.applies_to_lines)
    if item.applies_to_lengths:
        entry["applies_to_lengths"] = list(item.applies_to_lengths)
    if item.price_retail is not None:
        entry["price_retail"] = item.price_retail
    if item.price_dealer_ru is not None:
        entry["price_dealer_ru"] = item.price_dealer_ru
    if item.discount_pct is not None:
        entry["discount_pct"] = item.discount_pct
    if item.price_class and item.price_class != UNKNOWN_PRICE_CLASS:
        entry["price_class"] = item.price_class
    if item.on_request:
        entry["on_request"] = True
    if item.allow_customer_value:
        entry["allow_customer_value"] = True
    if item.range_min is not None:
        entry["range_min"] = item.range_min
    if item.range_max is not None:
        entry["range_max"] = item.range_max
    return entry


# ──────────────────── atomic write ────────────────────

def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Записать JSON в схеме prices.json (indent=2, кириллица, финальный \\n)."""
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_text(path, text)


def _atomic_write_text(path: Path, text: str) -> None:
    """Атомарная запись текста: temp в той же директории → fsync → os.replace."""
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        # Сбой посреди записи: temp удаляем, целевой файл остаётся прежним.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# ──────────────────── cache ────────────────────

def _default_backup_path(prices_path: Path) -> Path:
    return prices_path.with_name("prices.backup.json")


def _clear_prices_cache() -> None:
    """Сбросить кэш load_prices (R4). Вне Streamlit-рантайма — безопасный no-op."""
    try:
        from src.data_loader import load_prices

        load_prices.clear()
    except Exception:
        pass
