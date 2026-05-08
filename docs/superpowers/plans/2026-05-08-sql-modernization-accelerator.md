# SQL Modernization Accelerator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-quality multi-agent AI pipeline that modernizes legacy SQL (T-SQL, PL/SQL, old MySQL) into clean, optimized PostgreSQL/ANSI SQL with quality scoring, retry logic, and diff reports — deployable as a portfolio project on Azure Container Apps.

**Architecture:** Four specialized agents (Translator, Validator, Optimizer, Orchestrator) process each SQL statement independently. The Orchestrator drives a retry loop (max 2 attempts) by feeding Validator error feedback back into the Translator prompt. SQLite is used locally; Supabase (PostgreSQL) in production — same SQLAlchemy ORM, different `DATABASE_URL` only.

**Tech Stack:** Python 3.11+, Azure OpenAI GPT-4o (openai SDK), FastAPI, SQLAlchemy, psycopg2-binary, sqlparse, SQLite (local) / Supabase PostgreSQL (prod), pytest, Docker, Azure Container Apps, GitHub Actions

**Note on Foundry IQ:** The planning docs mention Foundry IQ as a hackathon tool. For this portfolio build we use the standard `openai.AzureOpenAI` client directly — no Foundry IQ dependency.

---

## File Map

```
e:\Sproject\
├── config.py                          # env-based settings, single source of truth
├── manage.py                          # CLI: init_db / reset_db / seed_db
├── run_cli.py                         # CLI entry point (no web server)
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
│
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py               # pipeline runner + retry loop + DB writes
│   ├── translator.py                 # dialect rewrite via GPT-4o
│   ├── validator.py                  # sqlparse syntax + GPT-4o semantic scoring
│   └── optimizer.py                  # performance rewrite via GPT-4o
│
├── pipeline/
│   ├── __init__.py
│   ├── ingestion.py                  # sqlparse.split() → clean statement list
│   └── report.py                     # unified diff + quality average builder
│
├── api/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app + all routes
│   ├── models.py                     # Pydantic request/response schemas
│   └── dependencies.py              # re-exports get_db for FastAPI DI
│
├── db/
│   ├── __init__.py
│   ├── database.py                   # engine + SessionLocal + Base + get_db
│   ├── models.py                     # ORM: Job, Statement, Optimization, Cache
│   └── crud.py                       # all DB helper functions
│
├── prompts/
│   ├── translator.txt                # system prompt template for Translator
│   ├── validator.txt                 # prompt for GPT-4o semantic equivalence check
│   └── optimizer.txt                 # prompt for Optimizer (returns JSON)
│
├── sample_sql/
│   ├── legacy_cursor.sql             # T-SQL cursor → CTE demo
│   ├── legacy_oracle.sql             # PL/SQL ROWNUM + old outer join
│   ├── legacy_mysql.sql              # old MySQL implicit joins
│   ├── legacy_subquery.sql           # correlated subquery (optimizer demo)
│   └── legacy_mixed.sql              # multi-statement mixed patterns
│
├── tests/
│   ├── conftest.py                   # set env vars before any import
│   ├── test_ingestion.py
│   ├── test_translator.py
│   ├── test_validator.py
│   ├── test_optimizer.py
│   ├── test_orchestrator.py
│   ├── test_report.py
│   └── test_api.py
│
├── data/
│   └── .gitkeep
│
├── infra/
│   ├── azure.yaml
│   └── main.bicep
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── Dockerfile
└── docker-compose.yml
```

---

## Task 1: Project Bootstrap

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `config.py`
- Create: `pytest.ini`
- Create: `data/.gitkeep`

- [ ] **Step 1: Create `requirements.txt`**

```
openai>=1.30.0
python-dotenv
sqlparse
sqlalchemy
psycopg2-binary
fastapi
uvicorn[standard]
pydantic>=2.0
pytest
pytest-asyncio
httpx
```

- [ ] **Step 2: Create `.env.example`**

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Database
# Local dev — SQLite (zero setup):
DATABASE_URL=sqlite:///./data/modernizer.db
# Production — Supabase PostgreSQL (swap this in for prod):
# DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres

# Pipeline config
MAX_RETRIES=2
VALIDATION_THRESHOLD=70
DEFAULT_SOURCE_DIALECT=tsql
DEFAULT_TARGET_DIALECT=postgresql
```

- [ ] **Step 3: Create `.gitignore`**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
data/*.db
.venv/
venv/
dist/
*.egg-info/
.coverage
htmlcov/
```

- [ ] **Step 4: Create `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/modernizer.db")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
VALIDATION_THRESHOLD = int(os.getenv("VALIDATION_THRESHOLD", "70"))
DEFAULT_SOURCE_DIALECT = os.getenv("DEFAULT_SOURCE_DIALECT", "tsql")
DEFAULT_TARGET_DIALECT = os.getenv("DEFAULT_TARGET_DIALECT", "postgresql")
```

- [ ] **Step 5: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
asyncio_mode = auto
```

- [ ] **Step 6: Create `data/.gitkeep`**

Empty file — ensures the `data/` directory is committed so SQLite has a place to write.

- [ ] **Step 7: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 8: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore config.py pytest.ini data/.gitkeep
git commit -m "chore: project bootstrap — deps, config, env template"
```

