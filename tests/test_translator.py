from unittest.mock import patch
from agents.translator import translate


@patch("agents.translator.call_qwen", return_value="SELECT * FROM emp LIMIT 10")
def test_translate_returns_sql_string(mock_call):
    result = translate("SELECT * FROM emp WHERE ROWNUM <= 10", "plsql", "postgresql")
    assert result == "SELECT * FROM emp LIMIT 10"


@patch("agents.translator.call_qwen", return_value="```sql\nSELECT 1\n```")
def test_translate_strips_markdown_fences(mock_call):
    result = translate("SELECT 1", "tsql", "postgresql")
    assert "```" not in result
    assert "SELECT 1" in result


@patch("agents.translator.call_qwen", return_value="SELECT * FROM emp LIMIT 10")
def test_translate_injects_error_context_into_system_prompt(mock_call):
    translate(
        "SELECT * FROM emp WHERE ROWNUM <= 10",
        "plsql",
        "postgresql",
        error_context=["ROWNUM still present in output"],
    )
    system_prompt = mock_call.call_args[0][0]
    assert "ROWNUM still present in output" in system_prompt


@patch("agents.translator.call_qwen", return_value="SELECT 1")
def test_translate_no_error_context_when_none(mock_call):
    translate("SELECT 1", "tsql", "postgresql", error_context=None)
    system_prompt = mock_call.call_args[0][0]
    assert "failed validation" not in system_prompt
