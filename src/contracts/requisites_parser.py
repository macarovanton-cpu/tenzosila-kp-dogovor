"""
requisites_parser.py — парсер блока реквизитов контрагента.

Чистая функция без Streamlit. Принимает произвольный текст (копипаст
карточки контрагента), возвращает dict ЗАКАЗЧИК_* с найденными полями.
Возвращаются ТОЛЬКО непустые поля (при слиянии в state не перетирает ручной ввод).

Принцип: ФОРМАТ значения первичен, подпись-якорь вторична.
При неоднозначности — пустое поле (юридический документ, лучше пусто).
"""
from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Валидация ИНН (контрольная сумма, без внешних зависимостей)
# ---------------------------------------------------------------------------

def _valid_inn(digits: str) -> bool:
    """Проверить контрольную сумму ИНН (10 или 12 цифр).

    10-значный ИНН: контрольная 10-я цифра по весам [2,4,10,3,5,9,4,6,8].
    12-значный ИНН: 11-я и 12-я контрольные цифры по двум наборам весов.
    Возвращает False если длина не 10/12 или сумма не совпадает.
    """
    if len(digits) not in (10, 12):
        return False
    d = [int(c) for c in digits]

    def _ctrl(weights: list[int], digs: list[int]) -> int:
        return (sum(w * v for w, v in zip(weights, digs)) % 11) % 10

    if len(digits) == 10:
        w = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        return _ctrl(w, d[:9]) == d[9]
    else:  # 12
        w11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        w12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        return _ctrl(w11, d[:10]) == d[10] and _ctrl(w12, d[:11]) == d[11]


# ---------------------------------------------------------------------------
# Вспомогательные паттерны
# ---------------------------------------------------------------------------

# Нормализация: убираем неразрывные пробелы и двойные пробелы
_NBSP = re.compile(r"[\xa0  ]+")

# Числовые токены: последовательности цифр (для ИНН/КПП/ОГРН/счетов/БИК)
_DIGITS_ONLY = re.compile(r"\d{7,25}")

# Email
_EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}")

# Телефон: +7/8 и дальше цифры (с любыми разделителями)
_PHONE_RE = re.compile(r"(?:\+7|8)[\s\-(]?\d{3}[\s\-)]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")

# Наименование организации: ОПФ + кавычки (жадный захват содержимого кавычек)
_NAME_RE = re.compile(
    r'(ООО|ПАО|ЗАО|АО|ИП)\s*["«“]([^"»”]{1,120})["»”]',
    re.IGNORECASE,
)

# Адрес: строка начинается с 6-значного индекса ИЛИ содержит «г.»/«ул.»/«пер.»
_ADDR_RE = re.compile(
    r"(?:\d{6}[,\s].{10,}|(?:^|\n)(?:г\.|ул\.|пер\.|пр\.|бульвар|проспект).{10,})",
    re.IGNORECASE | re.MULTILINE,
)

# Префиксы счетов
_RS_PREFIXES = ("407", "405", "406")
_KS_PREFIXES = ("301",)

# Якоря для реквизитов (для разрешения неоднозначных случаев)
_ANCHOR_BIK = re.compile(r"бик\b", re.IGNORECASE)
_ANCHOR_KPP = re.compile(r"кпп\b", re.IGNORECASE)
_ANCHOR_RS = re.compile(r"р/?с\b|расчётн|расчетн", re.IGNORECASE)
_ANCHOR_KS = re.compile(r"к/?с\b|корр?есп", re.IGNORECASE)

# Якоря для адресов
_ANCHOR_YUR = re.compile(r"юрид|юр\.", re.IGNORECASE)
_ANCHOR_POCT = re.compile(r"почт|факт", re.IGNORECASE)

# Якоря для директора (консервативно — только «в лице», «директор», «руководитель»)
_ANCHOR_DIRECTOR = re.compile(
    r"(?:в\s+лице|директор\b|руководитель\b|управляющий\b|президент\b)",
    re.IGNORECASE,
)

# Слова-должности (для извлечения из текста рядом с ФИО)
_POSITION_WORDS = re.compile(
    r"(генеральный\s+директор|исполнительный\s+директор|финансовый\s+директор"
    r"|технический\s+директор|коммерческий\s+директор|управляющий\s+директор"
    r"|председатель\s+правления|генеральный\s+менеджер"
    r"|председатель|президент|управляющий|директор"
    r"|индивидуальный\s+предприниматель)",
    re.IGNORECASE,
)

