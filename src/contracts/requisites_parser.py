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

from src.contracts.requisites_transforms import _OPF_MAP

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

# Полная ОПФ словами + кавычки: «Публичное акционерное общество «Вектор»».
# Маппинг полное→краткое переиспользуем из transforms (_OPF_MAP: краткое→полное).
# Сортировка по убыванию длины — чтобы «Акционерное общество» не перехватило
# хвост «Публичного/Закрытого акционерного общества».
_OPF_FULL_TO_SHORT = {full.lower(): short for short, full in _OPF_MAP.items()}
_NAME_FULL_OPF_RE = re.compile(
    r"("
    + "|".join(
        re.escape(full) for full in sorted(_OPF_FULL_TO_SHORT, key=len, reverse=True)
    )
    + r')\s*["«“]([^"»”]{1,120})["»”]',
    re.IGNORECASE,
)

# ИП + полное ФИО без кавычек: «ИП Петров Сергей Иванович». «ИП» —
# case-sensitive (иначе матчится внутри произвольного текста), полная форма
# ОПФ — без учёта регистра.
_NAME_IP_RE = re.compile(
    r"(?<![А-Яа-яёЁ])(?:ИП|(?i:Индивидуальный\s+предприниматель))\s+"
    r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)"
)

# Адрес: строка начинается с 6-значного индекса ИЛИ содержит «г.»/«ул.»/«пер.»
_ADDR_RE = re.compile(
    r"(?:\d{6}[,\s].{10,}|(?:^|\n)(?:г\.|ул\.|пер\.|пр\.|бульвар|проспект).{10,})",
    re.IGNORECASE | re.MULTILINE,
)

# Префиксы счетов (408 — счета ИП/физлиц: 40802, 40817 и т.п.)
_RS_PREFIXES = ("407", "405", "406", "408")
_KS_PREFIXES = ("301",)

# Якоря для реквизитов (для разрешения неоднозначных случаев).
# «р/?с(?:ч\w*)?» — покрывает «р/с», «р/сч», «р/счёт»: вариант «р/?сч?\b»
# не матчит «р/сч» (нет границы слова между «с» и «ч»).
_ANCHOR_BIK = re.compile(r"бик\b", re.IGNORECASE)
_ANCHOR_KPP = re.compile(r"кпп\b", re.IGNORECASE)
_ANCHOR_RS = re.compile(r"р/?с(?:ч\w*)?\b|расчётн|расчетн", re.IGNORECASE)
_ANCHOR_KS = re.compile(r"к/?с(?:ч\w*)?\b|корр?есп", re.IGNORECASE)

# Якоря для адресов
_ANCHOR_YUR = re.compile(r"юрид|юр\.", re.IGNORECASE)
_ANCHOR_POCT = re.compile(r"почт|факт", re.IGNORECASE)

# Границы-конца сегмента АДРЕСА: метка любого другого поля (по образцу
# _BANK_END). \b-гарды — чтобы «ул. Банковская» / «Телеграфная» не резали.
_ADDR_END = re.compile(
    r"(?<![А-Яа-яёЁ])(?:ИНН\b|КПП\b|ОГРН|БИК\b|ОКПО|ОКВЭД|[РрКк]/?сч?\b"
    r"|Расч[её]тн|Корр|Банк\b|Тел\b|Телефон|Факс|E-?mail|Эл\.\s*почт"
    r"|Директор|Руководител|в\s+лице|Основани|Контакт|Почтов|Юридич|Юр\.|Фактич)",
    re.IGNORECASE,
)

# Якоря для директора (консервативно — только «в лице», «директор», «руководитель»)
_ANCHOR_DIRECTOR = re.compile(
    r"(?:в\s+лице|директор\b|руководитель\b|управляющий\b|президент\b)",
    re.IGNORECASE,
)