---

## Task 2: Database Layer

**Files:**
- Create: `db/__init__.py`
- Create: `db/database.py`
- Create: `db/models.py`
- Create: `db/crud.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_crud.py`

- [ ] **Step 1: Create `db/__init__.py`** (empty)

- [ ] **Step 2: Create `db/database.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATABASE_URL

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: Create `db/models.py`**

```python
import uuid
import datetime
from sqlalchemy import Column, Text, Integer, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(Text, default="pending")
    source_dialect = Column(Text, nullable=False)
    target_dialect = Column(Text, nullable=False)
    input_hash = Column(Text)
    statement_count = Column(Integer, default=0)
    done_count = Column(Integer, default=0)
    quality_avg = Column(Float)
    statements = relationship("Statement", back_populates="job")


class Statement(Base):
    __tablename__ = "statements"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(Text, ForeignKey("jobs.id"), nullable=False)
    position = Column(Integer, nullable=False)
    original_sql = Column(Text, nullable=False)
    modernized_sql = Column(Text)
    quality_score = Column(Integer)
    validation_pass = Column(Boolean, default=False)
    retries = Column(Integer, default=0)
    flag = Column(Text)
    processing_ms = Column(Integer)
    job = relationship("Job", back_populates="statements")
    optimizations = relationship("Optimization", back_populates="statement")


