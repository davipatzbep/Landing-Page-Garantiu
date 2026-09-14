"""Store release risk snapshots, evidence, and subsequently observed outcomes."""

import csv
import math
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from io import StringIO


RELEASE_EXPORT_FIELDS = (
    "analysis_id", "release", "score", "computed_at", "outcome", "module",
    "module_score", "complexity_score", "bug_score", "test_health_score",
    "incident_score",
)
BUG_EXPORT_FIELDS = (
    "analysis_id", "release", "computed_at", "module", "file_path",
    "commit_hash", "message", "occurred_on",
)
INCIDENT_EXPORT_FIELDS = (
    "analysis_id", "release", "computed_at", "record_type", "module",
    "incident_count", "description", "occurred_on",
)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    """Apply the additive schema used by old scores and new evidence snapshots."""
    with closing(_connect(db_path)) as conn, conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS release_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_key TEXT NOT NULL DEFAULT '',
                release TEXT NOT NULL,
                score REAL NOT NULL CHECK(score >= 0 AND score <= 100),
                computed_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS release_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_key TEXT NOT NULL DEFAULT '',
                release TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK(outcome IN ('ok', 'falhou')),
                recorded_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS release_module_scores (
                analysis_id INTEGER NOT NULL,
                module TEXT NOT NULL CHECK(length(trim(module)) > 0),
                score REAL NOT NULL CHECK(score BETWEEN 0 AND 100),
                complexity_score REAL NOT NULL CHECK(complexity_score BETWEEN 0 AND 100),
                bug_score REAL NOT NULL CHECK(bug_score BETWEEN 0 AND 100),
                test_health_score REAL NOT NULL CHECK(test_health_score BETWEEN 0 AND 100),
                incident_score REAL NOT NULL CHECK(incident_score BETWEEN 0 AND 100),
                PRIMARY KEY (analysis_id, module),
                FOREIGN KEY (analysis_id) REFERENCES release_scores(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS release_bug_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER NOT NULL,
                module TEXT NOT NULL CHECK(length(trim(module)) > 0),
                file_path TEXT NOT NULL CHECK(length(trim(file_path)) > 0),
                commit_hash TEXT NOT NULL CHECK(length(trim(commit_hash)) > 0),
                message TEXT NOT NULL,
                occurred_on TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES release_scores(id) ON DELETE CASCADE,
                UNIQUE (analysis_id, module, file_path, commit_hash)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS release_incident_counts (
                analysis_id INTEGER NOT NULL,
                module TEXT NOT NULL CHECK(length(trim(module)) > 0),
                incident_count INTEGER NOT NULL CHECK(incident_count >= 0),
                PRIMARY KEY (analysis_id, module),
                FOREIGN KEY (analysis_id) REFERENCES release_scores(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS release_incident_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER NOT NULL,
                module TEXT NOT NULL CHECK(length(trim(module)) > 0),
                description TEXT NOT NULL CHECK(length(trim(description)) > 0),
                occurred_on TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES release_scores(id) ON DELETE CASCADE
            )"""
        )
        for statement in (
            "CREATE INDEX IF NOT EXISTS idx_release_scores_lookup ON release_scores(repo_key, release, computed_at DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_release_outcomes_lookup ON release_outcomes(repo_key, release, recorded_at DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_module_scores_module ON release_module_scores(module, analysis_id)",
            "CREATE INDEX IF NOT EXISTS idx_bug_evidence_analysis_module ON release_bug_evidence(analysis_id, module, occurred_on DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_bug_evidence_module ON release_bug_evidence(module, analysis_id)",
            "CREATE INDEX IF NOT EXISTS idx_incident_counts_module ON release_incident_counts(module, analysis_id)",
            "CREATE INDEX IF NOT EXISTS idx_incident_details_analysis_module ON release_incident_details(analysis_id, module, occurred_on DESC, id DESC)",
            "CREATE INDEX IF NOT EXISTS idx_incident_details_module ON release_incident_details(module, analysis_id)",
        ):
            conn.execute(statement)


def _validate_identity(release: str, repo_key: str) -> None:
    if not isinstance(release, str) or not release.strip():
        raise ValueError("release must be a nonempty string")
    if not isinstance(repo_key, str):
        raise ValueError("repo_key must be a string")


def _validate_score(score: float, name: str = "score") -> float:
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
        or not 0 <= score <= 100
    ):
        raise ValueError(f"{name} must be a finite number between 0 and 100")
    return float(score)


def _validate_text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValueError(f"{name} must be a nonempty string")
    return value if allow_empty else value.strip()


def _validate_iso_date(value: object, name: str) -> str:
    text = _validate_text(value, name)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{name} must use YYYY-MM-DD")
    return text


def _insert_release_score(
    conn: sqlite3.Connection, release: str, score: float, repo_key: str
) -> int:
    cursor = conn.execute(
        "INSERT INTO release_scores (repo_key, release, score, computed_at) "
        "VALUES (?, ?, ?, ?)",
        (repo_key, release, score, datetime.now(timezone.utc).isoformat()),
    )
    return cursor.lastrowid


def record_release_score(
    db_path: str, release: str, score: float, *, repo_key: str = ""
) -> int:
    """Compatibility writer for a score-only release snapshot."""
    _validate_identity(release, repo_key)
    validated_score = _validate_score(score)
    init_db(db_path)
    with closing(_connect(db_path)) as conn, conn:
        return _insert_release_score(conn, release, validated_score, repo_key)


def record_release_analysis(
    db_path: str,
    release: str,
    score: float,
    module_scores: list[dict],
    bug_evidence: list[dict],
    incident_counts: dict,
    incident_details: dict[str, list[dict]],
    *,
    repo_key: str = "",
) -> int:
    """Atomically persist one release score and all evidence for that snapshot."""
    _validate_identity(release, repo_key)
    validated_score = _validate_score(score)
    module_rows = []
    for item in module_scores:
        module = _validate_text(item.get("module"), "module")
        factors = item.get("factors")
        if not isinstance(factors, dict):
            raise ValueError("module factors must be a mapping")
        module_rows.append((
            module,
            _validate_score(item.get("score"), "module score"),
            _validate_score(factors.get("complexidade"), "complexity score"),
            _validate_score(factors.get("bugs"), "bug score"),
            _validate_score(factors.get("saude_testes"), "test health score"),
            _validate_score(factors.get("incidentes"), "incident score"),
        ))

    bug_rows = []
    for item in bug_evidence:
        bug_rows.append((
            _validate_text(item.get("module"), "bug module"),
            _validate_text(item.get("file_path"), "bug file path"),
            _validate_text(item.get("hash"), "bug commit hash"),
            _validate_text(item.get("message"), "bug message", allow_empty=True),
            _validate_iso_date(item.get("date"), "bug date"),
        ))

    count_rows = []
    for module, count in incident_counts.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("incident count must be a nonnegative integer")
        count_rows.append((_validate_text(module, "incident module"), count))

    detail_rows = []
    for module, details in incident_details.items():
        validated_module = _validate_text(module, "incident detail module")
        if not isinstance(details, list):
            raise ValueError("incident details must be lists")
        for item in details:
            detail_rows.append((
                validated_module,
                _validate_text(item.get("description"), "incident description"),
                _validate_iso_date(item.get("date"), "incident date"),
            ))

    init_db(db_path)
    with closing(_connect(db_path)) as conn, conn:
        analysis_id = _insert_release_score(
            conn, release, validated_score, repo_key,
        )
        conn.executemany(
            """INSERT INTO release_module_scores
               (analysis_id, module, score, complexity_score, bug_score,
                test_health_score, incident_score)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ((analysis_id, *row) for row in module_rows),
        )
        conn.executemany(
            """INSERT INTO release_bug_evidence
               (analysis_id, module, file_path, commit_hash, message, occurred_on)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ((analysis_id, *row) for row in bug_rows),
        )
        conn.executemany(
            """INSERT INTO release_incident_counts
               (analysis_id, module, incident_count) VALUES (?, ?, ?)""",
            ((analysis_id, *row) for row in count_rows),
        )
        conn.executemany(
            """INSERT INTO release_incident_details
               (analysis_id, module, description, occurred_on)
               VALUES (?, ?, ?, ?)""",
            ((analysis_id, *row) for row in detail_rows),
        )
        return analysis_id


def record_release_outcome(
    db_path: str, release: str, outcome: str, *, repo_key: str = ""
) -> int:
    """Record 'ok' or 'falhou' for an existing scored release."""
    _validate_identity(release, repo_key)
    if outcome not in ("ok", "falhou"):
        raise ValueError("outcome must be 'ok' or 'falhou'")
    init_db(db_path)
    with closing(_connect(db_path)) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO release_outcomes (repo_key, release, outcome, recorded_at) "
            "SELECT ?, ?, ?, ? WHERE EXISTS "
            "(SELECT 1 FROM release_scores WHERE repo_key = ? AND release = ?)",
            (repo_key, release, outcome, datetime.now(timezone.utc).isoformat(),
             repo_key, release),
        )
        if cursor.rowcount != 1:
            raise ValueError("release must have a recorded score in this repository")
        return cursor.lastrowid


def get_release_history(db_path: str, *, repo_key: str = "") -> list[dict]:
    """Return one latest score and outcome per release, newest score first."""
    if not isinstance(repo_key, str):
        raise ValueError("repo_key must be a string")
    init_db(db_path)
    with closing(_connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT s.release, s.score, s.computed_at,
                (SELECT o.outcome FROM release_outcomes o
                 WHERE o.repo_key = s.repo_key AND o.release = s.release
                 ORDER BY o.recorded_at DESC, o.id DESC LIMIT 1) AS outcome
            FROM release_scores s
            WHERE s.repo_key = ? AND s.id = (
                SELECT latest.id FROM release_scores latest
                WHERE latest.repo_key = s.repo_key AND latest.release = s.release
                ORDER BY latest.computed_at DESC, latest.id DESC LIMIT 1
            )
            ORDER BY s.computed_at DESC, s.id DESC""", (repo_key,)
        ).fetchall()
    return [dict(row) for row in rows]


def _latest_filter(alias: str) -> str:
    return f"""{alias}.id = (
        SELECT latest.id FROM release_scores latest
        WHERE latest.repo_key = {alias}.repo_key
          AND latest.release = {alias}.release
        ORDER BY latest.computed_at DESC, latest.id DESC LIMIT 1
    )"""


def get_release_export_rows(
    db_path: str, *, repo_key: str, release: str | None = None,
    module: str | None = None,
) -> list[dict]:
    """Return latest release snapshots and module factors for canonical CSV."""
    init_db(db_path)
    with closing(_connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT s.id AS analysis_id, s.release, s.score, s.computed_at,
                (SELECT o.outcome FROM release_outcomes o
                 WHERE o.repo_key = s.repo_key AND o.release = s.release
                 ORDER BY o.recorded_at DESC, o.id DESC LIMIT 1) AS outcome,
                m.module, m.score AS module_score, m.complexity_score,
                m.bug_score, m.test_health_score, m.incident_score
            FROM release_scores s
            LEFT JOIN release_module_scores m ON m.analysis_id = s.id
            WHERE s.repo_key = ? AND {_latest_filter('s')}
              AND (? IS NULL OR s.release = ?)
              AND (? IS NULL OR m.module = ?)
            ORDER BY s.computed_at DESC, s.id DESC, m.score DESC, m.module""",
            (repo_key, release, release, module, module),
        ).fetchall()
    return [dict(row) for row in rows]


def get_release_bug_evidence(
    db_path: str, *, repo_key: str, release: str | None = None,
    module: str | None = None,
) -> list[dict]:
    """Return file-level bug evidence from the latest snapshot per release."""
    init_db(db_path)
    with closing(_connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT s.id AS analysis_id, s.release, s.computed_at,
                b.module, b.file_path, b.commit_hash, b.message, b.occurred_on
            FROM release_bug_evidence b
            JOIN release_scores s ON s.id = b.analysis_id
            WHERE s.repo_key = ? AND {_latest_filter('s')}
              AND (? IS NULL OR s.release = ?)
              AND (? IS NULL OR b.module = ?)
            ORDER BY s.computed_at DESC, s.id DESC, b.occurred_on DESC,
                     b.module, b.file_path, b.id DESC""",
            (repo_key, release, release, module, module),
        ).fetchall()
    return [dict(row) for row in rows]


def get_release_incident_evidence(
    db_path: str, *, repo_key: str, release: str | None = None,
    module: str | None = None,
) -> list[dict]:
    """Return distinct count/detail incident records without duplicating counts."""
    init_db(db_path)
    common = (
        repo_key, release, release, module, module,
        repo_key, release, release, module, module,
    )
    with closing(_connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT s.id AS analysis_id, s.release, s.computed_at,
                'count' AS record_type, c.module, c.incident_count,
                NULL AS description, NULL AS occurred_on
            FROM release_incident_counts c
            JOIN release_scores s ON s.id = c.analysis_id
            WHERE s.repo_key = ? AND {_latest_filter('s')}
              AND (? IS NULL OR s.release = ?)
              AND (? IS NULL OR c.module = ?)
            UNION ALL
            SELECT s.id AS analysis_id, s.release, s.computed_at,
                'detail' AS record_type, d.module, NULL AS incident_count,
                d.description, d.occurred_on
            FROM release_incident_details d
            JOIN release_scores s ON s.id = d.analysis_id
            WHERE s.repo_key = ? AND {_latest_filter('s')}
              AND (? IS NULL OR s.release = ?)
              AND (? IS NULL OR d.module = ?)
            ORDER BY computed_at DESC, analysis_id DESC, record_type,
                     occurred_on DESC, module""",
            common,
        ).fetchall()
    return [dict(row) for row in rows]


def rows_to_csv(rows: list[dict], fieldnames: tuple[str, ...]) -> bytes:
    """Serialize canonical database values to an in-memory UTF-8 CSV."""
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in fieldnames})
    return output.getvalue().encode("utf-8")
