"""Ловушки W-домена (FIX_SPEC_payment_wording_2026-07-09): формулировки оплаты.

Финальная сверка обоих генераторов с целевыми формулировками: событийные
фразы, объекты и слова-типы совпадают дословно, деньги не сверяются.

W10 (осознанно): предлог везде дефолтный «от стоимости» (решение Антона);
эталоны рама/шеф-монтаж пишут «за …» — это НЕ регресс, не «чинить» обратно.
"""
from __future__ import annotations

import re

from src.contracts.payment_line import format_payment_line
from src.contracts.supply_filler import SUPPLY_TRIGGER_TEXTS
from src.ui.payment_lines_editor import _row_to_line
from tests.autoverify.docx_text import extract_text

# Пропись суммы с заглавной буквы — регресс W4 («(Один миллион …) рублей»)
_CAPITALIZED_WORDS_RE = re.compile(r"\([А-ЯЁ][^)]*\) рублей")


def _full_lines(generated) -> list[str]:
    """Строки оплаты Спец/Договора поставки — как печатают страница и runner."""
    trigger_texts = SUPPLY_TRIGGER_TEXTS if generated.flow == "supply" else None
    return [
        format_payment_line(_row_to_line(row), f"2.{i + 1}", trigger_texts)
        for i, row in enumerate(generated.payment_rows)
    ]


def _kp_lines(generated) -> list[str]:
    """Lite-строки КП (СПЕЦ_ОПЛАТА_П1..П6 собраны из render_payment_block)."""
    lines = [generated.data.get(f"СПЕЦ_ОПЛАТА_П{i}", "") for i in range(1, 7)]
    return [ln for ln in lines if ln]


def test_w_base_scenario_full_block(generated) -> None:
    """Базовый сценарий: 5 строк Спец по структуре FIX_SPEC (full).

    W2 — предоплата монтажа есть (дефолт 50/50); W3 — слова-типы парные.
    W1 (строка 3 с процентом и объектом «Весов и доставки») вынесена в
    отдельный фронт после Стадии 2: на системном дефолте (доставка 0/100 ≠
    весы 50/50) защёлка даёт flat — пересчёт графика не умеет составную
    сумму. До W1 строка 3 — плоская, но триггер уже из общего словаря.
    """
    if generated.fixture_id != "fundament_montazh_poverka":
        return
    lines = _full_lines(generated)
    assert len(lines) == 5, f"ожидалось 5 строк, получено {len(lines)}: {lines}"
    l1, l2, l3, l4, l5 = lines
    assert l1.startswith("2.1. Предоплата 50% от стоимости Весов и фундамента Весов")
    assert "с момента подписания настоящей Спецификации." in l1
    assert l2.startswith("2.2. Доплата 50% от стоимости фундамента Весов")
    assert "Акта выполненных работ по строительству фундамента." in l2
    assert l3.startswith("2.3. Доплата в размере")  # flat до W1 (осознанно)
    assert "получения уведомления о готовности Весов к отгрузке." in l3
    assert l4.startswith("2.4. Предоплата 50% от стоимости монтажных работ и поверки")
    assert "уведомления о готовности принять монтажную бригаду на месте монтажа." in l4
    assert l5.startswith("2.5. Доплата 50% от стоимости монтажных работ и поверки")
    assert "Акта выполненных работ по настоящей Спецификации." in l5


def test_w_base_scenario_kp_lite_block(generated) -> None:
    """Базовый сценарий: КП дословно равен форме 1 эталона PAYMENT_SPEC
    (хронология: фундамент раньше отгрузки; база в каждой строке;
    «(5 дней)»; сноска под блоком)."""
    if generated.fixture_id != "fundament_montazh_poverka":
        return
    assert _kp_lines(generated) == [
        "— Предоплата 50% стоимости весов и фундамента при подписании Договора (5 дней).",
        "— Доплата 50% стоимости фундамента по Акту строительства фундамента (5 дней).",
        "— Доплата 50% стоимости весов и доставки по готовности весов к отгрузке (5 дней).",
        "— Монтаж и поверка: предоплата 50% по готовности к монтажу, "
        "доплата 50% по Акту выполненных работ (5 дней).",
        "Сроки указаны в банковских днях.",
    ]


def test_w4_w5_lowercase_words_and_percent_style(generated) -> None:
    """W4: пропись строчными; W5: нет пробела перед «%» — на всех сценариях."""
    for line in _full_lines(generated) + _kp_lines(generated):
        assert not _CAPITALIZED_WORDS_RE.search(line), (
            f"{generated.fixture_id}: пропись с заглавной: {line!r}"
        )
        assert " %" not in line, (
            f"{generated.fixture_id}: пробел перед процентом: {line!r}"
        )


