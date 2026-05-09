#!/usr/bin/env python3
"""DB management: init_db, reset_db, seed_db."""
from __future__ import annotations

import sys

from db.database import SessionLocal, engine
from db.database import Base
from db import crud


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database initialised.")


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Database reset.")


def seed_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_sql = "SELECT 1"
        job = crud.create_job(db, "tsql", "postgresql", seed_sql, 1)
        print(f"Seeded: job {job.id}")
    finally:
        db.close()


COMMANDS = {"init_db": init_db, "reset_db": reset_db, "seed_db": seed_db}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python manage.py [{' | '.join(COMMANDS)}]", file=sys.stderr)
        sys.exit(1)
    COMMANDS[sys.argv[1]]()
