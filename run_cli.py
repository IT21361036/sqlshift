#!/usr/bin/env python3
"""CLI entry point: modernize a SQL file or inline SQL string."""
from __future__ import annotations

import argparse
import json
import sys

from db.database import SessionLocal, engine
from db.database import Base
from db import crud
from agents import orchestrator
from pipeline import ingestion


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLShift — legacy SQL modernizer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", metavar="FILE", help="Path to SQL file")
    group.add_argument("--sql", metavar="SQL", help="Inline SQL string")
    parser.add_argument("--source", default="tsql", help="Source dialect (default: tsql)")
    parser.add_argument("--target", default="postgresql", help="Target dialect (default: postgresql)")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    # Ensure DB tables exist
    Base.metadata.create_all(bind=engine)

    if args.input:
        try:
            with open(args.input, encoding="utf-8") as f:
                raw_sql = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
    else:
        raw_sql = args.sql

    # Pre-parse to get statement count for job creation
    statements = ingestion.parse_sql(raw_sql)
    statement_count = len(statements)

    db = SessionLocal()
    try:
        job = crud.create_job(db, args.source, args.target, raw_sql, statement_count)
        print(f"Job created: {job.id}", file=sys.stderr)
        report = orchestrator.run_job(SessionLocal, job.id, raw_sql, args.source, args.target)
    finally:
        db.close()

    if args.as_json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _pretty_print(report)


def _pretty_print(report: dict) -> None:
    print(f"\n{'='*60}")
    print(f"Job ID       : {report['job_id']}")
    print(f"Statements   : {report['statement_count']}")
    avg = report.get("quality_avg")
    print(f"Quality Avg  : {avg:.1f}/100" if avg is not None else "Quality Avg  : N/A")
    print(f"{'='*60}")
    for s in report.get("statements", []):
        pos = s.get("position", "?")
        score = s.get("quality_score")
        needs_review = s.get("flag") == "needs_human_review"
        flag = " ⚑ NEEDS REVIEW" if needs_review else ""
        print(f"\n[Statement {pos}] score={score}{flag}")
        print("--- Original ---")
        print(s.get("original_sql", ""))
        print("--- Modernized ---")
        print(s.get("modernized_sql", "") or "(none)")
        optimizations = s.get("optimizations", [])
        if optimizations:
            print("--- Optimizations ---")
            for opt in optimizations:
                print(f"  - {opt}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
