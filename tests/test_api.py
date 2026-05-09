from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base
import db.models  # ensure ORM models are registered with Base.metadata before create_all
from db import crud
from api.main import app
from api.dependencies import get_db

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_modernize_returns_job_id():
    with patch("api.main.orchestrator.run_job") as mock_run:
        response = client.post(
            "/modernize",
            json={"sql": "SELECT 1", "source_dialect": "tsql", "target_dialect": "postgresql"},
        )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)


def test_job_status_pending():
    with patch("api.main.orchestrator.run_job"):
        post = client.post(
            "/modernize",
            json={"sql": "SELECT 1", "source_dialect": "tsql", "target_dialect": "postgresql"},
        )
    job_id = post.json()["job_id"]
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] == "pending"


def test_job_status_not_found():
    response = client.get("/jobs/nonexistent-job-id")
    assert response.status_code == 404


def test_job_report_not_found():
    response = client.get("/jobs/nonexistent-job-id/report")
    assert response.status_code == 404


def test_job_report_empty():
    with patch("api.main.orchestrator.run_job"):
        post = client.post(
            "/modernize",
            json={"sql": "SELECT 1", "source_dialect": "mysql", "target_dialect": "postgresql"},
        )
    job_id = post.json()["job_id"]
    response = client.get(f"/jobs/{job_id}/report")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["statements"] == []


def test_history_returns_list():
    response = client.get("/history")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)
