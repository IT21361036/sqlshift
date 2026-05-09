import os
import sqlparse
import sqlparse.tokens as T
from agents.llm_client import call_qwen

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "validator.txt")

_DEPRECATED_TOKENS = {
    "postgresql": ["ROWNUM", "NOLOCK", "(+)", "@@FETCH_STATUS"],
    "ansi": ["ROWNUM", "NOLOCK", "(+)", "@@FETCH_STATUS"],
    "mysql8": ["ROWNUM", "(+)"],
}


def validate(original: str, translated: str, source_dialect: str, target_dialect: str) -> dict:
    score = 100
    issues = []

    try:
        parsed = sqlparse.parse(translated)
        if _has_syntax_error(parsed):
            score -= 40
            issues.append("Syntax error detected by sqlparse")
    except Exception:
        pass

    upper = translated.upper()
    for token in _DEPRECATED_TOKENS.get(target_dialect, []):
        if token.upper() in upper:
            score -= 20
            issues.append(f"Deprecated syntax still present: {token}")
            break

    if _column_count_mismatch(original, translated):
        score -= 15
        issues.append("SELECT column count differs from original")

    if _had_where(original) and not _had_where(translated):
        score -= 15
        issues.append("WHERE clause missing from translation")

    equiv = 1.0
    if score >= 25:
        equiv = _gpt_equivalence(original, translated, source_dialect, target_dialect)
        if equiv < 0.8:
            score -= 20
            issues.append(f"Semantic equivalence low: {equiv:.0%}")

    final = max(0, score)
    return {"score": final, "issues": issues, "passed": final >= 70}


def _has_syntax_error(parsed) -> bool:
    for stmt in parsed:
        for token in stmt.flatten():
            if token.ttype is T.Error:
                return True
    return False


def _had_where(sql: str) -> bool:
    return "WHERE" in sql.upper()


def _column_count_mismatch(original: str, translated: str) -> bool:
    def _count_cols(sql: str) -> int:
        stripped = sql.strip().upper()
        # Skip SELECT * — column count is indeterminate
        if "SELECT *" in stripped or "SELECT\n*" in stripped:
            return 0
        parsed = sqlparse.parse(sql)
        if not parsed:
            return 0
        in_select = False
        for token in parsed[0].tokens:
            if token.ttype is T.Keyword.DML and token.normalized == "SELECT":
                in_select = True
            elif in_select and token.ttype is T.Keyword:
                break
            elif in_select and not token.is_whitespace:
                return str(token).count(",") + 1
        return 0

    orig = _count_cols(original)
    trans = _count_cols(translated)
    return orig > 0 and trans > 0 and orig != trans


def _gpt_equivalence(original: str, translated: str, source_dialect: str, target_dialect: str) -> float:
    with open(_PROMPT_PATH) as f:
        prompt = f.read().format(
            source_dialect=source_dialect,
            target_dialect=target_dialect,
            original_sql=original,
            translated_sql=translated,
        )
    try:
        result = call_qwen("", prompt)
        return float(result.strip())
    except Exception:
        return 0.8  # neutral default — neither rewards nor penalizes API failures
