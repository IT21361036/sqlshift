import pytest
from pipeline.ingestion import parse_sql


def test_single_statement():
    result = parse_sql("SELECT * FROM employees")
    assert result == ["SELECT * FROM employees"]


def test_multiple_statements():
    result = parse_sql("SELECT 1; SELECT 2;")
    assert len(result) == 2


def test_filters_empty_statements():
    result = parse_sql("SELECT 1;;;SELECT 2")
    assert len(result) == 2


def test_empty_input():
    assert parse_sql("") == []


def test_whitespace_only():
    assert parse_sql("   \n\n   ") == []


def test_preserves_multiline_statement():
    sql = """SELECT e.name, d.name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id
WHERE e.salary > 50000"""
    result = parse_sql(sql)
    assert len(result) == 1
    assert "LEFT JOIN" in result[0]
