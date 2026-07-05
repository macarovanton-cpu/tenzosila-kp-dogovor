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

# Слитный формат «ИНН/КПП 10цифр/9цифр»: первое → ИНН, второе → КПП.
# Подпись + формат 10/9 однозначны, берём по ДЛИНЕ (без контрольной суммы).
# Границы (?<!\d)…(?!\d) — ровно 10/9; иначе формат не совпал → не угадываем.
_INN_KPP_SLASH_RE = re.compile(
    r"ИНН\s*/\s*КПП\s*:?\s*(?<!\d)(\d{10})\s*/\s*(\d{9})(?!\d)", re.IGNORECASE
)

# Email
_EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}")

# Телефон: +7/8 и дальше цифры (с любыми разделителями, включая код города
# в скобках вида «+7 (473) ...» — пробел и скобка считаются отдельно).
# Цифровые границы (?<!\d)…(?!\d) — чтобы не матчить телефон внутри длинного
# числа (р/с, к/с), где «8…» — просто внутренняя цифра счёта.
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
)

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

# Маркеры «чужой» строки: ФИО оттуда НЕ принадлежит директору
# (главбух / контакт / телефон / e-mail / почта / факс).
_OTHER_ROLE_RE = re.compile(
    r"бухгалт|главбух|контакт|тел\b|телефон|e-?mail|почт|факс", re.IGNORECASE
)

# ФИО: три слова с заглавной буквы (фамилия имя отчество)
_FIO_RE = re.compile(r"[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+")


# ---------------------------------------------------------------------------
# Label-anchored слой: словарь якорей-меток и резка текста по ним
# ---------------------------------------------------------------------------

# Канонический ключ поля -> синонимы метки. Полный словарь участвует в
# СКАНИРОВАНИИ (даже поля, которые берём не из сегмента — ИНН/КПП/ОГРН/БИК/
# директор/тел/email), чтобы текстовые сегменты (банк, адреса, основание)
# корректно обрывались на СЛЕДУЮЩЕЙ метке.
_ANCHORS: dict[str, list[str]] = {
    "NAME_FULL": ["Полное фирменное наименование", "Полное наименование"],
    "NAME_SHORT": ["Сокращенное наименование", "Краткое наименование", "Сокр. наименование"],
    "INN": ["ИНН"],
    "KPP": ["КПП"],
    "OGRN": ["ОГРНИП", "ОГРН"],
    "OKPO": ["ОКПО"],
    "OKVED": ["ОКВЭД2", "ОКВЭД"],
    "ADDR_YUR": ["Юридический адрес", "Юр. адрес", "Юр.адрес", "Адрес регистрации"],
    "ADDR_POCT": ["Почтовый адрес", "Почт. адрес", "Факт. адрес", "Фактический адрес"],
    "RS": ["Расчетный счет", "Расчётный счёт", "Р/сч", "расч. счет", "Р/с", "р/с"],
    "BANK": ["Банк получателя", "Наименование банка", "Банк"],
    "BIK": ["БИК"],
    "KS": ["Корреспондентский счет", "Корр. счет", "Кор. счёт", "К/с"],
    "DIRECTOR": ["Генеральный директор", "Ген. директор", "Глава КФХ", "Директор", "Руководитель", "ИП"],
    "OSNOVANIE": ["Действует на основании", "на основании", "Основание"],
    "PHONE": ["Контактный телефон", "Телефон", "Тел.", "Т."],
    "EMAIL": ["E-mail", "Email", "Эл. почта", "Почта"],
}


def _build_anchor_scan_re() -> re.Pattern[str]:
    """Единая альтернация всех синонимов меток, длинные раньше коротких.

    Границы слов (`\\b`) с обеих сторон, регистронезависимо. Пробел внутри
    синонима трактуем как `\\s+` (после нормализации _NBSP это один пробел).
    Длинные раньше коротких — иначе короткий синоним обрубает длинный
    («Банк» до «Банк получателя»).
    """
    all_syn: list[str] = []
    for syns in _ANCHORS.values():
        all_syn.extend(syns)
    all_syn.sort(key=len, reverse=True)
    escaped = [re.escape(s).replace(r"\ ", r"\s+") for s in all_syn]
    pattern = r"\b(?:" + "|".join(escaped) + r")\b"
    return re.compile(pattern, re.IGNORECASE)


_ANCHOR_SCAN_RE = _build_anchor_scan_re()

# Обратная карта: нормализованный (lower, один пробел) синоним -> ключ.
_SYN_TO_KEY: dict[str, str] = {}
for _key, _syns in _ANCHORS.items():
    for _syn in _syns:
        _SYN_TO_KEY[re.sub(r"\s+", " ", _syn.lower())] = _key


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
    # 0. Label-anchored слой: резка текста по меткам-якорям.
    #    Действуем из сегментов на банк, адреса, основание, Р/с, К/с
    #    (приоритет метки). Остальное — существующими путями ниже.
    # ------------------------------------------------------------------
    segments = _segment_by_labels(text)
    _extract_bank(segments, result)
    _extract_addresses_from_segments(segments, result)
    _extract_osnovanie_from_segments(segments, result)
    _extract_rs_ks_from_segments(segments, result)

    # ------------------------------------------------------------------
    # 1. Email и телефон (однозначные паттерны, полный текст)
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
    # 3. Числовые токены: ИНН, ОГРН, БИК, КПП, р/с, к/с (полный текст).
    #    Слитный «ИНН/КПП …/…» разбираем ДО общей логики. Guard'ы
    #    not-in/setdefault не перетирают уже заполненное из сегментов.
    # ------------------------------------------------------------------
    _extract_inn_kpp_slash(text, result)
    _extract_numeric_fields(text, result)

    # ------------------------------------------------------------------
    # 4. Адреса (fallback для безметочных). Запуск по «остаточному»
    #    тексту: сегменты банка/основания/наименования забелены, чтобы
    #    город из строки банка («…, г. Екб») не утёк в адрес.
    # ------------------------------------------------------------------
    residual = _blank_ranges(
        text,
        [(s, e) for key, _, s, e in segments
         if key in ("BANK", "OSNOVANIE", "NAME_FULL", "NAME_SHORT")],
    )
    _extract_addresses(residual, result)

    # ------------------------------------------------------------------
    # 5. ФИО директора, должность (best-effort, консервативно; полный текст)
    # ------------------------------------------------------------------
    _extract_director_fields(text, result)

    return result


