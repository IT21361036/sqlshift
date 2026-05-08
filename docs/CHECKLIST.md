# Project Checklist — SQLShift

## Implementation Tasks

- [x] **Task 1:** Bootstrap — config.py, requirements.txt, .env.example, pytest.ini, directory scaffold
- [x] **Task 2:** DB layer — database.py, models.py (Job, Statement, Optimization, Cache), crud.py
- [x] **Task 3:** Ingestion — pipeline/ingestion.py (sqlparse split + filter); pipeline/report.py (diff + quality avg)
- [x] **Task 4:** Prompts — prompts/translator.txt, prompts/validator.txt, prompts/optimizer.txt
- [x] **Task 5:** LLM client — agents/llm_client.py (Ollama/Qwen via OpenAI-compatible API)
- [x] **Task 6:** Translator agent — agents/translator.py (dialect rewrite + fence stripping)
- [x] **Task 7:** Validator agent — agents/validator.py (sqlparse + Qwen dual scoring)
- [x] **Task 7b:** Optimizer agent — agents/optimizer.py (JSON rewrite + JSONDecodeError fallback)
- [x] **Task 8:** Orchestrator — agents/orchestrator.py (retry loop, error_context, needs_human_review)
- [x] **Task 9:** FastAPI web layer — api/main.py (5 routes: /health /modernize /jobs /report /history)
- [x] **Task 10:** CLI runner — run_cli.py, manage.py (init_db/reset_db/seed_db), 5 sample SQL files
- [x] **Task 11:** Docker + CI/CD — Dockerfile, docker-compose.yml, ci.yml, deploy.yml, infra/

## Quality Gates

- [x] 40/40 tests passing (pytest)
- [x] All LLM calls mocked in tests
- [x] Spec compliance review passed for each task
- [x] Code quality review passed for each task
- [ ] `docker build` local verification
- [ ] Live `docker-compose up` smoke test

## Git / Deployment

- [x] Feature branch `feat/implementation` (16 commits)
- [ ] Push to `https://github.com/IT21361036/sqlshift`
- [ ] Open PR: `feat/implementation` → `main`
- [ ] Merge to main
- [ ] (Optional) Azure Container Apps deployment
- [ ] (Optional) Supabase PostgreSQL production DB wired up

## Portfolio Polish (Optional)

- [ ] Decide on frontend (simple HTML/JS vs React vs none)
- [ ] Record demo GIF (legacy SQL in → diff report out)
- [ ] Update README with live URL, architecture diagram, example output
