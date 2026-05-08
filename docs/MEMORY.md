# Project Memory — SQLShift

## What This Project Is

Multi-agent Python pipeline that converts legacy SQL (T-SQL, PL/SQL, old MySQL) to modern PostgreSQL/ANSI SQL. Built as a portfolio project.

---

## Architecture Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| LLM provider | Ollama + `qwen2.5-coder:7b` | Free, local, no API key needed for portfolio |
| Database (local) | SQLite | Zero setup, file-based |
| Database (prod) | Supabase PostgreSQL | Free tier, PostgreSQL-native, easy to demo |
| DB swap mechanism | `DATABASE_URL` env var only | Same SQLAlchemy ORM, no code change |
| Web framework | FastAPI | Async, auto-docs, modern Python |
| Orchestration | Custom Python (no Foundry IQ) | Foundry IQ is hackathon-only, not needed here |
| Frontend | None (CLI + REST API) | Explicitly ruled out in design plan; may add later |

---

## 4-Agent Design

| Agent | File | LLM? | Responsibility |
|-------|------|------|----------------|
| Orchestrator | `agents/orchestrator.py` | No | Routes statements, drives retry loop, writes DB |
| Translator | `agents/translator.py` | Yes | Dialect rewrite via Qwen |
| Validator | `agents/validator.py` | Yes | sqlparse syntax check + Qwen semantic score (0–100) |
| Optimizer | `agents/optimizer.py` | Yes | Performance rewrites, returns `{optimized_sql, changes}` |

**Retry loop:** Orchestrator retries up to `MAX_RETRIES=2` times if Validator score < `VALIDATION_THRESHOLD=70`. Passes Validator error list back to Translator as `error_context`. After cap → sets `flag="needs_human_review"`.

---

## LLM Client

All agents share one client via `agents/llm_client.py`:

```python
client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
def call_qwen(system_prompt, user_message) -> str
```

Ollama uses the OpenAI-compatible API, so the standard `openai` SDK works with `base_url="http://localhost:11434/v1"`.

---

## Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./data/sqlshift.db` | Swap SQLite ↔ Supabase |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Model to use |
| `MAX_RETRIES` | `2` | Retry cap per statement |
| `VALIDATION_THRESHOLD` | `70` | Min score to pass |

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Health check |
| POST | `/modernize` | Submit SQL job (async, returns job_id) |
| GET | `/jobs/{id}` | Job status |
| GET | `/jobs/{id}/report` | Full report with diffs |
| GET | `/history` | All past jobs |

---

## Test Strategy

- All LLM calls mocked in tests (no Ollama server needed)
- `conftest.py` sets `DATABASE_URL=sqlite:///:memory:` before imports
- Tests mock `agents.<module>.call_qwen` directly
- API tests use `TestClient` with in-memory SQLite override via `app.dependency_overrides`

---

## Git Workflow

- All development on `feat/implementation`
- Merge to `main` via PR only
- Worktree at `e:\Sproject\.worktrees\implementation`
- Remote: `https://github.com/IT21361036/sqlshift.git`
