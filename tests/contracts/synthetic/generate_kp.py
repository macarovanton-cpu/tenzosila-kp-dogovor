"""Генератор синтетических КП в формате PDF (reportlab).

Каждый PDF содержит 4 страницы:
- Стр. 1-2: филлер (титул + описание)
- Стр. 3: характеристики модели весов
- Стр. 4: спецификация + условия оплаты

Extractor читает стр. 3-5 через extract_kp_text().
"""

import os
import random
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Шрифт
# ---------------------------------------------------------------------------

_FONT_REGISTERED = False


def _register_font() -> str:
    """Регистрирует кириллический шрифт, возвращает имя."""
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return "CyrFont"
    windir = os.environ.get("WINDIR", r"C:\Windows")
    for name in ("arial.ttf", "calibri.ttf", "times.ttf"):
        path = os.path.join(windir, "Fonts", name)
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("CyrFont", path))
            _FONT_REGISTERED = True
            return "CyrFont"
    raise RuntimeError("Кириллический TTF-шрифт не найден в системе")


# ---------------------------------------------------------------------------
# Данные
# ---------------------------------------------------------------------------


@dataclass
class SpecRow:
    """Строка спецификации КП."""
    name: str
    quantity: str
    price: int
    deadline: str


@dataclass
class KpCase:
    """Полный набор данных для одного синтетического КП."""
    case_id: int
    model: str
    max_load: int
    platform_length: int
    platform_width: int
    temp_range: str
    discreteness: str
    sensor_model: str
    sensor_count: int
    has_fence: bool
    fence_height_mm: int | None
    spec_rows: list[SpecRow] = field(default_factory=list)
    total: int = 0
    payment_conditions: list[str] = field(default_factory=list)
    nds: int = 22


def fmt_price(n: int) -> str:
    """1850000 → '1 850 000'"""
    s = str(n)
    parts = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    return " ".join(reversed(parts))


def _gen_prices(case_id: int, has_fence: bool) -> dict[str, int]:
    """Псевдослучайные, но воспроизводимые цены."""
    rng = random.Random(42 + case_id)
    r = lambda lo, hi: round(rng.randint(lo, hi) / 10_000) * 10_000
    prices = {
        "scales": r(1_800_000, 2_800_000),
        "foundation": r(1_400_000, 1_700_000),
        "installation": r(180_000, 220_000),
        "delivery": r(60_000, 150_000),
        "verification": r(50_000, 80_000),
    }
    if has_fence:
        prices["fence"] = r(200_000, 400_000)
    return prices


def _build_payment_conditions(case: KpCase) -> list[str]:
    """Строит условия оплаты для кейса."""
    t = case.total
    if case.case_id == 1:
        half = t // 2
        return [
            f"Аванс — 50% от общей цены договора {fmt_price(half)} рублей "
            f"в т.ч. НДС {case.nds}% в течение 5 банковских дней "
            f"с даты подписания договора",
            f"Окончательный расчёт — 50% от общей цены договора "
            f"{fmt_price(t - half)} рублей в т.ч. НДС {case.nds}% "
            f"в течение 5 банковских дней после завершения всех работ",
        ]
    if case.case_id == 2:
        p30 = round(t * 0.3)
        p70 = t - p30
        return [
            f"Аванс — 30% от общей цены договора {fmt_price(p30)} рублей "
            f"в т.ч. НДС {case.nds}% в течение 5 банковских дней "
            f"с даты подписания договора",
            f"Оплата — 70% от общей цены договора {fmt_price(p70)} рублей "
            f"в т.ч. НДС {case.nds}% в течение 10 банковских дней "
            f"после доставки весов на завод",
        ]
    if case.case_id == 3:
        scales_row = next(r for r in case.spec_rows if "Весы" in r.name)
        fund_row = next(r for r in case.spec_rows if "фундамент" in r.name.lower())
        inst_row = next(r for r in case.spec_rows if "Монтаж" in r.name)
        ver_row = next(r for r in case.spec_rows if "поверка" in r.name.lower())
        fence_row = next((r for r in case.spec_rows if "ограждение" in r.name.lower()), None)
        s50 = scales_row.price // 2
        f50 = fund_row.price // 2
        rest = inst_row.price + ver_row.price + (fence_row.price if fence_row else 0)
        return [
            f"Аванс — 50% стоимости весов {fmt_price(s50)} рублей "
            f"и 50% стоимости фундамента {fmt_price(f50)} рублей, "
            f"итого {fmt_price(s50 + f50)} рублей "
            f"в т.ч. НДС {case.nds}% в течение 5 рабочих дней "
            f"с даты подписания договора",
            f"Оплата — 50% стоимости весов {fmt_price(scales_row.price - s50)} "
            f"рублей в т.ч. НДС {case.nds}% "
            f"в течение 5 рабочих дней после доставки весов на завод",
            f"Оплата — 50% стоимости фундамента "
            f"{fmt_price(fund_row.price - f50)} рублей "
            f"в т.ч. НДС {case.nds}% "
            f"в течение 5 рабочих дней после завершения фундаментных работ",
            f"Окончательный расчёт — оплата монтажа и поверки "
            f"{fmt_price(rest)} рублей в т.ч. НДС {case.nds}% "
            f"в течение 10 рабочих дней после завершения всех работ",
        ]
    if case.case_id == 4:
        return [
            f"Оплата — 100% от общей цены договора {fmt_price(t)} рублей "
            f"в т.ч. НДС {case.nds}% в течение 10 рабочих дней "
            f"после завершения монтажа и пусконаладки",
        ]
    if case.case_id == 5:
        p30 = round(t * 0.3)
        p70 = t - p30
        return [
            f"Аванс — 30% от общей цены договора {fmt_price(p30)} рублей "
            f"в т.ч. НДС {case.nds}% в течение 5 рабочих дней "
            f"с даты подписания договора",
            f"Оплата — 70% от общей цены договора {fmt_price(p70)} рублей "
            f"в т.ч. НДС {case.nds}% в течение 10 рабочих дней "
            f"после доставки весов на завод",
        ]
    return []


