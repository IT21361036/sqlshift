from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field

SUPPORTED_DIALECTS = Literal["tsql", "mysql", "oracle", "postgresql", "sqlite"]


class ModernizeRequest(BaseModel):
    sql: str = Field(..., min_length=1, max_length=524288)  # 512 KB ceiling
    source_dialect: SUPPORTED_DIALECTS = "tsql"
    target_dialect: SUPPORTED_DIALECTS = "postgresql"


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
