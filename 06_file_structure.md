# File Structure — SQL Modernization Accelerator

## Complete Project Layout

```
sql-modernization-agent/
│
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py          # main pipeline, retry loop, DB writes
│   ├── translator.py            # dialect translation + few-shot prompts
│   ├── validator.py             # syntax + semantic validation, scoring
│   └── optimizer.py             # performance rewrites, index hints
│
├── pipeline/
│   ├── __init__.py
│   ├── ingestion.py             # parse .sql file into statement list
│   └── report.py                # diff generation + quality summary builder
│
├── api/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app + all routes (optional)
│   ├── models.py                # Pydantic request/response schemas
│   └── dependencies.py          # shared FastAPI deps (DB session, auth)
│
├── db/
│   ├── __init__.py
│   ├── database.py              # SQLAlchemy engine + session factory
│   ├── models.py                # ORM table definitions (Job, Statement...)
│   └── crud.py                  # create/read/update helper functions
│
├── prompts/
│   ├── translator.txt           # system prompt template for Translator
│   ├── validator.txt            # system prompt for semantic equivalence check
│   └── optimizer.txt            # system prompt for Optimizer
│
├── sample_sql/
│   ├── legacy_cursor.sql        # T-SQL cursor → CTE demo
│   ├── legacy_oracle.sql        # PL/SQL ROWNUM + old outer join
│   ├── legacy_mysql.sql         # old MySQL implicit joins + functions
│   ├── legacy_subquery.sql      # correlated subquery for optimizer demo
│   └── legacy_mixed.sql         # multi-statement file with several patterns
│
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py        # unit tests for SQL file parsing
│   ├── test_translator.py       # unit tests for translator prompts
│   ├── test_validator.py        # unit tests for scoring logic
│   ├── test_optimizer.py        # unit tests for optimization rewrites
│   └── test_pipeline_e2e.py     # end-to-end pipeline test with sample files
│
├── infra/
│   ├── azure.yaml               # azd deployment manifest
│   ├── main.bicep               # Azure resource definitions (IaC)
│   └── container-app.yaml       # Container Apps configuration
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # run tests on every pull request
│       └── deploy.yml           # build + push + deploy on merge to main
│
├── data/
│   └── .gitkeep                 # SQLite DB file created here at runtime
│
├── manage.py                    # DB init, seed, reset CLI commands
├── run_cli.py                   # CLI entry point (no web server needed)
├── Dockerfile
├── docker-compose.yml           # local dev with hot reload
├── requirements.txt
├── .env.example                 # template — commit this, NOT .env
├── .gitignore
└── README.md
```

---

## Key Files Explained

### `agents/orchestrator.py`
The brain of the pipeline. Calls Ingestion → Translator → Validator → Optimizer
in sequence. Manages the retry loop. Writes results to the database.
Runs as an async function so multiple statements can process concurrently.

### `agents/translator.py`
Loads the prompt from `prompts/translator.txt`, injects the source dialect,
target dialect, legacy SQL, and optional error context. Calls Azure OpenAI.
Returns the translated SQL string only (strips any markdown if present).

### `agents/validator.py`
Runs `sqlparse` first (fast, deterministic). Then calls GPT-4o for semantic
equivalence check. Combines both into a 0–100 score. Returns score + issues list.

### `agents/optimizer.py`
Calls GPT-4o with the optimizer prompt. Expects JSON back with
`{ "optimized_sql": "...", "changes": [...] }`. Parses response and returns both.

### `pipeline/ingestion.py`
Uses `sqlparse.split()` to divide a raw SQL string into individual statements.
Filters out empty statements and SQL comments. Returns a list of clean strings.

### `pipeline/report.py`
Takes the original SQL and modernized SQL for each statement. Generates a
side-by-side diff. Computes the job-level quality average. Returns a
structured report object ready for the API response or CLI output.

### `db/crud.py`
Helper functions: `create_job()`, `update_job_status()`, `write_statement()`,
`get_job_report()`, `check_cache()`, `write_cache()`. These are called by
the Orchestrator — no raw SQL queries anywhere outside this file.

### `run_cli.py`
Entry point for the CLI path. Usage:
```bash
python run_cli.py --input sample_sql/legacy_cursor.sql \
                  --source tsql \
                  --target postgresql
```
Prints the diff report and quality score to the terminal. No web server needed.

### `manage.py`
```bash
python manage.py init_db    # create all tables
python manage.py seed_db    # insert sample test data
python manage.py reset_db   # drop and recreate all tables (dev only)
```

---

## Environment Variables

### `.env.example`
```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Foundry IQ (used during hackathon)
FOUNDRY_IQ_ENDPOINT=https://your-foundry-endpoint

# Database
DATABASE_URL=sqlite:///./data/modernizer.db

# Pipeline config
MAX_RETRIES=2
VALIDATION_THRESHOLD=70
DEFAULT_SOURCE_DIALECT=tsql
DEFAULT_TARGET_DIALECT=postgresql
```

---

## Requirements

### `requirements.txt`
```
openai>=1.30.0
azure-identity
azure-keyvault-secrets
python-dotenv
sqlparse
sqlalchemy
fastapi
uvicorn[standard]
pydantic>=2.0
pytest
pytest-asyncio
httpx
```
