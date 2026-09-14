from pathlib import Path
import subprocess

import pytest

from garantiu.test_execution import generate_pytest_report
from tests.conftest import init_repo


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    with init_repo(root) as repo:
        (root / "test_example.py").write_text(
            "def test_pass():\n    assert True\n", encoding="utf-8",
        )
        repo.index.add(["test_example.py"])
        repo.index.commit("initial")
        yield repo


def test_generates_fresh_reports_and_preserves_earlier_results(project, tmp_path):
    first = generate_pytest_report(project, "HEAD", tmp_path / "data")
    assert first["exit_code"] == 0
    assert first["results"][0]["status"] == "passed"
    path = Path(project.working_tree_dir) / "test_example.py"
    path.write_text("def test_fail():\n    assert False\n", encoding="utf-8")
    project.index.add(["test_example.py"])
    project.index.commit("failing test")
    second = generate_pytest_report(project, "HEAD", tmp_path / "data")
    assert second["exit_code"] == 1
    assert second["results"][0]["status"] == "failed"
    assert first["path"] != second["path"]
    assert Path(first["path"]).is_file()
    assert Path(second["path"]).is_relative_to(tmp_path / "data")


def test_reports_in_repository_do_not_block_next_run(project):
    first = generate_pytest_report(project, "HEAD", project.working_tree_dir)
    second = generate_pytest_report(project, "HEAD", project.working_tree_dir)
    assert Path(first["path"]).is_file()
    assert second["results"][0]["status"] == "passed"


def test_empty_suite_is_explicit(project, tmp_path):
    path = Path(project.working_tree_dir) / "test_example.py"
    path.write_text("# no tests\n", encoding="utf-8")
    project.index.add(["test_example.py"])
    project.index.commit("empty suite")
    result = generate_pytest_report(project, "HEAD", tmp_path / "data")
    assert result["exit_code"] == 5
    assert result["results"] == []


def test_rejects_different_selected_commit(project, tmp_path):
    ref = project.head.commit.hexsha
    root = Path(project.working_tree_dir)
    (root / "test_example.py").write_text("# changed", encoding="utf-8")
    project.index.add(["test_example.py"])
    project.index.commit("new commit")
    with pytest.raises(ValueError):
        generate_pytest_report(project, ref, tmp_path / "data")
    assert not (tmp_path / "data").exists()


@pytest.mark.parametrize("pending", ["unstaged", "staged", "untracked"])
def test_runs_local_changes_and_identifies_working_tree(project, tmp_path, pending):
    root = Path(project.working_tree_dir)
    name = "test_new.py" if pending == "untracked" else "test_example.py"
    (root / name).write_text("def test_local():\n    assert False\n", encoding="utf-8")
    if pending == "staged":
        project.index.add([name])
    result = generate_pytest_report(project, "HEAD", tmp_path / "data")
    assert result["working_tree_dirty"] is True
    assert result["exit_code"] == 1
    assert any(case["name"] == "test_local" and case["status"] == "failed" for case in result["results"])
    assert Path(result["path"]).is_file()


def test_bare_repository_requires_local_clone(project, tmp_path):
    with project.clone(tmp_path / "bare", bare=True) as bare:
        with pytest.raises(ValueError, match="pasta local"):
            generate_pytest_report(bare, "HEAD", tmp_path / "data")


@pytest.mark.parametrize("failure", ["timeout", "launch", "interrupted", "missing", "invalid"])
def test_execution_errors_never_import_partial_or_stale_report(project, tmp_path, monkeypatch, failure):
    def run(command, **kwargs):
        output = Path(command[-1].split("=", 1)[1])
        assert kwargs["cwd"] == Path(project.working_tree_dir)
        assert "shell" not in kwargs
        if failure != "missing":
            output.write_text("invalid" if failure == "invalid" else "<testsuites/>")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 120)
        if failure == "launch":
            raise OSError("cannot launch")
        return subprocess.CompletedProcess(command, 2 if failure == "interrupted" else 0)

    monkeypatch.setattr("garantiu.test_execution.subprocess.run", run)
    with pytest.raises(ValueError):
        generate_pytest_report(project, "HEAD", tmp_path / "data")
    assert not list((tmp_path / "data").rglob("*.xml"))
