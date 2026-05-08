# SQL Modernization Accelerator

> Agentic AI Hackathon — Microsoft Partner Skilling Hub — May 26–27, 2026

A multi-agent AI pipeline that modernizes legacy SQL (T-SQL, PL/SQL, old MySQL)
into clean, optimized, modern SQL using Azure OpenAI GPT-4o and Microsoft Foundry IQ.

---

## Live Demo

`https://sql-modernizer.azurecontainerapps.io` *(live after Day 2 deployment)*

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/sql-modernization-agent
cd sql-modernization-agent
cp .env.example .env
# Fill in AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY

pip install -r requirements.txt
python manage.py init_db

# Run via CLI
python run_cli.py --input sample_sql/legacy_cursor.sql --source tsql --target postgresql

# Or run as web API
uvicorn api.main:app --reload
# → http://localhost:8000/docs
```

---

## How It Works

```
Legacy SQL file
  → Ingestion (sqlparse splits into statements)
  → Orchestrator routes each statement through:
      Translator (GPT-4o) → Validator (sqlparse + GPT-4o) → Optimizer (GPT-4o)
      ↻ retry with error context if score < 70 (max 2 retries)
  → Report: diff + quality score (0–100) + optimization list
  → Result stored in SQLite / Azure SQL
```

---

## Documentation Index

| File | Contents |
|------|---------|
| `01_project_overview.md` | What this project does, tech stack, portfolio value |
| `02_architecture.md` | System layers, agent flow, deployment flow, ASCII diagrams |
| `03_design_plan.md` | All design decisions, API contract, scoring logic, error handling |
| `04_agents.md` | Each agent's responsibility, system prompts, code patterns |
| `05_database.md` | All 4 tables with SQL schema, ORM models, setup commands |
| `06_file_structure.md` | Complete folder layout, each file explained, env vars, requirements |
| `07_deployment.md` | Local dev, Docker, GitHub Actions CI/CD, azd deploy steps |
| `08_implementation_plan.md` | Hour-by-hour hackathon plan, risks, sample SQL to create |

---

## Architecture (Quick View)

```
User (Browser / CLI)
  └─ FastAPI (optional)
      └─ Agent Pipeline (Python + Foundry IQ)
          ├─ Ingestion → Orchestrator → Translator → Validator → Optimizer
          └─ SQLite / Azure SQL
              └─ Azure OpenAI · Azure Monitor · Azure Key Vault
                  └─ Azure Container Apps (Docker) · GitHub Actions
```

---

## Badge Criteria

- Attend both days live (May 26–27)
- Complete minimum 2 projects
- Badge shared via Credly after the event
