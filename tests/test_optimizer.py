import json
import pytest
from unittest.mock import patch, MagicMock
from agents.optimizer import optimize


def _mock_response(optimized_sql: str, changes: list):
    msg = MagicMock()
    msg.content = json.dumps({"optimized_sql": optimized_sql, "changes": changes})
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("agents.optimizer._get_client")
def test_optimize_returns_sql_and_changes(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(
        "WITH avg_sal AS (SELECT dept_id, AVG(salary) avg FROM employees GROUP BY dept_id) SELECT name FROM employees",
        ["Replaced correlated subquery with CTE"],
    )
    mock_get_client.return_value = mock_client
    result = optimize("SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id)", "postgresql")
    assert "optimized_sql" in result
    assert "changes" in result
    assert len(result["changes"]) == 1


@patch("agents.optimizer._get_client")
def test_optimize_no_changes_returns_original(mock_get_client):
    sql = "SELECT id FROM users WHERE active = 1"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(sql, [])
    mock_get_client.return_value = mock_client
    result = optimize(sql, "postgresql")
    assert result["optimized_sql"] == sql
    assert result["changes"] == []


@patch("agents.optimizer._get_client")
def test_optimize_passes_target_dialect_to_prompt(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response("SELECT 1", [])
    mock_get_client.return_value = mock_client
    optimize("SELECT 1", "mysql8")
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_content = next(m["content"] for m in call_kwargs["messages"] if m["role"] == "system")
    assert "mysql8" in system_content
