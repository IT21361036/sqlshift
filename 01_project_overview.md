# SQL Modernization Accelerator — Project Overview

## What This Project Is

An agentic AI pipeline that accepts legacy SQL files (T-SQL, PL/SQL, old MySQL), processes each statement through four specialized AI agents, and outputs modernized SQL with a quality score, diff report, and optimization list.

Built for the **Microsoft Agentic AI Hackathon — May 26–27, 2026**.

---

## The Five Phases

| Phase | What happens |
|-------|-------------|
| Ingestion | `.sql` file is parsed into individual statements using `sqlparse` |
| Translate | Translator agent rewrites each statement to the target dialect via GPT-4o |
| Validate | Validator agent scores translation 0–100; triggers retry if score < 70 |
| Optimize | Optimizer agent rewrites for performance (CTEs, index hints, join rewrites) |
| Report | Diff report + quality score + JSON output assembled and stored in DB |

---

## Tech Stack

| Category | Tool |
|----------|------|
| Language | Python 3.11+ |
| AI model | Azure OpenAI GPT-4o |
| Orchestration | Microsoft Foundry IQ |
| Web layer | FastAPI (optional) |
| Database | SQLite (local) / Azure SQL (production) |
| Secrets | Azure Key Vault |
| Monitoring | Azure Monitor + App Insights |
| Containerization | Docker |
| Image registry | Azure Container Registry |
| Hosting | Azure Container Apps |
| CI/CD | GitHub Actions |
| IaC deployment | azd CLI (Azure Developer CLI) |
| SQL parsing | `sqlparse` library |
| ORM | SQLAlchemy |

---

## What This Project Is NOT Using

| Tool | Reason excluded |
|------|----------------|
| n8n | Workflow automation tool — wrong category for custom AI agents |
| LangChain | Adds abstraction with no benefit; Foundry IQ is the orchestrator |
| Redis / message queue | Not needed; pipeline is synchronous per-request at hackathon scope |
| External vector database | No RAG required; translation is prompt-based |

---

## Input / Output

### Input
```json
{
  "sql": "DECLARE @id INT\nDECLARE cur CURSOR FOR...",
  "source_dialect": "tsql",
  "target_dialect": "postgresql"
}
```

### Output (per statement)
```json
{
  "statement_id": 3,
  "original_sql": "SELECT * FROM emp WHERE ROWNUM <= 10",
  "modernized_sql": "SELECT * FROM emp LIMIT 10",
  "quality_score": 94,
  "validation_passed": true,
  "retries": 0,
  "optimizations": ["ROWNUM replaced with LIMIT"],
  "processing_ms": 1240
}
```

---

## Portfolio Value

- Demonstrates multi-agent orchestration with specialized roles
- Solves a real enterprise problem (legacy SQL migration costs billions annually)
- Shows Azure AI Foundry deployment pipeline with monitoring
- Includes agent quality evaluation, retry logic, and safety scoring
- Deployable to a live URL anyone can demo

---

## Hackathon Badge Criteria

To earn the digital badge (shared via Credly):
- Attend **both days** live (May 26 and May 27)
- Complete **minimum 2 projects**
- This project counts as **one** — pair with "Build and Deploy Intelligent AI Agents" for the second
