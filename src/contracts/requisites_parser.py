"""
requisites_parser.py — парсер блока реквизитов контрагента.

Чистая функция без Streamlit. Принимает произвольный текст (копипаст
карточки контрагента), возвращает dict ЗАКАЗЧИК_* с найденными полями.
Возвращаются ТОЛЬКО непустые поля (при слиянии в state не перетирает ручной ввод).

Принцип: ФОРМАТ значения первичен, подпись-якорь вторична.
При неоднозначности — пустое поле (юридический документ, лучше пусто).
"""
from __future__ import annotations

import logging
import re

_logger = logging.getLogger(__name__)


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

# Слитный формат «ИНН/КПП 10цифр/9цифр»: первое → ИНН, второе → КПП.
# Подпись + формат 10/9 однозначны, берём по ДЛИНЕ (без контрольной суммы).
# Границы (?<!\d)…(?!\d) — ровно 10/9; иначе формат не совпал → не угадываем.
_INN_KPP_SLASH_RE = re.compile(
    r"ИНН\s*/\s*КПП\s*:?\s*(?<!\d)(\d{10})\s*/\s*(\d{9})(?!\d)", re.IGNORECASE
)

# Email
_EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}")

# Телефон: гибкий кандидат (код города 3-5 цифр, дальше произвольные группы
# цифр с разделителями). Раньше жёстко зашивали разбивку 3-3-2-2 — реальные
# карточки её не соблюдают (4-5-значный код города даёт другую разбивку
# остатка). Точность — по ОБЩЕМУ числу цифр (см. _find_phone), как ИНН/БИК/КПП
# в этом файле уже проверяются по формату, а не по жёсткой форме записи.
# Цифровые границы (?<!\d)…(?!\d) — чтобы не матчить телефон внутри длинного
# числа (р/с, к/с).
_PHONE_CANDIDATE_RE = re.compile(
    r"(?<!\d)(\+7|8)?[\s\-]?\(?\d{3,5}\)?(?:[\s\-]?\d{1,4}){1,4}(?!\d)"
)
# Якорь для варианта без префикса +7/8: без него риск принять произвольное
# 10-значное число (ИНН, часть счёта) за телефон.
_PHONE_ANCHOR_RE = re.compile(r"\bтел\w*|\bфакс\w*", re.IGNORECASE)


# Окно поиска якоря «тел/факс» перед кандидатом без префикса: покрывает
# «Телефон для связи: …», но не всю строку — в слитной карточке (вся карточка
# одной строкой) якорь где-то на строке есть всегда, и первый 10-значник (ИНН)
# уезжал в телефон.
_PHONE_ANCHOR_WINDOW = 40


def _find_phone(text: str) -> str | None:
    """Найти телефон в тексте.

    С префиксом (+7/8) — всего 11 цифр, ищем где угодно. Без префикса —
    ровно 10 цифр, но только если якорь «тел»/«факс» стоит непосредственно
    ПЕРЕД кандидатом, в пределах окна на той же строке (иначе не угадываем —
    см. принцип модуля).
    """
    for m in _PHONE_CANDIDATE_RE.finditer(text):
        raw = m.group(0).strip()
        digits = re.sub(r"\D", "", raw)
        if m.group(1):
            if len(digits) == 11:
                return raw
            continue
        if len(digits) == 10:
            line_start = text.rfind("\n", 0, m.start()) + 1
            window = text[max(line_start, m.start() - _PHONE_ANCHOR_WINDOW): m.start()]
            if _PHONE_ANCHOR_RE.search(window):
                return raw
    return None

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
    r"|председатель|президент|управляющий|руководитель|директор"
    r"|глава\s+кфх|индивидуальный\s+предприниматель)",
    re.IGNORECASE,
)

# Маркеры «чужой» строки: ФИО оттуда НЕ принадлежит директору
# (главбух / контакт / телефон / e-mail / почта / факс).
_OTHER_ROLE_RE = re.compile(
    r"бухгалт|главбух|контакт|тел\b|телефон|e-?mail|почт|факс", re.IGNORECASE
)

# ФИО: три слова с заглавной буквы (фамилия имя отчество)
_FIO_RE = re.compile(r"[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+")

# Основание: метка-начало («на основании» / «Основание:»). Резать до следующей
# метки поля, а НЕ до первой точки/запятой — иначе «Доверенность № 5 от
# 12.01.2026» обрежется по дате.
_OSNOV_START = re.compile(r"(?:на\s+)?основани\w*\s*:?\s*", re.IGNORECASE)

# Метка банка (первое вхождение — начало сегмента). Слово «Банк» матчим только
# как начало поля (перед ним не буква и не дефис): «в Банк», «Банк:»,
# «Наименование банка», «Банк получателя» — но НЕ «Сбербанк» и НЕ «Тест-Банк».
_BANK_LABEL = re.compile(
    r"(?:наименование\s+банка|банк\w*\s+получателя|(?<![А-Яа-яёЁ\-])банк\w*)\s*:?\s*",
    re.IGNORECASE,
)

