import sqlite3
from contextlib import closing

import pytest

from garantiu.test_history import flakiness_by_module, record_test_run


def result(status="passed", name="test_a", classname="checkout.gateway"):
    return {"classname": classname, "name": name, "status": status, "time": 0.1}


def test_empty_and_single_run(tmp_path):
    db = str(tmp_path / "tests.db")
    assert flakiness_by_module(db) == {}
    record_test_run(db, [result()])
    assert flakiness_by_module(db) == {"checkout": 0.0}


def test_flips_include_skipped_and_average_per_test(tmp_path):
    db = str(tmp_path / "tests.db")
    for status in ("passed", "failed", "skipped", "passed"):
        record_test_run(db, [result(status)])
    record_test_run(db, [result(name="stable")])
    record_test_run(db, [result(name="stable")])
    assert flakiness_by_module(db) == {"checkout": 50.0}


def test_same_name_different_class_and_repository_are_isolated(tmp_path):
    db = str(tmp_path / "tests.db")
    record_test_run(db, [result()], repo_key="one")
    record_test_run(db, [result("failed")], repo_key="two")
    record_test_run(db, [result("failed", classname="checkout.other")], repo_key="one")
    assert flakiness_by_module(db, repo_key="one") == {"checkout": 0.0}
    assert flakiness_by_module(db, repo_key="two") == {"checkout": 0.0}
    assert flakiness_by_module(db) == {}


def test_insertion_order_controls_flips_even_when_timestamps_tie(tmp_path):
    db = str(tmp_path / "tests.db")
    for status in ("passed", "passed", "failed", "failed"):
        record_test_run(db, [result(status)])
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE test_runs SET recorded_at = '2026-01-01'")
    assert flakiness_by_module(db) == {"checkout": 33.3}


@pytest.mark.parametrize("invalid", [
    result("unknown"), result(name=""), result(classname=""),
    result(classname=".gateway"),
])
def test_invalid_run_does_not_partially_write(tmp_path, invalid):
    db = str(tmp_path / "tests.db")
    record_test_run(db, [result()])
    with pytest.raises(ValueError):
        record_test_run(db, [result("failed"), invalid])
    assert flakiness_by_module(db) == {"checkout": 0.0}
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT count(*) FROM test_runs").fetchone()[0] == 1


def test_duplicate_identity_in_one_run_is_rejected(tmp_path):
    db = str(tmp_path / "tests.db")
    with pytest.raises(ValueError, match="duplicate"):
        record_test_run(db, [result(), result("failed")])
    assert flakiness_by_module(db) == {}
