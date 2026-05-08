# Architecture — SQL Modernization Accelerator

## System Layers

The system is organized into 5 layers, each with a clear responsibility.

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — User                                         │
│  Browser (Web UI)  ·  CLI Terminal                      │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / stdin
┌────────────────────────▼────────────────────────────────┐
│  Layer 2 — API (FastAPI) [OPTIONAL]                     │
│  POST /modernize  ·  GET /jobs/:id  ·  GET /jobs/report │
└────────────────────────┬────────────────────────────────┘
                         │ function call
┌────────────────────────▼────────────────────────────────┐
│  Layer 3 — Agent Pipeline (Python + Foundry IQ)         │
│                                                         │
│  [ Ingestion — sqlparse splits .sql into statements ]   │
│                         │                               │
│              [ Orchestrator Agent ]                     │
│             /            |            \                 │
│   [Translator]    [Validator]    [Optimizer]            │
│     GPT-4o       score 0–100      GPT-4o                │
│                   ↻ retry                               │
│                         │                               │
│      [ SQLite (local) / Azure SQL (prod) ]              │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS API calls
┌────────────────────────▼────────────────────────────────┐
│  Layer 4 — Azure AI Services                            │
│  Azure OpenAI (GPT-4o)  ·  Azure Monitor  ·  Key Vault  │
└────────────────────────┬────────────────────────────────┘
                         │ deployed via azd
┌────────────────────────▼────────────────────────────────┐
│  Layer 5 — Infrastructure & DevOps                      │
│  Docker  ·  Azure Container Registry  ·                 │
│  Azure Container Apps  ·  GitHub Actions                │
└─────────────────────────────────────────────────────────┘
```

---

## Agent Interaction Flow

```
Legacy SQL file
      │
      ▼
  Ingestion (sqlparse)
      │  splits into statements
      ▼
  Orchestrator Agent
      │
      ├──────────────────────────────┐
      │                              │
      ▼                              │
  Translator Agent (GPT-4o)         │
      │  translated SQL              │
      ▼                              │
  Validator Agent                   │
      │  score < 70?  ───────────────┘
      │                   retry with error context (max 2)
      │  score ≥ 70
      ▼
  Optimizer Agent (GPT-4o)
      │  optimized SQL
      ▼
  Report Generator
      │  diff + quality score + JSON
      ▼
  Database (write result)
      │
      ▼
  API response / CLI output
```

---

## Data Flow (per statement)

```
input_sql
  → sqlparse.split()           # list of statements
  → translator.run(stmt)       # GPT-4o: translate dialect
  → validator.run(stmt, trans) # sqlparse + GPT-4o: score
  → if score < 70:
      translator.run(stmt, error_context=issues)  # retry
  → optimizer.run(translated)  # GPT-4o: perf rewrite
  → report.build(original, optimized, score)
  → db.write(job_id, result)
```

---

## Deployment Flow

```
git push origin main
      │
      ▼
GitHub Actions: ci.yml
  ├── pytest (unit + e2e tests)
  └── if pass → trigger deploy.yml

GitHub Actions: deploy.yml
  ├── docker build -t sql-modernizer .
  ├── docker push → Azure Container Registry
  ├── azd deploy → Azure Container Apps
  └── GET /health → confirm live

Live URL: https://sql-modernizer.azurecontainerapps.io
```

---

## Component Responsibilities

| Component | Responsibility | File |
|-----------|---------------|------|
| Ingestion | Parse `.sql` file into statement list | `pipeline/ingestion.py` |
| Orchestrator | Route statements, manage retry loop, write DB | `agents/orchestrator.py` |
| Translator | Rewrite SQL to target dialect via GPT-4o | `agents/translator.py` |
| Validator | Score translation 0–100, return issues list | `agents/validator.py` |
| Optimizer | Rewrite for performance via GPT-4o | `agents/optimizer.py` |
| Report builder | Generate diff + quality summary | `pipeline/report.py` |
| FastAPI app | HTTP routes (optional web layer) | `api/main.py` |
| Database | Store jobs, statements, results, cache | `db/` |
| GitHub Actions | CI (test) + CD (build, push, deploy) | `.github/workflows/` |
