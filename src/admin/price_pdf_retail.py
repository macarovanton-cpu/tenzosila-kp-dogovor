"""Парсер розничного PDF: стр.3 (опции/услуги/фундаменты),
стр.4 (ПАК ОРИОН — 5 суммарных позиций), стр.19 (навесы — turnkey по длинам).
Чистый backend без Streamlit. Дилерская цена не парсится (только retail).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pdfplumber

from src.admin.price_models import PriceItem

logger = logging.getLogger(__name__)

# Порядок важен: «стандарт+» до «стандарт», «автоматика+» до «автоматика».
_ORION_LEVELS: dict[str, str] = {
    "лайт": "lite",
    "стандарт+": "standard_plus",
    "стандарт": "standard",
    "автоматика+": "auto_plus",
    "автоматика": "auto",
}

# Страница 3: колонки цен 18м / 20м / 24м.
_P3_PRICE_COLS = (19, 22, 25)
_P3_LENGTHS = (18, 20, 24)

_CANOPY_LEN_RE = re.compile(r"ВЕСТА[-–](\d+)\s*м", re.IGNORECASE)


def parse_retail_pdf(pdf_path: str | Path) -> list[PriceItem]:
    """Розничный PDF → список опций, услуг, навесов и компонентов ОРИОН."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        items: list[PriceItem] = []
        items += _parse_page3(pdf.pages[2])
        items += _parse_page4(pdf.pages[3])
        items += _parse_page19(pdf.pages[18])
    return items


# ──────────────────── страница 3 (опции / услуги) ────────────────────

def _parse_page3(page) -> list[PriceItem]:
    table = page.extract_tables()[0]
    items: list[PriceItem] = []
    for row in table:
        if len(row) < 26:
            continue
        label = _row_label(row, end=19)
        if not label:
            continue
        result = _match_p3(label)
        if result is None:
            continue
        kind = result[0]
        if kind == "sized":
            _, family, price_class = result
            for col, length in zip(_P3_PRICE_COLS, _P3_LENGTHS):
                price = _to_int(row[col])
                if price is not None:
                    items.append(_item("option", f"{family}_{length}",
                                       f"{label}, {length}м", price, price_class))
        else:
            _, key, price_class, on_request = result
            price = None if on_request else _price_single(row)
            items.append(_item("option", key, label, price, price_class,
                               on_request=on_request))
    return items


def _match_p3(label: str) -> tuple | None:
    """Метка строки → (kind, ...) или None (пропустить)."""
    low = label.lower()
    # Размерные (18/20/24м) — порядок: специфичное до общего
    if "рам" in low and "весы" in low:
        return ("sized", "frame", "A_retail_and_dealer")
    if "ограждение" in low and "лайт" in low:
        return ("sized", "fence_light", "A_retail_and_dealer")
    if "ограждение" in low and "норма" in low:
        return ("sized", "fence_norma", "A_retail_and_dealer")
    if "люк" in low and "фл" in low:
        return ("sized", "hatches_fl", "A_retail_and_dealer")
    if "люк" in low:
        return ("sized", "hatches_f", "A_retail_and_dealer")
    if "фундамент" in low and "лайт" in low:
        return ("sized", "foundation_lite_sl_fl", "B_retail_only")
    if "фундамент" in low and "стандарт" in low:
        return ("sized", "foundation_std_sl_fl", "B_retail_only")
    if "фундамент" in low and ("с/ф" in low or "веста-с" in low):
        return ("sized", "foundation_s_f", "B_retail_only")
    if "строительн" in low and "работ" in low:
        return ("sized", "construction_works", "B_retail_only")
    # Однопрайсовые — шеф-монтаж до монтаж
    if "пандус" in low and ("фл" in low or "сл" in low):
        return ("single", "ramp_set_fl_sl", "A_retail_and_dealer", False)
    if "пандус" in low:
        return ("single", "ramp_set_f_s", "A_retail_and_dealer", False)
    if "закладн" in low:
        return ("single", "embedded_parts", "A_retail_and_dealer", False)
    if "резин" in low:
        return ("single", "rubber_t_6m", "A_retail_and_dealer", False)
    if "калибровк" in low:
        return ("single", "factory_calibration", "A_retail_and_dealer", False)
    if "бетонн" in low and "основан" in low:
        return ("single", "concrete_base_on_frame", "B_retail_only", False)
    if "курирован" in low:
        return ("single", "foundation_supervision", "B_retail_only", False)
    if "опор" in low and ("кабель" in low or "орион" in low):
        return ("single", "orion_cable_poles", "B_retail_only", False)
    if "шеф-монтаж" in low:
        return ("single", "shef_montazh_s_f", "B_retail_only", True)
    if "монтаж" in low and ("веста" in low or "секц" in low):
        # install_default — C_manual_range, range из prices.json (вручную);
        # 175К в PDF информативны, merge возьмёт ключ из prices.json
        return None
    if "горыныч" in low or "подогрев" in low:
        return ("single", "heating_gorynych", "B_retail_only", True)
    return None