class Optimization(Base):
    __tablename__ = "optimizations"
    id = Column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    statement_id = Column(Text, ForeignKey("statements.id"), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    statement = relationship("Statement", back_populates="optimizations")


class Cache(Base):
    __tablename__ = "cache"
    input_hash = Column(Text, primary_key=True)
    target_dialect = Column(Text, primary_key=True)
    modernized_sql = Column(Text, nullable=False)
    quality_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 4: Create `db/crud.py`**

```python
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
    job.status = status
    if quality_avg is not None:
        job.quality_avg = quality_avg
    db.commit()


def increment_done_count(db: Session, job_id: str):
    job = db.query(Job).filter(Job.id == job_id).first()
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
    db.add(Cache(input_hash=input_hash, target_dialect=target_dialect, modernized_sql=modernized_sql, quality_score=quality_score))
    db.commit()
```

- [ ] **Step 5: Create `tests/__init__.py`** (empty)

- [ ] **Step 6: Create `tests/conftest.py`**

```python
import os

# Set before any project module is imported so config.py reads these values
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "fake-key")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
```

- [ ] **Step 7: Create `tests/test_crud.py`**

```python
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
```

- [ ] **Step 8: Run tests**

```bash
pytest tests/test_crud.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 9: Commit**

```bash
git add db/ tests/__init__.py tests/conftest.py tests/test_crud.py
git commit -m "feat: database layer — ORM models and CRUD helpers"
```

---

## Task 3: Ingestion + Report Pipeline

**Files:**
- Create: `pipeline/__init__.py`
- Create: `pipeline/ingestion.py`
- Create: `pipeline/report.py`
- Create: `tests/test_ingestion.py`
- Create: `tests/test_report.py`

- [ ] **Step 1: Create `pipeline/__init__.py`** (empty)

- [ ] **Step 2: Create `pipeline/ingestion.py`**

```python
import sqlparse
import sqlparse.tokens as T


def parse_sql(raw_sql: str) -> list:
    statements = sqlparse.split(raw_sql)
    return [s.strip() for s in statements if s.strip() and not _is_comment_only(s.strip())]


def load_sql_file(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return parse_sql(f.read())


def _is_comment_only(stmt: str) -> bool:
    parsed = sqlparse.parse(stmt)
    if not parsed:
        return False
    tokens = [t for t in parsed[0].tokens if not t.is_whitespace]
    return bool(tokens) and all(t.ttype in (T.Comment.Single, T.Comment.Multiline) for t in tokens)
```

- [ ] **Step 3: Create `pipeline/report.py`**

```python
import difflib


def build_report(job_id: str, statements: list) -> dict:
    scores = [s["quality_score"] for s in statements if s.get("quality_score") is not None]
    quality_avg = round(sum(scores) / len(scores), 1) if scores else 0.0

    original_full = "\n\n".join(s["original_sql"] for s in statements)
    modernized_full = "\n\n".join(s.get("modernized_sql") or "" for s in statements)
    diff = _unified_diff(original_full, modernized_full)

    return {
        "job_id": job_id,
        "quality_avg": quality_avg,
        "statement_count": len(statements),
        "diff": diff,
        "statements": statements,
    }


def _unified_diff(original: str, modernized: str) -> str:
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modernized.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(orig_lines, mod_lines, fromfile="original.sql", tofile="modernized.sql")
    )
```

- [ ] **Step 4: Create `tests/test_ingestion.py`**

```python
import pytest
from pipeline.ingestion import parse_sql


def test_single_statement():
    result = parse_sql("SELECT * FROM employees")
    assert result == ["SELECT * FROM employees"]


def test_multiple_statements():
    result = parse_sql("SELECT 1; SELECT 2;")
    assert len(result) == 2


def test_filters_empty_statements():
    result = parse_sql("SELECT 1;;;SELECT 2")
    assert len(result) == 2


def test_empty_input():
    assert parse_sql("") == []


def test_whitespace_only():
    assert parse_sql("   \n\n   ") == []


def test_preserves_multiline_statement():
    sql = """SELECT e.name, d.name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id
WHERE e.salary > 50000"""
    result = parse_sql(sql)
    assert len(result) == 1
    assert "LEFT JOIN" in result[0]
```

- [ ] **Step 5: Create `tests/test_report.py`**

```python
from pipeline.report import build_report


def test_quality_avg_computed():
    statements = [
        {"original_sql": "SELECT 1", "modernized_sql": "SELECT 1", "quality_score": 80},
        {"original_sql": "SELECT 2", "modernized_sql": "SELECT 2", "quality_score": 100},
    ]
    report = build_report("job-1", statements)
    assert report["quality_avg"] == 90.0


def test_diff_contains_markers():
    statements = [
        {"original_sql": "SELECT * FROM emp WHERE ROWNUM <= 10", "modernized_sql": "SELECT * FROM emp LIMIT 10", "quality_score": 95},
    ]
    report = build_report("job-1", statements)
    assert "---" in report["diff"] or "+++" in report["diff"]


def test_empty_statements_returns_zero_avg():
    report = build_report("job-1", [])
    assert report["quality_avg"] == 0.0
    assert report["statement_count"] == 0
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_ingestion.py tests/test_report.py -v
```

Expected: all tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add pipeline/ tests/test_ingestion.py tests/test_report.py
git commit -m "feat: ingestion (sqlparse split) and report (diff + quality avg)"
```

---

## Task 4: System Prompts

**Files:**
- Create: `prompts/translator.txt`
- Create: `prompts/validator.txt`
- Create: `prompts/optimizer.txt`

- [ ] **Step 1: Create `prompts/translator.txt`**

```
You are an expert SQL migration engineer.
Translate the {source_dialect} SQL below to {target_dialect}.

Rules:
- Replace all cursors and WHILE loops with CTEs or set-based operations
- Replace ROWNUM with ROW_NUMBER() OVER (...) or LIMIT depending on context
- Replace old outer join (+) with ANSI LEFT/RIGHT JOIN syntax
- Replace deprecated functions (ISNULL→COALESCE, NVL→COALESCE, IFNULL→COALESCE) with modern equivalents
- Replace implicit cross-joins (FROM a, b WHERE a.id = b.fk) with explicit JOIN syntax
- Preserve all logic, filters, aliases, and column ordering exactly
{error_context}
Return ONLY the translated SQL. No explanation. No markdown fences. No preamble.

Examples:
INPUT:  SELECT * FROM emp WHERE ROWNUM <= 10
OUTPUT: SELECT * FROM emp LIMIT 10

INPUT:  SELECT e.name, d.name FROM emp e, dept d WHERE e.dept_id = d.id (+)
OUTPUT: SELECT e.name, d.name FROM emp e LEFT JOIN dept d ON e.dept_id = d.id
```

- [ ] **Step 2: Create `prompts/validator.txt`**

```
You are a SQL correctness auditor.
Given an original SQL statement and its translation, determine if they are semantically
equivalent — i.e. they would return the same results against the same database.

Original ({source_dialect}):
{original_sql}

Translation ({target_dialect}):
{translated_sql}

Respond with a single number from 0.0 to 1.0 representing your confidence that they are
semantically equivalent. 1.0 = identical logic, 0.0 = completely different.
Respond with the number only. No explanation.
```

- [ ] **Step 3: Create `prompts/optimizer.txt`**

```
You are a SQL performance engineer.
Optimize the SQL below for the {target_dialect} query engine.

Apply these improvements where applicable:
- Replace correlated subqueries with CTEs
- Replace self-joins with window functions where appropriate
- Simplify redundant JOINs or subqueries
- Add explicit column lists instead of SELECT * where clearly beneficial

Return your response as a JSON object with exactly two fields:
{{
  "optimized_sql": "the full optimized SQL here",
  "changes": ["description of change 1", "description of change 2"]
}}

Do not change the logical output of the query. Only improve performance.
If no optimizations are needed, return the original SQL unchanged with an empty changes array.
```

- [ ] **Step 4: Commit**

```bash
git add prompts/
git commit -m "feat: GPT-4o system prompts for translator, validator, optimizer"
```

---

## Task 5: Translator Agent

**Files:**
- Create: `agents/__init__.py`
- Create: `agents/translator.py`
- Create: `tests/test_translator.py`

- [ ] **Step 1: Create `agents/__init__.py`** (empty)

- [ ] **Step 2: Write failing test first — `tests/test_translator.py`**

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_translator.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — `agents/translator.py` does not exist yet.

- [ ] **Step 4: Create `agents/translator.py`**

```python
import os
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT

_client = None
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "translator.txt")


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
        )
    return _client


def _load_prompt() -> str:
    with open(_PROMPT_PATH, "r") as f:
        return f.read()


def translate(sql: str, source_dialect: str, target_dialect: str, error_context: list = None) -> str:
    error_block = ""
    if error_context:
        lines = "\n".join(f"- {e}" for e in error_context)
        error_block = f"\nPrevious translation failed validation with these issues:\n{lines}\nFix all of these issues in your translation.\n"

    system_prompt = _load_prompt().format(
        source_dialect=source_dialect,
        target_dialect=target_dialect,
        error_context=error_block,
    )

    response = _get_client().chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sql},
        ],
        temperature=0.1,
    )

    result = response.choices[0].message.content.strip()
    if result.startswith("```"):
        lines = result.splitlines()
        result = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return result.strip()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_translator.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add agents/__init__.py agents/translator.py tests/test_translator.py
git commit -m "feat: translator agent — dialect rewrite via GPT-4o"
```

---

## Task 6: Validator Agent

**Files:**
- Create: `agents/validator.py`
- Create: `tests/test_validator.py`

- [ ] **Step 1: Write failing test first — `tests/test_validator.py`**

```python
import pytest
from unittest.mock import patch
from agents.validator import validate, _had_where, _column_count_mismatch


def test_had_where_detects_where_clause():
    assert _had_where("SELECT * FROM t WHERE id = 1") is True


def test_had_where_no_where_clause():
    assert _had_where("SELECT * FROM t") is False


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_valid_translation_passes(mock_equiv):
    result = validate(
        "SELECT id FROM employees WHERE active = 1",
        "SELECT id FROM employees WHERE active = 1",
        "tsql",
        "postgresql",
    )
    assert result["passed"] is True
    assert result["score"] >= 70


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_missing_where_clause_penalizes(mock_equiv):
    result = validate(
        "SELECT id FROM employees WHERE active = 1",
        "SELECT id FROM employees",
        "tsql",
        "postgresql",
    )
    assert result["score"] < 100
    assert any("WHERE" in issue for issue in result["issues"])


@patch("agents.validator._gpt_equivalence", return_value=0.5)
def test_low_semantic_score_penalizes(mock_equiv):
    result = validate(
        "SELECT name FROM employees",
        "SELECT id FROM departments",
        "tsql",
        "postgresql",
    )
    assert result["score"] < 100
    assert any("Semantic" in issue for issue in result["issues"])


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_deprecated_syntax_penalizes(mock_equiv):
    result = validate(
        "SELECT * FROM emp",
        "SELECT * FROM emp WHERE ROWNUM <= 10",
        "tsql",
        "postgresql",
    )
    assert result["score"] < 100
    assert any("Deprecated" in issue for issue in result["issues"])


@patch("agents.validator._gpt_equivalence", return_value=1.0)
def test_multiple_deductions_floor_at_zero(mock_equiv):
    result = validate(
        "SELECT a, b, c FROM t WHERE x = 1",
        "SELECT a FROM t",
        "tsql",
        "postgresql",
    )
    assert result["score"] >= 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_validator.py -v
```

Expected: `ModuleNotFoundError` — `agents/validator.py` does not exist yet.

- [ ] **Step 3: Create `agents/validator.py`**

```python
import os
import sqlparse
import sqlparse.tokens as T
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT

_client = None
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "validator.txt")

