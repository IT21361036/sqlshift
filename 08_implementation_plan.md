# Implementation Plan — SQL Modernization Accelerator

## Before the Hackathon (Do Now)

### Today — Request Azure OpenAI Access

Go to [portal.azure.com](https://portal.azure.com) → Create resource → Azure OpenAI.
Deploy a `gpt-4o` model inside the resource.

> **This is the most critical pre-step.** Microsoft manually approves OpenAI resource
> creation. It can take 24–48 hours. If you wait until May 25, you may have no AI
> access on Day 1 of the hackathon.

### This Week — Dev Environment Setup

```bash
# Install tools
brew install azd                          # Mac
winget install microsoft.azd             # Windows

# Verify Python
python --version                          # needs 3.11+

# Install project dependencies
pip install openai azure-identity python-dotenv sqlparse sqlalchemy fastapi uvicorn pytest

# Test Azure OpenAI connection from Python
python -c "
import openai, os
from dotenv import load_dotenv
load_dotenv()
client = openai.AzureOpenAI(
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version='2024-02-01'
)
r = client.chat.completions.create(
    model='gpt-4o',
    messages=[{'role': 'user', 'content': 'Say: connection works'}]
)
print(r.choices[0].message.content)
"
```

If you see "connection works" — your Azure OpenAI is ready.

### Before May 26 — Sample SQL + azd Test

1. Create `sample_sql/` folder with 5–8 legacy SQL files (see Appendix below)
2. Run `azd up` on a minimal Hello World FastAPI app to confirm deployment works
3. Create your GitHub repo: `sql-modernization-agent`
4. Register for the hackathon on the Microsoft Partner Skilling Hub

---

## Hackathon Day 1 — May 26

### 8:00–10:00 AM — Ingestion + Translator

**Goal:** Raw SQL file in → translated SQL out

- [ ] `pipeline/ingestion.py` — `sqlparse.split()` on raw input
- [ ] `prompts/translator.txt` — write system prompt with few-shot examples
- [ ] `agents/translator.py` — call Azure OpenAI, return SQL string
- [ ] `python run_cli.py --input sample_sql/legacy_cursor.sql --source tsql --target postgresql`
- [ ] Verify: GPT-4o returns translated SQL only (no markdown, no explanation)

### 10:00 AM–12:00 PM — Validator + Retry Loop

**Goal:** Translation is scored; bad translations are corrected automatically

- [ ] `agents/validator.py` — sqlparse check + GPT-4o semantic check + scoring
- [ ] Retry logic in `agents/orchestrator.py` — max 2 retries with error context
- [ ] Test: submit a deliberately broken translation, confirm retry fires
- [ ] Test: confirm `needs_human_review` flag appears after 2 failed retries

### 12:00–3:00 PM — Orchestrator + Database

**Goal:** Full pipeline runs end-to-end, results stored in DB

- [ ] `db/database.py` + `db/models.py` + `db/crud.py`
- [ ] `python manage.py init_db`
- [ ] Wire all agents in `agents/orchestrator.py`
- [ ] Run full pipeline on all 5 sample SQL files
- [ ] Verify results appear in SQLite with correct scores and retry counts

### 3:00–5:00 PM — Fixes + Polish

**Goal:** Stable, passing, all sample files modernized cleanly

- [ ] Fix any prompt issues discovered during testing
- [ ] Write unit tests in `tests/` for at least translator and validator
- [ ] Commit everything to GitHub
- [ ] Write Day 1 progress notes in README

---

## Hackathon Day 2 — May 27

### 8:00–10:00 AM — Optimizer + Report Layer

**Goal:** Output includes performance improvements and diff view

- [ ] `prompts/optimizer.txt` — write optimizer system prompt
- [ ] `agents/optimizer.py` — call GPT-4o, parse JSON response
- [ ] `pipeline/report.py` — generate diff + quality summary
- [ ] Optional: `api/main.py` — FastAPI routes wrapping the pipeline
- [ ] Test optimizer on a correlated subquery → confirm CTE rewrite

### 10:00 AM–12:00 PM — Deploy to Azure

**Goal:** Live URL, anyone can use it

- [ ] Write `Dockerfile` and test locally: `docker build && docker run`
- [ ] `azd up` — provision Azure resources and deploy
- [ ] Verify live endpoint: `curl POST /modernize` with sample SQL
- [ ] Open Azure Monitor — confirm agent traces are visible
- [ ] Set up App Insights alerts for error rates

### 12:00–1:00 PM — Portfolio Polish

**Goal:** Project looks great on GitHub and LinkedIn

- [ ] Record 2-minute demo GIF (legacy SQL in → diff report out)
- [ ] Update README with: live URL, architecture diagram, setup instructions, example output
- [ ] Write LinkedIn post: explain the 4-agent design and what you learned
- [ ] Confirm badge criteria: both days attended, 2 projects completed

---

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Azure OpenAI approval pending on Day 1 | Request access today. Fallback: use OpenAI directly by swapping `AZURE_OPENAI_ENDPOINT` |
| One SQL statement causes infinite retry | Hard cap: `max_retries = 2` in orchestrator. After cap → `needs_human_review` |
| Token limit exceeded on large stored procedure | Ingestion splits by statement. Add `len(stmt) > 4000` check → skip with warning |
| azd deployment fails during hackathon | Test `azd up` before May 26 on a Hello World app |
| No time for FastAPI web UI | Drop it. CLI tool + deployed API endpoint is a complete portfolio project |
| GPT-4o returns markdown fences in SQL | Strip with: `sql.strip().strip('`').strip()` |

---

## Appendix — Sample Legacy SQL Files to Create

### `sample_sql/legacy_cursor.sql` (T-SQL)
```sql
DECLARE @OrderID INT
DECLARE order_cursor CURSOR FOR
    SELECT OrderID FROM Orders WHERE Status = 1
OPEN order_cursor
FETCH NEXT FROM order_cursor INTO @OrderID
WHILE @@FETCH_STATUS = 0
BEGIN
    UPDATE Orders SET Status = 2 WHERE OrderID = @OrderID
    FETCH NEXT FROM order_cursor INTO @OrderID
END
CLOSE order_cursor
DEALLOCATE order_cursor
```

### `sample_sql/legacy_oracle.sql` (PL/SQL)
```sql
SELECT e.emp_name, d.dept_name
FROM employees e, departments d
WHERE e.dept_id = d.dept_id (+)
AND   e.salary > 50000
AND   ROWNUM <= 100
```

### `sample_sql/legacy_subquery.sql` (correlated subquery for Optimizer)
```sql
SELECT emp_name, salary
FROM employees e
WHERE salary > (
    SELECT AVG(salary)
    FROM employees
    WHERE dept_id = e.dept_id
)
ORDER BY salary DESC
```
