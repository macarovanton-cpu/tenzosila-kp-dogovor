#!/usr/bin/env python
"""
make_template.py — собирает kp_template.docx из эталонного КП Гипсобетон.

Идемпотентен: при повторном запуске перезаписывает templates/kp_template.docx
с тем же результатом.

Запуск:
    python src/generators/make_template.py
"""
import copy
import os
from lxml import etree
from docx import Document

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
SRC  = os.path.join(BASE, "03_knowledge_base/sample_kps/Гипсобетон_ВЕСТА-С-80-18.docx")
DST  = os.path.join(BASE, "templates/kp_template.docx")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

def qn(tag):
    return f"{{{W}}}{tag}"


# ---------------------------------------------------------------------------
# Run helpers
# ---------------------------------------------------------------------------

def get_para_text(para):
    return "".join(r.text or "" for r in para.runs)


def merge_runs(para):
    """Merge all runs in paragraph into the first; keep first run's formatting."""
    runs = para.runs
    if len(runs) <= 1:
        return
    full = "".join(r.text or "" for r in runs)
    runs[0].text = full
    for run in runs[1:]:
        run._r.getparent().remove(run._r)


def set_para_text(para, text):
    """Merge runs, then set text of the single remaining run."""
    merge_runs(para)
    if para.runs:
        para.runs[0].text = text
    else:
        from docx.oxml import OxmlElement
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = text
        r.append(t)
        para._p.append(r)


# ---------------------------------------------------------------------------
# Footer placeholders (manager_*)
# ---------------------------------------------------------------------------

def _replace_chunk_text(chunk: list, new_text: str) -> None:
    """Сжать список runs в первый, заменить текст, удалить остальные."""
    if not chunk:
        return
    chunk[0].text = new_text
    for r in chunk[1:]:
        r._r.getparent().remove(r._r)


def _split_runs_by_breaks(para) -> list[list]:
    """Разбить runs параграфа на чанки по соседним '\\n'-runs (line breaks)."""
    chunks: list[list] = [[]]
    for r in para.runs:
        # python-docx возвращает '\n' для <w:br/> элементов
        if r.text == "\n":
            chunks.append([])
        else:
            chunks[-1].append(r)
    return [c for c in chunks if c]


def replace_footer_placeholders(doc) -> None:
    """Заменить статические данные менеджера в колонтитуле на плейсхолдеры.

    В эталонном Гипсобетон-КП футер представлен таблицей: cell[0] содержит
    'Макаров Антон\\nМенеджер', cell[1] — телефон\\nemail. Между строками —
    line break (<w:br/>), который python-docx показывает как run.text == '\\n'.
    Заменяем чанки между линейными разрывами, line break'ы сохраняем.
    """
    line_replacements = {
        "Макаров Антон": "{{ manager_full_name }}",
        "+7 903 651-85-77": "{{ manager_phone }}",
        "a.makarov@tenzosila.ru": "{{ manager_email }}",
    }

    for section in doc.sections:
        footer = section.footer
        if footer is None:
            continue
        # Параграфы напрямую в footer
        for para in footer.paragraphs:
            _apply_chunk_replacements(para, line_replacements)
        # Таблицы в footer
        for table in footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        _apply_chunk_replacements(para, line_replacements)


def _apply_chunk_replacements(para, line_replacements: dict[str, str]) -> None:
    """Найти чанки runs (между line break'ами), сопоставить с line_replacements
    и заменить текст на плейсхолдер."""
    chunks = _split_runs_by_breaks(para)
    if not chunks:
        return
    for chunk in chunks:
        full = "".join(r.text or "" for r in chunk)
        if not full:
            continue
        for old, placeholder in line_replacements.items():
            if old in full:
                _replace_chunk_text(chunk, full.replace(old, placeholder))
                break


# ---------------------------------------------------------------------------
# ОРИОН block removal
# ---------------------------------------------------------------------------