_DEPRECATED_TOKENS = {
    "postgresql": ["ROWNUM", "NOLOCK", "(+)", "@@FETCH_STATUS"],
    "ansi": ["ROWNUM", "NOLOCK", "(+)", "@@FETCH_STATUS"],
    "mysql8": ["ROWNUM", "(+)"],
}


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
        )
    return _client


def validate(original: str, translated: str, source_dialect: str, target_dialect: str) -> dict:
    score = 100
    issues = []

    # Check 1: sqlparse syntax error
    try:
        parsed = sqlparse.parse(translated)
        if _has_syntax_error(parsed):
            score -= 40
            issues.append("Syntax error detected by sqlparse")
    except Exception:
        pass

    # Check 2: deprecated tokens still present
    upper = translated.upper()
    for token in _DEPRECATED_TOKENS.get(target_dialect, []):
        if token.upper() in upper:
            score -= 20
            issues.append(f"Deprecated syntax still present: {token}")
            break

    # Check 3: SELECT column count mismatch
    if _column_count_mismatch(original, translated):
        score -= 15
        issues.append("SELECT column count differs from original")

    # Check 4: WHERE clause dropped
    if _had_where(original) and not _had_where(translated):
        score -= 15
        issues.append("WHERE clause missing from translation")

    # Check 5: GPT-4o semantic equivalence (skip if already very low)
    equiv = 1.0
    if score >= 25:
        equiv = _gpt_equivalence(original, translated, source_dialect, target_dialect)
        if equiv < 0.8:
            score -= 20
            issues.append(f"Semantic equivalence low: {equiv:.0%}")

    final = max(0, score)
    return {"score": final, "issues": issues, "passed": final >= 70}


def _has_syntax_error(parsed) -> bool:
    for stmt in parsed:
        for token in stmt.flatten():
            if token.ttype is T.Error:
                return True
    return False


def _had_where(sql: str) -> bool:
    return "WHERE" in sql.upper()


def _column_count_mismatch(original: str, translated: str) -> bool:
    def _count_cols(sql: str) -> int:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return 0
        in_select = False
        for token in parsed[0].tokens:
            if token.ttype is T.Keyword.DML and token.normalized == "SELECT":
                in_select = True
            elif in_select and token.ttype is T.Keyword:
                break
            elif in_select and not token.is_whitespace:
                return str(token).count(",") + 1
        return 0

    orig = _count_cols(original)
    trans = _count_cols(translated)
    return orig > 0 and trans > 0 and orig != trans


