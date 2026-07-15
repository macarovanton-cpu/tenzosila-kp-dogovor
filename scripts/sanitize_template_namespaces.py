"""Лечит ns0-порчу префиксов namespace в word/document.xml DOCX-шаблонов.

Причина порчи: скрипты на xml.etree.ElementTree теряют исходные префиксы при
tostring() и переобъявляют их как ns0/ns1/... При этом mc:Ignorable продолжает
ссылаться на пропавшие префиксы (w14, wp14, ...) — файл формально валиден как
XML, но Word видит необъявленные префиксы в Ignorable.

Лечение: пересобрать корень с каноническим nsmap (URI → исходный префикс),
перенести детей без изменений. Структура и текст обязаны совпасть — ассерты
внутри это проверяют.

Запуск: python scripts/sanitize_template_namespaces.py
"""
from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
DOC_PART = "word/document.xml"

# Здоровые git-версии — источник канонических префиксов.
HEALTHY_SOURCE: dict[str, str] = {
    "templates/contracts/spec_v2.docx": "8795cca",
    "templates/contracts/contract.docx": "0e16119",
}

# Резерв: URI, которого нет в здоровом nsmap (мог прийти с более поздних правок).
STANDARD_PREFIXES: dict[str, str] = {
    W_NS: "w",
    MC_NS: "mc",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships": "r",
    "http://schemas.openxmlformats.org/officeDocument/2006/math": "m",
    "http://schemas.openxmlformats.org/drawingml/2006/main": "a",
    "http://schemas.openxmlformats.org/drawingml/2006/picture": "pic",
    "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing": "wp",
    "http://schemas.microsoft.com/office/word/2010/wordml": "w14",
    "http://schemas.microsoft.com/office/word/2012/wordml": "w15",
    "http://schemas.microsoft.com/office/word/2018/wordml": "w16",
    "http://schemas.microsoft.com/office/word/2015/wordml/symex": "w16se",
    "http://schemas.microsoft.com/office/word/2016/wordml/cid": "w16cid",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing": "wp14",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingShape": "wps",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup": "wpg",
    "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas": "wpc",
    "urn:schemas-microsoft-com:office:office": "o",
    "urn:schemas-microsoft-com:vml": "v",
    "urn:schemas-microsoft-com:office:word": "w10",
    "http://www.w3.org/XML/1998/namespace": "xml",
}


def _healthy_nsmap(path: str) -> dict[str, str]:
    """Префикс → URI из здоровой git-версии шаблона."""
    sha = HEALTHY_SOURCE.get(path)
    if sha is None:
        return {}
    blob = subprocess.run(
        ["git", "show", f"{sha}:{path}"], capture_output=True, check=True
    ).stdout
    tmp = Path(".sanitize_healthy.tmp")
    tmp.write_bytes(blob)
    try:
        with zipfile.ZipFile(tmp) as z:
            root = etree.fromstring(z.read(DOC_PART))
    finally:
        tmp.unlink()
    return {prefix: uri for prefix, uri in root.nsmap.items() if prefix}


def _canonical_prefix(uri: str, healthy: dict[str, str]) -> str:
    """Префикс для URI, уцелевшего в испорченном файле."""
    by_uri = {v: k for k, v in healthy.items()}
    prefix = by_uri.get(uri) or STANDARD_PREFIXES.get(uri)
    if prefix is None:
        raise SystemExit(
            f"STOP: URI {uri!r} не найден ни в здоровом nsmap, ни в таблице "
            f"стандартных OOXML-префиксов. Добавь его в STANDARD_PREFIXES."
        )
    return prefix


def _uri_for_prefix(prefix: str, healthy: dict[str, str]) -> str:
    """URI для префикса из mc:Ignorable, чьё объявление ET выбросил целиком."""
    by_prefix = {v: k for k, v in STANDARD_PREFIXES.items()}
    uri = healthy.get(prefix) or by_prefix.get(prefix)
    if uri is None:
        raise SystemExit(
            f"STOP: префикс {prefix!r} из mc:Ignorable не найден ни в здоровом "
            f"nsmap, ни в таблице стандартных OOXML-префиксов. "
            f"Добавь его в STANDARD_PREFIXES."
        )
    return uri


def _text_of(root: etree._Element) -> str:
    return "".join(node.text or "" for node in root.iter(f"{{{W_NS}}}t"))


def _counts(root: etree._Element) -> tuple[int, int, int]:
    """(детей корня, w:p, строк таблиц) — структурный отпечаток."""
    return (
        len(root),
        len(root.findall(f".//{{{W_NS}}}p")),
        len(root.findall(f".//{{{W_NS}}}tr")),
    )


def sanitize_xml(xml_bytes: bytes, healthy: dict[str, str]) -> bytes | None:
    """None — если файл уже здоров (идемпотентность)."""
    old = etree.fromstring(xml_bytes)
    if old.prefix == "w":
        return None

    # Отпечаток снимаем до extend — lxml переносит детей, старый корень пустеет.
    old_text, old_counts = _text_of(old), _counts(old)

    nsmap = {_canonical_prefix(uri, healthy): uri for uri in old.nsmap.values()}
    # Префиксы из mc:Ignorable, чьи объявления ET выбросил как «неиспользуемые».
    ignorable = old.get(f"{{{MC_NS}}}Ignorable", "")
    for prefix in ignorable.split():
        nsmap.setdefault(prefix, _uri_for_prefix(prefix, healthy))

    new = etree.Element(old.tag, nsmap=nsmap)
    new.attrib.update(old.attrib)
    new.extend(old)

    assert _text_of(new) == old_text, "текст изменился при пересборке"
    assert _counts(new) == old_counts, f"структура поплыла: {_counts(new)} != {old_counts}"

    ignorable = new.get(f"{{{MC_NS}}}Ignorable", "")
    undeclared = [p for p in ignorable.split() if p not in nsmap]
    assert not undeclared, f"mc:Ignorable ссылается на необъявленные префиксы: {undeclared}"

    return etree.tostring(
        new, encoding="UTF-8", xml_declaration=True, standalone=True
    )


def sanitize_docx(path: Path) -> bool:
    """True — файл вылечен, False — уже был здоров."""
    healthy = _healthy_nsmap(path.as_posix())
    with zipfile.ZipFile(path) as z:
        items = z.infolist()
        payload = {item.filename: z.read(item.filename) for item in items}

    fixed = sanitize_xml(payload[DOC_PART], healthy)
    if fixed is None:
        return False
    payload[DOC_PART] = fixed

    tmp = path.with_suffix(".sanitized.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in items:
            zout.writestr(item, payload[item.filename])
    shutil.move(tmp, path)
    return True


def main() -> None:
    for name in HEALTHY_SOURCE:
        path = Path(name)
        changed = sanitize_docx(path)
        print(f"{name}: {'вылечен' if changed else 'уже здоров (no-op)'}")
        # Идемпотентность: повторный прогон обязан быть no-op.
        assert not sanitize_docx(path), f"{name}: повторный прогон не no-op"


if __name__ == "__main__":
    main()
