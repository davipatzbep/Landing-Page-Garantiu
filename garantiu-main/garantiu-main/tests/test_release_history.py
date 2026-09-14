import sqlite3
from contextlib import closing

import pytest

from garantiu.release_history import (
    BUG_EXPORT_FIELDS,
    INCIDENT_EXPORT_FIELDS,
    RELEASE_EXPORT_FIELDS,
    get_release_bug_evidence,
    get_release_export_rows,
    get_release_history,
    get_release_incident_evidence,
    init_db,
    record_release_analysis,
    record_release_outcome,
    record_release_score,
    rows_to_csv,
)


def analysis_payload():
    modules = [{
        "module": "checkout", "score": 82.5,
        "factors": {
            "complexidade": 90.0, "bugs": 80.0,
            "saude_testes": 70.0, "incidentes": 90.0,
        },
    }]
    bugs = [{
        "module": "checkout", "file_path": "checkout/pay.py",
        "hash": "abc123", "message": "fix: cobrança duplicada",
        "date": "2026-09-09",
    }]
    counts = {"checkout": 3, "auth": 0}
    details = {
        "checkout": [{
            "description": "Falha ao confirmar pagamento",
            "date": "2026-09-10",
        }],
    }
    return modules, bugs, counts, details


def test_empty_and_scores_join_latest_outcomes(tmp_path):
    db = str(tmp_path / "releases.db")
    assert get_release_history(db) == []
    assert record_release_score(db, "v1", 58) == 1
    record_release_outcome(db, "v1", "ok")
    record_release_score(db, "v2", 85)
    history = get_release_history(db)
    assert [r["release"] for r in history] == ["v2", "v1"]
    assert history[0]["score"] == 85
    assert history[0]["outcome"] is None
    assert history[1]["outcome"] == "ok"


def test_reanalysis_is_one_row_and_timestamp_ties_use_ids(tmp_path):
    db = str(tmp_path / "releases.db")
    record_release_score(db, "v1", 58)
    record_release_score(db, "v2", 20)
    record_release_score(db, "v1", 85)
    record_release_outcome(db, "v1", "ok")
    record_release_outcome(db, "v1", "falhou")
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE release_scores SET computed_at = '2026-01-01'")
        conn.execute("UPDATE release_outcomes SET recorded_at = '2026-01-01'")
    history = get_release_history(db)
    assert [r["release"] for r in history] == ["v1", "v2"]
    assert history[0] == {
        "release": "v1", "score": 85, "computed_at": "2026-01-01", "outcome": "falhou"
    }


def test_repository_scope_and_unknown_release(tmp_path):
    db = str(tmp_path / "releases.db")
    record_release_score(db, "v1", 10, repo_key="one")
    with pytest.raises(ValueError, match="recorded score"):
        record_release_outcome(db, "v1", "ok", repo_key="two")
    record_release_score(db, "v1", 90, repo_key="two")
    record_release_outcome(db, "v1", "falhou", repo_key="two")
    assert get_release_history(db) == []
    assert get_release_history(db, repo_key="one")[0]["outcome"] is None
    assert get_release_history(db, repo_key="one")[0]["score"] == 10
    assert get_release_history(db, repo_key="two")[0]["outcome"] == "falhou"
    with pytest.raises(ValueError, match="recorded score"):
        record_release_outcome(db, "missing", "ok")


@pytest.mark.parametrize("score", [-1, 101, float("nan"), float("inf"), "20", True])
def test_invalid_score_rejected(tmp_path, score):
    db = str(tmp_path / "releases.db")
    with pytest.raises(ValueError):
        record_release_score(db, "v1", score)
    assert get_release_history(db) == []


@pytest.mark.parametrize("release", ["", "   ", None])
def test_empty_release_rejected(tmp_path, release):
    db = str(tmp_path / "releases.db")
    with pytest.raises(ValueError):
        record_release_score(db, release, 20)
    with pytest.raises(ValueError):
        record_release_outcome(db, release, "ok")


def test_invalid_outcome_rejected(tmp_path):
    with pytest.raises(ValueError, match="outcome"):
        record_release_outcome(str(tmp_path / "releases.db"), "v1", "talvez")


