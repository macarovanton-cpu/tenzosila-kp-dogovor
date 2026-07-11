"""
requisites_transforms.py — производные поля реквизитов контрагента.

Чистые функции без Streamlit. Принимают исходные поля ЗАКАЗЧИК_*,
возвращают производные (полное наименование, инициалы, РП должности,
склонение ФИО). Результат редактируемый — менеджер правит промахи.
"""
from __future__ import annotations

import json
import logging
import re

from src.contracts.utils import infer_director_gender

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ОПФ: краткое → полное наименование
# ---------------------------------------------------------------------------

_OPF_MAP: dict[str, str] = {
    "ООО": "Общество с ограниченной ответственностью",
    "АО": "Акционерное общество",
    "ПАО": "Публичное акционерное общество",
    "ЗАО": "Закрытое акционерное общество",
    "ИП": "Индивидуальный предприниматель",
}

# Точный ведущий токен: ООО/АО/ПАО/ЗАО/ИП как отдельное слово в начале строки
_OPF_RE = re.compile(r'^(' + '|'.join(re.escape(k) for k in _OPF_MAP) + r')\b')


def full_name_from_short(short: str) -> str:
    """ООО "Ромашка" → Общество с ограниченной ответственностью "Ромашка".

    Разворачивает ТОЛЬКО ведущий токен ОПФ (не матчит подстрокой).
    Незнакомый/отсутствующий префикс → "".
    """
    s = short.strip()
    m = _OPF_RE.match(s)
    if not m:
        return ""
    opf = m.group(1)
    rest = s[m.end():].strip()
    full_opf = _OPF_MAP[opf]
    return f"{full_opf} {rest}".strip() if rest else full_opf


# ---------------------------------------------------------------------------
# Инициалы директора
# ---------------------------------------------------------------------------

# ФИО в формате «Фамилия И.О.» (в т.ч. с пробелом между инициалами): по нему
# невозможны РП-склонение и определение пола — derive деградирует мягко.
_FIO_SURNAME_INITIALS_RE = re.compile(
    r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ]\.\s?[А-ЯЁ]\."
)


def director_initials(fio: str) -> str:
    """Фамилия Имя Отчество → И.О. Фамилия.

    При ФИО из двух слов (нет отчества) → И. Фамилия.
    При формате «Фамилия И.О.» → И.О. Фамилия (перестановка).
    При одном слове → "".
    """
    parts = fio.strip().split()
    if len(parts) < 2:
        return ""
    last = parts[0]
    # «Иванов И.И.» — инициалы уже готовы, только переставить
    if len(parts) == 2 and re.fullmatch(r"[А-ЯЁ]\.[А-ЯЁ]\.", parts[1]):
        return f"{parts[1]} {last}"
    first_init = parts[1][0].upper() + "." if parts[1] else ""
    mid_init = parts[2][0].upper() + "." if len(parts) >= 3 and parts[2] else ""
    initials = (first_init + mid_init) if mid_init else first_init
    return f"{initials} {last}"


# ---------------------------------------------------------------------------
# Должность в родительном падеже
# ---------------------------------------------------------------------------

_POSITION_GENITIVE: dict[str, str] = {
    "директор": "директора",
    "генеральный директор": "генерального директора",
    "исполнительный директор": "исполнительного директора",
    "финансовый директор": "финансового директора",
    "технический директор": "технического директора",
    "коммерческий директор": "коммерческого директора",
    "управляющий директор": "управляющего директора",
    "президент": "президента",
    "председатель": "председателя",
    "председатель правления": "председателя правления",
    "генеральный менеджер": "генерального менеджера",
    "управляющий": "управляющего",
    "индивидуальный предприниматель": "индивидуального предпринимателя",
}


def position_genitive(position: str) -> str:
    """Должность → родительный падеж (по словарю).

    Незнакомая должность → "" (не перетираем РП-поле мусором).
    """
    key = position.strip().lower()
    return _POSITION_GENITIVE.get(key, "")


# ---------------------------------------------------------------------------
# Petrovich: склонение ФИО
# ---------------------------------------------------------------------------

_petrovich_instance = None

# Орфография РЯ: после велярных г/к/х пишется «и», не «ы». petrovich 2.0.1
# этого правила не знает и для ж. имён с основой на г/к/х перед финальным -а
# отдаёт неверный род. падеж (Ольга→Ольгы вместо Ольги). Правим ТОЧЕЧНО
# результат склонения ИМЕНИ (firstname), а не всю ФИО-строку: в фамилии «-ы»
# после к/г может быть легитимным.
_VELAR_GENITIVE_RE = re.compile(r"([гкхГКХ])ы$")


def _fix_velar_genitive(name: str) -> str:
    """Финальное «-ы» после велярной г/к/х → «-и» (Ольгы→Ольги)."""
    return _VELAR_GENITIVE_RE.sub(r"\1и", name)


def _get_petrovich():
    """Ленивая инициализация с фиксом кодировки (petrovich 2.0.1 / Windows)."""
    global _petrovich_instance
    if _petrovich_instance is not None:
        return _petrovich_instance
    from petrovich.main import Petrovich, DEFAULT_RULES_PATH  # noqa: PLC0415
    from petrovich.enums import Case, Gender  # noqa: PLC0415, F401
    p = Petrovich.__new__(Petrovich)
    p.separators = ("-", " ")
    # Явно указываем UTF-8: стандартный __init__ открывает без encoding
    with open(DEFAULT_RULES_PATH, encoding="utf-8") as f:
        p.data = json.load(f)
    _petrovich_instance = p
    return p


