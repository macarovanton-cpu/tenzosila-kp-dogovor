"""Тесты kp_generator: контекст, имя файла, генерация DOCX."""
from __future__ import annotations

import re
import zipfile
from datetime import date
from io import BytesIO

from docx import Document

from src.generators.kp_generator import (
    build_filename,
    build_main_scale_label,
    build_template_context,
    generate_kp,
)


def _state(**overrides) -> dict:
    base = {
        "kp_number": "47141",
        "kp_date": date(2026, 4, 22),
        "kp_valid_days": 15,
        "total_term_days": 35,
        "manager_id": "makarov_av",
        "client_name": "АО «Гипсобетон»",
        "model_line": "С",
        "model_max": 80,
        "model_length": 18,
        "model_id": "vesta-с-80-18",
        "model_price": 2_450_000,
        "warranty_months": 36,
        "is_dual_range": False,
        "sensor_id": "zemic_dhm9b_30t",
        "indicator_id": "titan_3cs",
        "construction_beam": "Двутавр 30Б1",
        "construction_beam_count": 8,
        "construction_center_beam": "Швеллер №12",
        "construction_center_beam_count": 2,
        "construction_deck_mm": 10,
        "construction_underlining_mm": 4,
        "options": {},
        "spec_items_overrides": {},
        "payment_preset_id": "prepay_50_postpay_50",
        "payment_split_state": {},
        "payment_percents": {"p1": 50, "p2": 50},
        "payment_days": 5,
        "payment_custom_text": "",
    }
    base.update(overrides)
    return base


# --- build_main_scale_label ---


def test_build_main_scale_label_single_range():
    model = {"verification_division_kg": 20}
    assert build_main_scale_label(model, is_dual_range=False) == "20 кг"


def test_build_main_scale_label_dual_range():
    model = {
        "verification_division_kg": 50,
        "dual_range": {
            "w1": {"max_load_t": 60, "e_kg": 20},
            "w2": {"max_load_t": 80, "e_kg": 50},
        },
    }
    label = build_main_scale_label(model, is_dual_range=True)
    assert "20 кг (до 60 т)" in label
    assert "50 кг (от 60 до 80 т)" in label
    assert "\n" in label
    assert " / " not in label


# --- build_template_context ---


def test_build_template_context_keys(prices):
    state = _state()
    ctx = build_template_context(state, prices)
    expected_keys = {
        "client_name", "kp_number", "kp_date", "kp_valid_days",
        "warranty_text", "max_load_t", "platform_size",
        "main_scale_label", "construction_description",
        "model_full_name",
        "sensor_label", "sensor_temp_range",
        "indicator_label", "indicator_temp_range",
        "spec_items", "total_price", "total_term_days", "vat_percent",
        "payment_terms_block",
        "manager_full_name", "manager_phone", "manager_email",
    }
    assert expected_keys <= set(ctx.keys()), (
        f"Missing keys: {expected_keys - set(ctx.keys())}"
    )
    assert "division_info" not in ctx


def test_build_template_context_values(prices):
    state = _state()
    ctx = build_template_context(state, prices)
    assert ctx["client_name"] == "АО «Гипсобетон»"
    assert ctx["kp_number"] == "47141"
    assert ctx["kp_date"] == "22.04.2026"
    assert ctx["kp_valid_days"] == "15 дней"
    assert ctx["warranty_text"] == "36 месяцев"
    assert ctx["vat_percent"] == "22"
    assert ctx["manager_full_name"] == "Макаров Антон"
    assert isinstance(ctx["spec_items"], list)
    assert all("name" in i and "price" in i and "term_days" in i for i in ctx["spec_items"])


def test_pluralize_kp_valid_days_and_warranty(prices):
    state = _state(kp_valid_days=21, warranty_months=24)
    ctx = build_template_context(state, prices)
    assert ctx["kp_valid_days"] == "21 день"
    assert ctx["warranty_text"] == "24 месяца"


