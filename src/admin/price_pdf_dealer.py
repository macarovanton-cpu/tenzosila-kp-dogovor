"""Парсер дилерского PDF: секция автовесов ВЕСТА (линейки ФЛ/СЛ/Ф/С/П) до
заголовка «Автомобильные весы ВЕСТА-М» → list[PriceItem]. Чистый backend без
Streamlit. Дилерская цена берётся из PDF напрямую, формулой НЕ вычисляется.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pdfplumber

from src.admin.price_models import MODEL_PRICE_CLASS, PriceItem

logger = logging.getLogger(__name__)

# Фиксированная таблица «линейка в PDF → буква кириллического ключа».
_LINE_LETTERS = {"ВЕСТА-ФЛ": "фл", "ВЕСТА-СЛ": "сл", "ВЕСТА-Ф": "ф", "ВЕСТА-С": "с", "ВЕСТА-П": "п"}
_SKIP_LINES = {"ВЕСТА-СБ"}  # редкая линейка вне scope
_OPTION_CLASS = "A_retail_and_dealer"

# «60т-18м», «60т-20м 4х», «120т-24м» → (груз, длина, ширина|None).
_SIZE_RE = re.compile(r"(\d+)\s*т\s*-\s*(\d+)\s*м(?:\s+(\d)\s*[хx])?")
# Длина опции из «18м» (для размерных семейств).
_OPT_LEN_RE = re.compile(r"(\d+)\s*м")


def parse_dealer_pdf(pdf_path: str | Path) -> list[PriceItem]:
    """Дилерский PDF → список моделей и железных опций секции ВЕСТА."""
    rows = _read_rows(pdf_path)
    model_rows: list[tuple] = []
    options: list[PriceItem] = []

    for row in rows:
        label = _norm(_cell(row, 0))
        size = _norm(_cell(row, 1))
        m = _SIZE_RE.match(size)
        if m:
            width = int(m.group(3)) if m.group(3) else None
            model_rows.append((label, int(m.group(1)), int(m.group(2)), width,
                               _to_int(_cell(row, 2)), _to_int(_cell(row, 4)), _to_int(_cell(row, 3))))
            continue
        key = _option_key(label, _opt_length(size))
        if key is not None:
            options.append(_make_option(key, label, row))
        elif label and not _is_header(label):
            logger.warning("нераспознанная строка опции: %r", label)

    return _build_models(model_rows) + options


def _read_rows(pdf_path: str | Path) -> list[list]:
    """Строки таблиц pages 1–2 до заголовка «Автомобильные весы ВЕСТА-М»."""
    out: list[list] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if _is_stop(_norm(_cell(row, 0))):
                        return out
                    out.append(row)
    return out


def _build_models(model_rows: list[tuple]) -> list[PriceItem]:
    """Сегментация строк на группы линеек и сборка PriceItem.

    Границы линеек — по строгому убыванию размера (ton, len): линейка идёт по
    возрастанию, новая начинается со сброса. Строгое «<» оставляет пары ширины
    3х/4х (равный размер) в одной группе; 3х отбрасывается на эмиссии, поэтому
    метка линейки, сидящая на 3х-строке (ВЕСТА-С), не теряется.
    """
    items: list[PriceItem] = []
    group: list[tuple] = []
    prev_size: tuple[int, int] | None = None
    group_label: str | None = None

    for row in model_rows:
        size = (row[1], row[2])
        label = row[0]
        boundary = (prev_size is not None and size < prev_size) or (
            bool(label) and group_label is not None and label != group_label
        )
        if boundary:
            _emit_group(group, items)
            group, prev_size, group_label = [], None, None
        group.append(row)
        if label:
            group_label = label
        prev_size = size

    _emit_group(group, items)
    return items


def _emit_group(group: list[tuple], items: list[PriceItem]) -> None:
    if not group:
        return
    labels = {row[0] for row in group if row[0]}
    if not labels:
        logger.warning("группа моделей без метки линейки: %d строк", len(group))
        return
    label = sorted(labels)[0]
    if len(labels) > 1:
        logger.warning("группа моделей с несколькими метками: %s", labels)
    if label in _SKIP_LINES:
        return
    letter = _LINE_LETTERS.get(label)
    if letter is None:
        logger.warning("неизвестная линейка: %r", label)
        return

    for lbl, ton, length, width, retail, dealer, disc in group:
        # Вариант опор 3х выведен из продаж с 2026 г.; берём только 4х.
        # Игнор явный — не зависит от порядка строк в PDF (доменное решение).
        if width == 3:
            continue
        items.append(_item(
            "model", f"vesta-{letter}-{ton}-{length}", f"{label} {ton}т-{length}м",
            retail, dealer, disc, MODEL_PRICE_CLASS,
            {"retail": retail, "dealer_ru": dealer, "dealer_discount_pct": disc}))


def _option_key(label: str, length: int | None) -> str | None:
    """Семейство железной опции → существующий option_key из prices.json."""
    low = label.lower()
    compact = label.replace(" ", "")
    if "пандус" in low:
        if "фл/сл" in compact.lower():
            return "ramp_set_fl_sl"
        if "ф/с" in compact.lower():
            return "ramp_set_f_s"
        return None
    if "закладн" in low:
        return "embedded_parts"
    if "резин" in low:
        return "rubber_t_6m"
    if length is None:
        return None
    if "рам" in low:
        return f"frame_{length}"
    if "ограждение" in low and "лайт" in low:
        return f"fence_light_{length}"
    if "ограждение" in low and "норма" in low:
        return f"fence_norma_{length}"
    if "люк" in low:
        return f"hatches_fl_{length}" if "ВЕСТА-ФЛ" in compact else f"hatches_f_{length}"
    return None


def _make_option(key: str, label: str, row: list) -> PriceItem:
    retail, dealer, disc = _to_int(_cell(row, 2)), _to_int(_cell(row, 4)), _to_int(_cell(row, 3))
    return _item("option", key, label, retail, dealer, disc, _OPTION_CLASS, {
        "price_retail": retail, "price_dealer_ru": dealer,
        "discount_pct": disc, "price_class": _OPTION_CLASS,
    })


def _item(item_type: str, key: str, label: str, retail: int | None, dealer: int | None,
          disc: int | None, price_class: str, raw: dict[str, Any]) -> PriceItem:
    """Фабрика PriceItem с общими дефолтами (плоские поля без диапазонов)."""
    return PriceItem(
        item_type=item_type, key=key, label=label,
        price_retail=retail, price_dealer_ru=dealer, discount_pct=disc,
        price_class=price_class, on_request=False, allow_customer_value=False,
        range_min=None, range_max=None, applies_to_lines=[], applies_to_lengths=[],
        raw_payload=raw,
    )


def _cell(row: list, idx: int) -> Any:
    return row[idx] if row and idx < len(row) else None


def _norm(text: str | None) -> str:
    """Убрать переносы, неразрывный дефис; схлопнуть пробелы."""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("‑", "-")
    return re.sub(r"\s+", " ", text).strip()


def _to_int(cell: str | None) -> int | None:
    """«1 668 432» / «8%» → int; пусто → None (учитывает неразрывные пробелы)."""
    digits = re.sub(r"\D", "", cell or "")
    return int(digits) if digits else None


def _opt_length(size: str) -> int | None:
    m = _OPT_LEN_RE.search(size)
    return int(m.group(1)) if m else None


def _is_header(label: str) -> bool:
    return label.lower().startswith("автомобильные весы") or label == "Модель"


def _is_stop(label: str) -> bool:
    return "автомобильные весы" in label.lower() and "веста-м" in label.lower()
