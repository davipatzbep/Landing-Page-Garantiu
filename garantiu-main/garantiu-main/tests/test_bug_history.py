import pytest

from garantiu.bug_history import (
    bug_evidence_for_files,
    bug_history_detail_by_module,
    build_bug_history,
    get_bug_fix_commits,
)
from tests.conftest import init_repo


@pytest.fixture
def repo_with_bug_fixes(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    (repo_path / "checkout").mkdir()
    f = repo_path / "checkout" / "gateway.py"

    f.write_text("v1")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("initial commit")

    f.write_text("v2")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("fix: corrige calculo do gateway")

    f.write_text("v3")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("add new feature")

    f.write_text("v4")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("fixes bug in refund flow")

    return str(repo_path)


def test_get_bug_fix_commits_filters_by_message(repo_with_bug_fixes):
    commits = get_bug_fix_commits(repo_with_bug_fixes)
    assert len(commits) == 2
    messages = [c["message"] for c in commits]
    assert any("corrige" in m for m in messages)
    assert any("fixes bug" in m for m in messages)


def test_build_bug_history_counts_per_file(repo_with_bug_fixes):
    history = build_bug_history(repo_with_bug_fixes)
    assert history["checkout/gateway.py"] == 2


def test_bug_details_recent_first(repo_with_bug_fixes):
    details = bug_history_detail_by_module(repo_with_bug_fixes, "checkout")
    assert len(details) == 2
    assert details[0]["message"].startswith("fixes bug")
    assert details[1]["message"].startswith("fix:")
    assert all(len(item["date"]) == 10 for item in details)
    assert bug_history_detail_by_module(repo_with_bug_fixes, "missing") == []


def test_bug_details_root_module_and_one_entry_for_multiple_files(tmp_path):
    repo = init_repo(tmp_path)
    for name in ["app.py", "README.md", "checkout/a.py", "checkout/b.py"]:
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("initial", encoding="utf-8")
    repo.index.add(["app.py", "README.md", "checkout/a.py", "checkout/b.py"])
    commit = repo.index.commit(
        "fix: initial bug", commit_date="2026-03-05T12:00:00 +0000"
    )
    assert bug_history_detail_by_module(str(tmp_path), "README.md") == []
    for module in ["app.py", "checkout"]:
        details = bug_history_detail_by_module(str(tmp_path), module)
        assert details == [{
            "hash": commit.hexsha, "message": "fix: initial bug",
            "date": "2026-03-05",
        }]

    evidence = bug_evidence_for_files(
        str(tmp_path), {"checkout/a.py", "checkout/b.py"}
    )
    assert {(item["file_path"], item["hash"]) for item in evidence} == {
        ("checkout/a.py", commit.hexsha),
        ("checkout/b.py", commit.hexsha),
    }


def test_selected_ref_history_excludes_other_branch_and_later_fixes(tmp_path):
    with init_repo(tmp_path) as repo:
        (tmp_path / "checkout").mkdir()
        source = tmp_path / "checkout/gateway.py"
        source.write_text("initial", encoding="utf-8")
        repo.index.add(["checkout/gateway.py"])
        initial = repo.index.commit("initial")
        main_branch = repo.active_branch.name
        source.write_text("main fix", encoding="utf-8")
        repo.index.add(["checkout/gateway.py"])
        main_fix = repo.index.commit("fix: main only")
        branch = repo.create_head("release-test", initial)
        branch.checkout()
        source.write_text("release fix", encoding="utf-8")
        repo.index.add(["checkout/gateway.py"])
        release_fix = repo.index.commit("fix: release only")
        repo.heads[main_branch].checkout()

        assert [c["hash"] for c in get_bug_fix_commits(str(tmp_path))] == [
            main_fix.hexsha
        ]
        for ref in ["release-test", release_fix.hexsha]:
            assert [c["hash"] for c in get_bug_fix_commits(
                str(tmp_path), ref=ref
            )] == [release_fix.hexsha]
            assert build_bug_history(str(tmp_path), ref=ref) == {
                "checkout/gateway.py": 1
            }
            details = bug_history_detail_by_module(
                str(tmp_path), "checkout", ref=ref
            )
            assert [c["hash"] for c in details] == [release_fix.hexsha]
        assert get_bug_fix_commits(str(tmp_path), ref=initial.hexsha) == []
        assert build_bug_history(str(tmp_path), ref=initial.hexsha) == {}
        assert bug_history_detail_by_module(
            str(tmp_path), "checkout", ref=initial.hexsha
        ) == []
        assert repo.active_branch.name == main_branch