def decline_fio(fio: str, gender: str) -> tuple[str, bool]:
    """Склонить ФИО в родительный падеж через petrovich.

    Возвращает (фио_рп, uncertain):
    - uncertain=True, если хотя бы один компонент не изменился (не склонился)
      или произошла любая ошибка.
    - Fallback при ошибке — исходное ФИО, uncertain=True.

    gender: 'male' | 'female'.
    """
    from petrovich.enums import Case  # noqa: PLC0415

    fio = fio.strip()
    if not fio:
        return ("", False)

    parts = fio.split()
    if len(parts) < 2:
        # Одно слово — нет составных частей для уверенного склонения
        return (fio, True)

    g_str = gender if gender in ("male", "female") else "male"
    last_orig = parts[0]
    first_orig = parts[1]
    mid_orig = parts[2] if len(parts) >= 3 else ""

    try:
        p = _get_petrovich()
        last_decl = p.lastname(last_orig, Case.GENITIVE, g_str)
        # Пост-коррекция велярных прицельно к компоненту ИМЕНИ.
        first_decl = _fix_velar_genitive(
            p.firstname(first_orig, Case.GENITIVE, g_str)
        )
        mid_decl = (
            p.middlename(mid_orig, Case.GENITIVE, g_str)
            if mid_orig else ""
        )
    except Exception as exc:
        _logger.warning("decline_fio: petrovich error for %r: %s", fio, exc)
        return (fio, True)

    # Детектируем несработавшее склонение: хотя бы один значимый компонент
    # вернулся без изменений (petrovich молча возвращает исходное на незнакомых)
    unchanged = (
        last_decl == last_orig
        or first_decl == first_orig
        or (mid_orig and mid_decl == mid_orig)
    )
    if unchanged:
        _logger.warning(
            "decline_fio: неуверенное склонение для %r (компонент не изменён)",
            fio,
        )

    result_parts = [last_decl, first_decl]
    if mid_decl:
        result_parts.append(mid_decl)
    return (" ".join(result_parts), unchanged)


# ---------------------------------------------------------------------------
# Публичная точка входа
# ---------------------------------------------------------------------------

def fill_missing_derived(fields: dict[str, str]) -> list[str]:
    """Вписать производные поля in-place ТОЛЬКО в пустые (извлечённое из
    документа не перетираем). Возвращает warnings для менеджера.

    Используется в режиме B после LLM-извлечения: промт больше не заполняет
    падежи/инициалы (A4), их считает код."""
    derived, warnings = derive_requisites(fields)
    for key, value in derived.items():
        if not fields.get(key):
            fields[key] = value
    return warnings


def derive_requisites(
    fields: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Вычислить производные поля из исходных ЗАКАЗЧИК_*.

    Возвращает (derived, warnings):
    - derived — только непустые производные (не перетираем то, что уже есть);
    - warnings — сообщения для менеджера (неуверенное склонение и т.п.).
    """
    derived: dict[str, str] = {}
    warnings: list[str] = []

    # 1. Полное наименование из краткого
    short = fields.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ", "").strip()
    if short:
        full = full_name_from_short(short)
        if full:
            derived["ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ"] = full

    # 2. Пол директора по отчеству (используем существующую функцию).
    # По «Фамилия И.О.» отчества нет: пол не выводим (молчаливый male для
    # женщины сломал бы «действующего/действующей» в преамбуле).
    fio = fields.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "").strip()
    fio_is_initials = bool(_FIO_SURNAME_INITIALS_RE.fullmatch(fio))
    gender = fields.get("ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", "").strip()
    if fio and not gender and not fio_is_initials:
        gender = infer_director_gender(fio)
    if gender:
        derived["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] = gender

    # 3. Инициалы
    if fio:
        initials = director_initials(fio)
        if initials:
            derived["ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ"] = initials

    # 4. Должность в РП
    position = fields.get("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ", "").strip()
    if position:
        pos_rp = position_genitive(position)
        if pos_rp:
            derived["ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП"] = pos_rp

    # 5. ФИО в РП через petrovich. По инициалам склонение невозможно —
    # мягкая деградация: именительный в поле (видимый текст в преамбуле,
    # а не дыра) + явный warning вместо неуверенного вызова petrovich.
    if fio and fio_is_initials:
        derived["ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП"] = fio
        warnings.append(
            "ФИО руководителя распознано в формате «Фамилия И.О.» — "
            "родительный падеж не построен (оставлен именительный). "
            "Впишите полное ФИО и распознайте повторно."
        )
    elif fio:
        effective_gender = gender or "male"
        fio_rp, uncertain = decline_fio(fio, effective_gender)
        if fio_rp:
            derived["ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП"] = fio_rp
        if uncertain:
            warnings.append(
                "Проверьте склонение ФИО руководителя в родительном падеже "
                f"(поле «ФИО (род. падеж)»): автоматическое склонение неуверенно "
                f"для «{fio}»."
            )

    return derived, warnings
