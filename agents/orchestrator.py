import time
from sqlalchemy.orm import Session
from agents import translator, validator, optimizer
from pipeline import ingestion, report
from db import crud
from config import MAX_RETRIES


def run_job(session_factory, job_id: str, raw_sql: str, source_dialect: str, target_dialect: str) -> dict:
    db = session_factory()
    try:
        crud.update_job_status(db, job_id, "running")
        statements = ingestion.parse_sql(raw_sql)
        results = []

        for i, stmt in enumerate(statements, start=1):
            result = _process_statement(db, stmt, source_dialect, target_dialect, job_id, i)
            results.append(result)
            crud.increment_done_count(db, job_id)

        rep = report.build_report(job_id, results)
        crud.update_job_status(db, job_id, "done", quality_avg=rep["quality_avg"])
        return rep
    finally:
        db.close()


def _process_statement(db: Session, stmt: str, source_dialect: str, target_dialect: str, job_id: str, position: int) -> dict:
    start_ms = int(time.time() * 1000)
    flag = None
    retries = 0
    val_result = {"score": 0, "issues": [], "passed": False}

    translated = translator.translate(stmt, source_dialect, target_dialect)

    for attempt in range(MAX_RETRIES + 1):
        val_result = validator.validate(stmt, translated, source_dialect, target_dialect)

        if val_result["passed"]:
            break

        if attempt < MAX_RETRIES:
            retries += 1
            translated = translator.translate(
                stmt, source_dialect, target_dialect, error_context=val_result["issues"]
            )
        else:
            flag = "needs_human_review"

    opt_result = optimizer.optimize(translated, target_dialect)
    processing_ms = int(time.time() * 1000) - start_ms

    crud.write_statement(
        db=db,
        job_id=job_id,
        position=position,
        original_sql=stmt,
        modernized_sql=opt_result["optimized_sql"],
        quality_score=val_result["score"],
        validation_pass=val_result["passed"],
        retries=retries,
        flag=flag,
        processing_ms=processing_ms,
        changes=opt_result["changes"],
    )

    return {
        "position": position,
        "original_sql": stmt,
        "modernized_sql": opt_result["optimized_sql"],
        "quality_score": val_result["score"],
        "validation_passed": val_result["passed"],
        "retries": retries,
        "flag": flag,
        "processing_ms": processing_ms,
        "optimizations": opt_result["changes"],
    }
