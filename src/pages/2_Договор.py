"""Страница генерации договора и спецификации."""
from __future__ import annotations

import logging
import sys
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.contracts.clauses_renderer import build_contract_clauses  # noqa: E402
from src.contracts.extractor import extract_card_data, extract_kp_data_legacy  # noqa: E402
from src.contracts.filler import (  # noqa: E402
    fill_spec_with_items,
    fill_template,
    get_unfilled_placeholders,
)
from src.contracts.fundament_lookup import (  # noqa: E402
    BuildTaskResolution,
    list_build_task_files,
    resolve_build_task,
    resolve_control_sheet,
)
from src.contracts.from_kp import (  # noqa: E402
    build_specification_from_kp_snapshot,
    build_specification_items,
)
from src.contracts.payment_line import format_payment_line  # noqa: E402
from src.contracts.spec_items import make_custom_item, recalculate_totals  # noqa: E402
from src.contracts.spec_v2_filler import fill_spec_v2  # noqa: E402
from src.contracts.state import (  # noqa: E402
    clear_generated,
    collect_for_template,
    get_payment_lines,
    get_spec_items,
    init_contract_state,
    is_extracted,
    set_extracted_data,
    set_requisites,
    set_spec_items,
    set_specification,
    sync_field,
    sync_manual_field,
)
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
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Определения полей
# ---------------------------------------------------------------------------