def _build_case(case_id: int, model: str, max_load: int,
                platform_length: int, sensor_model: str,
                sensor_count: int, has_fence: bool,
                fence_height_mm: int | None) -> KpCase:
    """Собирает полный KpCase с ценами и условиями оплаты."""
    prices = _gen_prices(case_id, has_fence)
    c = KpCase(
        case_id=case_id, model=model, max_load=max_load,
        platform_length=platform_length, platform_width=3,
        temp_range="-30...+40",
        discreteness="20 кг" if max_load <= 60 else "20/50 кг",
        sensor_model=sensor_model, sensor_count=sensor_count,
        has_fence=has_fence, fence_height_mm=fence_height_mm,
    )
    rows: list[SpecRow] = []
    rows.append(SpecRow(
        f"Весы автомобильные {model}, датчики {sensor_model} {sensor_count} шт.",
        "1 комплект", prices["scales"], "30 рабочих дней",
    ))
    if has_fence:
        rows.append(SpecRow(
            f"Ограждение въездное h={fence_height_mm} мм",
            "1 комплект", prices["fence"], "30 рабочих дней",
        ))
    rows.append(SpecRow(
        f"Строительство фундамента под {model}",
        "1 комплект", prices["foundation"], "25 рабочих дней",
    ))
    rows.append(SpecRow(
        "Монтаж и пусконаладка весов",
        "1 комплект", prices["installation"], "10 рабочих дней",
    ))
    rows.append(SpecRow(
        "Доставка весов до объекта",
        "1 комплект", prices["delivery"], "10 рабочих дней",
    ))
    rows.append(SpecRow(
        "Первичная поверка весов",
        "1 комплект", prices["verification"], "5 рабочих дней",
    ))
    c.spec_rows = rows
    c.total = sum(r.price for r in rows)
    c.payment_conditions = _build_payment_conditions(c)
    return c


CASES: list[KpCase] = [
    _build_case(1, "ВЕСТА-С-60-12",  60,  12, "Zemic",    8,  False, None),
    _build_case(2, "ВЕСТА-С-80-18",  80,  18, "Zemic",   10,  True,  200),
    _build_case(3, "ВЕСТА-С-100-20", 100, 20, "HBM C16i", 10, True,  400),
    _build_case(4, "ВЕСТА-П-100-18", 100, 18, "HBM C16i", 10, False, None),
    _build_case(5, "ВЕСТА-С-80-20",  80,  20, "Zemic",   10,  True,  200),
]


# ---------------------------------------------------------------------------
# PDF-генерация
# ---------------------------------------------------------------------------


