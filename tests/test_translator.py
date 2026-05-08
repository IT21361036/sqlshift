import pytest
from unittest.mock import patch, MagicMock
from agents.translator import translate


def _mock_openai_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("agents.translator._get_client")
def test_translate_returns_sql_string(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "SELECT * FROM emp LIMIT 10"
    )
    mock_get_client.return_value = mock_client
    result = translate("SELECT * FROM emp WHERE ROWNUM <= 10", "plsql", "postgresql")
    assert result == "SELECT * FROM emp LIMIT 10"


@patch("agents.translator._get_client")
def test_translate_strips_markdown_fences(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "```sql\nSELECT 1\n```"
    )
    mock_get_client.return_value = mock_client
    result = translate("SELECT 1", "tsql", "postgresql")
    assert "```" not in result
    assert "SELECT 1" in result


@patch("agents.translator._get_client")
def test_translate_injects_error_context_into_system_prompt(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response(
        "SELECT * FROM emp LIMIT 10"
    )
    mock_get_client.return_value = mock_client
    translate(
        "SELECT * FROM emp WHERE ROWNUM <= 10",
        "plsql",
        "postgresql",
        error_context=["ROWNUM still present in output"],
    )
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_content = next(m["content"] for m in call_kwargs["messages"] if m["role"] == "system")
    assert "ROWNUM still present in output" in system_content


@patch("agents.translator._get_client")
def test_translate_no_error_context_when_none(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_openai_response("SELECT 1")
    mock_get_client.return_value = mock_client
    translate("SELECT 1", "tsql", "postgresql", error_context=None)
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_content = next(m["content"] for m in call_kwargs["messages"] if m["role"] == "system")
    assert "failed validation" not in system_content
