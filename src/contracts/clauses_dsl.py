"""clauses_dsl.py — безопасный DSL-парсер для applies_when-выражений."""
from __future__ import annotations

import ast
from typing import Any

_ALLOWED_VARS = frozenset({
    "foundation_scope",
    "installation_scope",
    "verification_scope",
    "has_orion",
    "orion_poles_scope",
    "winter_concrete",
    "true",
    "false",
})


def _validate(node: ast.AST) -> None:
    """Рекурсивная валидация AST. Raises ValueError на запрещённые конструкции."""
    if isinstance(node, ast.Expression):
        _validate(node.body)
    elif isinstance(node, ast.Constant):
        pass
    elif isinstance(node, ast.Name):
        if node.id not in _ALLOWED_VARS:
            raise ValueError(f"Переменная не разрешена: {node.id!r}")
    elif isinstance(node, ast.BoolOp):
        if not isinstance(node.op, (ast.And, ast.Or)):
            raise ValueError(f"Недопустимый логический оператор: {type(node.op).__name__}")
        for val in node.values:
            _validate(val)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, ast.Not):
            raise ValueError(f"Недопустимый унарный оператор: {type(node.op).__name__}")
        _validate(node.operand)
    elif isinstance(node, ast.Compare):
        _validate(node.left)
        for op in node.ops:
            if not isinstance(op, (ast.Eq, ast.NotEq, ast.In, ast.NotIn)):
                raise ValueError(f"Недопустимый оператор сравнения: {type(op).__name__}")
        for comp in node.comparators:
            _validate(comp)
    elif isinstance(node, ast.Tuple):
        for elt in node.elts:
            _validate(elt)
    else:
        raise ValueError(f"Недопустимый тип узла AST: {type(node).__name__}")


def _eval(node: ast.AST, ctx: dict[str, Any]) -> Any:
    """Вычислить значение валидированного AST-узла на контексте ctx."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.Name):
        if node.id == "true":
            return True
        if node.id == "false":
            return False
        if node.id not in ctx:
            raise KeyError(node.id)
        return ctx[node.id]
    elif isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval(v, ctx) for v in node.values)
        return any(_eval(v, ctx) for v in node.values)
    elif isinstance(node, ast.UnaryOp):
        return not _eval(node.operand, ctx)
    elif isinstance(node, ast.Compare):
        left = _eval(node.left, ctx)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval(comp, ctx)
            if isinstance(op, ast.Eq) and left != right:
                return False
            if isinstance(op, ast.NotEq) and left == right:
                return False
            if isinstance(op, ast.In) and left not in right:
                return False
            if isinstance(op, ast.NotIn) and left in right:
                return False
            left = right
        return True
    elif isinstance(node, ast.Tuple):
        return tuple(_eval(e, ctx) for e in node.elts)
    raise ValueError(f"Не могу вычислить узел: {type(node).__name__}")


class Expression:
    def __init__(self, node: ast.AST) -> None:
        self._node = node

    def evaluate(self, context: dict[str, Any]) -> bool:
        return bool(_eval(self._node, context))


def parse(expr: str) -> Expression:
    """Разобрать выражение applies_when. Raises ValueError на недопустимые конструкции."""
    try:
        tree = ast.parse(expr.strip(), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"Синтаксическая ошибка в выражении {expr!r}: {e}") from e
    _validate(tree.body)
    return Expression(tree.body)