# Границы-конца сегмента БАНКА: следующая метка ЛЮБОГО ДРУГОГО поля. Слово
# «Банк» СЮДА НЕ входит — иначе внутреннее «Банк» в названии («РНКБ Банк»,
# «Банк «Санкт-Петербург»») оборвёт сегмент. Баланс кавычек НЕ учитываем.
_BANK_END = re.compile(
    r"(?:БИК\b|ИНН\b|КПП\b|ОГРН|ОКПО|ОКВЭД|К/?с\b|Корр|Кор\.|Р/?с\b|Расч[её]тн"
    r"|Тел\b|Телефон|Факс|E-?mail|Эл\.\s*почт|Почтов|Юридич|Юр\.|Адрес"
    r"|Основани|в\s+лице|Директор|Руководител|Президент|Председател|Контакт)",
    re.IGNORECASE,
)

# Границы-конца сегмента ОСНОВАНИЯ: как у банка, плюс «Банк» (основание не
# содержит слова «Банк»).
_OSNOV_END = re.compile(
    r"(?:БИК\b|ИНН\b|КПП\b|ОГРН|ОКПО|ОКВЭД|Банк|К/?с\b|Корр|Кор\.|Р/?с\b|Расч[её]тн"
    r"|Тел\b|Телефон|Факс|E-?mail|Эл\.\s*почт|Почтов|Юридич|Юр\.|Адрес"
    r"|в\s+лице|Директор|Руководител|Президент|Председател|Контакт)",
    re.IGNORECASE,
)


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

    phone = _find_phone(text)
    if phone:
        result["ЗАКАЗЧИК_ТЕЛЕФОН"] = phone
    elif _PHONE_ANCHOR_RE.search(text):
        _logger.warning(
            "в тексте есть якорь тел/факс, но телефон не распознан: %r", text[:200]
        )

    # ------------------------------------------------------------------
    # 2. Банк (label-anchored) — ДО имени/адреса: сегмент банка забеливаем,
    #    чтобы ОПФ+кавычки банка («АО «Альфа-Банк»») не подменили краткое
    #    наименование, а город из банка («, г. Красноярск») не утёк в адрес.
    # ------------------------------------------------------------------
    bank_span = _extract_bank(text, result)
    scan_text = _blank_span(text, bank_span) if bank_span else text

    # ------------------------------------------------------------------
    # 3. Наименование организации (по тексту без сегмента банка)
    # ------------------------------------------------------------------
    m = _NAME_RE.search(scan_text)
    if m:
        opf = m.group(1).upper()
        name = m.group(2).strip()
        result["ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"] = f'{opf} "{name}"'

    # ------------------------------------------------------------------
    # 4. Числовые токены: ИНН, ОГРН, БИК, КПП, р/с, к/с (по полному тексту —
    #    в названии банка цифр нет, забеливание не нужно).
    # ------------------------------------------------------------------
    # Слитный «ИНН/КПП …/…» разбираем ДО общей логики (она не перетрёт —
    # использует not-in/setdefault).
    _extract_inn_kpp_slash(text, result)
    _extract_numeric_fields(text, result)

    # ------------------------------------------------------------------
    # 5. Адреса (по тексту без сегмента банка)
    # ------------------------------------------------------------------
    _extract_addresses(scan_text, result)

    # ------------------------------------------------------------------
    # 6. ФИО директора, должность (best-effort, консервативно) и основание
    # ------------------------------------------------------------------
    _extract_director_fields(text, result)
    _extract_osnovanie(text, result)

    return result