# --- equipment_info (datчик/терминал) ---


def test_build_template_context_has_equipment_keys(prices):
    state = _state()
    ctx = build_template_context(state, prices)
    new_keys = {
        "model_full_name",
        "sensor_label", "sensor_temp_range",
        "indicator_label", "indicator_temp_range",
    }
    assert new_keys.issubset(ctx.keys())
    assert "division_info" not in ctx


def test_sensor_indicator_labels_match_state(prices):
    state = _state(sensor_id="mera_cdl_30t", indicator_id="titan_3c")
    ctx = build_template_context(state, prices)
    assert ctx["sensor_label"] == "Mera CDL-30t"
    assert ctx["sensor_temp_range"] == "-40...+40"
    assert ctx["indicator_label"] == "ТИТАН 3Ц"


def test_unknown_sensor_id_falls_back_to_default(prices):
    state = _state(sensor_id="несуществующий")
    ctx = build_template_context(state, prices)
    assert ctx["sensor_label"] == "Zemic DHM9B-30t"


# --- build_filename ---


def test_build_filename_translit_russian():
    state = _state(client_name="ООО «Гипсобетон»")
    name = build_filename(state)
    assert name.startswith("КП_")
    assert name.endswith("_2026-04-22.docx")
    # Транслитерация: «Гипсобетон» → Gipsobeton
    assert "Gipsobeton" in name or "gipsobeton" in name.lower()


def test_build_filename_empty_client_uses_fallback():
    state = _state(client_name="")
    name = build_filename(state)
    assert name.startswith("КП_")


def test_build_filename_includes_model():
    state = _state()
    name = build_filename(state)
    assert "80-18" in name  # часть model_full_name


# --- generate_kp ---


def test_generate_kp_returns_zip_bytes(prices):
    """Сгенерированные байты — валидный zip (DOCX)."""
    state = _state()
    docx = generate_kp(state, prices)
    assert isinstance(docx, bytes)
    assert len(docx) > 1000
    assert docx.startswith(b"PK")  # zip signature


def test_generate_kp_no_remaining_jinja(prices):
    """В готовом DOCX нет неподставленных {{ или {% (включая колонтитул)."""
    state = _state()
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))

    parts: list[str] = []
    for p in doc.paragraphs:
        parts.append("".join(r.text or "" for r in p.runs))
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    parts.append("".join(r.text or "" for r in p.runs))
    for s in doc.sections:
        f = s.footer
        if f is None:
            continue
        for p in f.paragraphs:
            parts.append("".join(r.text or "" for r in p.runs))
        for t in f.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        parts.append("".join(r.text or "" for r in p.runs))

    text = " ".join(parts)
    assert "{{" not in text, "Остались плейсхолдеры {{...}}"
    assert "{%" not in text, "Остались jinja-теги {%...%}"


def test_generated_docx_preserves_tx_labels(prices):
    """Подписи в строках 10/11 таблицы ТХ не затёрты плейсхолдерами."""
    state = _state(model_id="vesta-с-80-18")
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    tx = doc.tables[2]
    assert tx.rows[10].cells[0].text.strip() == "Максимальная нагрузка, т"
    assert tx.rows[11].cells[0].text.strip().startswith(
        "Цена поверочного деления"
    )


def test_generated_docx_description_cell_is_empty(prices):
    """В строке «Описание весов» колонка значения пуста."""
    state = _state()
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    tx = doc.tables[2]
    assert "Описание весов" in tx.rows[9].cells[0].text
    assert tx.rows[9].cells[2].text.strip() == ""


def test_section_title_includes_model_name(prices):
    """Заголовок 'Характеристики ВЕСТА-С-80-18' использует model_full_name."""
    state = _state(model_id="vesta-с-80-18")
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Характеристики ВЕСТА-С-80-18" in full_text


