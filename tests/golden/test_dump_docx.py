"""Тесты дампа DOCX: шапка стилей + интеграция на реальных файлах (P0-01)."""

from __future__ import annotations

from pathlib import Path

import pytest

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from tests.golden.dump_docx import dump_docx
from tests.golden.dump_styles import build_style_names, used_style_lines

_W = nsdecls("w")


# ── Шапка стилей ─────────────────────────────────────────────────────────

_STYLES_XML = (
    f"<w:styles {_W}>"
    '<w:style w:type="paragraph" w:styleId="Base">'
    '<w:name w:val="Обычный"/><w:rPr><w:sz w:val="24"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="Child">'
    '<w:name w:val="Текст договора"/><w:basedOn w:val="Base"/>'
    "<w:pPr><w:jc w:val='both'/></w:pPr></w:style>"
    '<w:style w:type="paragraph" w:styleId="Unused">'
    '<w:name w:val="Неиспользуемый"/></w:style>'
    "</w:styles>"
)


def test_style_names_map():
    names = build_style_names(parse_xml(_STYLES_XML))
    assert names == {"Base": "Обычный", "Child": "Текст договора", "Unused": "Неиспользуемый"}


def test_used_styles_include_based_on_parents():
    """[STYLE] включает basedOn-родителей: регресс в родителе виден в шапке."""
    styles_el = parse_xml(_STYLES_XML)
    names = build_style_names(styles_el)
    lines = used_style_lines(styles_el, {"Child"}, names, {})
    assert lines == [
        "[STYLE] 'Обычный' pPr{} rPr{sz=12}",
        "[STYLE] 'Текст договора' based='Обычный' pPr{jc=both} rPr{}",
    ]


# ── Интеграция: реальные сгенерированные DOCX (output/ не в git) ─────────

_ROOT = Path(__file__).resolve().parents[2]
_SMOKE_KP = _ROOT / "output" / "КП_тест_gipsobeton.docx"
_SMOKE_SPEC = _ROOT / "output" / "contracts" / "Спецификация_31_2026_ООО «Автобан-Эксплуатация».docx"
_SMOKE_SUPPLY = _ROOT / "output" / "contracts" / "Договор_поставки_21_2026_ООО _Завод деталей_.docx"

_SMOKE_FILES = [
    pytest.param(p, id=p.stem[:30])
    for p in (_SMOKE_KP, _SMOKE_SPEC, _SMOKE_SUPPLY)
]

# кэш дампов: стабильность и так требует двух прогонов на файл,
# контент-тесты переиспользуют второй, не дампя третий раз
_DUMPS: dict[Path, str] = {}


def _cached_dump(path: Path) -> str:
    if path not in _DUMPS:
        _DUMPS[path] = dump_docx(path)
    return _DUMPS[path]


@pytest.mark.parametrize("path", _SMOKE_FILES)
def test_dump_stable_and_nonempty(path: Path):
    """L1-стабильность: два прогона на одном DOCX -> байт-в-байт идентично."""
    if not path.exists():
        pytest.skip(f"смоук-файл отсутствует (output/ не в git): {path.name}")
    first = dump_docx(path)
    second = dump_docx(path)
    _DUMPS[path] = second
    assert first == second
    assert first.startswith("=== DOCX-DUMP v1 ===\n")
    assert len(first.splitlines()) > 100
    assert first.endswith("\n") and "\r" not in first


@pytest.mark.skipif(not _SMOKE_SPEC.exists(), reason="output/ не в git")
def test_spec_dump_captures_key_content():
    """Спецификация spec_v2: таблица, textbox подписи, docDefaults в шапке."""
    text = _cached_dump(_SMOKE_SPEC)
    assert "[DEFAULTS] rPr{font=Times New Roman}" in text
    assert "TBL{" in text and "ИТОГО" in text
    assert "TXBX" in text  # подписной блок — python-docx API его не видит
    assert "=== HEADER default (sect 1) ===" in text
    assert "[FIELD 'PAGE" in text  # нумерация страниц в footer


@pytest.mark.skipif(not _SMOKE_SUPPLY.exists(), reason="output/ не в git")
def test_supply_dump_captures_compose_order():
    """Договор поставки (docxcompose ×3): следы склейки и колонтитул с номером."""
    text = _cached_dump(_SMOKE_SUPPLY)
    # порядок склейки: pageBreakBefore приложений + явные разрывы страниц
    assert text.count(";pgbrk}") + text.count("{pgbrk}") >= 2
    assert text.count("[PAGEBREAK]") >= 1
    hdr = text.split("=== HEADER", 1)[1]
    assert "Договор поставки" in hdr  # {{ДОГОВОР_НОМЕР}} заполнен в header
    # footer у склеенного supply пуст (поля PAGE нет) — это факт документа,
    # секция FOOTER в дампе присутствует
    assert "=== FOOTER default (sect 1) ===" in text


@pytest.mark.skipif(not _SMOKE_KP.exists(), reason="output/ не в git")
def test_kp_dump_captures_header_textbox_and_sections():
    """КП: textbox с реквизитами в колонтитуле + разрыв секции посреди документа."""
    text = _cached_dump(_SMOKE_KP)
    hdr = text.split("=== HEADER", 1)[1]
    assert "TXBX" in hdr and "ИНН" in hdr
    assert text.count("SECT{") >= 2  # sectPr в pPr + финальный
    assert "[MEDIA] word/media/" in text
