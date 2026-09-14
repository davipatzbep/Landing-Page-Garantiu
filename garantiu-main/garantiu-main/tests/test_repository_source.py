import os
import subprocess
from pathlib import Path

import git
import pytest

from garantiu.repository_source import prepare_repository, repository_key
from garantiu.git_reader import get_changed_files
from tests.conftest import init_repo


@pytest.mark.parametrize("url", [
    "https://github.com/Owner/Project", "https://github.com/owner/project.git/",
    " https://github.com/OWNER/PROJECT/ ",
])
def test_github_identity_is_stable(url):
    assert repository_key(url) == "https://github.com/owner/project"


@pytest.mark.parametrize("url", [
    "https://github.com/owner/project/tree/main",
    "https://github.com/owner/project?token=value",
    "https://user:password@github.com/owner/project",
    "https://github.com.evil.example/owner/project",
    "http://github.com/owner/project", "file:///tmp/repo",
    "git@github.com:owner/project.git", "https://github.com/owner/..",
    "https://github.com/owner/project#readme", "https://github.com/owner",
])
def test_reject_unsupported_urls_before_network(url, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid URL must not access network")
    monkeypatch.setattr(subprocess, "run", unexpected)
    with pytest.raises(ValueError):
        with prepare_repository(url):
            pass


@pytest.fixture
def remote_fixture(tmp_path, monkeypatch):
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    with init_repo(upstream) as repo:
        (upstream / "checkout").mkdir()
        source = upstream / "checkout/pay.py"
        source.write_text("first\n", encoding="utf-8")
        repo.index.add(["checkout/pay.py"])
        repo.index.commit("initial")
        repo.create_tag("v1")
        source.write_text("first\nsecond\n", encoding="utf-8")
        repo.index.add(["checkout/pay.py"])
        repo.index.commit("fix: payment")
        repo.create_head("release/test")
    calls = []
    real_run = subprocess.run

    def clone_fixture(command, **kwargs):
        if "clone" in command and command[-2].startswith("https://github.com/"):
            calls.append(command)
            assert kwargs["timeout"] == 120
            assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
            command = [*command[:-2], str(upstream), command[-1]]
        return real_run(command, **kwargs)

    monkeypatch.setattr(subprocess, "run", clone_fixture)
    return upstream, calls


def test_local_path_is_preserved(remote_fixture):
    upstream, calls = remote_fixture
    with prepare_repository(str(upstream)) as source:
        assert source.key == os.path.normcase(str(upstream.resolve()))
        assert source.path == source.key
    assert upstream.exists()
    assert not calls


def test_remote_clone_full_history_branches_refresh_and_cleanup(remote_fixture):
    upstream, calls = remote_fixture
    with prepare_repository("https://github.com/owner/project.git") as source:
        clone_path = Path(source.path)
        assert source.key == "https://github.com/owner/project"
        with git.Repo(source.path) as repo:
            assert repo.bare
            assert repo.commit("release/test").hexsha == repo.commit("HEAD").hexsha
        assert get_changed_files(source.path, "v1", "HEAD")[0]["lines_added"] == 1
    assert not clone_path.exists()
    with git.Repo(upstream) as repo:
        (upstream / "checkout/pay.py").write_text("new\n", encoding="utf-8")
        repo.index.add(["checkout/pay.py"])
        latest = repo.index.commit("new release").hexsha
    with prepare_repository("https://github.com/owner/project") as source:
        with git.Repo(source.path) as repo:
            assert repo.commit("HEAD").hexsha == latest
    assert len(calls) == 2


def test_analysis_error_removes_temporary_clone(remote_fixture):
    with pytest.raises(ValueError, match="analysis failed"):
        with prepare_repository("https://github.com/owner/project") as source:
            clone_path = Path(source.path)
            raise ValueError("analysis failed")
    assert not clone_path.exists()


@pytest.mark.parametrize("timeout", [False, True])
def test_download_errors_are_actionable_and_do_not_leak_stderr(monkeypatch, timeout):
    paths = []
    def failed(command, **kwargs):
        paths.append(Path(command[-1]))
        if timeout:
            raise subprocess.TimeoutExpired(command, 120)
        raise subprocess.CalledProcessError(128, command, stderr=b"sensitive details")
    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(ValueError) as error:
        with prepare_repository("https://github.com/owner/project"):
            pass
    assert "sensitive details" not in str(error.value)
    assert "120 segundos" in str(error.value) if timeout else "acesso" in str(error.value)
    assert not paths[0].parent.exists()