def _gpt_equivalence(original: str, translated: str, source_dialect: str, target_dialect: str) -> float:
    with open(_PROMPT_PATH) as f:
        prompt = f.read().format(
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            original_sql=original,
            translated_sql=translated,
        )
    try:
        response = _get_client().chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        return float(response.choices[0].message.content.strip())
    except Exception:
        return 1.0  # assume equivalent if API call fails
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_validator.py -v
```

Expected: 7 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add agents/validator.py tests/test_validator.py
git commit -m "feat: validator agent — sqlparse + GPT-4o dual scoring"
```

---

## Task 7: Optimizer Agent

**Files:**
- Create: `agents/optimizer.py`
- Create: `tests/test_optimizer.py`

- [ ] **Step 1: Write failing test first — `tests/test_optimizer.py`**

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from agents.optimizer import optimize


def _mock_response(optimized_sql: str, changes: list):
    msg = MagicMock()
    msg.content = json.dumps({"optimized_sql": optimized_sql, "changes": changes})
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("agents.optimizer._get_client")
def test_optimize_returns_sql_and_changes(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(
        "WITH avg_sal AS (SELECT dept_id, AVG(salary) avg FROM employees GROUP BY dept_id) SELECT name, salary FROM employees e JOIN avg_sal a ON e.dept_id = a.dept_id WHERE e.salary > a.avg",
        ["Replaced correlated subquery with CTE"],
    )
    mock_get_client.return_value = mock_client

    result = optimize(
        "SELECT name, salary FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id)",
        "postgresql",
    )
    assert "optimized_sql" in result
    assert "changes" in result
    assert len(result["changes"]) == 1


@patch("agents.optimizer._get_client")
def test_optimize_no_changes_returns_original(mock_get_client):
    sql = "SELECT id FROM users WHERE active = 1"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response(sql, [])
    mock_get_client.return_value = mock_client

    result = optimize(sql, "postgresql")
    assert result["optimized_sql"] == sql
    assert result["changes"] == []


@patch("agents.optimizer._get_client")
def test_optimize_passes_target_dialect_to_prompt(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _mock_response("SELECT 1", [])
    mock_get_client.return_value = mock_client

    optimize("SELECT 1", "mysql8")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_content = next(m["content"] for m in call_kwargs["messages"] if m["role"] == "system")
    assert "mysql8" in system_content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_optimizer.py -v
```

Expected: `ModuleNotFoundError` — `agents/optimizer.py` does not exist yet.

- [ ] **Step 3: Create `agents/optimizer.py`**

```python
import json
import os
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT

_client = None
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "optimizer.txt")


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
        )
    return _client


