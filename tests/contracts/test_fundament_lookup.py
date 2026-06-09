"""Тесты lookup библиотеки фундаментных приложений."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts import fundament_lookup as fl


@pytest.fixture
def fundament_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    build_task = tmp_path / "build_task"
    control_sheet = tmp_path / "control_sheet"
    build_task.mkdir()
    control_sheet.mkdir()
    monkeypatch.setattr(fl, "BUILD_TASK_DIR", build_task)
    monkeypatch.setattr(fl, "CONTROL_SHEET_DIR", control_sheet)
    return build_task, control_sheet


def _snapshot(
    execution: str | None,
    sections: int | None = 3,
    model_code: str | None = "ВЕСТА-С-60-18",
) -> dict:
    return {
        "foundation_execution": execution,
        "foundation_sections": sections,
        "model_code": model_code,
    }


@pytest.mark.parametrize(
    ("line", "expected_family"),
    [
        ("С", "С_Ф"),
        ("Ф", "С_Ф"),
        ("П", "С_Ф"),
        ("СЛ", "СЛ_ФЛ"),
        ("ФЛ", "СЛ_ФЛ"),
    ],
)
def test_resolve_build_task_pandus_family_by_line(
    fundament_dirs: tuple[Path, Path],
    line: str,
    expected_family: str,
) -> None:
    build_task, _ = fundament_dirs
    expected_file = build_task / f"пандусный_{expected_family}_3скц.docx"
    expected_file.touch()

    result = fl.resolve_build_task(_snapshot("пандусный", model_code=f"ВЕСТА-{line}-60-18"))

    assert result.path == expected_file
    assert result.family == expected_family
    assert result.reason == ""


@pytest.mark.parametrize(
    ("execution", "expected_filename"),
    [
        ("приямок", "приямок_3скц.docx"),
        ("rama_concrete", "rama_concrete_3скц.docx"),
        ("rama_road_slabs", "rama_road_slabs_3скц.docx"),
        ("rama_pag_slabs", "rama_pag_slabs_3скц.docx"),
    ],
)
def test_resolve_build_task_all_execution_branches(
    fundament_dirs: tuple[Path, Path],
    execution: str,
    expected_filename: str,
) -> None:
    build_task, _ = fundament_dirs
    expected_file = build_task / expected_filename
    expected_file.touch()

    result = fl.resolve_build_task(_snapshot(execution))

    assert result.path == expected_file
    assert result.filename == expected_filename
    assert result.reason == ""


@pytest.mark.parametrize("execution", ["монолитная_плита", None])
def test_resolve_build_task_valid_without_application(
    fundament_dirs: tuple[Path, Path],
    execution: str | None,
) -> None:
    result = fl.resolve_build_task(_snapshot(execution))

    assert result.path is None
    assert "не подключается" in result.reason


def test_resolve_build_task_requires_sections(fundament_dirs: tuple[Path, Path]) -> None:
    result = fl.resolve_build_task(_snapshot("приямок", sections=None))

    assert result.path is None
    assert "количество секций" in result.reason


def test_resolve_build_task_requires_pandus_family(fundament_dirs: tuple[Path, Path]) -> None:
    result = fl.resolve_build_task(_snapshot("пандусный", model_code="ВЕСТА-X-60-18"))

    assert result.path is None
    assert "семейство" in result.reason


def test_resolve_build_task_missing_file_is_clear(fundament_dirs: tuple[Path, Path]) -> None:
    result = fl.resolve_build_task(_snapshot("rama_concrete", sections=4))

    assert result.path is None
    assert result.filename == "rama_concrete_4скц.docx"
    assert "не найден" in result.reason


def test_resolve_build_task_unknown_execution(fundament_dirs: tuple[Path, Path]) -> None:
    result = fl.resolve_build_task(_snapshot("неизвестно"))

    assert result.path is None
    assert "Неизвестный тип" in result.reason


@pytest.mark.parametrize(
    ("execution", "sections", "filename"),
    [
        ("пандусный", 2, "control_sheet_пандусный_2скц.docx"),
        ("приямок", 3, "control_sheet_приямок_3скц.docx"),
    ],
)
def test_resolve_control_sheet_available(
    fundament_dirs: tuple[Path, Path],
    execution: str,
    sections: int,
    filename: str,
) -> None:
    _, control_sheet = fundament_dirs
    expected_file = control_sheet / filename
    expected_file.touch()

    assert fl.resolve_control_sheet(execution, sections) == expected_file


@pytest.mark.parametrize(
    ("execution", "sections"),
    [
        ("приямок", 2),
        ("rama_concrete", 3),
        ("пандусный", None),
        (None, 3),
    ],
)
def test_resolve_control_sheet_unavailable(
    fundament_dirs: tuple[Path, Path],
    execution: str | None,
    sections: int | None,
) -> None:
    assert fl.resolve_control_sheet(execution, sections) is None