# ──────────────────── страница 4 (ПАК ОРИОН) ────────────────────

def _parse_page4(page) -> list[PriceItem]:
    tables = page.extract_tables()
    if not tables:
        return []
    items: list[PriceItem] = []
    for row in tables[0][1:]:  # пропустить заголовок
        name_cell = _norm(row[0]) if row[0] else ""
        price_cell = str(row[2]) if len(row) > 2 and row[2] else ""
        if not name_cell or not price_cell:
            continue
        level = _orion_level(name_cell)
        if level is None:
            continue
        equip, shef = _parse_orion_price_cell(price_cell)
        if equip is not None and shef is not None:
            total: int | None = equip + shef
            on_req = False
        else:
            total = None
            on_req = True
        prefix = name_cell.split(":")[0].strip()
        raw_extra: dict[str, Any] = {"individual_calc": True}
        items.append(_item("option", f"orion_{level}",
                           f"{prefix} (оборудование + шеф-монтаж)", total,
                           "B_retail_only", on_request=on_req, raw_extra=raw_extra))
    return items


def _orion_level(label: str) -> str | None:
    low = label.lower()
    for key, level in _ORION_LEVELS.items():
        if key in low:
            return level
    return None


def _parse_orion_price_cell(cell: str) -> tuple[int | None, int | None]:
    """'Оборудование =\\n299 900\\nШеф-Монтаж =\\n165 000' → (299900, 165000)."""
    nums = [_to_int(p) for p in cell.split("\n")]
    nums = [n for n in nums if n is not None]
    return (nums[0] if nums else None), (nums[1] if len(nums) > 1 else None)


# ──────────────────── страница 19 (навесы) ────────────────────

def _parse_page19(page) -> list[PriceItem]:
    tables = page.extract_tables()
    if not tables:
        return []
    totals: dict[int, int] = {}
    on_request_lengths: set[int] = set()
    for row in tables[0][1:]:  # пропустить заголовок
        label = _norm(row[0]) if row[0] else ""
        price_cell = _norm(row[2]) if len(row) > 2 and row[2] else ""
        if not label:
            continue
        if "освещ" in label.lower():
            continue  # освещение не входит в turnkey
        m = _CANOPY_LEN_RE.search(label)
        length = int(m.group(1)) if m else None
        if length is None:
            continue
        if _is_on_request(price_cell):
            on_request_lengths.add(length)
            continue
        price = _to_int(price_cell)
        if price is not None:
            totals[length] = totals.get(length, 0) + price
    items: list[PriceItem] = []
    for length in sorted(set(totals) | on_request_lengths):
        if length in on_request_lengths:
            items.append(_item("option", f"canopy_turnkey_{length}",
                               f"Навес под ключ ВЕСТА-{length}м", None, "B_retail_only",
                               on_request=True))
        else:
            items.append(_item("option", f"canopy_turnkey_{length}",
                               f"Навес под ключ ВЕСТА-{length}м (навес + фундамент + монтаж)",
                               totals[length], "B_retail_only"))
    return items


# ──────────────────── вспомогательные функции ────────────────────

def _item(item_type: str, key: str, label: str, price_retail: int | None,
          price_class: str, on_request: bool = False,
          raw_extra: dict[str, Any] | None = None) -> PriceItem:
    raw: dict[str, Any] = {"price_retail": price_retail, "price_class": price_class}
    if raw_extra:
        raw.update(raw_extra)
    return PriceItem(
        item_type=item_type, key=key, label=label,
        price_retail=price_retail, price_dealer_ru=None, discount_pct=None,
        price_class=price_class, on_request=on_request, allow_customer_value=False,
        range_min=None, range_max=None, applies_to_lines=[], applies_to_lengths=[],
        raw_payload=raw,
    )


def _row_label(row: list, end: int) -> str:
    """Собрать текст из колонок 0..end-1, соединить без разделителя."""
    parts = [_norm(str(row[i])) for i in range(min(end, len(row)))
             if row[i] is not None]
    return "".join(parts)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def _to_int(cell: str | None) -> int | None:
    digits = re.sub(r"\D", "", str(cell) if cell else "")
    return int(digits) if digits else None


def _price_single(row: list) -> int | None:
    """Однопрайсовая позиция: col 22 (20м) если есть, иначе col 19."""
    if len(row) > 22:
        p = _to_int(row[22])
        if p is not None:
            return p
    return _to_int(row[19]) if len(row) > 19 else None


def _is_on_request(cell: str) -> bool:
    low = cell.lower()
    return "по запросу" in low or "рассчитывается" in low
