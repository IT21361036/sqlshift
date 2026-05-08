import difflib


def build_report(job_id: str, statements: list) -> dict:
    scores = [s["quality_score"] for s in statements if s.get("quality_score") is not None]
    quality_avg = round(sum(scores) / len(scores), 1) if scores else 0.0

    original_full = "\n\n".join(s["original_sql"] for s in statements)
    modernized_full = "\n\n".join(s.get("modernized_sql") or "" for s in statements)
    diff = _unified_diff(original_full, modernized_full)

    return {
        "job_id": job_id,
        "quality_avg": quality_avg,
        "statement_count": len(statements),
        "diff": diff,
        "statements": statements,
    }


def _unified_diff(original: str, modernized: str) -> str:
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modernized.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(orig_lines, mod_lines, fromfile="original.sql", tofile="modernized.sql")
    )
