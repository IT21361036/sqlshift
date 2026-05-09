from pipeline.report import build_report


def test_quality_avg_computed():
    statements = [
        {"original_sql": "SELECT 1", "modernized_sql": "SELECT 1", "quality_score": 80},
        {"original_sql": "SELECT 2", "modernized_sql": "SELECT 2", "quality_score": 100},
    ]
    report = build_report("job-1", statements)
    assert report["quality_avg"] == 90.0


def test_diff_contains_markers():
    statements = [
        {"original_sql": "SELECT * FROM emp WHERE ROWNUM <= 10", "modernized_sql": "SELECT * FROM emp LIMIT 10", "quality_score": 95},
    ]
    report = build_report("job-1", statements)
    assert "---" in report["diff"] or "+++" in report["diff"]


def test_empty_statements_returns_zero_avg():
    report = build_report("job-1", [])
    assert report["quality_avg"] == 0.0
    assert report["statement_count"] == 0
