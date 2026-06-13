"""Replace customer full-name placeholders with short-name placeholders in DOCX templates."""
from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


OLD = "{{ЗАКАЗЧИК_ПОЛНОЕ_НАИМЕНОВАНИЕ}}"
NEW = "{{ЗАКАЗЧИК_КРАТКОЕ_НАИМЕНОВАНИЕ}}"
TEMPLATES = [
    Path("templates/contracts/contract.docx"),
    Path("templates/contracts/spec_v2.docx"),
]
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")


def _set_text(node: ET.Element, value: str) -> None:
    node.text = value
    if value.startswith(" ") or value.endswith(" "):
        node.set(XML_SPACE, "preserve")


def _replace_in_scope(scope: ET.Element) -> int:
    """Replace OLD with NEW across all w:t nodes inside one XML scope."""
    replacements = 0

    while True:
        text_nodes = list(scope.findall(f".//{W_NS}t"))
        texts = [node.text or "" for node in text_nodes]
        combined = "".join(texts)
        start = combined.find(OLD)
        if start < 0:
            return replacements

        end = start + len(OLD)
        char_map: list[tuple[int, int]] = []
        for node_index, text in enumerate(texts):
            char_map.extend((node_index, offset) for offset in range(len(text)))

        start_node_index, start_offset = char_map[start]
        end_node_index, end_offset = char_map[end - 1]
        start_node = text_nodes[start_node_index]
        end_node = text_nodes[end_node_index]

        if start_node_index == end_node_index:
            original = start_node.text or ""
            replaced = original[:start_offset] + NEW + original[end_offset + 1 :]
            _set_text(start_node, replaced)
        else:
            start_original = start_node.text or ""
            end_original = end_node.text or ""
            _set_text(start_node, start_original[:start_offset] + NEW)
            for node in text_nodes[start_node_index + 1 : end_node_index]:
                _set_text(node, "")
            _set_text(end_node, end_original[end_offset + 1 :])

        replacements += 1


def _patch_xml(xml_bytes: bytes) -> tuple[bytes, int]:
    root = ET.fromstring(xml_bytes)
    replacements = 0
    for para in root.findall(f".//{W_NS}p"):
        replacements += _replace_in_scope(para)
    if replacements == 0:
        return xml_bytes, 0
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), replacements


def patch_docx(path: Path) -> int:
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=".docx",
    )
    tmp_path = Path(tmp.name)
    tmp.close()

    total = 0
    with zipfile.ZipFile(path, "r") as zin, zipfile.ZipFile(
        tmp_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                try:
                    data, count = _patch_xml(data)
                except ET.ParseError:
                    count = 0
                total += count
            zout.writestr(item, data)

    tmp_path.replace(path)
    return total


def placeholders_in_docx(path: Path) -> list[str]:
    found: list[str] = []
    with zipfile.ZipFile(path, "r") as z:
        for name in z.namelist():
            if not (name.startswith("word/") and name.endswith(".xml")):
                continue
            try:
                root = ET.fromstring(z.read(name))
            except ET.ParseError:
                continue
            for para in root.findall(f".//{W_NS}p"):
                text = "".join(
                    node.text or "" for node in para.findall(f".//{W_NS}t")
                )
                found.extend(PLACEHOLDER_RE.findall(text))
    return sorted(set(found))


def main() -> None:
    for template in TEMPLATES:
        count = patch_docx(template)
        placeholders = placeholders_in_docx(template)
        print(f"{template}: replaced {count}")
        print("placeholders:")
        for placeholder in placeholders:
            print(f"  {placeholder}")


if __name__ == "__main__":
    main()
