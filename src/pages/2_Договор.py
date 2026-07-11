"""Страница генерации договора и спецификации."""
from __future__ import annotations

import re
import sys
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.contracts.clauses_renderer import build_contract_clauses  # noqa: E402
from src.contracts.clauses_context import build_clauses_context, winter_surcharge_allowed  # noqa: E402
from src.contracts.compose import compose_spec_with_attachments, compose_supply  # noqa: E402
from src.contracts.extractor import extract_kp_data_legacy  # noqa: E402
from src.contracts.filler import (  # noqa: E402
    fill_spec_with_items,
    fill_template,
    get_unfilled_placeholders,
)
from src.contracts.fundament_lookup import (  # noqa: E402
    BuildTaskResolution,
    list_build_task_files,
    pretty_name,
    resolve_build_task,
    resolve_control_sheet,
)
from src.contracts.kp_load import build_kp_payload  # noqa: E402
from src.contracts.payment_line import format_payment_line, orion_poles_without_foundation  # noqa: E402
from src.contracts.recommendations import ORION_POLES_WITHOUT_FOUNDATION_TEXT  # noqa: E402
from src.contracts.spec_items import make_custom_item, recalculate_totals  # noqa: E402
from src.contracts.spec_v2_filler import fill_spec_v2  # noqa: E402
from src.contracts.supply_filler import build_supply_context, decide_contract_type  # noqa: E402
from src.contracts.state import (  # noqa: E402
    clear_generated,
    collect_for_template,
    get_model_qty,
    get_payment_lines,
    get_spec_items,
    init_contract_state,
    is_extracted,
    merge_requisites,
    set_extracted_data,
    set_requisites,
    set_spec_items,
    set_specification,
    sync_field,
    sync_manual_field,
)
from src.contracts.requisites_extract import (  # noqa: E402
    NoTextLayerError,
    extract_text,
)
from src.contracts.requisites_parser import parse_requisites  # noqa: E402
from src.contracts.requisites_transforms import derive_requisites  # noqa: E402
from src.contracts.requisites_validation import validate_requisites  # noqa: E402
from src.contracts.utils import format_date_parts, infer_director_gender  # noqa: E402
from src.data_loader import load_models, load_payment_terms, load_prices  # noqa: E402
from src.storage.supabase_client import (  # noqa: E402
    StorageError,
    get_kp_by_number,
    list_recent_kps,
)
from src.ui.payment_lines_editor import render_payment_lines_editor  # noqa: E402
from src.utils.format import sanitize_filename  # noqa: E402

CONTRACT_TEMPLATE = Path("templates/contracts/contract.docx")
SPEC_TEMPLATE = Path("templates/contracts/spec_foundation_install.docx")
SPEC_V2_TEMPLATE = Path("templates/contracts/spec_v2.docx")
OUTPUT_DIR = Path("output/contracts")

st.set_page_config(page_title="Договор", page_icon="📄", layout="wide")
init_contract_state()

# ---------------------------------------------------------------------------
# Определения полей
# ---------------------------------------------------------------------------

REQUISITE_FIELDS: list[tuple[str, str]] = [
    ("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ", "Краткое наименование"),
    ("ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ", "Полное наименование"),
    ("ЗАКАЗЧИК_АДРЕС_ЮР", "Юридический адрес"),
    ("ЗАКАЗЧИК_АДРЕС_ПОЧТ", "Почтовый адрес"),
    ("ЗАКАЗЧИК_ИНН", "ИНН"),
    ("ЗАКАЗЧИК_КПП", "КПП"),
    ("ЗАКАЗЧИК_ОГРН", "ОГРН"),
    ("ЗАКАЗЧИК_ОСНОВАНИЕ", "Основание"),
    ("ЗАКАЗЧИК_БАНК", "Банк"),
    ("ЗАКАЗЧИК_БИК", "БИК"),
    ("ЗАКАЗЧИК_РС", "Расчётный счёт"),
    ("ЗАКАЗЧИК_КС", "Корреспондентский счёт"),
    ("ЗАКАЗЧИК_ТЕЛЕФОН", "Телефон"),
    ("ЗАКАЗЧИК_EMAIL", "Email"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ", "Должность руководителя"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "ФИО руководителя"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП", "Должность (род. падеж)"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП", "ФИО (род. падеж)"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ", "Инициалы"),
]

SPEC_FIELDS: list[tuple[str, str]] = [
    ("СПЕЦ_НДС", "Ставка НДС"),
    ("СПЕЦ_МОДЕЛЬ_КРАТКОЕ", "Модель (кратко)"),
    ("СПЕЦ_МАКС_НАГРУЗКА", "Макс. нагрузка"),
    ("СПЕЦ_П1_НАИМЕНОВАНИЕ", "П1 — Наименование"),
    ("СПЕЦ_П1_СУММА", "П1 — Сумма"),
    ("СПЕЦ_П1_СРОК", "П1 — Срок"),
    ("СПЕЦ_П2_НАИМЕНОВАНИЕ", "П2 — Наименование"),
    ("СПЕЦ_П2_СУММА", "П2 — Сумма"),
    ("СПЕЦ_П2_СРОК", "П2 — Срок"),
    ("СПЕЦ_П3_НАИМЕНОВАНИЕ", "П3 — Наименование"),
    ("СПЕЦ_П3_СУММА", "П3 — Сумма"),
    ("СПЕЦ_П3_СРОК", "П3 — Срок"),
    ("СПЕЦ_П4_НАИМЕНОВАНИЕ", "П4 — Наименование"),
    ("СПЕЦ_П4_СУММА", "П4 — Сумма"),
    ("СПЕЦ_П4_СРОК", "П4 — Срок"),
    ("СПЕЦ_П5_НАИМЕНОВАНИЕ", "П5 — Наименование"),
    ("СПЕЦ_П5_СУММА", "П5 — Сумма"),
    ("СПЕЦ_П5_СРОК", "П5 — Срок"),
    ("СПЕЦ_ИТОГО", "Итого"),
    ("СПЕЦ_ИТОГО_ПРОПИСЬ", "Итого прописью"),
    ("СПЕЦ_ОПЛАТА_П1", "Условие оплаты 1"),
    ("СПЕЦ_ОПЛАТА_П2", "Условие оплаты 2"),
    ("СПЕЦ_ОПЛАТА_П3", "Условие оплаты 3"),
    ("СПЕЦ_ОПЛАТА_П4", "Условие оплаты 4"),
    ("СПЕЦ_ОПЛАТА_П5", "Условие оплаты 5"),
    ("СПЕЦ_ОПЛАТА_П6", "Условие оплаты 6"),
    ("СПЕЦ_СРОК_ПОСТАВКИ", "Срок поставки"),
    ("СПЕЦ_СРОК_ФУНДАМЕНТ", "Срок фундамент"),
    ("СПЕЦ_СРОК_МОНТАЖ", "Срок монтаж"),
]

