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
    """Базовый сценарий: КП дословно равен блоку «КП (lite)» из FIX_SPEC."""
    if generated.fixture_id != "fundament_montazh_poverka":
        return
    assert _kp_lines(generated) == [
        "— Предоплата 50% стоимости весов и фундамента — подписание Договора.",
        "— Доплата 50% за весы и доставку — готовность Весов к отгрузке.",
        "— Доплата 50% за фундамент — Акт по строительству фундамента.",
        "— Монтаж и поверка: 50% предоплата — готовность к монтажу; "
        "50% доплата — Акт выполненных работ.",
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
    """W9: опоры/кабель-трассы ОРИОН названы в объекте и триггере обоих документов."""
    if generated.fixture_id != "orion_poles":
        return
    full = "\n".join(_full_lines(generated))
    kp = "\n".join(_kp_lines(generated))
    assert "фундамента Весов и установку опор и кабель-трасс для ПАК ОРИОН" in full
    assert (
        "Акта выполненных работ по строительству фундамента "
        "и установке опор и кабель-трасс" in full
    )
    assert "за фундамент и установку опор и кабель-трасс для ПАК ОРИОН" in kp
    assert (
        "Акт по строительству фундамента "
        "и установке опор и кабель-трасс" in kp
    )


def test_w_rama_ramps_named_in_both(generated) -> None:
    """Рама/пандусы называются в объекте весов обоих документов (реш. Антона)."""
    if generated.fixture_id != "rama_ploshadka_montazh":
        return
    full = "\n".join(_full_lines(generated))
    kp = "\n".join(_kp_lines(generated))
    assert "Весов, комплекта пандусов и рамы" in full
    assert "стоимости весов, комплекта пандусов и рамы" in kp
    assert "за весы, комплект пандусов, раму и доставку" in kp