def test_w6_shefmontazh_named_in_both(generated) -> None:
    """W6: на шеф-монтажном сценарии оба документа пишут «шеф-монтаж».

    Предлог — дефолтное «от стоимости» (W10), не эталонное «за».
    """
    if generated.fixture_id != "rama_shefmontazh":
        return
    full = "\n".join(_full_lines(generated))
    kp = "\n".join(_kp_lines(generated))
    assert "от стоимости шеф-монтажных работ и поверки" in full
    assert "монтажных работ и поверки в размере" not in full.replace(
        "шеф-монтажных работ и поверки", ""
    ), f"остался объект «монтажных работ» без шеф-: {full!r}"
    assert "— Шеф-монтаж и поверка:" in kp


def test_w9_orion_poles_named_in_both(generated) -> None:
    """W9: опоры/кабель-трассы ОРИОН названы в объекте и триггере обоих документов.

    Падеж — родительный в ОБОИХ регистрах («и установки опор»): база везде
    «(от) стоимости …» (эталон PAYMENT_SPEC; до фикса печаталось «и установку»).
    """
    if generated.fixture_id != "orion_poles":
        return
    full = "\n".join(_full_lines(generated))
    kp = "\n".join(_kp_lines(generated))
    assert "фундамента Весов и установки опор и кабель-трасс для ПАК ОРИОН" in full
    assert "и установку опор" not in full, f"регресс падежа (вин. после «стоимости»): {full!r}"
    assert (
        "Акта выполненных работ по строительству фундамента "
        "и установке опор и кабель-трасс" in full
    )
    assert "стоимости фундамента и установки опор и кабель-трасс для ПАК ОРИОН" in kp
    assert "по Акту строительства фундамента и установки опор" in kp


def test_a6_ruble_noun_agrees_in_line_and_itogo(generated) -> None:
    """A6/B9: существительное «рубль» согласуется с числом сквозь весь путь.

    Фикстура ruble_declension: сумма 3 455 971 (кончается на …1) → «рубль»
    (единственное). До фикста печаталось «рублей» и в строке оплаты (код,
    payment_line), и в ИТОГО (шаблон+филлер). Пятно B9: все прежние фикстуры
    кончались на «тысяч»/«сотен», declension никогда не стрелял.
    """
    if generated.fixture_id != "ruble_declension":
        return

    # Строка оплаты (код-путь): единственная prepay_100 = ИТОГО.
    lines = _full_lines(generated)
    assert len(lines) == 1, f"prepay_100 → ожидалась 1 строка, {len(lines)}: {lines}"
    line = lines[0]
    assert "3 455 971 (" in line, line
    assert "семьдесят один) рубль," in line, f"строка оплаты не согласовала: {line!r}"
    assert "рублей" not in line, f"регресс A6 в строке оплаты: {line!r}"

    # Строка ИТОГО (шаблон+филлер): рендер реальной Спецификации.
    spec_text = extract_text(generated.docx_paths["spec"])
    assert "3 455 971 (" in spec_text
    assert "семьдесят один) рубль," in spec_text, \
        "ИТОГО в Спецификации не согласовал «рубль» (плейсхолдер СПЕЦ_ИТОГО_РУБ?)"
    assert ") рублей" not in spec_text, "регресс A6 в ИТОГО Спецификации"


def test_b9_days_singular_agrees_in_kp_and_spec(generated) -> None:
    """Замок days=5 снят: days=1 согласуется в ОБОИХ проводах.

    Фикстура days_singular: prepay_100, payment_days=1. До фикса печаталось
    «1 (одного) банковских дней» (Спецификация/Договор) и «1 банковских дней»
    (КП) — существительное/прилагательное не согласовывались с числом.
    """
    if generated.fixture_id != "days_singular":
        return

    # Провод Спецификация/Договор (код-путь): format_payment_line.
    full = "\n".join(_full_lines(generated))
    assert "в течение 1 (одного) банковского дня" in full, \
        f"провод Спецификация/Договор не согласовал days=1: {full!r}"
    assert "банковских дней" not in full, f"регресс в проводе Договор: {full!r}"

    # Провод КП (настоящая генерация документа): render_payment_block.
    # Эталон: срок в скобках «(1 день)», единица — в сноске под блоком.
    kp = "\n".join(_kp_lines(generated))
    assert "(1 день)" in kp, f"провод КП не согласовал days=1: {kp!r}"
    assert "(1 дней)" not in kp, f"регресс согласования в проводе КП: {kp!r}"
    assert "банковских дней" not in kp, f"регресс в проводе КП: {kp!r}"


def test_w_rama_ramps_named_in_both(generated) -> None:
    """Рама/пандусы называются в объекте весов обоих документов (реш. Антона)."""
    if generated.fixture_id != "rama_ploshadka_montazh":
        return
    full = "\n".join(_full_lines(generated))
    kp = "\n".join(_kp_lines(generated))
    assert "Весов, комплекта пандусов и рамы" in full
    assert "стоимости весов, комплекта пандусов и рамы" in kp
    assert "стоимости весов, комплекта пандусов, рамы и доставки" in kp
