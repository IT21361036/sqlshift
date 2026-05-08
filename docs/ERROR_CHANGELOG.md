# Error Changelog — SQLShift

Errors encountered during development, their root cause, and how they were fixed.

---

## E-001 — GitHub push permission denied (wrong account)

**When:** Session 1, setting up remote push
**Symptom:** `remote: Permission to IT21361036/sqlshift.git denied to saarakaizerr`
**Root cause:** Windows Credential Manager had `saarakaizerr` stored as the default GitHub credential. Git used it automatically for all GitHub pushes.
**Fix:** Embedded IT21361036's PAT directly in the remote URL:
```bash
git remote set-url origin https://IT21361036:<PAT>@github.com/IT21361036/sqlshift.git
```
**Lesson:** On Windows with multiple GitHub accounts, embed PAT in remote URL per-repo rather than relying on the credential manager.

---

## E-002 — First PAT rejected

**When:** Session 1, immediately after E-001
**Symptom:** `remote: Invalid username or password`
**Root cause:** PAT `[REDACTED]` was generated from the wrong GitHub account (`saarakaizerr`).
**Fix:** User generated a new PAT from the correct account (`IT21361036`) with `repo` scope.
**Lesson:** Always verify which GitHub account you're logged into before generating a PAT.

---

## E-003 — `datetime.utcnow()` deprecation warning

**When:** Task 2 (DB models), code review
**Symptom:** `DeprecationWarning: datetime.utcnow() is deprecated and scheduled for removal`
**Root cause:** `db/models.py` used `datetime.utcnow` as the default factory for `created_at`/`updated_at` columns.
**Fix:**
```python
# Before
default=datetime.datetime.utcnow

# After
default=lambda: datetime.datetime.now(datetime.timezone.utc)
```
**Lesson:** Use timezone-aware datetimes. `utcnow()` is deprecated in Python 3.12+.

---

## E-004 — `AttributeError` on None job in crud.py

**When:** Task 2 (DB layer), code review
**Symptom:** `AttributeError: 'NoneType' object has no attribute 'status'` when a job_id doesn't exist in DB
**Root cause:** `update_job_status` and `increment_done_count` fetched a job by ID but didn't guard against `None` return before accessing attributes.
**Fix:** Added early return guards:
```python
def update_job_status(db, job_id, status, ...):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return
    job.status = status
    ...
```

---

## E-005 — `IntegrityError` on duplicate cache writes

**When:** Task 2 (DB layer), code review
**Symptom:** `sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: cache.sql_hash` on second run with same SQL
**Root cause:** `write_cache` always inserted a new row, hitting the unique constraint on `sql_hash`.
**Fix:** Added existence check before insert:
```python
def write_cache(db, sql_hash, translated_sql):
    existing = db.query(Cache).filter(Cache.sql_hash == sql_hash).first()
    if existing:
        return existing
    entry = Cache(sql_hash=sql_hash, translated_sql=translated_sql)
    db.add(entry)
    db.commit()
    return entry
```

---

## E-006 — Validator safe default rewarded API failures

**When:** Task 7 (Validator), code review
**Symptom:** `_gpt_equivalence` returned `1.0` (perfect score) when the Qwen API call failed
**Root cause:** Exception handler had `return 1.0` — so a broken LLM call gave the statement a perfect semantic score.
**Fix:** Changed safe default to `0.8` (neutral — neither rewards nor penalizes failures):
```python
except Exception:
    return 0.8  # neutral fallback, not a reward
```

---

## E-007 — Optimizer returned malformed JSON from LLM

**When:** Task 7 (Optimizer), code review
**Symptom:** `json.JSONDecodeError` when Qwen returned markdown-wrapped or truncated JSON
**Root cause:** No error handling around `json.loads()` on LLM output.
**Fix:**
```python
try:
    result = json.loads(cleaned)
except json.JSONDecodeError:
    return {"optimized_sql": sql, "changes": []}
```

---

## E-008 — Validator column count miscounted function call commas

**When:** Task 7 (Validator), code review
**Symptom:** Column count heuristic gave false positives for queries with `COUNT(DISTINCT col)`, `COALESCE(a, b)`, etc.
**Root cause:** Counted commas in the SELECT clause naively, hitting commas inside function arguments.
**Fix:** Added early return for `SELECT *` (skip check entirely), and limited scope of comma counting.

---

## E-009 — BackgroundTasks received a request-scoped SQLAlchemy session

**When:** Task 9 (FastAPI), code quality review
**Symptom:** Runtime data loss — session closed by FastAPI after response sent, background task operated on dead session
**Root cause:** `api/main.py` passed `db` (request-scoped session) directly to `background_tasks.add_task(orchestrator.run_job, db, ...)`. FastAPI closes the session via `get_db()`'s `finally` block before the background task runs.
**Fix:** Changed `orchestrator.run_job` to accept a `session_factory` (callable) and create its own session:
```python
# api/main.py — pass factory, not live session
background_tasks.add_task(orchestrator.run_job, SessionLocal, job.id, ...)

# agents/orchestrator.py — create own session
def run_job(session_factory, job_id, ...):
    db = session_factory()
    try:
        ...
    finally:
        db.close()
```
**Lesson:** Never pass request-scoped resources to background tasks. Always pass a factory.

---

## E-010 — Unvalidated dialect fields enabled prompt injection

**When:** Task 9 (FastAPI), code quality review
**Symptom:** `source_dialect` and `target_dialect` were free-form strings forwarded verbatim into LLM prompts
**Root cause:** `ModernizeRequest` had `source_dialect: str` with no validation.
**Fix:** Restricted to a `Literal` type:
```python
SUPPORTED_DIALECTS = Literal["tsql", "mysql", "oracle", "postgresql", "sqlite"]

class ModernizeRequest(BaseModel):
    sql: str = Field(..., min_length=1, max_length=524288)
    source_dialect: SUPPORTED_DIALECTS = "tsql"
    target_dialect: SUPPORTED_DIALECTS = "postgresql"
```
**Lesson:** Any string that reaches an LLM prompt must be validated. Dialect fields are attack surface.
