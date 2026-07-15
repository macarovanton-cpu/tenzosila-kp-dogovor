"""Страж: ns0-порча / необъявленный mc:Ignorable в DOCX-шаблонах (A11).

Порча ломает открытие в Word, но XML остаётся валидным — сеть её не видела
месяц. Охват — только git-tracked шаблоны: клиенту уезжает то, что в репо.
"""
from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

from scripts.sanitize_template_namespaces import DOC_PART, is_document_xml_healthy

REPO_ROOT = Path(__file__).resolve().parents[1]


def _tracked_templates() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "templates/**/*.docx"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out.split()


@pytest.mark.parametrize("name", _tracked_templates())
def test_template_document_xml_healthy(name: str) -> None:
    with zipfile.ZipFile(REPO_ROOT / name) as z:
        ok, reason = is_document_xml_healthy(z.read(DOC_PART))
    assert ok, f"{name}: {reason}"