def _make_styles(font_name: str) -> dict[str, ParagraphStyle]:
    """Создаёт набор стилей для PDF."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"],
            fontName=font_name, fontSize=18, leading=22,
        ),
        "heading": ParagraphStyle(
            "H2", parent=base["Heading2"],
            fontName=font_name, fontSize=14, leading=18,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontName=font_name, fontSize=10, leading=13,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"],
            fontName=font_name, fontSize=9, leading=11,
        ),
    }


def _build_page1(story: list, case: KpCase, styles: dict) -> None:
    """Стр. 1 — титул."""
    story.append(Spacer(1, 80 * mm))
    story.append(Paragraph("КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ", styles["title"]))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        f"на поставку автомобильных весов {case.model}",
        styles["heading"],
    ))
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph(
        "ТПК «Тензосила» — производство весоизмерительного оборудования",
        styles["body"],
    ))
    story.append(PageBreak())


def _build_page2(story: list, case: KpCase, styles: dict) -> None:
    """Стр. 2 — описание компании (филлер)."""
    story.append(Paragraph("О компании", styles["heading"]))
    story.append(Spacer(1, 5 * mm))
    text = (
        "ТПК «Тензосила» — российский производитель автомобильных, "
        "вагонных и платформенных весов серии ВЕСТА. "
        "Компания осуществляет полный цикл: проектирование, производство, "
        "строительство фундамента, монтаж, пусконаладку и метрологическую "
        "поверку весоизмерительного оборудования."
    )
    story.append(Paragraph(text, styles["body"]))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "Все весы ВЕСТА внесены в Государственный реестр средств измерений "
        "и имеют свидетельство об утверждении типа.",
        styles["body"],
    ))
    story.append(PageBreak())


def _build_page3(story: list, case: KpCase, styles: dict, font: str) -> None:
    """Стр. 3 — характеристики модели."""
    story.append(Paragraph(
        f"Характеристики {case.model}", styles["heading"],
    ))
    story.append(Spacer(1, 5 * mm))

    data = [
        ["Параметр", "Значение"],
        ["Наибольший предел взвешивания (НПВ)", f"{case.max_load} т"],
        ["Габариты платформы (Д×Ш)", f"{case.platform_length}×{case.platform_width} м"],
        ["Диапазон рабочих температур", case.temp_range],
        ["Дискретность", case.discreteness],
        ["Модель датчиков", case.sensor_model],
        ["Количество датчиков", f"{case.sensor_count} шт."],
    ]
    if case.has_fence:
        data.append(["Ограждение въездное", f"h={case.fence_height_mm} мм"])

    tbl = Table(data, colWidths=[200, 200])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDDDDD")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(PageBreak())


def _build_page4(story: list, case: KpCase, styles: dict, font: str) -> None:
    """Стр. 4 — спецификация + условия оплаты."""
    story.append(Paragraph("Спецификация", styles["heading"]))
    story.append(Spacer(1, 5 * mm))

    header = ["№", "Наименование", "Кол-во", "Цена, руб.", "Срок"]
    rows = [header]
    for i, row in enumerate(case.spec_rows, 1):
        rows.append([
            str(i), row.name, row.quantity,
            fmt_price(row.price), row.deadline,
        ])
    rows.append(["", "ИТОГО", "", fmt_price(case.total), ""])

    tbl = Table(rows, colWidths=[25, 195, 65, 85, 80])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDDDDD")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, -1), (-1, -1), font),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EEEEEE")),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Условия поставки и оплаты:", styles["heading"]))
    story.append(Spacer(1, 3 * mm))
    for i, cond in enumerate(case.payment_conditions, 1):
        story.append(Paragraph(f"{i}. {cond}", styles["small"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(f"НДС: {case.nds}%", styles["body"]))


def generate_kp_pdf(case: KpCase, output_path: Path) -> None:
    """Генерирует один синтетический КП-PDF."""
    font = _register_font()
    styles = _make_styles(font)

    doc = SimpleDocTemplate(
        str(output_path), pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=15 * mm, rightMargin=15 * mm,
    )
    story: list = []
    _build_page1(story, case, styles)
    _build_page2(story, case, styles)
    _build_page3(story, case, styles, font)
    _build_page4(story, case, styles, font)

    doc.build(story)


def generate_all() -> None:
    """Генерирует все 5 КП в fixtures/."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    for case in CASES:
        path = FIXTURES_DIR / f"case_{case.case_id}_kp.pdf"
        generate_kp_pdf(case, path)


if __name__ == "__main__":
    generate_all()
    print(f"Сгенерировано {len(CASES)} КП в {FIXTURES_DIR}")
