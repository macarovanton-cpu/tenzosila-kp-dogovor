# tests/contracts/test_clauses_dsl.py
"""Тесты безопасного DSL-парсера applies_when."""
import pytest


class TestLiterals:
    def test_true_uppercase(self):
        from src.contracts.clauses_dsl import parse
        assert parse("True").evaluate({}) is True

    def test_true_lowercase(self):
        from src.contracts.clauses_dsl import parse
        assert parse("true").evaluate({}) is True

    def test_false_lowercase(self):
        from src.contracts.clauses_dsl import parse
        assert parse("false").evaluate({}) is False


class TestAllowedVars:
    def test_bool_var(self):
        from src.contracts.clauses_dsl import parse
        assert parse("has_orion").evaluate({"has_orion": True}) is True
        assert parse("has_orion").evaluate({"has_orion": False}) is False

    def test_string_compare_allowed_var(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('verification_scope == "supplier"')
        assert expr.evaluate({"verification_scope": "supplier"}) is True
        assert expr.evaluate({"verification_scope": "customer"}) is False

    def test_missing_var_raises_key_error(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(KeyError, match="has_orion"):
            parse("has_orion").evaluate({})


class TestInOperator:
    def test_in_tuple(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('foundation_scope in ("contractor_full", "contractor_with_materials")')
        assert expr.evaluate({"foundation_scope": "contractor_full"}) is True
        assert expr.evaluate({"foundation_scope": "none"}) is False

    def test_not_equal(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('installation_scope != "none"')
        assert expr.evaluate({"installation_scope": "full"}) is True
        assert expr.evaluate({"installation_scope": "none"}) is False


class TestLogical:
    def test_and(self):
        from src.contracts.clauses_dsl import parse
        expr = parse("has_orion and winter_concrete")
        assert expr.evaluate({"has_orion": True, "winter_concrete": True}) is True
        assert expr.evaluate({"has_orion": True, "winter_concrete": False}) is False

    def test_or(self):
        from src.contracts.clauses_dsl import parse
        expr = parse('has_orion or foundation_scope == "rama"')
        assert expr.evaluate({"has_orion": False, "foundation_scope": "rama"}) is True
        assert expr.evaluate({"has_orion": False, "foundation_scope": "none"}) is False

    def test_not(self):
        from src.contracts.clauses_dsl import parse
        assert parse("not has_orion").evaluate({"has_orion": False}) is True
        assert parse("not has_orion").evaluate({"has_orion": True}) is False

    def test_parentheses_complex(self):
        from src.contracts.clauses_dsl import parse
        expr = parse(
            'foundation_scope in ("contractor_full", "contractor_with_materials")'
            ' and not (has_orion and orion_poles_scope == "by_contractor")'
        )
        ctx_true = {"foundation_scope": "contractor_full", "has_orion": False, "orion_poles_scope": "none"}
        ctx_false = {"foundation_scope": "contractor_full", "has_orion": True, "orion_poles_scope": "by_contractor"}
        assert expr.evaluate(ctx_true) is True
        assert expr.evaluate(ctx_false) is False


class TestSecurity:
    def test_function_call_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("eval('x')")

    def test_attribute_access_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("foundation_scope.encode()")

    def test_import_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse('__import__("os")')

    def test_unknown_variable_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError, match="не разрешена"):
            parse("unknown_var")

    def test_subscript_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("items[0]")

    def test_lambda_rejected(self):
        from src.contracts.clauses_dsl import parse
        with pytest.raises(ValueError):
            parse("lambda x: x")


class TestRealClausesYaml:
    """Все 28 applies_when из data/clauses.yaml должны парситься успешно."""

    EXPRS = [
        'verification_scope == "supplier"',
        'foundation_scope in ("contractor_full", "contractor_with_materials") and not (has_orion and orion_poles_scope == "by_contractor")',
        'foundation_scope in ("contractor_full", "contractor_with_materials") and has_orion and orion_poles_scope == "by_contractor"',
        'installation_scope != "none"',
        'foundation_scope == "customer_builds"',
        'foundation_scope == "rama"',
        'foundation_scope in ("contractor_full", "contractor_with_materials")',
        'foundation_scope == "contractor_with_materials"',
        'installation_scope == "shefmontazh"',
        'has_orion or foundation_scope == "rama"',
        'verification_scope == "customer"',
        'has_orion and orion_poles_scope == "by_customer"',
        'has_orion',
        'winter_concrete',
        'true',
    ]

    def test_all_real_exprs_parse(self):
        from src.contracts.clauses_dsl import parse
        for expr in self.EXPRS:
            try:
                parse(expr)
            except ValueError as e:
                pytest.fail(f"Не удалось разобрать {expr!r}: {e}")