# ФИО: три слова с заглавной буквы (фамилия имя отчество)
_FIO_RE = re.compile(r"[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+")

# Основание: текст после «на основании»
_OSNOV_RE = re.compile(r"на\s+основании\s+(.+?)(?:\.|,|$|\n)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------------------

def parse_requisites(text: str) -> dict[str, str]:
    """Разобрать вставленный блок реквизитов в dict ЗАКАЗЧИК_*.

    Возвращает ТОЛЬКО непустые распознанные поля.
    При неоднозначности — поле отсутствует (не угадываем).
    """
    if not text:
        return {}

    # Нормализация
    text = _NBSP.sub(" ", text)
    result: dict[str, str] = {}

    # ------------------------------------------------------------------
    # 1. Email и телефон (однозначные паттерны)
    # ------------------------------------------------------------------
    m = _EMAIL_RE.search(text)
    if m:
        result["ЗАКАЗЧИК_EMAIL"] = m.group(0)

    m = _PHONE_RE.search(text)
    if m:
        result["ЗАКАЗЧИК_ТЕЛЕФОН"] = m.group(0)

    # ------------------------------------------------------------------
    # 2. Наименование организации
    # ------------------------------------------------------------------
    m = _NAME_RE.search(text)
    if m:
        opf = m.group(1).upper()
        name = m.group(2).strip()
        result["ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"] = f'{opf} "{name}"'

    # ------------------------------------------------------------------
    # 3. Числовые токены: ИНН, ОГРН, БИК, КПП, р/с, к/с
    # ------------------------------------------------------------------
    _extract_numeric_fields(text, result)

    # ------------------------------------------------------------------
    # 4. Адреса
    # ------------------------------------------------------------------
    _extract_addresses(text, result)

    # ------------------------------------------------------------------
    # 5. ФИО директора, должность, основание (best-effort, консервативно)
    # ------------------------------------------------------------------
    _extract_director_fields(text, result)

    return result


def _extract_numeric_fields(text: str, result: dict[str, str]) -> None:
    """Извлечь числовые реквизиты из текста и записать в result."""
    # Разбиваем текст на строки для локального поиска якорей
    lines = text.splitlines()

    for line in lines:
        digits_in_line = _DIGITS_ONLY.findall(line)
        for digits in digits_in_line:
            length = len(digits)

            # ИНН: 10 или 12 цифр + валидная контрольная сумма
            if length in (10, 12) and _valid_inn(digits):
                if "ЗАКАЗЧИК_ИНН" not in result:
                    result["ЗАКАЗЧИК_ИНН"] = digits
                continue

            # ОГРН: 13 или 15 цифр
            if length in (13, 15):
                if "ЗАКАЗЧИК_ОГРН" not in result:
                    result["ЗАКАЗЧИК_ОГРН"] = digits
                continue

            # БИК vs КПП: оба 9 цифр
            if length == 9:
                _resolve_bik_kpp(digits, line, result)
                continue

            # р/с vs к/с: оба 20 цифр
            if length == 20:
                _resolve_rs_ks(digits, line, result)
                continue


def _resolve_bik_kpp(digits: str, context: str, result: dict[str, str]) -> None:
    """9 цифр: определить БИК или КПП по префиксу и якорям.

    БИК: начинается на 04.
    КПП: не начинается на 04.
    При неоднозначности (нестандартный префикс + нет якоря) — не записываем.
    """
    starts_04 = digits.startswith("04")

    if starts_04:
        if "ЗАКАЗЧИК_БИК" not in result:
            result["ЗАКАЗЧИК_БИК"] = digits
    else:
        # не 04 → КПП, но только если нет якоря БИК рядом
        if _ANCHOR_BIK.search(context):
            # Якорь БИК есть, но префикс не 04 — неоднозначность → пусто
            return
        if "ЗАКАЗЧИК_КПП" not in result:
            result["ЗАКАЗЧИК_КПП"] = digits


def _resolve_rs_ks(digits: str, context: str, result: dict[str, str]) -> None:
    """20 цифр: определить р/с или к/с по префиксу и якорям.

    к/с: начинается на 301.
    р/с: начинается на 407/405/406.
    Иначе: якорь определяет; без якоря → пусто.
    """
    starts_ks = digits.startswith("301")
    starts_rs = any(digits.startswith(p) for p in _RS_PREFIXES)

    if starts_ks and not starts_rs:
        if "ЗАКАЗЧИК_КС" not in result:
            result["ЗАКАЗЧИК_КС"] = digits
    elif starts_rs and not starts_ks:
        if "ЗАКАЗЧИК_РС" not in result:
            result["ЗАКАЗЧИК_РС"] = digits
    else:
        # Неоднозначный префикс — используем якорь
        has_rs = _ANCHOR_RS.search(context)
        has_ks = _ANCHOR_KS.search(context)
        if has_ks and not has_rs and "ЗАКАЗЧИК_КС" not in result:
            result["ЗАКАЗЧИК_КС"] = digits
        elif has_rs and not has_ks and "ЗАКАЗЧИК_РС" not in result:
            result["ЗАКАЗЧИК_РС"] = digits
        # Оба якоря или ни одного → пустое поле (не угадываем)


def _extract_addresses(text: str, result: dict[str, str]) -> None:
    """Извлечь юридический и почтовый адреса по якорям.

    Без якоря: весь найденный адрес → АДРЕС_ЮР, почтовый пуст.
    С якорями: разводим по АДРЕС_ЮР / АДРЕС_ПОЧТ.
    """
    # Разбиваем на строки, ищем строки-кандидаты адресов
    lines = text.splitlines()
    addr_candidates: list[tuple[str, str]] = []  # (тип_якоря: yur|poct|none, строка)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Строка выглядит как адрес?
        is_addr = (
            re.search(r"\d{6}", stripped)  # индекс
            or re.search(r"(?:г\.|ул\.|пер\.|пр-т|проспект|бульвар)\s", stripped, re.IGNORECASE)
        )
        if not is_addr:
            continue
        if _ANCHOR_YUR.search(stripped):
            addr_candidates.append(("yur", stripped))
        elif _ANCHOR_POCT.search(stripped):
            addr_candidates.append(("poct", stripped))
        else:
            addr_candidates.append(("none", stripped))

    for kind, addr_line in addr_candidates:
        # Очищаем строку от якорного слова
        addr_clean = re.sub(
            r"(?:юридич[а-я]*|юр\.|почтов[а-я]*|фактич[а-я]*)\s*(?:адрес\s*)?:?\s*",
            "",
            addr_line,
            flags=re.IGNORECASE,
        ).strip()
        if not addr_clean:
            continue
        if kind == "yur" and "ЗАКАЗЧИК_АДРЕС_ЮР" not in result:
            result["ЗАКАЗЧИК_АДРЕС_ЮР"] = addr_clean
        elif kind == "poct" and "ЗАКАЗЧИК_АДРЕС_ПОЧТ" not in result:
            result["ЗАКАЗЧИК_АДРЕС_ПОЧТ"] = addr_clean
        elif kind == "none" and "ЗАКАЗЧИК_АДРЕС_ЮР" not in result:
            # Без якоря → юридический (менеджер разведёт руками)
            result["ЗАКАЗЧИК_АДРЕС_ЮР"] = addr_clean


def _extract_director_fields(text: str, result: dict[str, str]) -> None:
    """Извлечь ФИО директора, должность, основание — консервативно.

    ФИО директора: ТОЛЬКО при явном якоре «в лице» / «директор» / «руководитель»
    вплотную к ФИО. При нескольких кандидатах → пусто (правка №2).
    """
    # Основание: текст после «на основании»
    m = _OSNOV_RE.search(text)
    if m:
        osnov = m.group(1).strip().rstrip(".,;")
        if osnov:
            result["ЗАКАЗЧИК_ОСНОВАНИЕ"] = osnov

    # Ищем все вхождения якорей директора
    director_fios: list[str] = []
    director_positions: list[str] = []

    for anchor_match in _ANCHOR_DIRECTOR.finditer(text):
        # Окно: 200 символов после якоря
        window_start = anchor_match.start()
        window = text[window_start: window_start + 200]

        # Ищем должность в окне
        pos_m = _POSITION_WORDS.search(window)
        if pos_m:
            director_positions.append(pos_m.group(1).strip())

        # Ищем ФИО в окне
        fio_m = _FIO_RE.search(window)
        if fio_m:
            director_fios.append(fio_m.group(0))

    # Консервативно: берём только при единственном найденном ФИО директора
    unique_fios = list(dict.fromkeys(director_fios))  # порядок сохраняем
    if len(unique_fios) == 1:
        result["ЗАКАЗЧИК_ДИРЕКТОР_ФИО"] = unique_fios[0]
    # else: ноль или несколько → пусто (не угадываем)

    # Должность: тоже берём только при однозначном якоре
    unique_positions = list(dict.fromkeys(director_positions))
    if len(unique_positions) == 1:
        result["ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ"] = unique_positions[0].capitalize()
