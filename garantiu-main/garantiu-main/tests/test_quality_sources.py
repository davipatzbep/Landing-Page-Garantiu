import git
import pytest

from garantiu.quality_sources import (
    TEMPLATE_NAMES, create_missing_quality_templates, discover_quality_sources,
    discover_quality_sources_in_directory,
)
from tests.conftest import init_repo


def test_discovers_quality_files_by_content_in_local_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with init_repo(project) as repo:
        (project / "src.py").write_text("value = 1\n", encoding="utf-8")
        repo.index.add(["src.py"])
        repo.index.commit("initial")
    reports = project / "reports"
    reports.mkdir()
    junit = reports / "custom.xml"
    counts = reports / "operational.csv"
    details = reports / "events.csv"
    junit.write_text("<testsuite><testcase name='ok'/></testsuite>", encoding="utf-8")
    counts.write_text("module,incident_count\ncheckout,2\n", encoding="utf-8")
    details.write_text(
        "module,description,date\ncheckout,outage,2026-09-10\n",
        encoding="utf-8",
    )
    (reports / "other.xml").write_text("<project/>", encoding="utf-8")

    found = discover_quality_sources(str(project))

    assert found == {
        "junit": [str(junit.resolve())],
        "incident_counts": [str(counts.resolve())],
        "incident_details": [str(details.resolve())],
    }


def test_bare_repository_returns_repo_locations_and_prefers_known_names(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with init_repo(project) as repo:
        (project / "reports").mkdir()
        (project / "reports/results.xml").write_text(
            "<testsuite/>", encoding="utf-8",
        )
        (project / "z.xml").write_text("<testsuite/>", encoding="utf-8")
        repo.index.add(["reports/results.xml", "z.xml"])
        repo.index.commit("reports")
    bare = tmp_path / "project.git"
    with git.Repo.clone_from(project, bare, bare=True):
        pass

    found = discover_quality_sources(str(bare))

    assert found["junit"] == ["repo:reports/results.xml", "repo:z.xml"]


@pytest.mark.parametrize("directory_name", [".venv", "sample_data", "fixtures", "garantiu-junit"])
def test_ignores_non_production_candidate_directories(tmp_path, directory_name):
    project = tmp_path / "project"
    project.mkdir()
    with init_repo(project) as repo:
        (project / "src.py").write_text("value = 1\n", encoding="utf-8")
        repo.index.add(["src.py"])
        repo.index.commit("initial")
    ignored = project / directory_name
    ignored.mkdir()
    (ignored / "junit.xml").write_text("<testsuite/>", encoding="utf-8")

    assert discover_quality_sources(str(project))["junit"] == []


def test_empty_directory_gets_templates_without_becoming_evidence(tmp_path):
    created = create_missing_quality_templates(tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == TEMPLATE_NAMES
    assert len(created) == 3
    assert discover_quality_sources_in_directory(tmp_path) == {
        "junit": [], "incident_counts": [], "incident_details": [],
    }
    assert create_missing_quality_templates(tmp_path) == []


def test_template_creation_preserves_existing_sources_and_templates(tmp_path):
    real_report = tmp_path / "existing.xml"
    real_report.write_text("<testsuites/>", encoding="utf-8")
    edited = tmp_path / "modelo-incidents.csv"
    edited.write_text("user content", encoding="utf-8")
    created = create_missing_quality_templates(tmp_path)
    assert len(created) == 1
    assert not (tmp_path / "modelo-junit.xml").exists()
    assert edited.read_text(encoding="utf-8") == "user content"
    assert real_report.read_text(encoding="utf-8") == "<testsuites/>"


def test_filled_copy_of_csv_template_is_discovered(tmp_path):
    create_missing_quality_templates(tmp_path)
    csv_path = tmp_path / "incidents.csv"
    csv_path.write_text("module,incident_count\ncheckout,2\n", encoding="utf-8")
    assert discover_quality_sources_in_directory(tmp_path)["incident_counts"] == [str(csv_path)]
