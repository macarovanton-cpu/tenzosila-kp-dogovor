"""
utils.py — вспомогательные функции: числа прописью, форматирование дат.
"""

ONES = [
    '', 'один', 'два', 'три', 'четыре', 'пять',
    'шесть', 'семь', 'восемь', 'девять', 'десять',
    'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать',
    'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать'
]
TENS = [
    '', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят',
    'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто'
]
HUNDREDS = [
    '', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот',
    'шестьсот', 'семьсот', 'восемьсот', 'девятьсот'
]

# (именительный ед., именительный мн., родительный мн.)
THOUSANDS = ('тысяча', 'тысячи', 'тысяч')
MILLIONS  = ('миллион', 'миллиона', 'миллионов')

# Для тысяч используем женский род
ONES_F = [
    '', 'одна', 'две', 'три', 'четыре', 'пять',
    'шесть', 'семь', 'восемь', 'девять', 'десять',
    'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать',
    'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать'
]


def _plural(n: int, forms: tuple) -> str:
    """Выбирает правильную форму слова для числа."""
    n = abs(n) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return forms[2]
    if n1 == 1:
        return forms[0]
    if 2 <= n1 <= 4:
        return forms[1]
    return forms[2]


def _hundreds(n: int, feminine: bool = False) -> str:
    """Преобразует число 1-999 в слова."""
    parts = []
    h = n // 100
    remainder = n % 100

    if h:
        parts.append(HUNDREDS[h])

    if remainder < 20:
        ones = ONES_F if feminine else ONES
        if remainder:
            parts.append(ones[remainder])
    else:
        t = remainder // 10
        o = remainder % 10
        if t:
            parts.append(TENS[t])
        if o:
            ones = ONES_F if feminine else ONES
            parts.append(ones[o])

    return ' '.join(parts)


def number_to_words(n: int) -> str:
    """
    Преобразует целое число в слова на русском языке.
    Пример: 2835000 → 'два миллиона восемьсот тридцать пять тысяч'
    """
    if n == 0:
        return 'ноль'

    parts = []

    millions = n // 1_000_000
    thousands = (n % 1_000_000) // 1_000
    remainder = n % 1_000

    if millions:
        parts.append(_hundreds(millions))
        parts.append(_plural(millions, MILLIONS))

    if thousands:
        parts.append(_hundreds(thousands, feminine=True))
        parts.append(_plural(thousands, THOUSANDS))

    if remainder:
        parts.append(_hundreds(remainder))

    return ' '.join(parts)


# ---------------------------------------------------------------------------
# Родительный падеж числительных для «в течение N (...) дней», диапазон 0–90.
# ---------------------------------------------------------------------------

_DAYS_GEN_UNITS: dict[int, str] = {
    0: 'нуля', 1: 'одного', 2: 'двух', 3: 'трёх', 4: 'четырёх',
    5: 'пяти', 6: 'шести', 7: 'семи', 8: 'восьми', 9: 'девяти',
}
_DAYS_GEN_TEENS: dict[int, str] = {
    10: 'десяти', 11: 'одиннадцати', 12: 'двенадцати', 13: 'тринадцати',
    14: 'четырнадцати', 15: 'пятнадцати', 16: 'шестнадцати',
    17: 'семнадцати', 18: 'восемнадцати', 19: 'девятнадцати',
}
_DAYS_GEN_TENS: dict[int, str] = {
    20: 'двадцати', 30: 'тридцати', 40: 'сорока', 50: 'пятидесяти',
    60: 'шестидесяти', 70: 'семидесяти', 80: 'восьмидесяти', 90: 'девяноста',
}


def days_genitive(n: int) -> str:
    """Число 0–90 в родительном падеже для пропись дней («семи», «сорока пяти»)."""
    if not 0 <= n <= 90:
        raise ValueError(f"days_genitive поддерживает 0–90, получено {n}")
    if n < 10:
        return _DAYS_GEN_UNITS[n]
    if n < 20:
        return _DAYS_GEN_TEENS[n]
    tens, unit = (n // 10) * 10, n % 10
    if unit == 0:
        return _DAYS_GEN_TENS[tens]
    return f"{_DAYS_GEN_TENS[tens]} {_DAYS_GEN_UNITS[unit]}"


MONTHS_RU = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}

MONTHS_RU_NOM = {
    1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель',
    5: 'май', 6: 'июнь', 7: 'июль', 8: 'август',
    9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'
}


_FEMALE_PATRONYMIC_SUFFIXES = ('овна', 'евна', 'ична', 'инична')


def infer_director_gender(full_name: str) -> str:
    """Определяет род директора по отчеству.
    Возвращает 'female' если отчество женское, иначе 'male'.
    """
    parts = full_name.strip().split()
    if len(parts) < 2:
        return 'male'
    patronymic = parts[-1].lower()
    if any(patronymic.endswith(s) for s in _FEMALE_PATRONYMIC_SUFFIXES):
        return 'female'
    return 'male'


def format_date_parts(date_str: str) -> dict:
    """
    Разбирает дату из строки и возвращает словарь с частями.
    Поддерживает форматы: DD.MM.YYYY, YYYY-MM-DD, D месяц YYYY
    Возвращает: {ДОГОВОР_ДЕНЬ, ДОГОВОР_МЕСЯЦ, ДОГОВОР_ГОД, ДОГОВОР_ДАТА_ПОЛНАЯ}
    """
    import re
    from datetime import datetime

    date_str = date_str.strip()
    day, month_num, year = None, None, None

    # Формат DD.MM.YYYY
    m = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_str)
    if m:
        day, month_num, year = int(m.group(1)), int(m.group(2)), int(m.group(3))

    # Формат YYYY-MM-DD
    if not day:
        m = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if m:
            year, month_num, day = int(m.group(1)), int(m.group(2)), int(m.group(3))

    if not day:
        # Пробуем текущую дату как fallback
        now = datetime.now()
        day, month_num, year = now.day, now.month, now.year

    month_name = MONTHS_RU.get(month_num, '')

    return {
        'ДОГОВОР_ДЕНЬ': str(day),
        'ДОГОВОР_МЕСЯЦ': month_name,
        'ДОГОВОР_ГОД': str(year),
        'ДОГОВОР_ДАТА_ПОЛНАЯ': f'{day:02d}.{month_num:02d}.{year}',
    }
