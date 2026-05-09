import json
from unittest.mock import patch
from agents.optimizer import optimize


@patch("agents.optimizer.call_qwen")
def test_optimize_returns_sql_and_changes(mock_call):
    mock_call.return_value = json.dumps({
        "optimized_sql": "WITH avg_sal AS (SELECT dept_id, AVG(salary) avg FROM employees GROUP BY dept_id) SELECT name FROM employees",
        "changes": ["Replaced correlated subquery with CTE"],
    })
    result = optimize("SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id)", "postgresql")
    assert "optimized_sql" in result
    assert len(result["changes"]) == 1


@patch("agents.optimizer.call_qwen")
def test_optimize_no_changes_returns_original(mock_call):
    sql = "SELECT id FROM users WHERE active = 1"
    mock_call.return_value = json.dumps({"optimized_sql": sql, "changes": []})
    result = optimize(sql, "postgresql")
    assert result["optimized_sql"] == sql
    assert result["changes"] == []


@patch("agents.optimizer.call_qwen")
def test_optimize_passes_target_dialect_to_prompt(mock_call):
    mock_call.return_value = json.dumps({"optimized_sql": "SELECT 1", "changes": []})
    optimize("SELECT 1", "mysql8")
    system_prompt = mock_call.call_args[0][0]
    assert "mysql8" in system_prompt


@patch("agents.optimizer.call_qwen", return_value="not valid json {{")
def test_optimize_handles_malformed_json(mock_call):
    sql = "SELECT id FROM users"
    result = optimize(sql, "postgresql")
    assert result["optimized_sql"] == sql
    assert result["changes"] == []
