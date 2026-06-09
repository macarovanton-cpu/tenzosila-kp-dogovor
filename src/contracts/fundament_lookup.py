"""Lookup приложений строительного задания и контрольного листа."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


FUNDAMENT_ROOT = Path("data/fundament")
BUILD_TASK_DIR = FUNDAMENT_ROOT / "build_task"
CONTROL_SHEET_DIR = FUNDAMENT_ROOT / "control_sheet"

_PANDUS_EXECUTION = "пандусный"
_PIT_EXECUTION = "приямок"
_MONOLITH_EXECUTION = "монолитная_плита"
_RAMA_EXECUTIONS = {
    "rama_concrete",
    "rama_road_slabs",
    "rama_pag_slabs",
}
_NO_BUILD_TASK_EXECUTIONS = {_MONOLITH_EXECUTION, None}
_CONTROL_SHEET_EXECUTIONS = {_PANDUS_EXECUTION, _PIT_EXECUTION}
_FAMILY_BY_LINE = {
    "С": "С_Ф",
    "Ф": "С_Ф",
    "П": "С_Ф",
    "СЛ": "СЛ_ФЛ",
    "ФЛ": "СЛ_ФЛ",
}


@dataclass(frozen=True)
class BuildTaskResolution:
    """Результат автоподбора строительного задания."""

    path: Path | None
    reason: str
    execution: str | None
    sections: int | None
    family: str | None = None
    filename: str | None = None


def list_build_task_files() -> list[Path]:
    """Вернуть DOCX из библиотеки строительных заданий."""
    return _list_docx(BUILD_TASK_DIR)


def list_control_sheet_files() -> list[Path]:
    """Вернуть DOCX из библиотеки контрольных листов."""
    return _list_docx(CONTROL_SHEET_DIR)


def resolve_build_task(snapshot: Mapping[str, Any]) -> BuildTaskResolution:
    """Подобрать строительное задание из snapshot КП."""
    execution = _normalize_execution(snapshot.get("foundation_execution"))
    sections = _normalize_sections(snapshot.get("foundation_sections"))
    model_code = str(snapshot.get("model_code") or "").strip()

    if execution in _NO_BUILD_TASK_EXECUTIONS:
        return BuildTaskResolution(
            path=None,
            reason=_no_build_task_reason(execution),
            execution=execution,
            sections=sections,
        )

    if execution not in {_PANDUS_EXECUTION, _PIT_EXECUTION, *_RAMA_EXECUTIONS}:
        return BuildTaskResolution(
            path=None,
            reason=f"Неизвестный тип фундамента: {execution or 'не указан'}",
            execution=execution,
            sections=sections,
        )

    if sections not in (2, 3, 4):
        return BuildTaskResolution(
            path=None,
            reason="Не указано количество секций 2/3/4 для строительного задания",
            execution=execution,
            sections=sections,
        )

    family = None
    if execution == _PANDUS_EXECUTION:
        line = _line_from_model_code(model_code)
        family = _FAMILY_BY_LINE.get(line or "")
        if family is None:
            return BuildTaskResolution(
                path=None,
                reason=f"Не удалось определить семейство С/Ф или СЛ/ФЛ из model_code: {model_code or 'пусто'}",
                execution=execution,
                sections=sections,
            )
        filename = f"{execution}_{family}_{sections}скц.docx"
    elif execution == _PIT_EXECUTION:
        filename = f"{execution}_{sections}скц.docx"
    else:
        filename = f"{execution}_{sections}скц.docx"

    path = BUILD_TASK_DIR / filename
    if not path.exists():
        return BuildTaskResolution(
            path=None,
            reason=f"Файл строительного задания не найден: {path}",
            execution=execution,
            sections=sections,
            family=family,
            filename=filename,
        )

    return BuildTaskResolution(
        path=path,
        reason="",
        execution=execution,
        sections=sections,
        family=family,
        filename=filename,
    )


def resolve_control_sheet(execution: str | None, sections: int | str | None) -> Path | None:
    """Подобрать контрольный лист, если он доступен для ручного выбора."""
    normalized_execution = _normalize_execution(execution)
    normalized_sections = _normalize_sections(sections)
    if (
        normalized_execution not in _CONTROL_SHEET_EXECUTIONS
        or normalized_sections not in (2, 3, 4)
    ):
        return None

    path = CONTROL_SHEET_DIR / (
        f"control_sheet_{normalized_execution}_{normalized_sections}скц.docx"
    )
    return path if path.exists() else None


def _list_docx(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("*.docx"), key=lambda p: p.name.casefold())


def _normalize_execution(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_sections(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _line_from_model_code(model_code: str) -> str | None:
    parts = model_code.split("-")
    if len(parts) < 2:
        return None
    return parts[1].strip() or None


def _no_build_task_reason(execution: str | None) -> str:
    if execution == _MONOLITH_EXECUTION:
        return "Монолитная плита: приложение не подключается, менеджер делает вручную"
    return "Фундамент не выбран: приложение не подключается"
