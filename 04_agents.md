# Agents — SQL Modernization Accelerator

## Overview

The pipeline uses 4 agents. Three call GPT-4o. One (`Validator`) uses
both `sqlparse` (deterministic) and GPT-4o (semantic). The Orchestrator
never calls GPT-4o — it only routes and assembles.

---

## Agent 1 — Orchestrator

**File:** `agents/orchestrator.py`  
**Tools:** Foundry IQ, SQLAlchemy  
**Does:** Routes each statement through the pipeline. Manages retry loop.
Writes results to the database. Returns the final job report.

```python
async def process_statement(stmt: str, source: str, target: str, job_id: str):
    translated = await translator.run(stmt, source, target)

    for attempt in range(3):  # max 2 retries
        result = await validator.run(stmt, translated)

        if result.score >= 70:
            break

        if attempt < 2:
            # Retry with specific error context so GPT-4o knows what to fix
            translated = await translator.run(
                stmt, source, target,
                error_context=result.issues
            )
        else:
            result.flag = "needs_human_review"

    optimized = await optimizer.run(translated)
    await db.write_statement(job_id, stmt, optimized, result)
    return optimized, result
```

---

## Agent 2 — Translator

**File:** `agents/translator.py`  
**Tools:** Azure OpenAI GPT-4o  
**Does:** Converts legacy SQL syntax to the target dialect.
Handles cursors → CTEs, ROWNUM → LIMIT, old outer joins, deprecated functions.

### System Prompt Template

```
You are an expert SQL migration engineer.
Translate the {source_dialect} SQL below to {target_dialect}.

Rules:
- Replace all cursors with CTEs or set-based operations
- Replace ROWNUM with ROW_NUMBER() OVER (...) or LIMIT
- Replace old outer join (+) with ANSI LEFT/RIGHT JOIN syntax
- Replace deprecated functions with modern equivalents
- Preserve all logic, filters, and column aliases exactly
{error_context}
Return ONLY the translated SQL.
No explanation. No markdown fences. No preamble.

Examples:
INPUT:  SELECT * FROM emp WHERE ROWNUM <= 10
OUTPUT: SELECT * FROM emp LIMIT 10

INPUT:  SELECT e.name, d.name FROM emp e, dept d WHERE e.dept_id = d.id (+)
OUTPUT: SELECT e.name, d.name FROM emp e LEFT JOIN dept d ON e.dept_id = d.id
```

### Error Context Injection (Retry)

```python
error_context = ""
if issues:
    error_context = f"""
Previous translation failed validation with these issues:
{chr(10).join(f'- {issue}' for issue in issues)}
Fix all of these issues in your translation.
"""
```

---

## Agent 3 — Validator

**File:** `agents/validator.py`  
**Tools:** `sqlparse` (syntax), Azure OpenAI GPT-4o (semantics)  
**Does:** Scores translated SQL 0–100. Returns score + issues list.
Triggers retry in Orchestrator if score < 70.

### Scoring Logic

```python
def score_translation(original: str, translated: str) -> dict:
    score = 100
    issues = []

    # Check 1: sqlparse syntax
    parsed = sqlparse.parse(translated)
    if has_syntax_error(parsed):
        score -= 40
        issues.append("Syntax error detected by sqlparse")

    # Check 2: GPT-4o semantic equivalence
    equiv = gpt_equivalence_check(original, translated)
    if equiv < 0.8:
        score -= 20
        issues.append(f"Semantic equivalence only {equiv:.0%}")

    # Check 3: deprecated syntax still present
    if contains_deprecated(translated, target_dialect):
        score -= 20
        issues.append("Deprecated syntax still present in output")

    # Check 4: column count mismatch
    if column_count_mismatch(original, translated):
        score -= 15
        issues.append("Column count differs from original")

    # Check 5: WHERE clause dropped
    if had_where_clause(original) and not has_where_clause(translated):
        score -= 15
        issues.append("WHERE clause missing from translation")

    return {"score": max(0, score), "issues": issues, "passed": score >= 70}
```

### GPT-4o Semantic Check Prompt

```
You are a SQL correctness auditor.
Given an original SQL statement and its translation, determine if they
are semantically equivalent — i.e. they would return the same results
against the same database.

Original ({source_dialect}):
{original_sql}

Translation ({target_dialect}):
{translated_sql}

Respond with a single number from 0.0 to 1.0 representing your confidence
that they are semantically equivalent. 1.0 = identical logic, 0.0 = completely different.
Respond with the number only. No explanation.
```

---

## Agent 4 — Optimizer

**File:** `agents/optimizer.py`  
**Tools:** Azure OpenAI GPT-4o  
**Does:** Rewrites validated SQL for performance. Returns optimized SQL
plus a human-readable list of changes made.

### System Prompt

```
You are a SQL performance engineer.
Optimize the SQL below for the {target_dialect} query engine.

Apply these improvements where applicable:
- Replace correlated subqueries with CTEs
- Replace nested loop patterns with hash joins where beneficial
- Add index hints for large table scans (use EXPLAIN-style reasoning)
- Simplify redundant JOINs or subqueries
- Use window functions instead of self-joins where appropriate

Return your response as JSON with two fields:
{
  "optimized_sql": "...",
  "changes": ["change 1 description", "change 2 description"]
}

Do not change the logical output of the query. Only improve performance.
```

---

## Agent Summary Table

| Agent | File | Calls GPT-4o | Other tools | Output |
|-------|------|-------------|-------------|--------|
| Orchestrator | `orchestrator.py` | No | Foundry IQ, DB | Final job report |
| Translator | `translator.py` | Yes | — | Translated SQL string |
| Validator | `validator.py` | Yes | sqlparse | Score + issues list |
| Optimizer | `optimizer.py` | Yes | — | Optimized SQL + changes list |