REQUISITE_FIELDS: list[tuple[str, str]] = [
    ("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ", "Краткое наименование"),
    ("ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ", "Полное наименование"),
    ("ЗАКАЗЧИК_ИНН", "ИНН"),
    ("ЗАКАЗЧИК_КПП", "КПП"),
    ("ЗАКАЗЧИК_ОГРН", "ОГРН"),
    ("ЗАКАЗЧИК_АДРЕС_ЮР", "Юридический адрес"),
    ("ЗАКАЗЧИК_АДРЕС_ПОЧТ", "Почтовый адрес"),
    ("ЗАКАЗЧИК_РС", "Расчётный счёт"),
    ("ЗАКАЗЧИК_БАНК", "Банк"),
    ("ЗАКАЗЧИК_КС", "Корреспондентский счёт"),
    ("ЗАКАЗЧИК_БИК", "БИК"),
    ("ЗАКАЗЧИК_ТЕЛЕФОН", "Телефон"),
    ("ЗАКАЗЧИК_EMAIL", "Email"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ", "Должность руководителя"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "ФИО руководителя"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ДОЛЖНОСТЬ_РП", "Должность (род. падеж)"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ФИО_РП", "ФИО (род. падеж)"),
    ("ЗАКАЗЧИК_ДИРЕКТОР_ИНИЦИАЛЫ", "Инициалы"),
    ("ЗАКАЗЧИК_ОСНОВАНИЕ", "Основание"),
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

_FOUND_OPTS = [
    "Авто (из позиций)", "Заказчик строит", "Подрядчик строит",
    "Подрядчик с материалами Заказчика", "Рама", "Без фундамента",
]
_FOUND_MAP: dict[str, str | None] = {
    "Авто (из позиций)": None, "Заказчик строит": "customer_builds",
    "Подрядчик строит": "contractor_full",
    "Подрядчик с материалами Заказчика": "contractor_with_materials",
    "Рама": "rama", "Без фундамента": "none",
}
_FOUND_RMAP = {v: k for k, v in _FOUND_MAP.items()}

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


def _render_field_group(
    title: str, fields: list[tuple[str, str]], section: str,
) -> None:
    st.subheader(title)
    ns = st.session_state["contract"][section]
    col1, col2 = st.columns(2)
    for i, (key, label) in enumerate(fields):
        wkey = f"w_{key}"
        st.session_state.setdefault(wkey, ns.get(key, ""))
        col = col1 if i % 2 == 0 else col2
        with col:
            if key in WIDE_FIELDS:
                st.text_area(
                    label, key=wkey, height=68,
                    on_change=sync_field, args=(section, key),
                )
            else:
                st.text_input(
                    label, key=wkey,
                    on_change=sync_field, args=(section, key),
                )


def _family_label(family: str | None) -> str:
    return family.replace("_", "/") if family else ""


def _build_task_auto_text(result: BuildTaskResolution) -> str:
    if result.path is None:
        return f"не подобрано: {result.reason}"
    parts = [result.execution or "без фундамента"]
    if result.sections:
        parts.append(f"{result.sections} секции")
    family = _family_label(result.family)
    if family:
        parts.append(family)
    return f"{', '.join(parts)} → {result.path.name}"


def _build_task_choice_index(options: list[str], attachments: dict) -> int:
    source = attachments.get("build_task_source", "auto")
    if source == "none":
        return options.index("Без приложения")
    if source == "manual":
        filename = Path(str(attachments.get("build_task_path") or "")).name
        if filename in options:
            return options.index(filename)
    return options.index("Авто-подбор")


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
    files_by_name = {path.name: path for path in build_task_files}
    options = ["Авто-подбор", "Без приложения", *files_by_name]
    widget_key = "w_build_task_choice"
    if widget_key not in st.session_state or st.session_state[widget_key] not in options:
        st.session_state[widget_key] = options[_build_task_choice_index(options, attachments)]

    selected = st.selectbox(
        "Выбор строительного задания",
        options,
        key=widget_key,
        help="Override для нестандартных случаев. Склейка приложений будет добавлена на шаге 9.",
    )
    if selected == "Авто-подбор":
        selected_build_task = auto_result.path
        attachments["build_task_source"] = "auto"
    elif selected == "Без приложения":
        selected_build_task = None
        attachments["build_task_source"] = "none"
    else:
        selected_build_task = files_by_name[selected]
        attachments["build_task_source"] = "manual"
    attachments["build_task_path"] = str(selected_build_task or "")

    if selected_build_task:
        st.caption(f"Итоговый выбор: {selected_build_task.name}")
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
        st.caption(f"Контрольный лист: {control_sheet.name}")


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
        search_clicked = st.button("Найти", key="kp_search_btn")

    kp_row = None
    if selected_label != "— выбрать —":
        kp_row = kp_options_map.get(selected_label)
    elif search_clicked and manual_kp_num:
        try:
            kp_row = get_kp_by_number(manual_kp_num.strip())
            if kp_row is None:
                st.warning(f"КП «{manual_kp_num}» не найден в базе.")
        except StorageError as e:
            st.error(f"Ошибка поиска: {e}")

    if kp_row is not None:
        try:
            prices = load_prices()
            models_json = load_models()
            payment_terms = load_payment_terms()
            spec = build_specification_from_kp_snapshot(
                kp_row, prices, models_json, payment_terms
            )
            set_specification(spec)
            _snap = kp_row.get("data") or kp_row.get("snapshot") or {}
            st.session_state["contract"]["kp_snapshot"] = _snap
            try:
                items = build_specification_items(kp_row, prices)
                set_spec_items(items)
                st.session_state["contract"]["kp_payment_snapshot"] = (
                    _snap.get("payment") or {}
                )
            except Exception as exc:
                _logger.warning("build_specification_items failed: %s", exc)
            st.success(f"КП «{kp_row.get('kp_number', '')}» загружен из базы.")
        except Exception as exc:
            st.error(f"Ошибка загрузки спецификации: {exc}")

    st.divider()
    st.subheader("Карточка контрагента")
    card_file_a = st.file_uploader(
        "PDF или DOCX карточки контрагента", type=["pdf", "docx"],
        key="upload_card_a",
    )
    if st.button("Извлечь реквизиты через AI", disabled=card_file_a is None):
        with st.spinner("AI извлекает реквизиты..."):
            try:
                card_path = _save_uploaded(card_file_a)
                card_data = extract_card_data(card_path)
                set_requisites(card_data.get("requisites", {}))
                st.success("Реквизиты извлечены.")
            except Exception as exc:
                st.error(f"Ошибка извлечения реквизитов: {exc}")

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
# Секция 2 — Форма проверки и правки (общая для обоих режимов)
# ---------------------------------------------------------------------------

edited_df = None  # Будет установлен в блоке data_editor если items существуют

if is_extracted():
    _render_field_group("Реквизиты заказчика", REQUISITE_FIELDS, "requisites")

    # Пол директора — предзаполняем из ФИО, пользователь может изменить вручную
    _req = st.session_state["contract"]["requisites"]
    _stored_gender = _req.get("ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", "")
    if not _stored_gender:
        _fio = _req.get("ЗАКАЗЧИК_ДИРЕКТОР_ФИО", "")
        _stored_gender = infer_director_gender(_fio) if _fio else "male"
        _req["ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"] = _stored_gender
    st.session_state.setdefault("w_ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ", _stored_gender)
    st.selectbox(
        "Пол директора (для согласования «действующего/действующей»)",
        options=["male", "female"],
        format_func=lambda x: {"male": "мужской", "female": "женский"}[x],
        key="w_ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ",
        on_change=sync_field,
        args=("requisites", "ЗАКАЗЧИК_ДИРЕКТОР_ПОЛ"),
    )

    st.divider()

    # ------------------------------------------------------------------
    # Секция 2.5 — Особые условия (override-флаги + clauses preview)
    # ------------------------------------------------------------------
    _cs_flags = st.session_state["contract"]["flags"]
    _cs_ovr = st.session_state["contract"]["scope_overrides"]

    st.subheader("Особые условия")
    _cs_flags.setdefault("winter_surcharge", bool(_cs_flags.get("winter_concrete", False)))
    _cs_flags.setdefault("winter_surcharge_amount", 200000)
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

    with st.expander("Override-флаги (для нестандартных случаев)", expanded=False):
        st.caption(
            "По умолчанию scope вычисляется из позиций спецификации. "
            "Здесь можно вручную переопределить."
        )
        _cur_f = _cs_ovr.get("foundation_scope")
        st.session_state.setdefault("w_foundation_scope", _FOUND_RMAP.get(_cur_f, "Авто (из позиций)"))
        _sel_f = st.selectbox("Тип фундамента", _FOUND_OPTS, key="w_foundation_scope")
        _cs_ovr["foundation_scope"] = _FOUND_MAP[_sel_f]

        _cur_i = _cs_ovr.get("installation_scope")
        st.session_state.setdefault("w_installation_scope", _INST_RMAP.get(_cur_i, "Авто (из позиций)"))
        _sel_i = st.selectbox("Тип монтажа", _INST_OPTS, key="w_installation_scope")
        _cs_ovr["installation_scope"] = _INST_MAP[_sel_i]

        _cur_v = _cs_ovr.get("verification_scope")
        st.session_state.setdefault("w_verification_scope", _VERIF_RMAP.get(_cur_v, "Авто (из позиций)"))
        _sel_v = st.selectbox("Поверку организует", _VERIF_OPTS, key="w_verification_scope")
        _cs_ovr["verification_scope"] = _VERIF_MAP[_sel_v]

        _items_check = get_spec_items()
        _has_orion = any(item.get("id") == "orion" for item in _items_check)
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
            use_container_width=True,
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

st.divider()

# ---------------------------------------------------------------------------
# Секция 4 — Генерация (общая)
# ---------------------------------------------------------------------------

cs = st.session_state["contract"]
generated = cs.get("generated")

if not generated:
    generate_disabled = (
        not (bool(cs.get("specification")) and bool(cs.get("requisites")))
        or not contract_number
        or not object_address
    )

    if st.button(
        "Сгенерировать договор и спецификацию", disabled=generate_disabled
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

        try:
            fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
            items_for_docx = get_spec_items()
            if items_for_docx:
                if edited_df is not None and hasattr(edited_df, "to_dict"):
                    items_for_docx = _rows_to_items(edited_df, items_for_docx)
                    for _i in items_for_docx:
                        _i["total"] = _i["quantity"] * _i["price_per_unit"]
                _gen_cs = st.session_state["contract"]
                _gen_deal = {
                    "items": items_for_docx,
                    "scope_overrides": _gen_cs.get("scope_overrides", {}),
                    "flags": _gen_cs.get("flags", {}),
                    "delivery_address": _gen_cs.get("manual", {}).get("object_address", ""),
                }
                _prows = get_payment_lines()
                if _prows:
                    from src.ui.payment_lines_editor import _row_to_line
                    data["_payment_lines"] = [
                        format_payment_line(_row_to_line(row), f"2.{i + 1}")
                        for i, row in enumerate(_prows)
                    ]
                try:
                    fill_spec_v2(str(SPEC_V2_TEMPLATE), data, items_for_docx, _gen_deal, str(spec_path))
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
                    fill_spec_with_items(str(SPEC_TEMPLATE), data, items_for_docx, str(spec_path))
            else:
                fill_template(str(SPEC_TEMPLATE), data, str(spec_path))

            for label, path in [("Договор", contract_path), ("Спецификация", spec_path)]:
                unfilled = get_unfilled_placeholders(str(path))
                if unfilled:
                    st.warning(f"{label} — не заполнены: {', '.join(unfilled)}")

            cs["generated"] = {
                "contract_bytes": contract_path.read_bytes(),
                "contract_filename": contract_fname,
                "spec_bytes": spec_path.read_bytes(),
                "spec_filename": spec_fname,
            }
            generated = cs["generated"]
        except Exception as exc:
            st.error(f"Ошибка генерации: {exc}")

if generated:
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
