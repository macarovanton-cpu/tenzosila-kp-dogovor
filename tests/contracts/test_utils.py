"""Тесты для src/contracts/utils.py — числа прописью и разбор дат."""

from datetime import datetime

import pytest

from src.contracts.utils import (
    due_days_phrase,
    format_date_parts,
    infer_director_gender,
    number_to_words,
    rubles_word,
)


class TestRublesWord:
    """A6: согласование «рубль» с числом (B9 — сеть ловит класс, не случай)."""

    @pytest.mark.parametrize("n,expected", [
        (1, 'рубль'),
        (2, 'рубля'),
        (4, 'рубля'),
        (5, 'рублей'),
        (11, 'рублей'),
        (21, 'рубль'),
        (22, 'рубля'),
        (100, 'рублей'),
        (1000, 'рублей'),
        (1_000_001, 'рубль'),
    ])
    def test_forms(self, n, expected):
        assert rubles_word(n) == expected

    def test_teens_are_genitive_plural(self):
        # 11–14 — ловушка: последняя цифра 1–4, но форма «рублей».
        for n in (11, 12, 13, 14, 111, 114):
            assert rubles_word(n) == 'рублей'


class TestDueDaysPhrase:
    """Замок days=5 снят: согласование «день»/«банковский» с числом (B9 — сеть
    ловит класс, не случай). Родительный падеж после «в течение»: 2-4 и 5+
    совпадают («дней»), расходится только форма для чисел на 1 (кроме 11)."""

    @pytest.mark.parametrize("n,expected", [
        (1,  "1 (одного) банковского дня"),
        (2,  "2 (двух) банковских дней"),
        (3,  "3 (трёх) банковских дней"),
        (4,  "4 (четырёх) банковских дней"),
        (5,  "5 (пяти) банковских дней"),
        (11, "11 (одиннадцати) банковских дней"),
        (20, "20 (двадцати) банковских дней"),
        (21, "21 (двадцати одного) банковского дня"),
        (22, "22 (двадцати двух) банковских дней"),
        (25, "25 (двадцати пяти) банковских дней"),
        (30, "30 (тридцати) банковских дней"),
    ])
    def test_with_words(self, n, expected):
        assert due_days_phrase(n) == expected

    def test_other_unit_adjective_agrees(self):
        assert due_days_phrase(1, "рабочих") == "1 (одного) рабочего дня"
        assert due_days_phrase(2, "рабочих") == "2 (двух) рабочих дней"

    def test_without_words_kp_wire(self):
        # Провод КП (payment_renderer.py) — без прописи в скобках, только
        # согласованные прилагательное и существительное.
        assert due_days_phrase(1, with_words=False) == "1 банковского дня"
        assert due_days_phrase(30, with_words=False) == "30 банковских дней"


class TestNumberToWords:
    def test_zero(self):
        assert number_to_words(0) == 'ноль'

    def test_one(self):
        assert number_to_words(1) == 'один'

    def test_nineteen(self):
        assert number_to_words(19) == 'девятнадцать'

    def test_hundred(self):
        assert number_to_words(100) == 'сто'

    def test_thousand(self):
        assert number_to_words(1000) == 'одна тысяча'

    def test_two_thousand(self):
        assert number_to_words(2000) == 'две тысячи'

    def test_five_thousand(self):
        assert number_to_words(5000) == 'пять тысяч'

    def test_million(self):
        assert number_to_words(1_000_000) == 'один миллион'

    def test_two_million_eight_hundred_thirty_five_thousand(self):
        assert number_to_words(2_835_000) == (
            'два миллиона восемьсот тридцать пять тысяч'
        )

    def test_all_digits(self):
        result = number_to_words(999_999_999)
        assert result == (
            'девятьсот девяносто девять миллионов '
            'девятьсот девяносто девять тысяч '
            'девятьсот девяносто девять'
        )

    def test_remainder_only(self):
        assert number_to_words(42) == 'сорок два'

    def test_hundreds_remainder(self):
        assert number_to_words(501) == 'пятьсот один'


class TestInferDirectorGender:
    def test_female_ovna(self):
        assert infer_director_gender('Иванова Мария Петровна') == 'female'

    def test_female_evna(self):
        assert infer_director_gender('Сидорова Анна Андреевна') == 'female'

    def test_female_ichna(self):
        assert infer_director_gender('Кузнецова Ольга Ильинична') == 'female'

    def test_male(self):
        assert infer_director_gender('Фокин Сергей Владимирович') == 'male'

    def test_no_patronymic(self):
        assert infer_director_gender('Иванов') == 'male'

    def test_empty(self):
        assert infer_director_gender('') == 'male'

    def test_two_words_male(self):
        assert infer_director_gender('Петров Александр') == 'male'

    def test_mixed_case(self):
        assert infer_director_gender('ИВАНОВА МАРИЯ ПЕТРОВНА') == 'female'


class TestFormatDateParts:
    def test_dd_mm_yyyy(self):
        result = format_date_parts('15.03.2026')
        assert result['ДОГОВОР_ДЕНЬ'] == '15'
        assert result['ДОГОВОР_МЕСЯЦ'] == 'марта'
        assert result['ДОГОВОР_ГОД'] == '2026'
        assert result['ДОГОВОР_ДАТА_ПОЛНАЯ'] == '15.03.2026'

    def test_yyyy_mm_dd(self):
        result = format_date_parts('2026-03-15')
        assert result['ДОГОВОР_ДЕНЬ'] == '15'
        assert result['ДОГОВОР_МЕСЯЦ'] == 'марта'
        assert result['ДОГОВОР_ГОД'] == '2026'

    def test_invalid_fallback_to_today(self):
        now = datetime.now()
        result = format_date_parts('мусор')
        assert result['ДОГОВОР_ДЕНЬ'] == str(now.day)
        assert result['ДОГОВОР_ГОД'] == str(now.year)

    def test_single_digit_day(self):
        result = format_date_parts('5.01.2025')
        assert result['ДОГОВОР_ДЕНЬ'] == '5'
        assert result['ДОГОВОР_МЕСЯЦ'] == 'января'
