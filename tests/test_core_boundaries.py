"""Стражи границ core/ (docs/MIGRATION_PLAN.md §1 G0, MIGRATION_PLAN_DELTA.md Д-2)."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "core"

# Модульные пакеты, которым запрещено импортировать друг друга напрямую.
# Расширять одной строкой при появлении tender/, margin/ (Д-2).
MODULE_PACKAGES = ["kp", "contracts"]


def _core_files() -> list[Path]:
    return sorted(CORE.rglob("*.py"))


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def test_core_has_no_streamlit_imports():
    violations = []
    for path in _core_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "streamlit" or alias.name.startswith("streamlit."):
                        violations.append(f"{path}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "streamlit" or module.startswith("streamlit."):
                    violations.append(f"{path}: from {module} import ...")
    assert not violations, "core/ не должен зависеть от Streamlit:\n" + "\n".join(violations)


def test_core_modules_do_not_import_each_other():
    violations = []
    for path in _core_files():
        module_name = _module_name(path)
        parts = module_name.split(".")
        own_pkg = parts[1] if len(parts) > 1 else None
        if own_pkg not in MODULE_PACKAGES:
            continue

        package = module_name if path.name == "__init__.py" else ".".join(parts[:-1])
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = [(alias.name, 0) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = [(node.module or "", node.level)]
            else:
                continue

            for name, level in targets:
                try:
                    resolved = (
                        importlib.util.resolve_name("." * level + name, package)
                        if level
                        else name
                    )
                except (ImportError, ValueError):
                    continue

                rparts = resolved.split(".")
                if len(rparts) < 2 or rparts[0] != "core":
                    continue
                target_pkg = rparts[1]
                if target_pkg in MODULE_PACKAGES and target_pkg != own_pkg:
                    violations.append(f"{path}: {own_pkg} импортирует {resolved}")

    assert not violations, (
        "Модули core/ не импортируют друг друга напрямую (Д-2):\n" + "\n".join(violations)
    )
