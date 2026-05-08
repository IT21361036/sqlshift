import hashlib
import uuid
from sqlalchemy.orm import Session
from db.models import Job, Statement, Optimization, Cache


def create_job(db: Session, source_dialect: str, target_dialect: str, input_sql: str, statement_count: int) -> Job:
    input_hash = hashlib.sha256(input_sql.encode()).hexdigest()
    job = Job(
        source_dialect=source_dialect,
        target_dialect=target_dialect,
        input_hash=input_hash,
        statement_count=statement_count,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job_status(db: Session, job_id: str, status: str, quality_avg: float = None):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return
    job.status = status
    if quality_avg is not None:
        job.quality_avg = quality_avg
    db.commit()


def increment_done_count(db: Session, job_id: str):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return
    job.done_count += 1
    db.commit()


def write_statement(
    db: Session,
    job_id: str,
    position: int,
    original_sql: str,
    modernized_sql: str,
    quality_score: int,
    validation_pass: bool,
    retries: int,
    flag: str,
    processing_ms: int,
    changes: list,
) -> Statement:
    stmt = Statement(
        job_id=job_id,
        position=position,
        original_sql=original_sql,
        modernized_sql=modernized_sql,
        quality_score=quality_score,
        validation_pass=validation_pass,
        retries=retries,
        flag=flag,
        processing_ms=processing_ms,
    )
    db.add(stmt)
    db.flush()
    for change in changes:
        db.add(Optimization(statement_id=stmt.id, description=change, category="performance"))
    db.commit()
    db.refresh(stmt)
    return stmt


def get_job(db: Session, job_id: str) -> Job:
    return db.query(Job).filter(Job.id == job_id).first()


def get_job_report(db: Session, job_id: str) -> dict:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return None
    stmts = db.query(Statement).filter(Statement.job_id == job_id).order_by(Statement.position).all()
    result = []
    for s in stmts:
        opts = db.query(Optimization).filter(Optimization.statement_id == s.id).all()
        result.append({
            "position": s.position,
            "original_sql": s.original_sql,
            "modernized_sql": s.modernized_sql,
            "quality_score": s.quality_score,
            "validation_passed": s.validation_pass,
            "retries": s.retries,
            "flag": s.flag,
            "processing_ms": s.processing_ms,
            "optimizations": [o.description for o in opts],
        })
    return {
        "job_id": job.id,
        "status": job.status,
        "quality_avg": job.quality_avg,
        "statement_count": job.statement_count,
        "statements": result,
    }


def get_history(db: Session, limit: int = 20) -> list:
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
    return [
        {
            "job_id": j.id,
            "created_at": j.created_at.isoformat(),
            "quality_avg": j.quality_avg,
            "statement_count": j.statement_count,
            "status": j.status,
        }
        for j in jobs
    ]


def check_cache(db: Session, input_hash: str, target_dialect: str) -> Cache:
    return db.query(Cache).filter(Cache.input_hash == input_hash, Cache.target_dialect == target_dialect).first()


def write_cache(db: Session, input_hash: str, target_dialect: str, modernized_sql: str, quality_score: int):
    existing = check_cache(db, input_hash, target_dialect)
    if existing:
        return
    db.add(Cache(input_hash=input_hash, target_dialect=target_dialect, modernized_sql=modernized_sql, quality_score=quality_score))
    db.commit()
