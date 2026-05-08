from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.models import (
    ModernizeRequest,
    ModernizeResponse,
    JobStatusResponse,
    JobReportResponse,
    StatementOut,
    HistoryItem,
    HistoryResponse,
    HealthResponse,
)
from api.dependencies import get_db
from db import crud
from db.database import SessionLocal
from agents import orchestrator
from pipeline import ingestion

app = FastAPI(title="SQLShift", version="1.0.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.post("/modernize", response_model=ModernizeResponse, status_code=202)
def modernize(req: ModernizeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    statements = ingestion.parse_sql(req.sql)
    job = crud.create_job(db, req.source_dialect, req.target_dialect, req.sql, len(statements))
    background_tasks.add_task(
        orchestrator.run_job,
        SessionLocal,
        job.id,
        req.sql,
        req.source_dialect,
        req.target_dialect,
    )
    return ModernizeResponse(job_id=job.id)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str, db: Session = Depends(get_db)):
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        source_dialect=job.source_dialect,
        target_dialect=job.target_dialect,
        statement_count=job.statement_count,
        done_count=job.done_count,
        quality_avg=job.quality_avg,
    )


@app.get("/jobs/{job_id}/report", response_model=JobReportResponse)
def job_report(job_id: str, db: Session = Depends(get_db)):
    report = crud.get_job_report(db, job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobReportResponse(
        job_id=report["job_id"],
        status=report["status"],
        quality_avg=report["quality_avg"],
        statement_count=report["statement_count"],
        statements=[
            StatementOut(
                position=s["position"],
                original_sql=s["original_sql"],
                modernized_sql=s["modernized_sql"],
                quality_score=s["quality_score"],
                validation_pass=s["validation_passed"],
                retries=s["retries"],
                flag=s["flag"],
                processing_ms=s["processing_ms"],
            )
            for s in report["statements"]
        ],
    )


@app.get("/history", response_model=HistoryResponse)
def history(db: Session = Depends(get_db)):
    jobs = crud.get_history(db)
    return HistoryResponse(
        jobs=[
            HistoryItem(
                job_id=j["job_id"],
                status=j["status"],
                quality_avg=j["quality_avg"],
                statement_count=j["statement_count"],
                created_at=j["created_at"],
            )
            for j in jobs
        ]
    )