def test_kp_valid_days_paragraph_is_bold(prices):
    """Срок действия КП — жирным шрифтом."""
    state = _state()
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    valid_paras = [
        p for p in doc.paragraphs if "Срок действия настоящего" in p.text
    ]
    assert valid_paras, "Параграф 'Срок действия настоящего' не найден"
    assert any(r.bold for r in valid_paras[0].runs)


def test_spec_item_name_is_richtext_with_9pt_subline(prices):
    """Имя модели в spec_items_fmt — RichText, вспомогательные строки 9pt."""
    state = _state(model_id="vesta-с-80-18")
    ctx = build_template_context(state, prices)
    name = ctx["spec_items"][0]["name"]
    # docxtpl.RichText сериализуется в XML с size в half-points
    xml = str(name)
    assert "ВЕСТА-С-80-18" in xml
    assert "Датчики:" in xml
    assert "Терминал" in xml
    # 9pt = half-points 18
    assert 'w:sz w:val="18"' in xml or 'sz w:val="18"' in xml, (
        f"9pt size не найден в RichText XML: {xml[:300]}"
    )


# --- 1.5b-fix3: шрифты, оранжевый «ВЕСТА», тире в payment-блоке ---


def test_generated_docx_specification_has_no_arial_runs(prices):
    """В run-ах body нет явного Arial — спецификация в PT Sans (1.5b-fix3)."""
    state = _state()
    docx = generate_kp(state, prices)
    with zipfile.ZipFile(BytesIO(docx)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert 'w:ascii="Arial"' not in xml, (
        "Найден явный Arial в run-ах — регрессия rPr"
    )


def test_generated_docx_vesta_is_orange(prices):
    """Слово «ВЕСТА» в заголовке имеет color D04514 (1.5b-fix3)."""
    state = _state()
    docx = generate_kp(state, prices)
    with zipfile.ZipFile(BytesIO(docx)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    pattern = re.compile(
        r'<w:r[^>]*>(?:(?!</w:r>).)*?w:val="D04514"(?:(?!</w:r>).)*?'
        r'<w:t[^>]*>ВЕСТА</w:t>(?:(?!</w:r>).)*?</w:r>',
        re.DOTALL,
    )
    assert pattern.search(xml), "Оранжевая «ВЕСТА» (D04514) не найдена"


def test_generated_docx_payment_lines_have_dashes(prices):
    """Блок «Условия поставки» содержит ≥ 2 строк с «— » (1.5b-fix3)."""
    state = _state(
        payment_preset_id="split_by_items",
        options={
            "foundation_s_f_18": {
                "enabled": True, "price": 1_900_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 1_900_000, "dealer_is_synthetic": False,
                "block": "foundations",
            },
        },
    )
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert text.count("— ") >= 2, (
        f"Меньше 2 строк с «— » в payment-блоке: {text!r}"
    )


def test_generate_kp_payment_block_contains_split_lines(prices):
    """split_by_items: убедимся, что строки про «по уведомлению» и
    «по факту готовности фундамента» есть в тексте."""
    state = _state(
        payment_preset_id="split_by_items",
        options={
            "foundation_s_f_18": {
                "enabled": True, "price": 1_900_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 1_900_000, "dealer_is_synthetic": False,
                "block": "foundations",
            },
        },
    )
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))
    text = " ".join(
        "".join(r.text or "" for r in p.runs) for p in doc.paragraphs
    )
    assert "по уведомлению" in text
    assert "фундамент" in text


def test_payment_block_paragraph_has_no_list_numbering(prices):
    """Параграф с «— Предоплата:» в готовом DOCX не содержит numPr —
    иначе Word добавляет list-маркер перед первой строкой, и получается
    двойное тире (1.5b-fix4)."""
    state = _state()
    docx = generate_kp(state, prices)
    with zipfile.ZipFile(BytesIO(docx)) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    # После рендера «— Предоплата:» — первая строка блока условий оплаты.
    marker = "Предоплата:"
    idx = xml.find(marker)
    assert idx > 0, f"'{marker}' не найден в document.xml"
    para_start = xml.rfind("<w:p ", 0, idx)
    para_end = xml.find("</w:p>", idx) + len("</w:p>")
    para_xml = xml[para_start:para_end]
    assert "<w:numPr>" not in para_xml, (
        "Параграф с «Предоплата:» содержит numPr — Word добавит лишний list-маркер"
    )


