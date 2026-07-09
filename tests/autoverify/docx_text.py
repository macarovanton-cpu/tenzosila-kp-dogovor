"""Извлечение текста/таблиц из DOCX и нормализации для проверок харнесса."""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from docx import Document

from tests.golden.dump_docx import dump_docx  # noqa: F401  (реэкспорт для тестов)

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# «НДС 22%», «НДС 22 %», «НДС(22%)», «НДС: 22%», с nbsp/narrow-nbsp внутри
_VAT_RE = re.compile(r"НДС[:\s]*\(?\s*(\d+)\s*%\s*\)?")
_SPACES_RE = re.compile(r"[\s  ]+")

# Части DOCX с видимым текстом: тело + колонтитулы (включая текст-боксы —
# raw-обход w:t ловит и их, в отличие от python-docx paragraphs)
_TEXT_PARTS_RE = re.compile(r"^word/(document|header\d*|footer\d*)\.xml$")


def extract_text(path: Path) -> str:
    """Весь видимый текст DOCX: по одному абзацу (w:p) на строку.

    Обходит w:t в document.xml и колонтитулах напрямую через XML —
    текст внутри таблиц и текст-боксов не теряется.
    """
    lines: list[str] = []
    with zipfile.ZipFile(path) as zf:
        names = sorted(n for n in zf.namelist() if _TEXT_PARTS_RE.match(n))
        for name in names:
            root = ElementTree.fromstring(zf.read(name))
            for p_el in root.iter(f"{_W_NS}p"):
                texts = [t.text or "" for t in p_el.iter(f"{_W_NS}t")]
                if texts:
                    lines.append("".join(texts))
    return "\n".join(lines)


def normalize_spaces(text: str) -> str:
    """nbsp/narrow-nbsp/переводы строк → одиночный пробел."""
    return _SPACES_RE.sub(" ", text)


def vat_rates(text: str) -> set[int]:
    """Все ставки НДС, упомянутые в тексте (нормализованный матч)."""
    return {int(m.group(1)) for m in _VAT_RE.finditer(normalize_spaces(text))}


def parse_money(text: str) -> int | None:
    """«1 553 000» / «1 553 000,00» → 1553000; не-число → None."""
    s = normalize_spaces(text).strip().replace(" ", "")
    s = s.split(",")[0].split(".")[0]
    if s.isdigit():
        return int(s)
    return None


def split_sections(text: str) -> dict[str, str]:
    """Разбить текст по нумерованным заголовкам «N. Заголовок» (верхний уровень)."""
    sections: dict[str, list[str]] = {"_preamble": []}
    current = "_preamble"
    for line in text.split("\n"):
        m = re.match(r"^(\d+)\.\s+\S", line.strip())
        if m:
            current = m.group(1)
            sections.setdefault(current, [])
        sections[current].append(line)
    return {k: "\n".join(v) for k, v in sections.items()}


@dataclass(frozen=True)
class SpecTable:
    """Таблица спецификации с итогом (per-unit колонка сумм)."""
    rows: list[tuple[str, int]]   # (наименование, сумма) — только числовые строки
    customer_side: list[str]      # позиции со значением «ЗАКАЗЧИК» (не в итого)
    itogo_per_1: int              # значение строки ИТОГО / ИТОГО за 1 весы


_ITOGO_PREFIXES = ("ИТОГО", "ОБЩАЯ ИТОГОВАЯ СУММА")


def find_spec_table(path: Path) -> SpecTable:
    """Найти таблицу со строкой ИТОГО и распарсить позиции + итог.

    Формат КП и спецификации v2 одинаков в важном: колонка 0 — наименование,
    колонка 1 — сумма; строка «ИТОГО»/«ИТОГО за 1 весы» закрывает позиции.
    Поставка (compose_supply) использует «ОБЩАЯ ИТОГОВАЯ СУММА» вместо «ИТОГО».
    """
    doc = Document(str(path))
    for table in doc.tables:
        rows: list[tuple[str, int]] = []
        customer: list[str] = []
        itogo: int | None = None
        for row in table.rows:
            cells = row.cells
            if len(cells) < 2:
                continue
            name = cells[0].text.strip()
            value_text = cells[1].text.strip()
            # «ИТОГО» (КП), «ИТОГО с НДС, руб.» (спека), «ИТОГО за 1 весы» (qty>1),
            # «ОБЩАЯ ИТОГОВАЯ СУММА» (поставка)
            if name.startswith(_ITOGO_PREFIXES):
                itogo = parse_money(value_text)
                break  # позиции закончились; «за N весов» не парсим
            if normalize_spaces(value_text).strip() == "ЗАКАЗЧИК":
                customer.append(name)
                continue
            value = parse_money(value_text)
            # Имя может быть пустым (RichText-имя модели в КП) — строка валидна,
            # если в колонке суммы стоит число; заголовок отсеивается по value=None.
            if value is not None:
                rows.append((name, value))
        if itogo is not None:
            return SpecTable(rows=rows, customer_side=customer, itogo_per_1=itogo)
    raise AssertionError(f"{path.name}: таблица со строкой ИТОГО не найдена")
