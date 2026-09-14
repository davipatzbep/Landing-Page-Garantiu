"""Persist test observations and calculate status changes per test."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone


def init_db(db_path: str) -> None:
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_key TEXT NOT NULL DEFAULT '',
                module TEXT NOT NULL,
                classname TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'skipped')),
                recorded_at TEXT NOT NULL
            )"""
        )


def record_test_run(
    db_path: str, test_results: list[dict], *, repo_key: str = ""
) -> None:
    """Store one complete run atomically, scoped to its repository.

    Test identity is (classname, name); duplicate identities in a single
    report are rejected because they cannot represent separate runs.
    """
    if not isinstance(repo_key, str):
        raise ValueError("repo_key must be a string")
    rows = []
    identities = set()
    recorded_at = datetime.now(timezone.utc).isoformat()
    for result in test_results:
        classname = result.get("classname")
        name = result.get("name")
        status = result.get("status")
        if not isinstance(classname, str) or not classname.strip():
            raise ValueError("classname must be a nonempty string")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a nonempty string")
        if status not in ("passed", "failed", "skipped"):
            raise ValueError("status must be passed, failed or skipped")
        identity = (classname, name)
        if identity in identities:
            raise ValueError(f"duplicate test identity: {classname}.{name}")
        identities.add(identity)
        module = classname.split(".")[0]
        if not module.strip():
            raise ValueError("classname must start with a module")
        rows.append((repo_key, module, classname, name, status, recorded_at))
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.executemany(
            "INSERT INTO test_runs "
            "(repo_key, module, classname, name, status, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )


def flakiness_by_module(db_path: str, *, repo_key: str = "") -> dict[str, float]:
    """Average each test's flips/(observations-1), including skipped statuses.

    Tests with one observation contribute zero. Observations are ordered by
    insertion id, so equal timestamps do not change the result.
    """
    if not isinstance(repo_key, str):
        raise ValueError("repo_key must be a string")
    init_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT module, classname, name, status FROM test_runs "
            "WHERE repo_key = ? ORDER BY id", (repo_key,)
        ).fetchall()
    by_test = {}
    for module, classname, name, status in rows:
        by_test.setdefault((module, classname, name), []).append(status)
    module_rates = {}
    for (module, _, _), statuses in by_test.items():
        flips = sum(a != b for a, b in zip(statuses, statuses[1:]))
        rate = flips / (len(statuses) - 1) if len(statuses) > 1 else 0.0
        module_rates.setdefault(module, []).append(rate)
    return {
        module: round(100 * sum(rates) / len(rates), 1)
        for module, rates in module_rates.items()
    }