def remove_orion_block(doc):
    """
    Удаляет блок 'Спецификация ПАК ОРИОН' (заголовок + таблица + сноска).
    Сохраняет заголовок 'Конструкция весов ВЕСТА' и всё после него.
    """
    body = doc.element.body
    children = list(body)

    start_idx = None
    end_idx   = None

    for i, elem in enumerate(children):
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag not in ("p", "tbl"):
            continue
        text = "".join(t.text or "" for t in elem.findall(f".//{qn('t')}"))

        if start_idx is None and "Спецификация ПАК ОРИОН" in text:
            start_idx = i

        if start_idx is not None and "* Цены и сроки подлежат уточнению" in text:
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        print(f"WARNING: ОРИОН-блок не найден (start={start_idx}, end={end_idx})")
        return

    to_remove = children[start_idx : end_idx + 1]
    for elem in to_remove:
        body.remove(elem)
    print(f"  Удалено {len(to_remove)} элементов (блок ОРИОН)")


# ---------------------------------------------------------------------------
# Spec table → jinja loop
# ---------------------------------------------------------------------------

def _set_tc_text(tc, text):
    """Установить текст первой ячейки <w:tc> на уровне XML."""
    from docx.oxml import OxmlElement
    ps = tc.findall(f'.//{qn("p")}')
    if not ps:
        return
    p = ps[0]
    for r in list(p.findall(qn("r"))):
        p.remove(r)
    r_el = OxmlElement('w:r')
    t_el = OxmlElement('w:t')
    t_el.text = text
    r_el.append(t_el)
    p.append(r_el)