def _extract_inn_kpp_slash(text: str, result: dict[str, str]) -> None:
    """Слитный «ИНН/КПП 10цифр/9цифр» → ИНН (первое) и КПП (второе) по длине."""
    m = _INN_KPP_SLASH_RE.search(text)
    if m:
        result.setdefault("ЗАКАЗЧИК_ИНН", m.group(1))
        result.setdefault("ЗАКАЗЧИК_КПП", m.group(2))


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

    БИК РФ всегда начинается на 04. Но КПП регионов с кодом 04 (напр. налоговые
    органы) — тоже на 04. Поэтому:
    - не 04 → БИК физически невозможен → КПП (якорь БИК без КПП = противоречие → пусто);
    - 04 → формат подходит обоим → явный одиночный якорь КПП перебивает дефолт-БИК.
    """
    starts_04 = digits.startswith("04")
    has_bik = bool(_ANCHOR_BIK.search(context))
    has_kpp = bool(_ANCHOR_KPP.search(context))

    if starts_04:
        if has_kpp and not has_bik:
            result.setdefault("ЗАКАЗЧИК_КПП", digits)
        else:
            # якорь БИК, оба якоря или нет якоря → БИК (дефолт для 04)
            result.setdefault("ЗАКАЗЧИК_БИК", digits)
    else:
        if has_bik and not has_kpp:
            # не 04 + якорь БИК → противоречие → пусто (не угадываем)
            return
        result.setdefault("ЗАКАЗЧИК_КПП", digits)


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
        # Индекс — отдельностоящее 6-значное число, а НЕ подстрока длинного
        # реквизита (ИНН/ОГРН/счёт): иначе любая числовая строка станет адресом.
        is_addr = (
            re.search(r"(?<!\d)\d{6}(?!\d)", stripped)  # индекс
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


def _next_content_line(text: str, anchor_start: int) -> str:
    """Первая непустая строка ПОСЛЕ строки, на которой стоит якорь."""
    for line in text[anchor_start:].split("\n")[1:]:
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _segment_until(text: str, start: int, boundary: re.Pattern[str]) -> str:
    """Сегмент от start до ближайшей границы: метка поля / перенос / конец."""
    rest = text[start:]
    end = rest.find("\n")
    if end == -1:
        end = len(rest)
    m = boundary.search(rest[:end])
    if m:
        end = m.start()
    return rest[:end]


def _blank_span(text: str, span: tuple[int, int]) -> str:
    """Заменить символы диапазона [start,end) пробелами (перенос сохраняем)."""
    start, end = span
    chars = list(text)
    for i in range(start, min(end, len(chars))):
        if chars[i] != "\n":
            chars[i] = " "
    return "".join(chars)


def _extract_bank(text: str, result: dict[str, str]) -> tuple[int, int] | None:
    """Название банка: от метки банка до следующей метки поля.

    Кавычки и слово «Банк» внутри названия игнорируем (см. _BANK_END). Возвращает
    диапазон сегмента (для забеливания перед разбором имени/адреса) или None.
    """
    for m in _BANK_LABEL.finditer(text):
        value_start = m.end()
        raw = _segment_until(text, value_start, _BANK_END)
        cleaned = raw.strip().rstrip(".,; ")
        # Сегмент без единой буквы (пусто, число, кавычка-огрызок) — не значение
        # банка: отбраковываем и пробуем следующую метку.
        if not cleaned or not re.search(r"[А-Яа-яёЁA-Za-z]", cleaned):
            continue
        result.setdefault("ЗАКАЗЧИК_БАНК", cleaned)
        return (m.start(), value_start + len(raw))
    return None


def _extract_osnovanie(text: str, result: dict[str, str]) -> None:
    """Основание: от метки «на основании»/«Основание:» до следующей метки поля.

    Не режем на точке/запятой — иначе «Доверенность № 5 от 12.01.2026»
    обрежется по дате.
    """
    m = _OSNOV_START.search(text)
    if not m:
        return
    raw = _segment_until(text, m.end(), _OSNOV_END)
    osnov = raw.strip().rstrip(".,; ")
    if osnov:
        result["ЗАКАЗЧИК_ОСНОВАНИЕ"] = osnov


def _extract_director_fields(text: str, result: dict[str, str]) -> None:
    """Извлечь ФИО директора и должность — консервативно.

    ФИО директора: ТОЛЬКО при явном якоре «в лице» / «директор» / «руководитель»
    вплотную к ФИО. При нескольких кандидатах → пусто (правка №2).
    Слово-должность в начале окна («Директор Ковалёв…») срезаем ДО поиска ФИО —
    иначе оно утечёт в ФИО (три слова с заглавной) и сломает РП/инициалы.
    """
    # Ищем все вхождения якорей директора
    director_fios: list[str] = []
    director_positions: list[str] = []

    for anchor_match in _ANCHOR_DIRECTOR.finditer(text):
        # Окно: строка самого якоря (до ближайшего \n). НЕ перетекаем на
        # следующую строку — иначе ФИО из строки главбуха/контакта попадёт
        # в директора.
        window_start = anchor_match.start()
        newline = text.find("\n", window_start)
        window_end = newline if newline != -1 else len(text)
        window = text[window_start:window_end]

        # Должность + срез приставки: ФИО ищем в остатке ПОСЛЕ слова-должности.
        pos_m = _POSITION_WORDS.search(window)
        fio_region = window
        if pos_m:
            director_positions.append(pos_m.group(1).strip())
            fio_region = window[pos_m.end():]

        # Ищем ФИО в остатке окна; если нет — на следующей непустой строке,
        # но только если та не вводит новую должность/контакт (главбух и т.п.).
        fio_m = _FIO_RE.search(fio_region)
        if not fio_m:
            next_line = _next_content_line(text, window_start)
            if (next_line
                    and not _OTHER_ROLE_RE.search(next_line)
                    and not _ANCHOR_DIRECTOR.search(next_line)):
                fio_m = _FIO_RE.search(next_line)
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