# --- per-item срок исполнения с vMerge ---


def test_generated_docx_term_days_with_vmerge(prices):
    """Полный набор позиций при total=30 → vMerge для весов+опций, отдельные
    ячейки для фундамента/монтажа/поверки/доставки.

    Ожидается:
      - 1-я content-row (модель): cell[2].text="24" + <w:vMerge w:val="restart"/>
      - 2-я / 3-я (frame, fence): cell[2].text="" + <w:vMerge/> (continue)
      - 4-я (foundation): "24", без vMerge
      - 5-я (install): "4", без vMerge
      - 6-я (verification): "1", без vMerge
      - 7-я (delivery): "1", без vMerge
    """
    state = _state(
        total_term_days=30,
        options={
            "frame_18": {
                "enabled": True, "price": 130_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 130_000, "dealer_is_synthetic": False,
                "block": "frames",
            },
            "fence_norma_18": {
                "enabled": True, "price": 128_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 128_000, "dealer_is_synthetic": False,
                "block": "fences",
            },
            "foundation_s_f_18": {
                "enabled": True, "price": 280_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 280_000, "dealer_is_synthetic": False,
                "block": "foundations",
            },
            "install_default": {
                "enabled": True, "price": 200_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 200_000, "dealer_is_synthetic": False,
                "block": "install",
            },
            "verification_default": {
                "enabled": True, "price": 30_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 30_000, "dealer_is_synthetic": False,
                "block": "verification",
            },
            "delivery_default": {
                "enabled": True, "price": 70_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 70_000, "dealer_is_synthetic": False,
                "block": "delivery",
            },
        },
    )
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))

    spec_table = None
    for t in doc.tables:
        if t.rows[0].cells[0].text.strip() == "Наименование":
            spec_table = t
            break
    assert spec_table is not None, "Таблица спецификации не найдена"

    # Читаем напрямую из XML: row.cells «склеивает» vMerge-ячейки и
    # возвращает дубликаты — это сбивает проверку.
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    qn = lambda tag: f"{{{W}}}{tag}"  # noqa: E731

    trs = spec_table._tbl.findall(qn("tr"))
    assert len(trs) >= 9, f"Ожидалось ≥9 строк, получено {len(trs)}"

    def col2_info(tr):
        tcs = tr.findall(qn("tc"))
        tc = tcs[2]
        text = "".join(t.text or "" for t in tc.iter(qn("t")))
        tcPr = tc.find(qn("tcPr"))
        vm = tcPr.find(qn("vMerge")) if tcPr is not None else None
        if vm is None:
            return text, "none"
        val = vm.get(qn("val"))
        return text, "restart" if val == "restart" else "continue"

    # Порядок content-rows совпадает со spec_items:
    # vesta-с-80-18 (модель), frame_18, fence_norma_18, foundation_s_f_18,
    # install_default, delivery_default, verification_default
    # (OPTION_BLOCKS_ORDER: install → delivery → verification).

    # row 1 = модель: vMerge=restart, value="24"
    text, vm = col2_info(trs[1])
    assert vm == "restart"
    assert text == "24"

    # row 2 = frame, row 3 = fence: vMerge=continue, value=""
    text, vm = col2_info(trs[2])
    assert vm == "continue"
    assert text == ""
    text, vm = col2_info(trs[3])
    assert vm == "continue"
    assert text == ""

    # row 4 = foundation: без vMerge, value="24"
    text, vm = col2_info(trs[4])
    assert vm == "none"
    assert text == "24"

    # row 5 = install: без vMerge, value="4"
    text, vm = col2_info(trs[5])
    assert vm == "none"
    assert text == "4"

    # row 6 = delivery: без vMerge, value="1"
    text, vm = col2_info(trs[6])
    assert vm == "none"
    assert text == "1"

    # row 7 = verification: без vMerge, value="1"
    text, vm = col2_info(trs[7])
    assert vm == "none"
    assert text == "1"

    # Маркеров в спек-таблице нет
    full_text = "".join(
        t.text or "" for t in spec_table._tbl.iter(qn("t"))
    )
    assert "⟦MERGE" not in full_text