def transform_spec_table(doc):
    """Заменяет 6 фиксированных строк спецификации на jinja-цикл {%tr%}.

    Итоговая структура таблицы в шаблоне:
      row 0: заголовок (header)
      row 1: {%tr for item in spec_items %}  ← маркер начала (удаляется при рендере)
      row 2: {{ item.name }} | {{ item.price }} | {{ item.term_days }}  ← шаблон (повторяется)
      row 3: {%tr endfor %}                  ← маркер конца (удаляется при рендере)
      row 4: ИТОГО | {{ total_price }}        ← статическая строка

    При рендере с N позициями → header + N строк + ИТОГО = N+2 строк.
    """
    from docx.oxml import OxmlElement

    spec_table = None
    for table in doc.tables:
        if table.rows and table.rows[0].cells:
            header_text = "".join(
                get_para_text(p) for p in table.rows[0].cells[0].paragraphs
            ).strip()
            if header_text == "Наименование":
                spec_table = table
                break
    if spec_table is None:
        raise RuntimeError("Таблица спецификации (заголовок 'Наименование') не найдена")

    # Клонируем row 1 ДО изменений — будет шаблоном контента
    content_tr = copy.deepcopy(spec_table.rows[1]._tr)

    # row 1 → маркер {%tr for %}: первая ячейка = тег, остальные — пусто
    for_row = spec_table.rows[1]
    tcs_for = for_row._tr.findall(qn("tc"))
    for i, tc in enumerate(tcs_for):
        _set_tc_text(tc, '{%tr for item in spec_items %}' if i == 0 else '')

    # content_tr → шаблон повторяемой строки
    tcs_content = content_tr.findall(qn("tc"))
    if len(tcs_content) >= 3:
        _set_tc_text(tcs_content[0], '{{ item.name }}')
        _set_tc_text(tcs_content[1], '{{ item.price }}')
        _set_tc_text(tcs_content[2], '{{ item.term_days }}')

    # endfor_tr → маркер {%tr endfor %}
    endfor_tr = copy.deepcopy(content_tr)
    for tc in endfor_tr.findall(qn("tc")):
        _set_tc_text(tc, '')
    endfor_tcs = endfor_tr.findall(qn("tc"))
    if endfor_tcs:
        _set_tc_text(endfor_tcs[0], '{%tr endfor %}')

    # Удаляем строки 2–6 (лишние позиции), строку 7 (ИТОГО) сохраняем
    rows_to_delete = list(spec_table.rows[2:7])
    for row in reversed(rows_to_delete):
        row._tr.getparent().remove(row._tr)
    # После удаления: rows[0]=header, rows[1]=for-marker, rows[2]=ИТОГО

    # Вставляем content_tr и endfor_tr перед ИТОГО
    itogo_row = spec_table.rows[2]
    itogo_row._tr.addprevious(endfor_tr)
    endfor_tr.addprevious(content_tr)
    # Итог: header | for-marker | content | endfor | ИТОГО

    print("  Таблица спецификации: transform OK (for-marker + content + endfor + ИТОГО)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def make_template():
    print(f"Источник : {SRC}")
    print(f"Шаблон   : {DST}")

    doc = Document(SRC)

    # -----------------------------------------------------------------------
    # 1. ШАПКА — body paragraphs
    # -----------------------------------------------------------------------
    for para in doc.paragraphs:
        full = get_para_text(para)

        # client_name
        if "АО Гипсобетон" in full:
            merge_runs(para)
            para.runs[0].text = full.replace("АО Гипсобетон", "{{ client_name }}")

        # kp_number + kp_date (в одном абзаце)
        elif "Коммерческое предложение № 47141" in full:
            merge_runs(para)
            new = (get_para_text(para)
                   .replace("47141",      "{{ kp_number }}")
                   .replace("22.04.2026", "{{ kp_date }}"))
            para.runs[0].text = new

        # vat_percent (body paragraph, not table)
        elif "НДС 22%" in full:
            merge_runs(para)
            para.runs[0].text = get_para_text(para).replace("22%", "{{ vat_percent }}%")

        # payment_terms_block (заменяет payment_line_1 в эталоне) — RichText с многострочным
        # содержимым, абзацные переносы добавляет docxtpl при рендере.
        elif full.startswith("Предоплата:"):
            merge_runs(para)
            para.runs[0].text = "{{ payment_terms_block }}"

        # kp_valid_days — переиспользуем абзац "Доплата:" под строку срока действия КП.
        elif full.startswith("Доплата:"):
            merge_runs(para)
            para.runs[0].text = (
                "Срок действия настоящего коммерческого предложения — "
                "{{ kp_valid_days }}."
            )

    # -----------------------------------------------------------------------
    # 2. ТАБЛИЦЫ
    # -----------------------------------------------------------------------
    for table in doc.tables:
        for row in table.rows:
            cells = row.cells
            if not cells:
                continue

            # Текст первой ячейки строки — для контекстного матчинга
            first_cell_text = "".join(
                get_para_text(p) for p in cells[0].paragraphs
            ).strip()

            for ci, cell in enumerate(cells):
                paras     = cell.paragraphs
                cell_text = "".join(get_para_text(p) for p in paras).strip()

                # --- warranty_text ---
                if cell_text == "36 месяца":
                    set_para_text(paras[0], "{{ warranty_text }}")

                # --- platform_size ---
                elif cell_text == "18×3":
                    set_para_text(paras[0], "{{ platform_size }}")

                # --- construction_description ---
                elif cell_text.startswith("Конструкция сплошная 09Г2С"):
                    set_para_text(paras[0], "{{ construction_description }}")


                # --- vat_percent ---
                elif "НДС 22%" in cell_text:
                    merge_runs(paras[0])
                    if paras[0].runs:
                        paras[0].runs[0].text = get_para_text(paras[0]).replace(
                            "22%", "{{ vat_percent }}%"
                        )

            # --- division_info (описание весов в таблице ТХ — пустая ячейка ЗНАЧЕНИЕ) ---
            if "Описание весов" in first_cell_text and len(cells) >= 3:
                set_para_text(cells[2].paragraphs[0], "{{ division_info }}")

            # --- max_load_t (контекстный матч по первой ячейке) ---
            if "Максимальная нагрузка" in first_cell_text and len(cells) >= 2:
                set_para_text(cells[1].paragraphs[0], "{{ max_load_t }}")

            # --- main_scale_label (цена поверочного деления — split runs) ---
            if "Цена поверочного деления" in first_cell_text and len(cells) >= 2:
                val_paras = cells[1].paragraphs
                for p in val_paras:
                    merge_runs(p)
                # Схлопываем все параграфы ячейки в один
                if len(val_paras) > 1:
                    combined = "".join(get_para_text(p) for p in val_paras)
                    set_para_text(val_paras[0], combined)
                    for p in val_paras[1:]:
                        p._p.getparent().remove(p._p)
                set_para_text(cells[1].paragraphs[0], "{{ main_scale_label }}")

            # --- total_price + total_term_days (ИТОГО — split runs) ---
            if first_cell_text == "ИТОГО" and len(cells) >= 2:
                val_paras = cells[1].paragraphs
                for p in val_paras:
                    merge_runs(p)
                set_para_text(val_paras[0], "{{ total_price }}")
            if first_cell_text == "ИТОГО" and len(cells) >= 3:
                term_paras = cells[2].paragraphs
                for p in term_paras:
                    merge_runs(p)
                set_para_text(term_paras[0], "{{ total_term_days }}")

    # -----------------------------------------------------------------------
    # 3. Таблица спецификации → jinja-цикл
    # -----------------------------------------------------------------------
    transform_spec_table(doc)

    # -----------------------------------------------------------------------
    # 4. Удаляем блок ОРИОН
    # -----------------------------------------------------------------------
    remove_orion_block(doc)

    # -----------------------------------------------------------------------
    # 4b. Подставляем плейсхолдеры менеджера в колонтитул
    # -----------------------------------------------------------------------
    replace_footer_placeholders(doc)

    # -----------------------------------------------------------------------
    # 5. Сохраняем
    # -----------------------------------------------------------------------
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    doc.save(DST)
    print(f"  Шаблон сохранён: {DST}")

    # -----------------------------------------------------------------------
    # 6. Sanity-check: 16 статических + 3 loop-плейсхолдера
    # -----------------------------------------------------------------------
    import re, zipfile
    expected_static_body = {
        "client_name", "kp_number", "kp_date", "kp_valid_days",
        "warranty_text", "division_info", "platform_size", "max_load_t",
        "construction_description", "main_scale_label",
        "total_price", "total_term_days", "vat_percent",
        "payment_terms_block",
    }
    expected_static_footer = {
        "manager_full_name", "manager_phone", "manager_email",
    }
    expected_static = expected_static_body | expected_static_footer
    saved = Document(DST)
    body_text = " ".join(
        "".join(r.text or "" for r in p.runs)
        for p in saved.paragraphs
    )
    for table in saved.tables:
        for row in table.rows:
            for cell in row.cells:
                body_text += " " + "".join(
                    "".join(r.text or "" for r in p.runs)
                    for p in cell.paragraphs
                )
    footer_text = ""
    for section in saved.sections:
        footer = section.footer
        if footer is None:
            continue
        for p in footer.paragraphs:
            footer_text += " " + "".join(r.text or "" for r in p.runs)
        for table in footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        footer_text += " " + "".join(r.text or "" for r in p.runs)

    all_text = body_text + " " + footer_text
    found_static = set(re.findall(r"\{\{\s*(\w+)\s*\}\}", all_text))
    problems = []
    missing_static = expected_static - found_static
    if missing_static:
        problems.append(f"Отсутствуют статические плейсхолдеры: {sorted(missing_static)}")
    for loop_str in ("{{ item.name }}", "{{ item.price }}", "{{ item.term_days }}"):
        if loop_str not in all_text:
            problems.append(f"Отсутствует loop-плейсхолдер: {loop_str}")
    with zipfile.ZipFile(DST) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    if "{%tr for" not in xml:
        problems.append("{%tr for} не найден в XML")
    if "{%tr endfor" not in xml:
        problems.append("{%tr endfor} не найден в XML")
    if problems:
        raise RuntimeError("Sanity-check FAILED:\n" + "\n".join(f"  - {p}" for p in problems))
    n_static = len(expected_static)
    print(f"  Проверка: {n_static} статических + 3 loop-плейсхолдера на месте [OK]")


if __name__ == "__main__":
    make_template()
