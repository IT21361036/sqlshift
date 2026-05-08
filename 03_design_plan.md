# Design Plan — SQL Modernization Accelerator

## Core Design Decisions

### Decision 1 — Single Responsibility Per Agent

Each agent has exactly one job:

- **Translator** — only translates SQL dialect. Nothing else.
- **Validator** — only scores correctness. Returns issues, not fixes.
- **Optimizer** — only rewrites for performance. Never translates.
- **Orchestrator** — only routes and assembles. Never calls GPT-4o directly.

**Why:** Single-responsibility makes each agent's system prompt focused and tight.
A focused prompt produces better GPT-4o output. It also makes debugging clean —
if translation fails, you open `translator.py` and its prompt file. Nothing else.

---

### Decision 2 — Retry Loop With Error Context

When Validator scores below 70/100, the Orchestrator re-runs the Translator
with the specific validation issues appended to the prompt.

```python
# Bad: blind retry — GPT-4o has no idea what went wrong
translated = await translator.run(stmt, source, target)

# Good: retry with error context — GPT-4o knows exactly what to fix
translated = await translator.run(
    stmt, source, target,
    error_context=validation_result.issues
)
```

**Retry cap:** Maximum 2 retries. After cap, statement is flagged
`needs_human_review` and the pipeline continues to the next statement.
Never blocks the whole job on one bad statement.

---

### Decision 3 — SQL Parsed Into Statements Before Agents Run

The ingestion layer splits the input file into individual statements using
`sqlparse` before any agent runs. Each statement is processed independently.

**Why:**
- Avoids token limit issues (one stored procedure per call, not whole file)
- Enables per-statement quality scores in the report
- Makes retry logic granular — one bad statement doesn't re-run all others
- Enables parallel processing in a future version

---

### Decision 4 — Dual Validation Signal

Validator uses two independent checks and combines them into a score:

1. `sqlparse` library — fast, deterministic syntax check
2. GPT-4o — semantic equivalence check ("does this SQL do the same thing?")

Both must pass for a high score. Using only GPT-4o risks confident wrong answers.
Using only `sqlparse` misses semantic errors. Together they catch more.

---

### Decision 5 — Secrets Never in Code

| Environment | Secret storage |
|-------------|---------------|
| Local dev | `.env` file, loaded by `python-dotenv` |
| Production | Azure Key Vault, injected as env vars by Container Apps at startup |

`.env` is in `.gitignore`. Only `.env.example` (with placeholder values) is committed.

---

### Decision 6 — SQLite Locally, Azure SQL in Production

Same SQLAlchemy ORM code works against both. Switch by changing `DATABASE_URL`
in the environment variables. Zero code changes needed for production deployment.

---

## API Contract

```
POST /modernize
  Request:  { sql: string, source_dialect: string, target_dialect: string }
  Response: { job_id: "uuid" }

GET /jobs/:id
  Response: { status: "pending|running|done|failed", progress: 0.0–1.0 }

GET /jobs/:id/report
  Response: {
    quality_avg: number,
    statements: [ { original_sql, modernized_sql, score, optimizations } ],
    diff: string
  }

GET /history
  Response: [ { job_id, created_at, quality_avg, statement_count } ]

GET /health
  Response: { status: "ok", version: "1.0.0" }
```

---

## Supported Dialects

| Source dialect | Notes |
|---------------|-------|
| `tsql` | Microsoft SQL Server — cursors, NOLOCK, deprecated syntax |
| `plsql` | Oracle — ROWNUM, CONNECT BY, old outer join `(+)` |
| `mysql5` | Old MySQL — implicit joins, non-standard functions |

| Target dialect | Notes |
|---------------|-------|
| `postgresql` | Default target — modern, open, widely supported |
| `ansi` | ANSI SQL 2016 standard |
| `mysql8` | Modern MySQL with ANSI compatibility |

---

## Quality Scoring Logic

```
score = 100

Deductions:
  sqlparse syntax error found:        -40
  semantic equivalence GPT score < 80%: -20
  deprecated syntax still present:    -20
  column count mismatch detected:     -15
  missing WHERE clause (if original had one): -15

score = max(0, score)
threshold to pass: 70
```

Scores are stored per-statement in the `statements` table and averaged
for the job-level `quality_avg` in the `jobs` table.

---

## Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| GPT-4o timeout | Retry once after 5s, then flag statement as `api_error` |
| sqlparse crash | Log error, skip syntax check, use GPT-4o score only |
| Score < 70 after 2 retries | Flag as `needs_human_review`, continue pipeline |
| Entire job fails | Set job `status = "failed"`, return partial results |
| Duplicate SQL submitted | Return cached result from `cache` table, skip agents |