def test_generated_docx_no_foundation_term_days(prices):
    """Без фундамента: T_осталось=24 (фиксированные те же 6), весы=24."""
    state = _state(
        total_term_days=30,
        options={
            "frame_18": {
                "enabled": True, "price": 130_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 130_000, "dealer_is_synthetic": False,
                "block": "frames",
            },
            "install_default": {
                "enabled": True, "price": 200_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 200_000, "dealer_is_synthetic": False,
                "block": "install",
            },
            "verification_default": {
                "enabled": True, "price": 30_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 30_000, "dealer_is_synthetic": False,
                "block": "verification",
            },
            "delivery_default": {
                "enabled": True, "price": 70_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 70_000, "dealer_is_synthetic": False,
                "block": "delivery",
            },
        },
    )
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))

    spec_table = None
    for t in doc.tables:
        if t.rows[0].cells[0].text.strip() == "Наименование":
            spec_table = t
            break
    assert spec_table is not None

    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    qn = lambda tag: f"{{{W}}}{tag}"  # noqa: E731

    # Модель в первой content-row → "24"
    trs = spec_table._tbl.findall(qn("tr"))
    tcs = trs[1].findall(qn("tc"))
    text = "".join(t.text or "" for t in tcs[2].iter(qn("t")))
    assert text == "24"


def test_generate_kp_raises_term_too_small(prices):
    """total_term_days=3 при полном наборе → TermDaysTooSmallError из generate_kp."""
    import pytest as _pytest

    from src.term_days import TermDaysTooSmallError

    state = _state(
        total_term_days=3,
        options={
            "install_default": {
                "enabled": True, "price": 200_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 200_000, "dealer_is_synthetic": False,
                "block": "install",
            },
            "verification_default": {
                "enabled": True, "price": 30_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 30_000, "dealer_is_synthetic": False,
                "block": "verification",
            },
            "delivery_default": {
                "enabled": True, "price": 70_000, "qty": 1,
                "customer_side": False, "is_on_request": False,
                "retail": 70_000, "dealer_is_synthetic": False,
                "block": "delivery",
            },
        },
    )
    with _pytest.raises(TermDaysTooSmallError) as exc:
        generate_kp(state, prices)
    d = exc.value.details
    assert d["total"] == 3
    assert d["min"] == 7
    assert d["install"] == 4


def test_validity_paragraph_uses_pt_sans(prices):
    """Параграф «Срок действия КП» использует PT Sans (не Times New Roman) и жирный."""
    state = _state()
    docx = generate_kp(state, prices)
    doc = Document(BytesIO(docx))

    target = None
    for para in doc.paragraphs:
        if "Срок действия настоящего" in para.text:
            target = para
            break

    assert target is not None, "Параграф со сроком действия не найден"

    fonts_found: set[str] = set()
    for run in target.runs:
        rpr = run._r.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
        if rpr is not None:
            rfonts = rpr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts")
            if rfonts is not None:
                W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                for attr in ("ascii", "hAnsi", "cs"):
                    val = rfonts.get(f"{{{W}}}{attr}")
                    if val:
                        fonts_found.add(val)

    assert any("PT Sans" in f for f in fonts_found), (
        f"Ожидался PT Sans в rFonts, найдено: {fonts_found}"
    )
    assert any(run.bold for run in target.runs), (
        "Срок действия КП должен быть жирным"
    )