# Лукбэк окна должности влево от якоря директора: вмещает самое длинное
# прилагательное («исполнительный » = 15 символов) с запасом. Тот же приём,
# что _PHONE_ANCHOR_WINDOW — не всю строку (слитная карточка = одна строка).
_POSITION_LOOKBEHIND = 25

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

# ФИО с инициалами: «Фамилия И.О.» — самый частый формат реальных карточек.
# Полное ФИО приоритетнее (по нему возможны РП/пол); инициалы — fallback.
_FIO_INITIALS_RE = re.compile(r"[А-ЯЁ][а-яё]+ [А-ЯЁ]\.\s?[А-ЯЁ]\.")

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

# Метка улицы прямо перед кандидатом «банк…» — это название улицы
# («ул. Банковская»), а не метка банка: такой матч отбраковываем.
_STREET_BEFORE_BANK = re.compile(
    r"(?<![А-Яа-яёЁ\-])(?:ул(?:ица|ицы)?|пер(?:еулок|еулка)?|просп(?:ект|екта)?"
    r"|пр-к?т|б-р|бульвар\w?|наб(?:ережн\w+)?|шоссе|ш|пл(?:ощад\w+)?"
    r"|проезд\w?|туп(?:ик\w?)?)\.?\s*$",
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
    _extract_name(scan_text, result)

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


def _extract_name(scan_text: str, result: dict[str, str]) -> None:
    """Краткое наименование: аббревиатура/полная ОПФ + кавычки, либо ИП + ФИО.

    Приоритет сверху вниз — первый сматчившийся вариант выигрывает.
    """
    m = _NAME_RE.search(scan_text)
    if m:
        opf = m.group(1).upper()
        name = m.group(2).strip()
        result["ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"] = f'{opf} "{name}"'
        return

    m = _NAME_FULL_OPF_RE.search(scan_text)
    if m:
        opf = _OPF_FULL_TO_SHORT[m.group(1).lower()]
        name = m.group(2).strip()
        result["ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"] = f'{opf} "{name}"'
        return

    m = _NAME_IP_RE.search(scan_text)
    if m:
        result["ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ"] = f"ИП {m.group(1).strip()}"


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
        for token in _DIGITS_ONLY.finditer(line):
            digits = token.group(0)
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
                _resolve_bik_kpp(digits, line, token.start(), result)
                continue

            # р/с vs к/с: оба 20 цифр
            if length == 20:
                _resolve_rs_ks(digits, line, result)
                continue


def _nearest_anchor_left(context: str, pos: int) -> str | None:
    """Ближайший к позиции pos якорь КПП/БИК слева: 'kpp' | 'bik' | None."""
    kpp_end = max((m.end() for m in _ANCHOR_KPP.finditer(context, 0, pos)), default=-1)
    bik_end = max((m.end() for m in _ANCHOR_BIK.finditer(context, 0, pos)), default=-1)
    if kpp_end == bik_end == -1:
        return None
    return "kpp" if kpp_end > bik_end else "bik"


def _resolve_bik_kpp(digits: str, context: str, pos: int, result: dict[str, str]) -> None:
    """9 цифр: определить БИК или КПП по префиксу и якорям.

    БИК РФ всегда начинается на 04. Но КПП регионов с кодом 04 (напр. налоговые
    органы) — тоже на 04. Поэтому:
    - не 04 → БИК физически невозможен → КПП (якорь БИК без КПП = противоречие → пусто);
    - 04 → формат подходит обоим → явный одиночный якорь КПП перебивает дефолт-БИК;
    - 04 + оба якоря на строке → привязка по ближайшему якорю СЛЕВА от токена
      (pos — позиция токена в context), иначе КПП региона 04 затирает БИК.
    """
    starts_04 = digits.startswith("04")
    has_bik = bool(_ANCHOR_BIK.search(context))
    has_kpp = bool(_ANCHOR_KPP.search(context))

    if starts_04:
        if has_kpp and not has_bik:
            result.setdefault("ЗАКАЗЧИК_КПП", digits)
        elif has_kpp and has_bik:
            nearest = _nearest_anchor_left(context, pos)
            if nearest == "kpp":
                result.setdefault("ЗАКАЗЧИК_КПП", digits)
            else:
                # ближайший слева БИК или якорей слева нет → БИК (дефолт для 04)
                result.setdefault("ЗАКАЗЧИК_БИК", digits)
        else:
            # якорь БИК или нет якоря → БИК (дефолт для 04)
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
    consumed: set[int] = set()  # строки-продолжения многострочного адреса

    for i, line in enumerate(lines):
        if i in consumed:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        # Строка выглядит как адрес?
        # Индекс — отдельностоящее 6-значное число, а НЕ подстрока длинного
        # реквизита (ИНН/ОГРН/счёт): иначе любая числовая строка станет адресом.
        index_m = re.search(r"(?<!\d)\d{6}(?!\d)", stripped)
        street_m = re.search(
            r"(?:г\.|ул\.|пер\.|пр-т|проспект|бульвар)\s", stripped, re.IGNORECASE
        )
        if not index_m and not street_m:
            continue
        # Значение — от начала адреса (индекс или уличный маркер, что раньше)
        # до метки следующего поля: иначе слитная карточка целиком уходит
        # в адрес (ИНН, счета, телефон — всё в одном поле договора).
        start = min(m.start() for m in (index_m, street_m) if m)
        value = stripped[start:]
        # Многострочный адрес (P1-5): для кандидата с индексом присоединяем
        # следующие строки, пока накопленное кончается запятой (улика
        # незавершённости). Стоп ДО поглощения на строке-метке другого поля —
        # так «Почтовый адрес: …» остаётся отдельным кандидатом.
        # _ADDR_END-сегментация (P0-3) применяется ПОСЛЕ склейки — последним
        # фильтром режет любой прилипший хвост.
        if index_m:
            j = i + 1
            while value.rstrip().endswith(",") and j < len(lines):
                nxt = lines[j].strip()
                if not nxt:
                    break
                end_at_start = _ADDR_END.search(nxt)
                if end_at_start and end_at_start.start() == 0:
                    break
                value += " " + nxt
                consumed.add(j)
                j += 1
        end_m = _ADDR_END.search(value)
        if end_m:
            value = value[:end_m.start()]
        value = value.strip(" ,;")
        if not value:
            continue
        if _ANCHOR_YUR.search(stripped):
            addr_candidates.append(("yur", value))
        elif _ANCHOR_POCT.search(stripped):
            addr_candidates.append(("poct", value))
        else:
            addr_candidates.append(("none", value))

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
        # Перед кандидатом стоит «ул./пер./проспект» — это улица
        # («ул. Банковская»), а не метка банка.
        if _STREET_BEFORE_BANK.search(text, max(0, m.start() - 24), m.start()):
            continue
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
        # в директора. Влево расширяем на _POSITION_LOOKBEHIND (не дальше
        # начала строки) — иначе прилагательное («Генеральный директор»)
        # остаётся за окном и должность обедняется до «Директор». Именно
        # ограниченный lookback, а не вся строка: в слитной карточке строка =
        # вся карточка, и поиск должности взял бы чужое слово-должность.
        line_start = text.rfind("\n", 0, anchor_match.start()) + 1
        window_start = max(line_start, anchor_match.start() - _POSITION_LOOKBEHIND)
        newline = text.find("\n", anchor_match.start())
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
        # Полное ФИО приоритетнее формата «Фамилия И.О.» (P1-2).
        fio_m = _FIO_RE.search(fio_region) or _FIO_INITIALS_RE.search(fio_region)
        if not fio_m:
            next_line = _next_content_line(text, window_start)
            if (next_line
                    and not _OTHER_ROLE_RE.search(next_line)
                    and not _ANCHOR_DIRECTOR.search(next_line)):
                fio_m = (_FIO_RE.search(next_line)
                         or _FIO_INITIALS_RE.search(next_line))
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