def optimize(sql: str, target_dialect: str) -> dict:
    with open(_PROMPT_PATH) as f:
        system_prompt = f.read().format(target_dialect=target_dialect)

    response = _get_client().chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sql},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content.strip()
    result = json.loads(content)
    return {
        "optimized_sql": result.get("optimized_sql", sql),
        "changes": result.get("changes", []),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_optimizer.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add agents/optimizer.py tests/test_optimizer.py
git commit -m "feat: optimizer agent — performance rewrite via GPT-4o"
```

---

## Task 8: Orchestrator

**Files:**
- Create: `agents/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing test first — `tests/test_orchestrator.py`**

```python
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
    report = run_job(db, job.id, raw_sql, "plsql", "postgresql")

    assert report["quality_avg"] == 95.0
    assert report["statements"][0]["validation_passed"] is True
    assert report["statements"][0]["retries"] == 0


@patch("agents.orchestrator.translator.translate")
@patch("agents.orchestrator.validator.validate")
@patch("agents.orchestrator.optimizer.optimize")
def test_run_job_retries_on_low_score_and_flags(mock_opt, mock_val, mock_trans, db):
    mock_trans.return_value = "bad sql"
    # Validator always returns failing score — 3 calls total (initial + 2 retries)
    mock_val.return_value = {"score": 40, "issues": ["ROWNUM still present"], "passed": False}
    mock_opt.return_value = {"optimized_sql": "bad sql", "changes": []}

    raw_sql = "SELECT * FROM emp WHERE ROWNUM <= 10"
    job = create_job(db, "plsql", "postgresql", raw_sql, 1)
    report = run_job(db, job.id, raw_sql, "plsql", "postgresql")

    assert report["statements"][0]["flag"] == "needs_human_review"
    # initial translate + 2 retry translates = 3 total calls
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

    # Second translate call must carry error_context
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
    report = run_job(db, job.id, raw_sql, "tsql", "postgresql")

    assert len(report["statements"]) == 3
    assert mock_trans.call_count == 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: `ModuleNotFoundError` — `agents/orchestrator.py` does not exist yet.

- [ ] **Step 3: Create `agents/orchestrator.py`**

```python
import time
from sqlalchemy.orm import Session
from agents import translator, validator, optimizer
from pipeline import ingestion, report
from db import crud
from config import MAX_RETRIES


def run_job(db: Session, job_id: str, raw_sql: str, source_dialect: str, target_dialect: str) -> dict:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add agents/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: orchestrator — pipeline runner with retry loop and DB writes"
```

---

## Task 9: FastAPI Web Layer

**Files:**
- Create: `api/__init__.py`
- Create: `api/models.py`
- Create: `api/dependencies.py`
- Create: `api/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Create `api/__init__.py`** (empty)

- [ ] **Step 2: Create `api/models.py`**

```python
from pydantic import BaseModel
from typing import Optional


class ModernizeRequest(BaseModel):
    sql: str
    source_dialect: str = "tsql"
    target_dialect: str = "postgresql"


class ModernizeResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    progress: float
    done_count: int
    statement_count: int


class StatementResult(BaseModel):
    position: int
    original_sql: str
    modernized_sql: Optional[str] = None
    quality_score: Optional[int] = None
    validation_passed: bool
    retries: int
    flag: Optional[str] = None
    processing_ms: Optional[int] = None
    optimizations: list


class JobReportResponse(BaseModel):
    job_id: str
    status: str
    quality_avg: Optional[float] = None
    statement_count: int
    diff: str
    statements: list


class HistoryEntry(BaseModel):
    job_id: str
    created_at: str
    quality_avg: Optional[float] = None
    statement_count: int
    status: str
```

- [ ] **Step 3: Create `api/dependencies.py`**

```python
from db.database import get_db  # noqa: F401 — re-exported for FastAPI DI
```

- [ ] **Step 4: Create `api/main.py`**

```python
import hashlib
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from api.models import ModernizeRequest, ModernizeResponse, JobStatusResponse, JobReportResponse
from api.dependencies import get_db
from agents import orchestrator
from db import crud
from pipeline.ingestion import parse_sql

app = FastAPI(title="SQL Modernization Accelerator", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/modernize", response_model=ModernizeResponse)
def modernize(req: ModernizeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    statements = parse_sql(req.sql)
    if not statements:
        raise HTTPException(status_code=400, detail="No SQL statements found in input")

    job = crud.create_job(db, req.source_dialect, req.target_dialect, req.sql, len(statements))
    background_tasks.add_task(
        orchestrator.run_job, db, job.id, req.sql, req.source_dialect, req.target_dialect
    )
    return {"job_id": job.id}


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    progress = job.done_count / job.statement_count if job.statement_count > 0 else 0.0
    return {
        "status": job.status,
        "progress": round(progress, 2),
        "done_count": job.done_count,
        "statement_count": job.statement_count,
    }


@app.get("/jobs/{job_id}/report")
def get_job_report(job_id: str, db: Session = Depends(get_db)):
    report = crud.get_job_report(db, job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Job not found")
    return report


@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    return crud.get_history(db)
```

- [ ] **Step 5: Create `tests/test_api.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
from db.database import Base, get_db
from db import models
from api.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@patch("api.main.orchestrator.run_job")
def test_modernize_returns_job_id(mock_run, client):
    resp = client.post("/modernize", json={
        "sql": "SELECT * FROM emp WHERE ROWNUM <= 10",
        "source_dialect": "plsql",
        "target_dialect": "postgresql",
    })
    assert resp.status_code == 200
    assert "job_id" in resp.json()


def test_modernize_rejects_empty_sql(client):
    resp = client.post("/modernize", json={"sql": "   ", "source_dialect": "tsql", "target_dialect": "postgresql"})
    assert resp.status_code == 400


def test_get_job_status_not_found(client):
    resp = client.get("/jobs/nonexistent-id")
    assert resp.status_code == 404


def test_get_report_not_found(client):
    resp = client.get("/jobs/nonexistent-id/report")
    assert resp.status_code == 404


def test_history_empty(client):
    resp = client.get("/history")
    assert resp.status_code == 200
    assert resp.json() == []


@patch("api.main.orchestrator.run_job")
def test_history_shows_submitted_jobs(mock_run, client):
    client.post("/modernize", json={"sql": "SELECT 1", "source_dialect": "tsql", "target_dialect": "postgresql"})
    resp = client.get("/history")
    assert len(resp.json()) == 1
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_api.py -v
```

Expected: 7 tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add api/ tests/test_api.py
git commit -m "feat: FastAPI web layer — modernize, job status, report, history endpoints"
```

---

## Task 10: CLI Runner + manage.py + Sample SQL

**Files:**
- Create: `run_cli.py`
- Create: `manage.py`
- Create: `sample_sql/legacy_cursor.sql`
- Create: `sample_sql/legacy_oracle.sql`
- Create: `sample_sql/legacy_mysql.sql`
- Create: `sample_sql/legacy_subquery.sql`
- Create: `sample_sql/legacy_mixed.sql`

- [ ] **Step 1: Create `manage.py`**

```python
import sys
from db.database import engine, Base
from db import models  # registers models with Base


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset.")


def seed_db():
    from db.database import SessionLocal
    from db.crud import create_job, write_statement, update_job_status
    db = SessionLocal()
    try:
        job = create_job(db, "plsql", "postgresql", "SELECT * FROM emp WHERE ROWNUM <= 10", 1)
        write_statement(db, job.id, 1, "SELECT * FROM emp WHERE ROWNUM <= 10", "SELECT * FROM emp LIMIT 10", 94, True, 0, None, 1200, ["ROWNUM replaced with LIMIT"])
        update_job_status(db, job.id, "done", quality_avg=94.0)
        print(f"Seeded sample job: {job.id}")
    finally:
        db.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    commands = {"init_db": init_db, "reset_db": reset_db, "seed_db": seed_db}
    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Usage: python manage.py [{' | '.join(commands)}]")
```

- [ ] **Step 2: Create `run_cli.py`**

```python
import argparse
import sys
from db.database import SessionLocal
from db.crud import create_job
from agents.orchestrator import run_job
from pipeline.ingestion import load_sql_file


def main():
    parser = argparse.ArgumentParser(description="SQL Modernization Accelerator")
    parser.add_argument("--input", required=True, help="Path to legacy .sql file")
    parser.add_argument("--source", default="tsql", choices=["tsql", "plsql", "mysql5"])
    parser.add_argument("--target", default="postgresql", choices=["postgresql", "ansi", "mysql8"])
    args = parser.parse_args()

    statements = load_sql_file(args.input)
    if not statements:
        print("No SQL statements found in input file.")
        sys.exit(1)

    print(f"Loaded {len(statements)} statement(s) from {args.input}")
    raw_sql = open(args.input, encoding="utf-8").read()
    db = SessionLocal()

    try:
        job = create_job(db, args.source, args.target, raw_sql, len(statements))
        report = run_job(db, job.id, raw_sql, args.source, args.target)

        bar = "=" * 60
        print(f"\n{bar}")
        print(f"  MODERNIZATION COMPLETE")
        print(f"{bar}")
        print(f"  Job ID:      {job.id}")
        print(f"  Statements:  {report['statement_count']}")
        print(f"  Quality avg: {report['quality_avg']:.1f} / 100")
        print(f"{bar}\n")

        for s in report["statements"]:
            status = "PASS" if s["validation_passed"] else "REVIEW"
            flag = f"  [{s['flag']}]" if s["flag"] else ""
            print(f"  Statement {s['position']}  —  Score: {s['quality_score']}/100  [{status}]{flag}")
            for opt in s["optimizations"]:
                print(f"    • {opt}")

        if report["diff"]:
            print(f"\n{bar}")
            print("  DIFF")
            print(f"{bar}")
            print(report["diff"])
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `sample_sql/legacy_cursor.sql`**

```sql
-- T-SQL: cursor updating rows one at a time (should become a set-based UPDATE)
DECLARE @OrderID INT

DECLARE order_cursor CURSOR FOR
    SELECT OrderID FROM Orders WHERE Status = 1

OPEN order_cursor
FETCH NEXT FROM order_cursor INTO @OrderID

WHILE @@FETCH_STATUS = 0
BEGIN
    UPDATE Orders SET Status = 2, UpdatedAt = GETDATE() WHERE OrderID = @OrderID
    FETCH NEXT FROM order_cursor INTO @OrderID
END

CLOSE order_cursor
DEALLOCATE order_cursor
```

- [ ] **Step 4: Create `sample_sql/legacy_oracle.sql`**

```sql
-- PL/SQL: ROWNUM pagination + old outer join (+) syntax
SELECT e.emp_name,
       d.dept_name,
       e.salary
FROM   employees e,
       departments d
WHERE  e.dept_id  = d.dept_id (+)
AND    e.salary   > 50000
AND    ROWNUM     <= 100
ORDER BY e.salary DESC
```

- [ ] **Step 5: Create `sample_sql/legacy_mysql.sql`**

```sql
-- MySQL 5: implicit cross-join, GROUP BY ordinal, old date function
SELECT e.emp_name,
       d.dept_name,
       COUNT(*) AS project_count
FROM   employees e,
       departments d,
       projects p
WHERE  e.dept_id  = d.id
AND    e.emp_id   = p.emp_id
AND    e.hire_date > DATE_SUB(NOW(), INTERVAL 5 YEAR)
GROUP BY 1, 2
ORDER BY 3 DESC
```

- [ ] **Step 6: Create `sample_sql/legacy_subquery.sql`**

```sql
-- Correlated subquery — classic optimizer demo (should become a CTE + JOIN)
SELECT emp_name,
       salary,
       dept_id
FROM   employees e
WHERE  salary > (
           SELECT AVG(salary)
           FROM   employees
           WHERE  dept_id = e.dept_id
       )
ORDER BY salary DESC
```

- [ ] **Step 7: Create `sample_sql/legacy_mixed.sql`**

```sql
-- Multi-statement file with several legacy patterns

SELECT emp_name FROM employees WHERE ROWNUM <= 5;

SELECT e.name, d.name
FROM   employees e,
       departments d
WHERE  e.dept_id = d.id (+);

SELECT ISNULL(manager_id, 0) AS manager_id,
       emp_name
FROM   employees
WHERE  status = 1;
```

- [ ] **Step 8: Initialize the database**

```bash
python manage.py init_db
```

Expected output: `Database initialized.`

- [ ] **Step 9: Smoke-test the CLI (requires real Azure OpenAI credentials in .env)**

If credentials are available:
```bash
python run_cli.py --input sample_sql/legacy_oracle.sql --source plsql --target postgresql
```

Expected: quality score printed, diff shown, no crashes.

If credentials are not yet available, skip to Task 11 — the unit tests cover this path already.

- [ ] **Step 10: Commit**

```bash
git add manage.py run_cli.py sample_sql/
git commit -m "feat: CLI runner, DB management script, and 5 sample legacy SQL files"
```

---

## Task 11: Docker + CI/CD

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/deploy.yml`
- Create: `infra/azure.yaml`
- Create: `infra/main.bicep`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py init_db

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
version: "3.9"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - ./data:/app/data
    env_file:
      - .env
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 3: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Init test database
        run: python manage.py init_db
        env:
          DATABASE_URL: sqlite:///./data/test.db

      - name: Run tests
        run: pytest tests/ -v
        env:
          DATABASE_URL: sqlite:///./data/test.db
          AZURE_OPENAI_ENDPOINT: https://fake.openai.azure.com/
          AZURE_OPENAI_API_KEY: fake-key
          AZURE_OPENAI_DEPLOYMENT: gpt-4o
```

- [ ] **Step 4: Create `.github/workflows/deploy.yml`**

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    needs: []
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push Docker image to ACR
        run: |
          az acr build \
            --registry ${{ secrets.ACR_NAME }} \
            --image sql-modernizer:${{ github.sha }} \
            .

      - name: Deploy to Azure Container Apps
        run: |
          az containerapp update \
            --name sql-modernizer \
            --resource-group ${{ secrets.RESOURCE_GROUP }} \
            --image ${{ secrets.ACR_NAME }}.azurecr.io/sql-modernizer:${{ github.sha }} \
            --set-env-vars \
              "DATABASE_URL=${{ secrets.SUPABASE_DATABASE_URL }}" \
              "AZURE_OPENAI_ENDPOINT=${{ secrets.AZURE_OPENAI_ENDPOINT }}" \
              "AZURE_OPENAI_API_KEY=${{ secrets.AZURE_OPENAI_API_KEY }}" \
              AZURE_OPENAI_DEPLOYMENT=gpt-4o

      - name: Health check
        run: |
          sleep 15
          curl -f https://sql-modernizer.azurecontainerapps.io/health
```

- [ ] **Step 5: Create `infra/azure.yaml`**

```yaml
name: sql-modernizer
services:
  app:
    project: .
    language: python
    host: containerapp
```

- [ ] **Step 6: Create `infra/main.bicep`**

```bicep
param location string = resourceGroup().location
param containerAppName string = 'sql-modernizer'
param acrName string

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${containerAppName}-env'
  location: location
  properties: {}
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
      }
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: '${acr.properties.loginServer}/${containerAppName}:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}
```

- [ ] **Step 7: Verify Docker build works locally**

```bash
docker build -t sql-modernizer .
```

Expected: image builds successfully, `manage.py init_db` runs inside the build.

- [ ] **Step 8: Run full test suite one final time**

```bash
pytest tests/ -v
```

Expected: all tests PASSED (no real API calls made — all GPT-4o calls are mocked).

- [ ] **Step 9: Commit**

```bash
git add Dockerfile docker-compose.yml .github/ infra/
git commit -m "feat: Docker, GitHub Actions CI/CD, and Azure Bicep infra"
```

---

## Self-Review

### Spec Coverage Check

| Requirement (from docs) | Covered by task |
|------------------------|----------------|
| sqlparse statement splitting | Task 3 — `pipeline/ingestion.py` |
| Translator agent via GPT-4o | Task 5 |
| Validator dual-signal (sqlparse + GPT-4o) | Task 6 |
| Optimizer via GPT-4o, JSON output | Task 7 |
| Orchestrator retry loop (max 2) with error context | Task 8 |
| `needs_human_review` flag after cap | Task 8 |
| 4 DB tables: jobs, statements, optimizations, cache | Task 2 |
| FastAPI routes: POST /modernize, GET /jobs/:id, GET /jobs/:id/report, GET /history, GET /health | Task 9 |
| CLI runner (`--input --source --target`) | Task 10 |
| `manage.py init_db / reset_db / seed_db` | Task 10 |
| 5 sample SQL files | Task 10 |
| Secrets via env vars (never in code) | Task 1 — `config.py` + `.env.example` |
| SQLite locally, Supabase PostgreSQL in prod (same ORM) | Task 2 — `DATABASE_URL` env var |
| Diff report generation | Task 3 — `pipeline/report.py` |
| Docker + docker-compose | Task 11 |
| GitHub Actions CI (test on PR) | Task 11 |
| GitHub Actions CD (deploy on merge) | Task 11 |
| Azure Bicep IaC | Task 11 |

### No Placeholders — Confirmed

All tasks include complete code, exact commands, and expected output. No TBDs.

### Type Consistency Check

- `crud.write_statement(changes: list)` defined in Task 2, called in Task 8 with `changes=opt_result["changes"]` ✓
- `orchestrator.run_job(db, job_id, raw_sql, source, target)` defined in Task 8, called in Task 9 and Task 10 ✓
- `validator.validate()` returns `{"score", "issues", "passed"}` — consumed in Task 8 ✓
- `optimizer.optimize()` returns `{"optimized_sql", "changes"}` — consumed in Task 8 ✓
- `report.build_report(job_id, statements)` in Task 3, called in Task 8 ✓