WIDE_FIELDS: set[str] = {
    "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ",
    "ЗАКАЗЧИК_АДРЕС_ЮР",
    "ЗАКАЗЧИК_АДРЕС_ПОЧТ",
    "СПЕЦ_ИТОГО_ПРОПИСЬ",
    "СПЕЦ_ОПЛАТА_П1",
    "СПЕЦ_ОПЛАТА_П2",
    "СПЕЦ_ОПЛАТА_П3",
    "СПЕЦ_ОПЛАТА_П4",
    "СПЕЦ_ОПЛАТА_П5",
    "СПЕЦ_ОПЛАТА_П6",
}

_SECTION_LABELS: dict[str, str] = {
    "obligations_supplier": "Обязательства Подрядчика",
    "obligations_customer": "Обязательства Заказчика",
    "special_conditions": "Особые условия",
    "final": "Заключительные положения",
}

# Читаемые метки scope для caption в режиме авто-определения из позиций
_FOUND_LABELS: dict[str, str] = {
    "contractor_full": "Подрядчик строит фундамент",
    "contractor_with_materials": "Подрядчик строит (материалы Заказчика)",
    "contractor_supervised": "Курирование строительства Подрядчиком",
    "rama": "Основание под раму",
    "customer_builds": "Заказчик строит фундамент",
    "existing_foundation": "Готовый фундамент Заказчика",
    "none": "Нет обязательств по фундаменту",
}

# Видимый выбор менеджера — только в случае 4 (нет позиции фундамента + есть монтаж)
_FOUND_MANUAL_OPTS = ["Заказчик строит фундамент", "Готовый фундамент Заказчика"]
_FOUND_MANUAL_MAP: dict[str, str | None] = {
    "Заказчик строит фундамент": None,          # дефолт customer_builds из else-ветки
    "Готовый фундамент Заказчика": "existing_foundation",
}
_FOUND_MANUAL_RMAP = {v: k for k, v in _FOUND_MANUAL_MAP.items()}

_INST_OPTS = ["Авто (из позиций)", "Полный монтаж", "Шеф-монтаж", "Без монтажа"]
_INST_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Полный монтаж": "full",
    "Шеф-монтаж": "shefmontazh", "Без монтажа": "none",
}
_INST_RMAP = {v: k for k, v in _INST_MAP.items()}

_VERIF_OPTS = ["Авто (из позиций)", "Подрядчик", "Заказчик", "Без поверки"]
_VERIF_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Подрядчик": "supplier",
    "Заказчик": "customer", "Без поверки": "none",
}
_VERIF_RMAP = {v: k for k, v in _VERIF_MAP.items()}

_ORION_OPTS = ["Авто (из позиций)", "Заказчик", "Подрядчик"]
_ORION_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Заказчик": "by_customer", "Подрядчик": "by_contractor",
}
_ORION_RMAP = {v: k for k, v in _ORION_MAP.items()}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BUCKET_OPTIONS = ["Оборудование", "Фундамент", "Монтаж и поверка"]

_PG_TO_BUCKET: dict[str | None, str] = {
    "scales": "Оборудование",
    "delivery": "Оборудование",
    None: "Оборудование",
    "foundation": "Фундамент",
    "installation_and_verification": "Монтаж и поверка",
}


def _bucket_to_pg(bucket: str, name: str) -> str:
    """UI-бакет → внутренний payment_group. Доставка определяется по имени."""
    if bucket == "Фундамент":
        return "foundation"
    if bucket == "Монтаж и поверка":
        return "installation_and_verification"
    if name.lower().startswith("доставка"):
        return "delivery"
    return "scales"


# Эвристика для warning'а (P1-5, docs/AUDIT_2026-07.md) — НЕ участвует в
# классификации payment_group. Ловит позиции, чьё имя похоже на монтаж/
# фундамент/поверку, но не подошло под анкореные паттерны в from_kp.py
# (_NAME_INSTALL_RE, _NAME_FOUNDATION_RE), поэтому осело в scales/delivery.
# Список слов откалиброван на 78 позициях из 17 реальных КП (Supabase):
# «бетон»/«плит»/«строительн»/«свая» либо ловили только шум (уже верно
# классифицированные пресеты), либо не встретились ни разу — убраны.
_SUSPECT_WORK_RE = re.compile(
    r"монтаж|поверк|пусконаладк|фундамент",
    re.IGNORECASE,
)


def _suspect_names(items: list[dict]) -> list[str]:
    """Имена позиций, похожих на монтаж/фундамент, но не так классифицированных."""
    return [
        it["name"] for it in items
        if it.get("payment_group") not in (
            "installation_and_verification", "foundation",
        )
        and _SUSPECT_WORK_RE.search(it.get("name", ""))
    ]


def _items_to_rows(items: list[dict]) -> list[dict]:
    """Конвертировать SpecItem list в строки для data_editor."""
    return [
        {
            "Наименование": item.get("name", ""),
            "Бакет": _PG_TO_BUCKET.get(item.get("payment_group"), "equipment"),
            "Ед.": item.get("unit", "шт"),
            "Кол-во": item.get("quantity", 1.0),
            "Цена с НДС, руб.": item.get("price_per_unit", 0.0),
            "Сумма с НДС, руб.": item.get("total", 0.0),
        }
        for item in items
    ]


