import pytest

from garantiu.decision_log import get_decision_history, record_decision


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "decisions.db")


def test_record_decision_rejects_invalid_decision(db_path):
    with pytest.raises(ValueError):
        record_decision(db_path, "release/2026.09", 74.0, "m.silva", "talvez")


def test_record_and_fetch_decision_history(db_path):
    record_decision(db_path, "release/2026.09", 74.0, "m.silva", "publicar")
    record_decision(db_path, "release/2026.09", 74.0, "m.silva", "cancelar")

    history = get_decision_history(db_path, "release/2026.09")

    assert len(history) == 2
    assert history[0]["decision"] == "cancelar"
    assert history[1]["decision"] == "publicar"
    assert all(h["release"] == "release/2026.09" for h in history)


def test_get_decision_history_empty_for_unknown_release(db_path):
    assert get_decision_history(db_path, "release/nunca-existiu") == []


def test_decision_requires_nonblank_author(db_path):
    with pytest.raises(ValueError):
        record_decision(db_path, "release", 50, "   ", "publicar")
    assert get_decision_history(db_path, "release") == []
