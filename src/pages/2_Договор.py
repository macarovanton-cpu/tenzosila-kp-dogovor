"""Страница генерации договора и спецификации."""
from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.contracts.extractor import extract_from_files  # noqa: E402
from src.contracts.filler import fill_template, get_unfilled_placeholders  # noqa: E402
from src.contracts.state import (  # noqa: E402
    collect_for_template,
    init_contract_state,
    is_extracted,
    set_extracted_data,
    sync_field,
    sync_manual_field,
)
from src.contracts.utils import format_date_parts  # noqa: E402
from src.utils.format import sanitize_filename  # noqa: E402

CONTRACT_TEMPLATE = Path("templates/contracts/contract.docx")
SPEC_TEMPLATE = Path("templates/contracts/spec_foundation_install.docx")
OUTPUT_DIR = Path("output/contracts")

st.set_page_config(page_title="Договор", page_icon="📄", layout="wide")
init_contract_state()

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
    ("СПЕЦ_П2_ПАРАМЕТРЫ", "П2 — Параметры"),
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_uploaded(uploaded_file) -> str:
    """Сохраняет UploadedFile во временный файл, возвращает путь."""
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getbuffer())
    tmp.close()
    return tmp.name


def _render_field_group(
    title: str, fields: list[tuple[str, str]], section: str,
) -> None:
    """Рисует блок полей в две колонки. section = 'requisites' | 'specification'."""
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


# ---------------------------------------------------------------------------
# Секция 1 — Загрузка файлов
# ---------------------------------------------------------------------------

st.title("Генерация договора")

st.subheader("Загрузка документов")
up_col1, up_col2 = st.columns(2)
with up_col1:
    kp_file = st.file_uploader(
        "PDF коммерческого предложения", type=["pdf"], key="upload_kp"
    )
with up_col2:
    card_file = st.file_uploader(
        "Карточка контрагента", type=["pdf", "docx"], key="upload_card"
    )

extract_disabled = not (kp_file and card_file)
if st.button("Извлечь данные через AI", disabled=extract_disabled):
    with st.spinner("AI извлекает данные..."):
        try:
            kp_path = _save_uploaded(kp_file)
            card_path = _save_uploaded(card_file)
            raw = extract_from_files(kp_path, card_path)
            set_extracted_data(raw)
            st.success("Данные извлечены")
        except Exception as exc:
            st.error(f"Ошибка извлечения: {exc}")

st.divider()

# ---------------------------------------------------------------------------
# Секция 2 — Форма проверки и правки
# ---------------------------------------------------------------------------

if is_extracted():
    _render_field_group("Реквизиты заказчика", REQUISITE_FIELDS, "requisites")
    st.divider()
    _render_field_group("Из коммерческого предложения", SPEC_FIELDS, "specification")
    st.divider()

# ---------------------------------------------------------------------------
# Секция 3 — Ручной ввод
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
# Секция 4 — Генерация
# ---------------------------------------------------------------------------

generate_disabled = (
    not is_extracted()
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

    nds = data.get("СПЕЦ_НДС", "")
    if not nds or "20" in nds:
        data["СПЕЦ_НДС"] = nds.replace("20", "22") if nds else "22"

    safe_name = sanitize_filename(
        data.get("ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ", "")
    )
    safe_number = sanitize_filename(contract_number)
    contract_fname = f"Договор_{safe_number}_{safe_name}.docx"
    spec_fname = f"Спецификация_{safe_number}_{safe_name}.docx"

    contract_path = OUTPUT_DIR / contract_fname
    spec_path = OUTPUT_DIR / spec_fname

    try:
        fill_template(str(CONTRACT_TEMPLATE), data, str(contract_path))
        fill_template(str(SPEC_TEMPLATE), data, str(spec_path))

        for label, path in [
            ("Договор", contract_path),
            ("Спецификация", spec_path),
        ]:
            unfilled = get_unfilled_placeholders(str(path))
            if unfilled:
                st.warning(
                    f"{label} — не заполнены: {', '.join(unfilled)}"
                )

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                f"Скачать {contract_fname}",
                data=contract_path.read_bytes(),
                file_name=contract_fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        with dl_col2:
            st.download_button(
                f"Скачать {spec_fname}",
                data=spec_path.read_bytes(),
                file_name=spec_fname,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        st.success("Документы сгенерированы")
    except Exception as exc:
        st.error(f"Ошибка генерации: {exc}")