def _rows_to_items(rows, original_items: list[dict]) -> list[dict]:
    """Конвертировать строки data_editor обратно в SpecItem list."""
    import uuid as _uuid
    result = []
    rows_list = rows.to_dict("records") if hasattr(rows, "to_dict") else list(rows)
    for i, row in enumerate(rows_list):
        if i < len(original_items):
            item = dict(original_items[i])
        else:
            item = {
                "id": f"custom_{_uuid.uuid4().hex[:8]}",
                "payment_group": None,
                "is_custom": True,
                "source": "custom",
                "metadata": {},
            }
        qty = float(row.get("Кол-во") or 1)
        price = float(row.get("Цена с НДС, руб.") or 0)
        name = str(row.get("Наименование") or "")
        bucket = str(row.get("Бакет") or "Оборудование")
        item["name"] = name
        item["unit"] = str(row.get("Ед.") or "шт")
        item["quantity"] = qty
        item["price_per_unit"] = price
        item["total"] = qty * price
        item["payment_group"] = _bucket_to_pg(bucket, name)
        result.append(item)
    return result


def _save_uploaded(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return tmp.name


@st.cache_data(show_spinner=False)
def _load_kp_full(kp_number: str, updated_at: str | None = None) -> dict | None:
    """Полный снапшот КП по номеру, кэшированный по (kp_number, updated_at).

    Дропдаун «Последние КП» отдаёт строку без `data` (list_recent_kps не тянет
    JSONB), поэтому снапшот дозагружаем отдельно. Кэш убирает повтор сетевого
    запроса на каждый rerun, пока КП выбран. updated_at в теле не используется —
    только как часть кэш-ключа: пересохранение КП под тем же номером обновляет
    updated_at → cache bust, иначе страница молча отдаёт старую версию снапшота.
    """
    return get_kp_by_number(kp_number)


def _render_field_group(
    title: str, fields: list[tuple[str, str]], section: str,
    derived_keys: frozenset[str] = frozenset(),
) -> None:
    st.subheader(title)
    ns = st.session_state["contract"][section]
    for i in range(0, len(fields), 2):
        cols = st.columns(2)
        for col, (key, label) in zip(cols, fields[i:i + 2]):
            wkey = f"w_{key}"
            st.session_state.setdefault(wkey, ns.get(key, ""))
            _args = (section, key, key not in derived_keys)
            with col:
                if key in WIDE_FIELDS:
                    st.text_area(
                        label, key=wkey, height=68,
                        on_change=sync_field, args=_args,
                    )
                else:
                    st.text_input(
                        label, key=wkey,
                        on_change=sync_field, args=_args,
                    )


def _build_task_auto_text(result: BuildTaskResolution) -> str:
    if result.path is None:
        return f"не подобрано: {result.reason}"
    return pretty_name(result.path)


def _build_task_choice_index(options: list[str | Path], attachments: dict) -> int:
    source = attachments.get("build_task_source", "auto")
    if source == "none":
        return options.index("Без приложения")
    if source == "manual":
        selected_path = Path(str(attachments.get("build_task_path") or ""))
        for index, option in enumerate(options):
            if isinstance(option, Path) and option == selected_path:
                return index
    return options.index("Авто-подбор")


def _build_task_option_label(option: str | Path) -> str:
    if isinstance(option, Path):
        return pretty_name(option)
    return option


def _render_fundament_attachment_choice() -> None:
    """Показать и сохранить выбор фундаментных приложений без склейки DOCX."""
    cs = st.session_state["contract"]
    attachments = cs.setdefault("attachments", {})
    snapshot = cs.get("kp_snapshot") or {}
    auto_result = resolve_build_task(snapshot)

    st.subheader("Приложения по фундаменту")
    auto_text = _build_task_auto_text(auto_result)
    if auto_result.path is not None:
        st.success(f"Строительное задание: {auto_text}")
    elif "не найден" in auto_result.reason:
        st.error(f"Строительное задание: {auto_text}")
    else:
        st.info(f"Строительное задание: {auto_text}")

    build_task_files = list_build_task_files()
    options: list[str | Path] = ["Авто-подбор", "Без приложения", *build_task_files]
    widget_key = "w_build_task_choice"
    if widget_key not in st.session_state or st.session_state[widget_key] not in options:
        st.session_state[widget_key] = options[_build_task_choice_index(options, attachments)]

    selected = st.selectbox(
        "Выбор строительного задания",
        options,
        key=widget_key,
        format_func=_build_task_option_label,
        help="Override для нестандартных случаев. Склейка приложений будет добавлена на шаге 9.",
    )
    if selected == "Авто-подбор":
        selected_build_task = auto_result.path
        attachments["build_task_source"] = "auto"
    elif selected == "Без приложения":
        selected_build_task = None
        attachments["build_task_source"] = "none"
    else:
        selected_build_task = selected
        attachments["build_task_source"] = "manual"
    attachments["build_task_path"] = str(selected_build_task or "")

    if selected_build_task:
        st.caption(f"Итоговый выбор: {pretty_name(selected_build_task)}")
    else:
        st.caption("Итоговый выбор: без строительного задания.")

    control_sheet = resolve_control_sheet(auto_result.execution, auto_result.sections)
    if control_sheet is None:
        st.session_state["w_include_control_sheet"] = False
        attachments["include_control_sheet"] = False
        attachments["control_sheet_path"] = ""
        st.caption("Контрольный лист недоступен для текущего типа фундамента и секций.")
        return

    st.session_state.setdefault(
        "w_include_control_sheet",
        bool(attachments.get("include_control_sheet", False)),
    )
    include_control_sheet = st.checkbox(
        "Добавить контрольный лист (Приложение №2)",
        key="w_include_control_sheet",
    )
    attachments["include_control_sheet"] = bool(include_control_sheet)
    attachments["control_sheet_path"] = str(control_sheet) if include_control_sheet else ""
    if include_control_sheet:
        st.caption(f"Контрольный лист: {pretty_name(control_sheet)}")


# ---------------------------------------------------------------------------
# Секция 0 — Режим источника данных
# ---------------------------------------------------------------------------

st.title("Генерация договора")

mode = st.radio(
    "Источник данных коммерческого предложения",
    options=["Из базы (по номеру)", "Из PDF файла (старый КП)"],
    captions=[
        "Основной путь — для КП, сгенерированных в этом инструменте",
        "Резервный — для старых КП до Supabase",
    ],
    horizontal=True,
    key="contract_mode",
)

st.divider()

# ---------------------------------------------------------------------------
# Секция 1 — Загрузка данных (разветвление по режиму)
# ---------------------------------------------------------------------------

if mode == "Из базы (по номеру)":
    # ---- Mode A: КП из Supabase + карточка ----
    st.subheader("Выбор КП из базы")

    try:
        recent = list_recent_kps(limit=50)
    except StorageError as e:
        st.error(f"Ошибка загрузки списка КП: {e}")
        recent = []

    kp_options_labels = ["— выбрать —"]
    kp_options_map: dict[str, dict] = {}
    for r in recent:
        price_str = f"{r.get('total_price', 0):,}".replace(",", " ")
        label = f"{r['kp_number']} — {r['client_name']} — {r.get('model_id', '')} — {price_str} ₽"
        kp_options_labels.append(label)
        kp_options_map[label] = r

    selected_label = st.selectbox(
        "Последние КП", kp_options_labels, key="kp_select"
    )

    st.caption("Или введите номер вручную:")
    manual_col1, manual_col2 = st.columns([3, 1])
    with manual_col1:
        manual_kp_num = st.text_input(
            "Номер КП", placeholder="КП-2026-001", label_visibility="collapsed",
            key="kp_number_input",
        )
    with manual_col2:
        # При активном выборе в дропдауне ручной поиск недостижим (elif ниже) —
        # блокируем кнопку, иначе клик молча перезагружает КП из дропдауна.
        _dropdown_active = selected_label != "— выбрать —"
        search_clicked = st.button(
            "Найти", key="kp_search_btn",
            disabled=_dropdown_active,
            help="Сначала верните дропдаун в «— выбрать —»" if _dropdown_active else None,
        )

    kp_row = None
    if selected_label != "— выбрать —":
        # list_recent_kps не возвращает `data` — дозагружаем полный снапшот.
        _summary = kp_options_map.get(selected_label)
        if _summary:
            try:
                kp_row = _load_kp_full(_summary["kp_number"], _summary.get("updated_at"))
            except StorageError as e:
                st.error(f"Ошибка загрузки КП: {e}")
    elif search_clicked and manual_kp_num:
        try:
            kp_row = _load_kp_full(manual_kp_num.strip())
            if kp_row is None:
                st.warning(f"КП «{manual_kp_num}» не найден в базе.")
        except StorageError as e:
            st.error(f"Ошибка поиска: {e}")

    if kp_row is not None:
        try:
            prices = load_prices()
            models_json = load_models()
            payment_terms = load_payment_terms()
            payload = build_kp_payload(kp_row, prices, models_json, payment_terms)
        except Exception as exc:
            st.error(
                f"Ошибка загрузки КП «{kp_row.get('kp_number', '')}»: {exc}. "
                "Данные на странице — от предыдущего КП."
            )
        else:
            # Коммит state только целиком: частичное обновление оставляет на
            # странице микс позиций/оплаты двух КП (см. STATUS, баг смены КП).
            # Смена КП меняет подпись авто-типа → радио пере-seed'ится честно.
            st.session_state["contract"]["current_kp_number"] = kp_row.get("kp_number")
            set_specification(payload["spec"])
            set_spec_items(payload["items"])
            st.session_state["contract"]["kp_snapshot"] = payload["snapshot"]
            st.session_state["contract"]["kp_payment_snapshot"] = payload["payment"]
            st.success(f"КП «{kp_row.get('kp_number', '')}» загружен из базы.")

else:
    # ---- Mode B: Legacy AI парсинг PDF КП + карточки ----
    st.info(
        "Используется AI-парсинг PDF КП. Возможны неточности — "
        "проверьте форму внимательно."
    )
    st.subheader("Загрузка документов")
    up_col1, up_col2 = st.columns(2)
    with up_col1:
        kp_file = st.file_uploader(
            "PDF коммерческого предложения", type=["pdf"], key="upload_kp"
        )
    with up_col2:
        card_file_b = st.file_uploader(
            "Карточка контрагента", type=["pdf", "docx"], key="upload_card"
        )

    extract_disabled = not (kp_file and card_file_b)
    if st.button("Извлечь данные через AI", disabled=extract_disabled):
        with st.spinner("AI извлекает данные..."):
            try:
                kp_path = _save_uploaded(kp_file)
                card_path = _save_uploaded(card_file_b)
                raw = extract_kp_data_legacy(kp_path, card_path)
                set_extracted_data(raw)
                st.success("Данные извлечены")
            except Exception as exc:
                st.error(f"Ошибка извлечения: {exc}")

st.divider()

# ---------------------------------------------------------------------------
# Секция 2 — Реквизиты заказчика (всегда видима, не зависит от is_extracted)
# ---------------------------------------------------------------------------

edited_df = None  # Будет установлен в блоке data_editor если items существуют

# Производное → его первичное поле: производное перезаписывает непустое
# текущее значение только при ИЗМЕНЕНИИ первичного в этом распознавании —
# иначе щадим ручную правку (напр. исправленное склонение ФИО_РП).
_DERIVED_PRIMARY = {
    "ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ": "ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ",
    "ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ": "ЗАКАЗЧИК_ДИРЕКТОР_ФИО",
    "ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП": "ЗАКАЗЧИК_ДИРЕКТОР_ФИО",
    "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП": "ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ",
}


def _apply_requisites_text(text: str) -> None:
    """Единый путь: parse → merge первичных (защита ручного ввода, P1-8) →
    derive от актуальных значений → merge производных."""
    _cs = st.session_state["contract"]
    _cur = dict(_cs["requisites"])  # снимок ДО мерджа — для "родитель изменился?"
    _parsed = parse_requisites(text)
    merge_requisites(_parsed)  # сам пропускает ключи из requisites_manual
    _actual = _cs["requisites"]  # состояние ПОСЛЕ мерджа первичных
    _derived, _warns = derive_requisites(_actual)
    for _dkey, _pkey in _DERIVED_PRIMARY.items():
        _primary_unchanged = _actual.get(_pkey, "") == _cur.get(_pkey, "")
        if _dkey in _derived and _cur.get(_dkey) and _primary_unchanged:
            _derived.pop(_dkey)
    merge_requisites(_derived)
    if "ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ" not in _cs.get("requisites_manual", set()):
        # Сброс пола → пере-inference из нового ФИО на рендере ниже.
        # Пропускаем, если пол выбран вручную (P1-8) — ручной выбор не затираем.
        st.session_state["contract"]["requisites"]["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] = ""
        st.session_state.pop("w_ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", None)
    for _w in _warns:
        st.warning(_w)
    if _parsed:
        st.success(f"Распознано полей: {len(_parsed)}. Проверьте и дополните.")
    else:
        st.info("Не удалось распознать реквизиты. Введите поля вручную.")
    # Разбор проблем распознавания: errors блокируют генерацию ниже
    _req_errors, _req_warns = validate_requisites(
        st.session_state["contract"]["requisites"]
    )
    for _e in _req_errors:
        st.error(_e)
    for _w in _req_warns:
        st.warning(_w)


def _clear_requisites() -> None:
    """Осознанный полный сброс полей под новую карточку (on_click callback:
    widget-ключи можно менять только до инстанцирования виджетов)."""
    set_requisites({key: "" for key, _label in REQUISITE_FIELDS})
    st.session_state["contract"]["requisites_manual"] = set()
    st.session_state["contract"]["requisites"]["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] = ""
    st.session_state.pop("w_ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", None)
    st.session_state["w_requisites_paste"] = ""


# Панель загрузки файла / вставки текста + парсер (единый regex-путь)
with st.expander("Реквизиты из файла или текста", expanded=not is_extracted()):
    st.caption(
        "Загрузите файл реквизитов или вставьте текст и нажмите «Распознать». "
        "Поля заполнятся автоматически (включая производные — полное "
        "наименование, инициалы, родительный падеж), уже заполненное не "
        "затирается. Поля можно редактировать."
    )
    _req_file = st.file_uploader(
        "Файл реквизитов (DOCX или PDF с текстовым слоем)",
        type=["docx", "pdf"],
        key="upload_requisites_file",
    )
    if st.button(
        "Распознать из файла", key="btn_parse_requisites_file",
        disabled=_req_file is None,
    ):
        try:
            _file_text = extract_text(Path(_save_uploaded(_req_file)))
        except NoTextLayerError:
            st.error(
                "В файле нет текстового слоя — вставьте реквизиты текстом. "
                "Распознавание сканов пока не поддерживается."
            )
        except Exception as exc:
            st.error(f"Ошибка чтения файла: {exc}")
        else:
            _apply_requisites_text(_file_text)
    st.text_area(
        "Блок реквизитов",
        key="w_requisites_paste",
        height=200,
        label_visibility="collapsed",
        placeholder="Вставьте реквизиты контрагента...",
    )
    _btn_col1, _btn_col2 = st.columns(2)
    with _btn_col1:
        if st.button("Распознать", key="btn_parse_requisites"):
            _apply_requisites_text(st.session_state.get("w_requisites_paste", ""))
    with _btn_col2:
        st.button(
            "Очистить реквизиты", key="btn_clear_requisites",
            on_click=_clear_requisites,
            help="Полный сброс всех полей реквизитов для новой карточки.",
        )

_render_field_group(
    "Реквизиты заказчика", REQUISITE_FIELDS[:-1], "requisites",
    derived_keys=frozenset(_DERIVED_PRIMARY),
)

# Последняя строка группы: Инициалы + Пол директора (предзаполняем из ФИО,
# пользователь может изменить вручную)
_req = st.session_state["contract"]["requisites"]
_stored_gender = _req.get("ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", "")
if not _stored_gender:
    _fio = _req.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "")
    _stored_gender = infer_director_gender(_fio) if _fio else "male"
    _req["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] = _stored_gender
st.session_state.setdefault("w_ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", _stored_gender)

_ini_key, _ini_label = REQUISITE_FIELDS[-1]
st.session_state.setdefault(f"w_{_ini_key}", _req.get(_ini_key, ""))
_ini_col, _pol_col = st.columns(2)
with _ini_col:
    st.text_input(
        _ini_label, key=f"w_{_ini_key}",
        on_change=sync_field, args=("requisites", _ini_key, False),
    )
with _pol_col:
    st.selectbox(
        "Пол директора",
        options=["male", "female"],
        format_func=lambda x: {"male": "мужской", "female": "женский"}[x],
        key="w_ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ",
        on_change=sync_field,
        args=("requisites", "ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"),
        help="Для согласования «действующего/действующей» в договоре.",
    )

st.divider()

if is_extracted():

    # ------------------------------------------------------------------
    # Секция 2.5 — Особые условия (foundation + зимний + overrides)
    # ------------------------------------------------------------------
    _cs_flags = st.session_state["contract"]["flags"]
    _cs_ovr = st.session_state["contract"]["scope_overrides"]

    st.subheader("Особые условия")

    # Вычислить предварительный контекст, чтобы понять что есть в позициях
    _spec_items_0 = get_spec_items()
    _ctx0 = build_clauses_context({
        "items": _spec_items_0,
        "scope_overrides": _cs_ovr,
        "flags": _cs_flags,
    })
    _install_present = _ctx0["installation_scope"] != "none"
    _has_found_item = any(it.get("id") in ("foundation", "rama") for it in _spec_items_0)

    if orion_poles_without_foundation(_spec_items_0):
        st.warning(
            "Опоры ОРИОН без строительства фундамента Подрядчиком: авто-текст "
            "оплаты/Акта сошлётся на «фундамент» некорректно, проверьте "
            "формулировку вручную"
        )
        with st.expander("Рекомендуемая формулировка — согласовать с юристом"):
            st.code(ORION_POLES_WITHOUT_FOUNDATION_TEXT)

    # --- Контроль основания ---
    st.markdown("**Основание под весы**")
    if _has_found_item:
        # Случаи 1–3: scope определён из позиции КП — показываем read-only метку
        _auto_label = _FOUND_LABELS.get(_ctx0["foundation_scope"], _ctx0["foundation_scope"])
        st.caption(f"Определено из позиций КП: {_auto_label}")
        # Guard: legacy-снапшот мог записать conflicting override
        _leg_ovr = _cs_ovr.get("foundation_scope")
        if _leg_ovr in ("customer_builds", "existing_foundation"):
            st.warning(
                f"⚠️ В снапшоте КП сохранён override «{_FOUND_LABELS.get(_leg_ovr, _leg_ovr)}», "
                "но в позициях есть фундамент/рама — позиция приоритетнее. "
                "Override проигнорирован."
            )
    elif _install_present:
        # Случай 4: нет позиции фундамента, но есть монтаж — менеджер выбирает
        _cur_f_manual = _cs_ovr.get("foundation_scope")
        _cur_f_label = _FOUND_MANUAL_RMAP.get(_cur_f_manual, "Заказчик строит фундамент")
        st.session_state.setdefault("w_foundation_scope_manual", _cur_f_label)
        _sel_f_manual = st.selectbox(
            "Тип основания",
            _FOUND_MANUAL_OPTS,
            key="w_foundation_scope_manual",
            help=(
                "«Заказчик строит»: заказчик строит фундамент по Строительному заданию (Приложение №1). "
                "«Готовый фундамент»: весы под существующий фундамент заказчика, без обязательств по стройке."
            ),
        )
        _cs_ovr["foundation_scope"] = _FOUND_MANUAL_MAP[_sel_f_manual]
    else:
        # Чистая поставка без монтажа — нет обязательств по фундаменту
        st.caption("Поставка без монтажа — обязательства по фундаменту не формируются.")
        # Сбросить stale foundation override чтобы не влиял на контекст
        _cs_ovr["foundation_scope"] = None

    # Вычислить итоговый scope после применения выбора
    _found_scope_final = build_clauses_context({
        "items": _spec_items_0,
        "scope_overrides": _cs_ovr,
        "flags": _cs_flags,
    })["foundation_scope"]

    # --- Зимний период — только если Подрядчик льёт бетон ---
    _cs_flags.setdefault("winter_surcharge", bool(_cs_flags.get("winter_concrete", False)))
    _cs_flags.setdefault("winter_surcharge_amount", 200000)
    if winter_surcharge_allowed(_found_scope_final):
        st.session_state.setdefault("w_winter_surcharge", _cs_flags.get("winter_surcharge", False))
        _winter_val = st.checkbox(
            "Зимний период (бетонные работы при +5 °C и ниже)",
            key="w_winter_surcharge",
        )
        _cs_flags["winter_surcharge"] = _winter_val
        _cs_flags["winter_concrete"] = _winter_val
        if _winter_val:
            st.session_state.setdefault(
                "w_winter_surcharge_amount",
                int(_cs_flags.get("winter_surcharge_amount") or 200000),
            )
            _cs_flags["winter_surcharge_amount"] = int(st.number_input(
                "Сумма зимнего удорожания, руб.",
                min_value=0,
                step=1000,
                key="w_winter_surcharge_amount",
            ))
    else:
        # Скрыт — сбрасываем залипшие флаги чтобы не попали в договор
        _cs_flags["winter_surcharge"] = False
        _cs_flags["winter_concrete"] = False

    with st.expander("Override-флаги (для нестандартных случаев)", expanded=False):
        st.caption(
            "По умолчанию scope монтажа, поверки и ОРИОН вычисляется из позиций КП. "
            "Здесь можно вручную переопределить."
        )
        _cur_i = _cs_ovr.get("installation_scope")
        st.session_state.setdefault("w_installation_scope", _INST_RMAP.get(_cur_i, "Авто (из позиций)"))
        _sel_i = st.selectbox("Тип монтажа", _INST_OPTS, key="w_installation_scope")
        _cs_ovr["installation_scope"] = _INST_MAP[_sel_i]

        _cur_v = _cs_ovr.get("verification_scope")
        st.session_state.setdefault("w_verification_scope", _VERIF_RMAP.get(_cur_v, "Авто (из позиций)"))
        _sel_v = st.selectbox("Поверку организует", _VERIF_OPTS, key="w_verification_scope")
        _cs_ovr["verification_scope"] = _VERIF_MAP[_sel_v]

        _has_orion = any(item.get("id") == "orion" for item in _spec_items_0)
        if _has_orion:
            _cur_o = _cs_ovr.get("orion_poles_scope")
            st.session_state.setdefault("w_orion_poles_scope", _ORION_RMAP.get(_cur_o, "Авто (из позиций)"))
            _sel_o = st.selectbox("Опоры ПАК ОРИОН", _ORION_OPTS, key="w_orion_poles_scope")
            _cs_ovr["orion_poles_scope"] = _ORION_MAP[_sel_o]

    with st.expander("Предпросмотр пунктов договора", expanded=False):
        _preview_deal = {
            "items": get_spec_items(),
            "scope_overrides": _cs_ovr,
            "flags": _cs_flags,
            "delivery_address": st.session_state["contract"].get("manual", {}).get("object_address", ""),
        }
        _clauses_preview = build_contract_clauses(_preview_deal)
        _total_count = sum(len(v) for v in _clauses_preview.values())
        for _sec_id, _sec_clauses in _clauses_preview.items():
            st.markdown(f"**{_SECTION_LABELS.get(_sec_id, _sec_id)}**")
            for _clause in _sec_clauses:
                st.text(f"  {_clause.auto_number}. {_clause.text[:60]}...")
        st.caption(f"Всего пунктов: {_total_count}")

    st.divider()
    spec_items = get_spec_items()
    if spec_items:
        st.subheader("Позиции спецификации")
        edited_df = st.data_editor(
            _items_to_rows(spec_items),
            num_rows="dynamic",
            column_config={
                "Наименование": st.column_config.TextColumn("Наименование"),
                "Бакет": st.column_config.SelectboxColumn(
                    "Бакет",
                    options=_BUCKET_OPTIONS,
                    width="medium",
                ),
                "Ед.": st.column_config.TextColumn("Ед.", width="small"),
                "Кол-во": st.column_config.NumberColumn("Кол-во", min_value=0, step=1),
                "Цена с НДС, руб.": st.column_config.NumberColumn(
                    "Цена с НДС, руб.", min_value=0, format="%d"
                ),
                "Сумма с НДС, руб.": st.column_config.NumberColumn(
                    "Сумма с НДС, руб.", disabled=True, format="%d"
                ),
            },
            key="spec_items_editor",
            width="stretch",
            hide_index=True,
        )

        if st.button("+ Добавить позицию"):
            current_items = _rows_to_items(edited_df, spec_items)
            current_items.append(make_custom_item())
            set_spec_items(current_items)
            if "spec_items_editor" in st.session_state:
                del st.session_state["spec_items_editor"]
            st.rerun()

        _synced = _rows_to_items(edited_df, spec_items)
        recalculate_totals(_synced)
        _totals_changed = len(_synced) == len(spec_items) and any(
            round(n["total"]) != round(o.get("total", 0))
            for n, o in zip(_synced, spec_items)
        )
        set_spec_items(_synced)
        if _totals_changed:
            if "spec_items_editor" in st.session_state:
                del st.session_state["spec_items_editor"]
            st.rerun()

        _unbucketed = [it["name"] for it in _synced if not it.get("payment_group")]
        if _unbucketed:
            st.error(
                "Позиции без бакета (укажите бакет в колонке): "
                + ", ".join(f"«{n}»" for n in _unbucketed)
            )

        _suspect = _suspect_names(_synced)
        if _suspect:
            st.warning(
                "Проверьте бакет — по названию похоже на монтаж/фундамент, "
                "но позиция отнесена к «Оборудование» (попадёт в сумму "
                "поставки): " + ", ".join(f"«{n}»" for n in _suspect)
            )

    else:
        _render_field_group("Из коммерческого предложения", SPEC_FIELDS, "specification")

    st.divider()
    render_payment_lines_editor()

    st.divider()
    _render_fundament_attachment_choice()

    st.divider()

# ---------------------------------------------------------------------------
# Секция 3 — Ручной ввод (общая)
# ---------------------------------------------------------------------------

# --- Автовыбор типа документа (с ручным override) ---
cs = st.session_state["contract"]
_auto_deal = {
    "items": get_spec_items(),
    "scope_overrides": cs.get("scope_overrides", {}),
    "flags": cs.get("flags", {}),
    "delivery_address": cs.get("manual", {}).get("object_address", ""),
}
_clauses_ctx_now = build_clauses_context(_auto_deal)
_auto_type = decide_contract_type(
    _clauses_ctx_now.get("installation_scope", "none"),
    _clauses_ctx_now.get("foundation_scope", "none"),
    bool(_clauses_ctx_now.get("has_orion", False)),
)
_auto_label = "Поставка" if _auto_type == "supply" else "Спецификация"
# Пере-seed радио только при смене подписи (КП или авто-тип) —
# ручной выбор пользователя переживает reruns.
_sig = f"{cs.get('current_kp_number', '')}:{_auto_type}"
if st.session_state.get("_contract_type_sig") != _sig:
    st.session_state["w_contract_type"] = _auto_label
    st.session_state["_contract_type_sig"] = _sig
w_contract_type = st.radio(
    "Тип документа",
    ["Спецификация", "Поставка"],
    horizontal=True,
    key="w_contract_type",
)

st.subheader("Параметры договора")
_manual = st.session_state["contract"]["manual"]
manual_col1, manual_col2 = st.columns(2)
with manual_col1:
    st.session_state.setdefault("w_contract_number", _manual["contract_number"])
    contract_number = st.text_input(
        "Номер договора", placeholder="1-2026",
        key="w_contract_number",
        on_change=sync_manual_field, args=("contract_number",),
    )
    st.session_state.setdefault(
        "w_contract_date", _manual["contract_date"] or date.today(),
    )
    contract_date = st.date_input(
        "Дата договора",
        key="w_contract_date",
        on_change=sync_manual_field, args=("contract_date",),
    )
with manual_col2:
    st.session_state.setdefault("w_object_address", _manual["object_address"])
    object_address = st.text_input(
        "Адрес объекта монтажа",
        key="w_object_address",
        on_change=sync_manual_field, args=("object_address",),
    )
    st.session_state.setdefault("w_spec_number", _manual["spec_number"])
    spec_number = st.text_input(
        "Номер спецификации",
        key="w_spec_number",
        on_change=sync_manual_field, args=("spec_number",),
    )
    # Срок действия используется только договором поставки.
    if w_contract_type == "Поставка":
        st.session_state.setdefault("w_valid_until", _manual.get("valid_until"))
        st.date_input(
            "Срок действия договора до",
            key="w_valid_until",
            on_change=sync_manual_field, args=("valid_until",),
        )

st.divider()

# ---------------------------------------------------------------------------
# Секция 4 — Генерация (общая)
# ---------------------------------------------------------------------------

generated = cs.get("generated")

if not generated:
    # Валидация текущих реквизитов (включая ручные правки) на каждом рендере.
    # Пустой dict не валидируем — работает старый гейт bool(requisites).
    _req_now = cs.get("requisites") or {}
    _req_errors, _req_warnings = (
        validate_requisites(_req_now) if _req_now else ([], [])
    )
    if _req_errors:
        with st.container(border=True):
            st.markdown(f"**:material/error: Ошибки реквизитов ({len(_req_errors)})**")
            for _e in _req_errors:
                st.markdown(f"- {_e}")
    if _req_warnings:
        with st.container(border=True):
            st.markdown(
                f"**:material/warning: Предупреждения по реквизитам "
                f"({len(_req_warnings)})**"
            )
            for _w in _req_warnings:
                st.markdown(f"- {_w}")

    generate_disabled = (
        not (bool(cs.get("specification")) and bool(cs.get("requisites")))
        or not contract_number
        or not object_address
        or bool(_req_errors)
    )

    # ⚠️ ЗЕРКАЛО: блок генерации ниже реплицирован в tests/autoverify/runner.py —
    # менять ПАРНО. Постоянный фикс — вынос в src/contracts/generate_service.py.
    if st.button(
        "Сгенерировать договор и спецификацию",
        disabled=generate_disabled,
        help="Сначала устраните ошибки в реквизитах" if _req_errors else None,
    ):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        data = collect_for_template()
        date_parts = format_date_parts(str(contract_date))
        data.update(date_parts)
        data["ДОГОВОР_НОМЕР"] = contract_number
        data["СПЕЦ_АДРЕС_ОБЪЕКТА"] = object_address
        data["СПЕЦ_НОМЕР"] = spec_number
        pol = data.get("ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", "male")
        data["ДИРЕКТОР_ПРИЧАСТИЕ"] = "действующей" if pol == "female" else "действующего"

        nds = data.get("СПЕЦ_НДС", "")
        if not nds or "20" in nds:
            data["СПЕЦ_НДС"] = nds.replace("20", "22") if nds else "22"

        safe_name = sanitize_filename(data.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ", ""))
        safe_number = sanitize_filename(contract_number)
        contract_fname = f"Договор_{safe_number}_{safe_name}.docx"
        spec_fname = f"Спецификация_{safe_number}_{safe_name}.docx"

        contract_path = OUTPUT_DIR / contract_fname
        spec_path = OUTPUT_DIR / spec_fname

        # --- Подготовка items и deal (общая для обоих флоу) ---
        items_for_docx = get_spec_items()
        if items_for_docx and edited_df is not None and hasattr(edited_df, "to_dict"):
            items_for_docx = _rows_to_items(edited_df, items_for_docx)
            for _i in items_for_docx:
                _i["total"] = _i["quantity"] * _i["price_per_unit"]
        _gen_cs = st.session_state["contract"]
        # Количество весов — из снапшота КП (single source). Legacy/пустой → 1.
        _model_qty = get_model_qty()
        _gen_deal = {
            "items": items_for_docx,
            "scope_overrides": _gen_cs.get("scope_overrides", {}),
            "flags": _gen_cs.get("flags", {}),
            "delivery_address": _gen_cs.get("manual", {}).get("object_address", ""),
        }
        _prows = get_payment_lines()

        if w_contract_type == "Поставка":
            # ----------------------------------------------------------
            # Supply-флоу: три docxtpl-шаблона → один DOCX
            # ----------------------------------------------------------
            try:
                supply_fname = f"Договор_поставки_{safe_number}_{safe_name}.docx"
                supply_path = OUTPUT_DIR / supply_fname
                supply_ctx = build_supply_context(
                    data, items_for_docx, _gen_deal, _prows,
                    _gen_cs.get("manual", {}), contract_date,
                    model_qty=_model_qty,
                )
                compose_supply(supply_ctx, supply_path)
                unfilled = get_unfilled_placeholders(str(supply_path))
                if unfilled:
                    st.warning(f"Договор поставки — не заполнены: {', '.join(unfilled)}")
                cs["generated"] = {
                    "contract_type": "supply",
                    "supply_bytes": supply_path.read_bytes(),
                    "supply_filename": supply_fname,
                }
                generated = cs["generated"]
            except Exception as exc:
                import traceback
                st.error(f"Ошибка генерации договора поставки: {exc}")
                st.code(traceback.format_exc(), language="python")
        else:
            # ----------------------------------------------------------
            # Spec-флоу: Договор + Спецификация (без изменений)
            # ----------------------------------------------------------
            try:
                fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
                if items_for_docx:
                    if _prows:
                        from src.ui.payment_lines_editor import _row_to_line
                        data["_payment_lines"] = [
                            format_payment_line(_row_to_line(row), f"2.{i + 1}")
                            for i, row in enumerate(_prows)
                        ]
                    try:
                        fill_spec_v2(str(SPEC_V2_TEMPLATE), data, items_for_docx, _gen_deal, str(spec_path), model_qty=_model_qty)
                    except Exception as exc_v2:
                        import traceback
                        from datetime import datetime
                        _tb_path = Path("docs") / f"v1.0_fillspec_traceback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        _tb_path.parent.mkdir(exist_ok=True)
                        with open(_tb_path, "w", encoding="utf-8") as f:
                            f.write(f"=== EXCEPTION ===\n{type(exc_v2).__name__}: {exc_v2}\n\n")
                            f.write(f"=== TRACEBACK ===\n{traceback.format_exc()}\n\n")
                            f.write(f"=== DATA KEYS ===\n{list(data.keys())}\n\n")
                            f.write(f"=== ITEMS COUNT ===\n{len(items_for_docx)}\n\n")
                            f.write("=== DEAL ===\n")
                            import json
                            f.write(json.dumps(_gen_deal, ensure_ascii=False, indent=2, default=str))
                        st.error(f"❌ fill_spec_v2 упал. Traceback: {_tb_path}")
                        st.code(traceback.format_exc(), language="python")
                        fill_spec_with_items(str(SPEC_TEMPLATE), data, items_for_docx, str(spec_path), model_qty=_model_qty)

                    attachments = _gen_cs.get("attachments", {})
                    compose_spec_with_attachments(spec_path, attachments, data)
                    clauses_ctx = build_clauses_context(_gen_deal)
                    build_task_missing = (
                        not attachments.get("build_task_path")
                        or attachments.get("build_task_source") == "none"
                    )
                    if clauses_ctx["foundation_scope"] in ("customer_builds", "contractor_supervised") and build_task_missing:
                        st.warning(
                            "В тексте Спецификации есть ссылка на Приложение №1 "
                            "(строительное задание), но файл не приложен."
                        )
                else:
                    fill_template(str(SPEC_TEMPLATE), data, str(spec_path))

                for label, path in [("Договор", contract_path), ("Спецификация", spec_path)]:
                    unfilled = get_unfilled_placeholders(str(path))
                    if unfilled:
                        st.warning(f"{label} — не заполнены: {', '.join(unfilled)}")

                cs["generated"] = {
                    "contract_type": "spec",
                    "contract_bytes": contract_path.read_bytes(),
                    "contract_filename": contract_fname,
                    "spec_bytes": spec_path.read_bytes(),
                    "spec_filename": spec_fname,
                }
                generated = cs["generated"]
            except Exception as exc:
                st.error(f"Ошибка генерации: {exc}")

if generated:
    if generated.get("contract_type") == "supply":
        st.download_button(
            f"Скачать {generated['supply_filename']}",
            data=generated["supply_bytes"],
            file_name=generated["supply_filename"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                f"Скачать {generated['contract_filename']}",
                data=generated["contract_bytes"],
                file_name=generated["contract_filename"],
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        with dl_col2:
            st.download_button(
                f"Скачать {generated['spec_filename']}",
                data=generated["spec_bytes"],
                file_name=generated["spec_filename"],
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
    st.success("Документы сгенерированы")
    if st.button("Сгенерировать заново"):
        clear_generated()
        st.rerun()
