import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from db import models
from db.crud import create_job
from agents.orchestrator import run_job


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@patch("agents.orchestrator.translator.translate")
@patch("agents.orchestrator.validator.validate")
@patch("agents.orchestrator.optimizer.optimize")
def test_run_job_completes_successfully(mock_opt, mock_val, mock_trans, db):
    mock_trans.return_value = "SELECT * FROM emp LIMIT 10"
    mock_val.return_value = {"score": 95, "issues": [], "passed": True}
    mock_opt.return_value = {"optimized_sql": "SELECT * FROM emp LIMIT 10", "changes": []}

    raw_sql = "SELECT * FROM emp WHERE ROWNUM <= 10"
    job = create_job(db, "plsql", "postgresql", raw_sql, 1)
    rep = run_job(db, job.id, raw_sql, "plsql", "postgresql")

    assert rep["quality_avg"] == 95.0
    assert rep["statements"][0]["validation_passed"] is True
    assert rep["statements"][0]["retries"] == 0


@patch("agents.orchestrator.translator.translate")
@patch("agents.orchestrator.validator.validate")
@patch("agents.orchestrator.optimizer.optimize")
def test_run_job_retries_on_low_score_and_flags(mock_opt, mock_val, mock_trans, db):
    mock_trans.return_value = "bad sql"
    mock_val.return_value = {"score": 40, "issues": ["ROWNUM still present"], "passed": False}
    mock_opt.return_value = {"optimized_sql": "bad sql", "changes": []}

    raw_sql = "SELECT * FROM emp WHERE ROWNUM <= 10"
    job = create_job(db, "plsql", "postgresql", raw_sql, 1)
    rep = run_job(db, job.id, raw_sql, "plsql", "postgresql")

    assert rep["statements"][0]["flag"] == "needs_human_review"
    # initial translate + 2 retry translates = 3 total
    assert mock_trans.call_count == 3


@patch("agents.orchestrator.translator.translate")
@patch("agents.orchestrator.validator.validate")
@patch("agents.orchestrator.optimizer.optimize")
def test_run_job_retries_pass_error_context(mock_opt, mock_val, mock_trans, db):
    mock_trans.return_value = "SELECT * FROM emp LIMIT 10"
    mock_val.side_effect = [
        {"score": 50, "issues": ["ROWNUM still present"], "passed": False},
        {"score": 95, "issues": [], "passed": True},
    ]
    mock_opt.return_value = {"optimized_sql": "SELECT * FROM emp LIMIT 10", "changes": []}

    raw_sql = "SELECT * FROM emp WHERE ROWNUM <= 10"
    job = create_job(db, "plsql", "postgresql", raw_sql, 1)
    run_job(db, job.id, raw_sql, "plsql", "postgresql")

    second_call = mock_trans.call_args_list[1]
    assert second_call.kwargs.get("error_context") == ["ROWNUM still present"]


@patch("agents.orchestrator.translator.translate")
@patch("agents.orchestrator.validator.validate")
@patch("agents.orchestrator.optimizer.optimize")
def test_run_job_processes_multiple_statements(mock_opt, mock_val, mock_trans, db):
    mock_trans.return_value = "SELECT 1"
    mock_val.return_value = {"score": 80, "issues": [], "passed": True}
    mock_opt.return_value = {"optimized_sql": "SELECT 1", "changes": []}

    raw_sql = "SELECT 1; SELECT 2; SELECT 3"
    job = create_job(db, "tsql", "postgresql", raw_sql, 3)
    rep = run_job(db, job.id, raw_sql, "tsql", "postgresql")

    assert len(rep["statements"]) == 3
    assert mock_trans.call_count == 3