def _segment_by_labels(text: str) -> list[tuple[str, str, int, int]]:
    """Разрезать текст по меткам-якорям.

    Для каждой найденной метки значение = текст от конца метки до начала
    СЛЕДУЮЩЕЙ метки (любой) или до конца текста. Возвращает список
    (канонический_ключ, значение, start, end), где start/end — позиции
    очищенного значения в исходном тексте (для «забеливания»).
    """
    matches = list(_ANCHOR_SCAN_RE.finditer(text))
    segments: list[tuple[str, str, int, int]] = []
    for i, m in enumerate(matches):
        syn_norm = re.sub(r"\s+", " ", m.group(0).lower())
        key = _SYN_TO_KEY.get(syn_norm)
        if key is None:
            continue
        value_start = m.end()
        value_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw = text[value_start:value_end]
        # Срезать ведущие «:», пробелы, переносы
        lstripped = raw.lstrip(" :\n\t")
        lead = len(raw) - len(lstripped)
        cleaned = lstripped.rstrip()
        if not cleaned:
            continue
        real_start = value_start + lead
        real_end = real_start + len(cleaned)
        segments.append((key, cleaned, real_start, real_end))
    return segments


def _extract_bank(
    segments: list[tuple[str, str, int, int]], result: dict[str, str]
) -> None:
    """Название банка из первого сегмента BANK: чистка пунктуации, отсев чисел."""
    for key, value, _, _ in segments:
        if key != "BANK":
            continue
        cleaned = value.strip().rstrip(",.; ")
        if not cleaned or re.fullmatch(r"[\d\s\-]+", cleaned):
            continue  # пусто или похоже на число — не банк
        result.setdefault("ЗАКАЗЧИК_БАНК", cleaned)
        break


def _extract_osnovanie_from_segments(
    segments: list[tuple[str, str, int, int]], result: dict[str, str]
) -> None:
    """Основание из сегмента OSNOVANIE — БЕЗ предлога (контракт _buyer_context)."""
    for key, value, _, _ in segments:
        if key != "OSNOVANIE":
            continue
        cleaned = value.strip().rstrip(".,;")
        if cleaned:
            result.setdefault("ЗАКАЗЧИК_ОСНОВАНИЕ", cleaned)
        break


def _extract_addresses_from_segments(
    segments: list[tuple[str, str, int, int]], result: dict[str, str]
) -> None:
    """Юр./почт. адреса из сегментов меток (приоритет метки над fallback)."""
    for key, value, _, _ in segments:
        cleaned = value.strip().rstrip(".,;")
        if not cleaned:
            continue
        if key == "ADDR_YUR":
            result.setdefault("ЗАКАЗЧИК_АДРЕС_ЮР", cleaned)
        elif key == "ADDR_POCT":
            result.setdefault("ЗАКАЗЧИК_АДРЕС_ПОЧТ", cleaned)


def _extract_rs_ks_from_segments(
    segments: list[tuple[str, str, int, int]], result: dict[str, str]
) -> None:
    """Р/с и К/с по 20-значному числу внутри сегмента своей метки (приоритет метки)."""
    for key, value, _, _ in segments:
        if key not in ("RS", "KS"):
            continue
        m = re.search(r"(?<!\d)\d{20}(?!\d)", value)
        if not m:
            continue
        target = "ЗАКАЗЧИК_РС" if key == "RS" else "ЗАКАЗЧИК_КС"
        result.setdefault(target, m.group(0))


def _blank_ranges(text: str, ranges: list[tuple[int, int]]) -> str:
    """Заменить символы в диапазонах [start,end) на пробелы (перенос строки — сохранить)."""
    if not ranges:
        return text
    chars = list(text)
    for start, end in ranges:
        for i in range(start, min(end, len(chars))):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


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


def _extract_director_fields(text: str, result: dict[str, str]) -> None:
    """Извлечь ФИО директора, должность, основание — консервативно.

    ФИО директора: ТОЛЬКО при явном якоре «в лице» / «директор» / «руководитель»
    вплотную к ФИО. При нескольких кандидатах → пусто (правка №2).

    Основание извлекается в label-anchored слое (_extract_osnovanie_from_segments),
    здесь только ФИО/должность.
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

        # Ищем должность в окне
        pos_m = _POSITION_WORDS.search(window)
        if pos_m:
            director_positions.append(pos_m.group(1).strip())

        # Ищем ФИО на строке якоря; если нет — на следующей непустой строке,
        # но только если та не вводит новую должность/контакт (главбух и т.п.).
        fio_m = _FIO_RE.search(window)
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