def test_additive_schema_migrates_legacy_database_and_enables_foreign_keys(tmp_path):
    db = str(tmp_path / "legacy.db")
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute(
            """CREATE TABLE release_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_key TEXT NOT NULL DEFAULT '', release TEXT NOT NULL,
                score REAL NOT NULL, computed_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE release_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_key TEXT NOT NULL DEFAULT '', release TEXT NOT NULL,
                outcome TEXT NOT NULL, recorded_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO release_scores VALUES (1, 'repo', 'v1', 42.5, '2026-01-01T12:00:00+00:00')"
        )

    init_db(db)
    init_db(db)

    with closing(sqlite3.connect(db)) as conn:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
        assert {
            "release_scores", "release_outcomes", "release_module_scores",
            "release_bug_evidence", "release_incident_counts",
            "release_incident_details",
        }.issubset(tables)
        for table in (
            "release_module_scores", "release_bug_evidence",
            "release_incident_counts", "release_incident_details",
        ):
            assert conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        assert conn.execute("SELECT COUNT(*) FROM release_scores").fetchone()[0] == 1
    assert get_release_history(db, repo_key="repo")[0]["score"] == 42.5


def test_record_release_analysis_persists_full_snapshot_and_survives_reopen(tmp_path):
    db = str(tmp_path / "releases.db")
    modules, bugs, counts, details = analysis_payload()

    analysis_id = record_release_analysis(
        db, "v1", 82.5, modules, bugs, counts, details, repo_key="repo",
    )

    releases = get_release_export_rows(db, repo_key="repo")
    assert releases == [{
        "analysis_id": analysis_id, "release": "v1", "score": 82.5,
        "computed_at": releases[0]["computed_at"], "outcome": None,
        "module": "checkout", "module_score": 82.5,
        "complexity_score": 90.0, "bug_score": 80.0,
        "test_health_score": 70.0, "incident_score": 90.0,
    }]
    assert get_release_bug_evidence(db, repo_key="repo")[0]["file_path"] == "checkout/pay.py"
    incident_rows = get_release_incident_evidence(db, repo_key="repo")
    assert {(row["record_type"], row["module"]) for row in incident_rows} == {
        ("count", "checkout"), ("count", "auth"), ("detail", "checkout"),
    }


def test_reanalysis_preserves_snapshots_but_summary_and_queries_use_latest(tmp_path):
    db = str(tmp_path / "releases.db")
    modules, bugs, counts, details = analysis_payload()
    first = record_release_analysis(
        db, "v1", 20, modules, bugs, counts, details, repo_key="repo",
    )
    modules[0]["score"] = 75.0
    second = record_release_analysis(
        db, "v1", 75, modules, [], {}, {}, repo_key="repo",
    )

    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM release_scores").fetchone()[0] == 2
    assert first != second
    assert get_release_history(db, repo_key="repo")[0]["score"] == 75
    assert get_release_export_rows(db, repo_key="repo")[0]["analysis_id"] == second
    assert get_release_bug_evidence(db, repo_key="repo") == []


def test_release_evidence_queries_filter_release_module_and_repository(tmp_path):
    db = str(tmp_path / "releases.db")
    modules, bugs, counts, details = analysis_payload()
    record_release_analysis(
        db, "v1", 82.5, modules, bugs, counts, details, repo_key="one",
    )
    record_release_analysis(
        db, "v2", 10, modules, bugs, counts, details, repo_key="two",
    )

    assert get_release_export_rows(db, repo_key="missing") == []
    assert get_release_bug_evidence(db, repo_key="two", release="v1") == []
    assert get_release_incident_evidence(
        db, repo_key="one", module="missing",
    ) == []
    assert len(get_release_bug_evidence(
        db, repo_key="one", release="v1", module="checkout",
    )) == 1


def test_duplicate_child_rolls_back_the_entire_analysis(tmp_path):
    db = str(tmp_path / "releases.db")
    modules, bugs, counts, details = analysis_payload()
    duplicate_bugs = bugs + [dict(bugs[0])]

    with pytest.raises(sqlite3.IntegrityError):
        record_release_analysis(
            db, "v1", 82.5, modules, duplicate_bugs, counts, details,
            repo_key="repo",
        )

    assert get_release_history(db, repo_key="repo") == []
    with closing(sqlite3.connect(db)) as conn:
        for table in (
            "release_module_scores", "release_bug_evidence",
            "release_incident_counts", "release_incident_details",
        ):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_csv_export_has_headers_unicode_and_canonical_values_without_writes(tmp_path):
    db = str(tmp_path / "releases.db")
    modules, bugs, counts, details = analysis_payload()
    record_release_analysis(
        db, "v1", 82.5, modules, bugs, counts, details, repo_key="repo",
    )
    before = get_release_history(db, repo_key="repo")

    releases_csv = rows_to_csv(
        get_release_export_rows(db, repo_key="repo"), RELEASE_EXPORT_FIELDS,
    ).decode("utf-8")
    bugs_csv = rows_to_csv(
        get_release_bug_evidence(db, repo_key="repo"), BUG_EXPORT_FIELDS,
    ).decode("utf-8")
    incidents_csv = rows_to_csv(
        get_release_incident_evidence(db, repo_key="repo"),
        INCIDENT_EXPORT_FIELDS,
    ).decode("utf-8")

    assert releases_csv.splitlines()[0] == ",".join(RELEASE_EXPORT_FIELDS)
    assert ",82.5," in releases_csv
    assert "cobrança duplicada" in bugs_csv
    assert "Falha ao confirmar pagamento" in incidents_csv
    assert rows_to_csv([], BUG_EXPORT_FIELDS).decode("utf-8") == ",".join(BUG_EXPORT_FIELDS) + "\n"
    assert get_release_history(db, repo_key="repo") == before
