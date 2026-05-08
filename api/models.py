from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class ModernizeRequest(BaseModel):
    sql: str
    source_dialect: str = "tsql"
    target_dialect: str = "postgresql"


class ModernizeResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    source_dialect: str
    target_dialect: str
    statement_count: int
    done_count: int
    quality_avg: Optional[float]


class StatementOut(BaseModel):
    position: int
    original_sql: str
    modernized_sql: Optional[str]
    quality_score: Optional[int]
    validation_pass: bool
    retries: int
    flag: Optional[str]
    processing_ms: Optional[int]


class JobReportResponse(BaseModel):
    job_id: str
    status: str
    quality_avg: Optional[float]
    statement_count: int
    statements: list[StatementOut]


class HistoryItem(BaseModel):
    job_id: str
    status: str
    quality_avg: Optional[float]
    statement_count: int
    created_at: str


class HistoryResponse(BaseModel):
    jobs: list[HistoryItem]


class HealthResponse(BaseModel):
    status: str
