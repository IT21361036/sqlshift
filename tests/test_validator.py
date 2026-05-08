import pytest
from unittest.mock import patch
from agents.validator import validate, _had_where, _column_count_mismatch


def test_had_where_detects_where_clause():
    assert _had_where("SELECT * FROM t WHERE id = 1") is True


def test_had_where_no_where_clause():
    assert _had_where("SELECT * FROM t") is False


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_valid_translation_passes(mock_equiv):
    result = validate(
        "SELECT id FROM employees WHERE active = 1",
        "SELECT id FROM employees WHERE active = 1",
        "tsql", "postgresql",
    )
    assert result["passed"] is True
    assert result["score"] >= 70


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_missing_where_clause_penalizes(mock_equiv):
    result = validate(
        "SELECT id FROM employees WHERE active = 1",
        "SELECT id FROM employees",
        "tsql", "postgresql",
    )
    assert result["score"] < 100
    assert any("WHERE" in issue for issue in result["issues"])


@patch("agents.validator._gpt_equivalence", return_value=0.5)
def test_low_semantic_score_penalizes(mock_equiv):
    result = validate(
        "SELECT name FROM employees",
        "SELECT id FROM departments",
        "tsql", "postgresql",
    )
    assert result["score"] < 100
    assert any("Semantic" in issue for issue in result["issues"])


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_deprecated_syntax_penalizes(mock_equiv):
    result = validate(
        "SELECT * FROM emp",
        "SELECT * FROM emp WHERE ROWNUM <= 10",
        "tsql", "postgresql",
    )
    assert result["score"] < 100
    assert any("Deprecated" in issue for issue in result["issues"])


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_multiple_deductions_floor_at_zero(mock_equiv):
    result = validate(
        "SELECT a, b, c FROM t WHERE x = 1",
        "SELECT a FROM t",
        "tsql", "postgresql",
    )
    assert result["score"] >= 0
