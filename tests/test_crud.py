import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from db import models  # registers models with Base
from db.crud import create_job, update_job_status, write_statement, get_job, get_job_report, get_history


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_job(db):
    job = create_job(db, "tsql", "postgresql", "SELECT 1", 1)
    assert job.id is not None
    assert job.status == "pending"
    assert job.statement_count == 1


def test_update_job_status(db):
    job = create_job(db, "tsql", "postgresql", "SELECT 1", 1)
    update_job_status(db, job.id, "done", quality_avg=88.5)
    fetched = get_job(db, job.id)
    assert fetched.status == "done"
    assert fetched.quality_avg == 88.5


def test_write_statement_and_report(db):
    job = create_job(db, "plsql", "postgresql", "SELECT * FROM emp WHERE ROWNUM <= 10", 1)
    write_statement(db, job.id, 1, "SELECT * FROM emp WHERE ROWNUM <= 10", "SELECT * FROM emp LIMIT 10", 94, True, 0, None, 1200, ["ROWNUM replaced with LIMIT"])
    update_job_status(db, job.id, "done", quality_avg=94.0)

    report = get_job_report(db, job.id)
    assert report["quality_avg"] == 94.0
    assert len(report["statements"]) == 1
    assert report["statements"][0]["optimizations"] == ["ROWNUM replaced with LIMIT"]


def test_get_job_report_not_found(db):
    assert get_job_report(db, "nonexistent") is None


def test_get_history(db):
    create_job(db, "tsql", "postgresql", "SELECT 1", 1)
    create_job(db, "plsql", "postgresql", "SELECT 2", 1)
    history = get_history(db)
    assert len(history) == 2
