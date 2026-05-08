# Database — SQL Modernization Accelerator

## Overview

The project uses a relational database with 4 tables.

| Environment | Database | Connection |
|-------------|----------|-----------|
| Local dev | SQLite | `sqlite:///./data/modernizer.db` — file-based, zero setup |
| Production | Azure SQL | Connection string from Azure Key Vault |

Same SQLAlchemy ORM code works against both. Switch database by
changing the `DATABASE_URL` environment variable only.

---

## Table: jobs

Tracks each modernization job submitted by the user.

```sql
CREATE TABLE jobs (
    id               TEXT PRIMARY KEY,     -- UUID
    created_at       DATETIME NOT NULL,
    status           TEXT NOT NULL,        -- pending | running | done | failed
    source_dialect   TEXT NOT NULL,        -- tsql | plsql | mysql5
    target_dialect   TEXT NOT NULL,        -- postgresql | ansi | mysql8
    input_hash       TEXT,                 -- SHA-256 of full input SQL (for cache lookup)
    statement_count  INTEGER DEFAULT 0,
    done_count       INTEGER DEFAULT 0,
    quality_avg      REAL                  -- average score across all statements
);
```

---

## Table: statements

Stores the result of each individual SQL statement within a job.

```sql
CREATE TABLE statements (
    id               TEXT PRIMARY KEY,     -- UUID
    job_id           TEXT NOT NULL REFERENCES jobs(id),
    position         INTEGER NOT NULL,     -- order in the original file (1-indexed)
    original_sql     TEXT NOT NULL,
    modernized_sql   TEXT,
    quality_score    INTEGER,              -- 0–100
    validation_pass  BOOLEAN DEFAULT FALSE,
    retries          INTEGER DEFAULT 0,    -- how many retries were needed (0, 1, or 2)
    flag             TEXT,                 -- NULL | needs_human_review | api_error
    processing_ms    INTEGER               -- total time for this statement
);
```

---

## Table: optimizations

Stores each individual optimization applied by the Optimizer agent.
One row per optimization per statement.

```sql
CREATE TABLE optimizations (
    id               TEXT PRIMARY KEY,     -- UUID
    statement_id     TEXT NOT NULL REFERENCES statements(id),
    description      TEXT NOT NULL,        -- e.g. "Replaced correlated subquery with CTE"
    category         TEXT NOT NULL         -- syntax | performance | safety
);
```

---

## Table: cache

Caches results so re-submitting identical SQL skips the whole pipeline.

```sql
CREATE TABLE cache (
    input_hash       TEXT NOT NULL,        -- SHA-256 of original_sql
    target_dialect   TEXT NOT NULL,        -- cache is dialect-specific
    modernized_sql   TEXT NOT NULL,
    quality_score    INTEGER NOT NULL,
    created_at       DATETIME NOT NULL,
    PRIMARY KEY (input_hash, target_dialect)
);
```

---

## Entity Relationships

```
jobs (1) ──────< statements (many)
                     │
statements (1) ──────< optimizations (many)

cache ─ ─ ─ ─ ─ ─ ─ > statements (lookup by hash, no FK)
```

---

## Setup Commands

```bash
# Initialize tables (run once, or on first startup)
python manage.py init_db

# Optional: seed with sample legacy SQL for testing
python manage.py seed_db

# Reset database (development only — drops and recreates all tables)
python manage.py reset_db
```

---

## ORM Models (SQLAlchemy)

```python
# db/models.py

from sqlalchemy import Column, Text, Integer, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base
import uuid, datetime

class Job(Base):
    __tablename__ = "jobs"
    id              = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)
    status          = Column(Text, default="pending")
    source_dialect  = Column(Text, nullable=False)
    target_dialect  = Column(Text, nullable=False)
    input_hash      = Column(Text)
    statement_count = Column(Integer, default=0)
    done_count      = Column(Integer, default=0)
    quality_avg     = Column(Float)
    statements      = relationship("Statement", back_populates="job")

class Statement(Base):
    __tablename__ = "statements"
    id              = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id          = Column(Text, ForeignKey("jobs.id"), nullable=False)
    position        = Column(Integer, nullable=False)
    original_sql    = Column(Text, nullable=False)
    modernized_sql  = Column(Text)
    quality_score   = Column(Integer)
    validation_pass = Column(Boolean, default=False)
    retries         = Column(Integer, default=0)
    flag            = Column(Text)
    processing_ms   = Column(Integer)
    job             = relationship("Job", back_populates="statements")
    optimizations   = relationship("Optimization", back_populates="statement")

class Optimization(Base):
    __tablename__ = "optimizations"
    id              = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id    = Column(Text, ForeignKey("statements.id"), nullable=False)
    description     = Column(Text, nullable=False)
    category        = Column(Text, nullable=False)
    statement       = relationship("Statement", back_populates="optimizations")

class Cache(Base):
    __tablename__ = "cache"
    input_hash      = Column(Text, primary_key=True)
    target_dialect  = Column(Text, primary_key=True)
    modernized_sql  = Column(Text, nullable=False)
    quality_score   = Column(Integer, nullable=False)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)
```
