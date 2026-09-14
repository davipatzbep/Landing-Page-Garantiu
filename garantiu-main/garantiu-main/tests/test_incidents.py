import pytest

from garantiu.incidents import (
    load_incident_details, load_incidents, load_project_incident_details,
    load_project_incidents,
)
from tests.conftest import init_repo


@pytest.fixture
def sample_incidents_csv(tmp_path):
    path = tmp_path / "incidents.csv"
    path.write_text("module,incident_count\ncheckout,3\nauth,1\ncatalogo,0\n")
    return str(path)


def test_load_incidents_reads_counts(sample_incidents_csv):
    incidents = load_incidents(sample_incidents_csv)
    assert incidents == {"checkout": 3, "auth": 1, "catalogo": 0}


def test_load_incidents_skips_bad_rows(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("module,incident_count\ncheckout,tres\nauth,2\n")
    incidents = load_incidents(str(path))
    assert incidents == {"auth": 2}


def test_incident_details_groups_sorts_and_reads_bom(tmp_path):
    path = tmp_path / "details.csv"
    path.write_text(
        'module,description,date\n'
        'checkout,"gateway, indisponível",2026-02-10\n'
        'checkout,cobrança duplicada,2026-03-05\n'
        'auth,sessão não expirava,2026-01-20\n', encoding="utf-8-sig"
    )
    details = load_incident_details(str(path))
    assert [item["date"] for item in details["checkout"]] == [
        "2026-03-05", "2026-02-10"
    ]
    assert details["checkout"][1]["description"] == "gateway, indisponível"
    assert details["auth"][0]["description"] == "sessão não expirava"


@pytest.mark.parametrize("row", [
    "checkout,outage,2026-02-30", "checkout,outage,20260305",
    "checkout,outage", "checkout,,2026-03-05", ",outage,2026-03-05",
])
def test_incident_details_rejects_invalid_rows(tmp_path, row):
    path = tmp_path / "details.csv"
    path.write_text("module,description,date\n" + row, encoding="utf-8")
    with pytest.raises(ValueError, match="linha 2"):
        load_incident_details(str(path))


@pytest.mark.parametrize("loader", [load_incidents, load_incident_details])
def test_incident_csv_requires_headers(tmp_path, loader):
    path = tmp_path / "invalid.csv"
    path.write_text("unexpected\nvalue\n", encoding="utf-8")
    with pytest.raises(ValueError, match="colunas obrigatórias"):
        loader(str(path))


def test_incident_counts_skip_missing_negative_and_empty_modules(tmp_path):
    path = tmp_path / "counts.csv"
    path.write_text(
        "module,incident_count\ncheckout\nauth,-1\n,3\nvalid,2\n",
        encoding="utf-8",
    )
    assert load_incidents(str(path)) == {"valid": 2}


def test_incident_details_header_only_is_empty(tmp_path):
    path = tmp_path / "details.csv"
    path.write_text("module,description,date\n", encoding="utf-8")
    assert load_incident_details(str(path)) == {}


def test_project_incident_loaders_read_repo_paths(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with init_repo(project) as repo:
        (project / "reports").mkdir()
        (project / "reports/incidents.csv").write_text(
            "module,incident_count\ncheckout,4\n", encoding="utf-8",
        )
        (project / "reports/incident_details.csv").write_text(
            "module,description,date\ncheckout,outage,2026-09-10\n",
            encoding="utf-8",
        )
        repo.index.add([
            "reports/incidents.csv", "reports/incident_details.csv",
        ])
        ref = repo.index.commit("incident reports").hexsha

        assert load_project_incidents(
            repo, ref, "repo:reports/incidents.csv",
        ) == {"checkout": 4}
        assert load_project_incident_details(
            repo, ref, "repo:reports/incident_details.csv",
        ) == {"checkout": [{"description": "outage", "date": "2026-09-10"}]}
