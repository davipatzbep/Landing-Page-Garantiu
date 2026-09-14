import math
import sqlite3
from datetime import datetime, timezone


def init_db(db_path: str) -> None:
    """Creates the decisions table if it doesn't already exist."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                release TEXT NOT NULL,
                score REAL NOT NULL,
                decided_by TEXT NOT NULL,
                decision TEXT NOT NULL,
                decided_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def record_decision(db_path: str, release: str, score: float, decided_by: str, decision: str) -> int:
    """
    Inserts a decision record. decision must be 'publicar' or 'cancelar'.
    Returns the new row's id.
    """
    if decision not in ("publicar", "cancelar"):
        raise ValueError("decision must be 'publicar' or 'cancelar'")
    if not release.strip() or not decided_by.strip():
        raise ValueError("Informe o release e o nome de quem decide.")
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("O score deve estar entre 0 e 100.")

    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO decisions (release, score, decided_by, decision, decided_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (release, score, decided_by.strip(), decision,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_decision_history(db_path: str, release: str) -> list:
    """Returns all decision records for a release, most recent first."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM decisions WHERE release = ? ORDER BY decided_at DESC, id DESC",
            (release,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
