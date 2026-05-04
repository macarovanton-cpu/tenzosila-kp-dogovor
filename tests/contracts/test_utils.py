"""Тесты для src/contracts/utils.py — числа прописью и разбор дат."""

from datetime import datetime

import pytest

from src.contracts.utils import format_date_parts, number_to_words


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
