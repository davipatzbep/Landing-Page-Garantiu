import pytest

from garantiu.git_reader import (
    classify_changed_path, get_changed_files, is_documentation_change,
    resolve_comparison_base,
)
from tests.conftest import init_repo


@pytest.fixture
def sample_repo(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    (repo_path / "checkout").mkdir()
    gateway = repo_path / "checkout" / "gateway.py"
    gateway.write_text("def pay():\n    pass\n")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("initial commit")
    repo.create_tag("v1.0.0")

    gateway.write_text("def pay():\n    pass\n\ndef refund():\n    pass\n")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("add refund")
    return str(repo_path)


def test_get_changed_files_detects_module_and_lines(sample_repo):
    changes = get_changed_files(sample_repo, "v1.0.0", "HEAD")
    assert len(changes) == 1
    assert changes[0]["path"] == "checkout/gateway.py"
    assert changes[0]["module"] == "checkout"
    assert changes[0]["lines_added"] == 3
    assert changes[0]["lines_removed"] == 0


def test_get_changed_files_resolves_module_on_rename_same_filename(tmp_path):
    repo_path = tmp_path / "repo3"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    (repo_path / "checkout").mkdir()
    gateway = repo_path / "checkout" / "gateway.py"
    gateway.write_text("def pay():\n    pass\n")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("initial commit")

    (repo_path / "billing").mkdir()
    repo.index.move(["checkout/gateway.py", "billing/gateway.py"])
    repo.index.commit("move gateway to billing")

    changes = get_changed_files(str(repo_path), "HEAD~1", "HEAD")
    assert len(changes) == 1
    assert changes[0]["module"] == "billing"
    assert changes[0]["path"] == "billing/gateway.py"


def test_get_changed_files_resolves_module_on_rename_different_filename(tmp_path):
    repo_path = tmp_path / "repo4"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    (repo_path / "checkout").mkdir()
    gateway = repo_path / "checkout" / "gateway.py"
    gateway.write_text("def pay():\n    pass\n\ndef refund():\n    pass\n")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("initial commit")

    (repo_path / "billing").mkdir()
    repo.index.move(["checkout/gateway.py", "billing/pay.py"])
    repo.index.commit("move and rename gateway to billing/pay")

    changes = get_changed_files(str(repo_path), "HEAD~1", "HEAD")
    assert len(changes) == 1
    assert changes[0]["module"] == "billing"
    assert changes[0]["path"] == "billing/pay.py"


def test_get_changed_files_preserves_unicode_path(tmp_path):
    repo_path = tmp_path / "repo-unicode"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    document = repo_path / "Grupo 1 - 2° Hackathon.pdf"
    document.write_text("v1", encoding="utf-8")
    repo.index.add([document.name])
    repo.index.commit("initial")
    document.write_text("v2", encoding="utf-8")
    repo.index.add([document.name])
    repo.index.commit("update unicode document")

    changes = get_changed_files(str(repo_path), "HEAD~1", "HEAD")

    assert changes[0]["path"] == document.name
    assert is_documentation_change(changes[0]["path"])
    repo.close()


def test_get_changed_files_uses_filename_as_module_at_repo_root(tmp_path):
    repo_path = tmp_path / "repo2"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    f = repo_path / "README.md"
    f.write_text("v1")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    repo.create_tag("v1.0.0")
    f.write_text("v1\nv2")
    repo.index.add(["README.md"])
    repo.index.commit("update readme")

    changes = get_changed_files(str(repo_path), "v1.0.0", "HEAD")
    assert changes[0]["module"] == "README.md"


def test_automatic_base_uses_latest_tag_before_head(sample_repo):
    import git

    with git.Repo(sample_repo) as repo:
        base_sha, label = resolve_comparison_base(repo, "AUTO", "HEAD")

        assert label == "v1.0.0"
        assert base_sha == repo.commit("v1.0.0").hexsha


def test_automatic_base_falls_back_to_first_commit_without_tags(tmp_path):
    import git

    repo_path = tmp_path / "repo-auto"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    source = repo_path / "app.py"
    source.write_text("print('v1')\n", encoding="utf-8")
    repo.index.add(["app.py"])
    root = repo.index.commit("initial")
    source.write_text("print('v2')\n", encoding="utf-8")
    repo.index.add(["app.py"])
    repo.index.commit("change code")

    base_sha, label = resolve_comparison_base(repo, "", "HEAD")

    assert base_sha == root.hexsha
    assert label == f"primeiro commit ({root.hexsha[:8]})"
    repo.close()


@pytest.mark.parametrize("path", [
    "README.md", "docs/architecture.png", "guide.rst", "notes.txt",
])
def test_documentation_changes_are_classified(path):
    assert is_documentation_change(path)


@pytest.mark.parametrize("path", [
    "app.py", "src/main.ts", "config/settings.toml", ".github/workflows/ci.yml",
])
def test_product_changes_are_not_classified_as_documentation(path):
    assert not is_documentation_change(path)


@pytest.mark.parametrize("path,category", [
    ("garantiu/scoring.py", "product_code"),
    ("src/styles.css", "product_code"),
    ("src/requirements.py", "product_code"),
    ("tests/test_scoring.py", "test_code"),
    ("src/__tests__/scoring.ts", "test_code"),
    ("src/scoring.spec.ts", "test_code"),
    ("src/scoring.test.js", "test_code"),
    ("src/scoring_test.go", "test_code"),
    ("README.md", "documentation"),
    ("docs/example.py", "documentation"),
    ("manual.pdf", "documentation"),
    (".gitignore", "repository_meta"),
    (".gitattributes", "repository_meta"),
    (".editorconfig", "repository_meta"),
    (".github/workflows/ci.yml", "repository_meta"),
    (".gitlab/pipeline.py", "repository_meta"),
    (".circleci/config.yml", "repository_meta"),
    (".streamlit/config.toml", "configuration"),
    ("config/settings.yaml", "configuration"),
    (".env.local", "configuration"),
    ("package.json", "dependency_metadata"),
    ("package-lock.json", "dependency_metadata"),
    ("requirements-dev.txt", "dependency_metadata"),
    ("pyproject.toml", "dependency_metadata"),
    ("assets/logo.png", "asset"),
    ("assets/font.woff2", "asset"),
    ("assets/movie.mp4", "asset"),
    ("dist/main.js", "generated_or_vendor"),
    ("build/main.py", "generated_or_vendor"),
    ("vendor/library.py", "generated_or_vendor"),
    ("node_modules/pkg/index.js", "generated_or_vendor"),
    (".venv/library.py", "generated_or_vendor"),
    ("src/__pycache__/source.py", "generated_or_vendor"),
    ("examples/example.py", "generated_or_vendor"),
    ("sample_data/sample.py", "quality_data"),
    ("fixtures/example.py", "quality_data"),
    ("reports/junit.xml", "quality_data"),
    ("reports/incidents.csv", "quality_data"),
    ("coverage/report.html", "quality_data"),
    ("htmlcov/index.html", "quality_data"),
    ("src/file.unrecognized", "unknown"),
    ("unrecognized", "unknown"),
    ("SRC\\TESTS\\example.PY", "test_code"),
])
def test_classify_changed_path_categories_and_precedence(path, category):
    classification = classify_changed_path(path)
    assert classification["category"] == category
    assert classification["include_in_risk"] is (category == "product_code")
    assert classification["reason"]


@pytest.mark.parametrize("suffix", [
    "py", "js", "jsx", "ts", "tsx", "java", "kt", "go", "rs", "rb",
    "php", "cs", "c", "cpp", "swift", "dart", "vue", "svelte", "html",
    "css", "sass", "less", "sql", "sh", "ps1", "bat",
])
def test_classify_recognized_product_languages(suffix):
    assert classify_changed_path(f"src/main.{suffix}")["include_in_risk"]


@pytest.mark.parametrize("old_path,new_path,expected", [
    ("tests/example.py", "src/example.py", "product_code"),
    ("src/example.py", "tests/example.py", "test_code"),
])
def test_classification_uses_renamed_destination(tmp_path, old_path, new_path, expected):
    with init_repo(tmp_path) as repo:
        original = tmp_path / old_path
        original.parent.mkdir()
        original.write_text("def example():\n    return 1\n", encoding="utf-8")
        repo.index.add([old_path])
        repo.index.commit("initial")
        (tmp_path / new_path).parent.mkdir()
        repo.index.move([old_path, new_path])
        repo.index.commit("move source")

        changes = get_changed_files(str(tmp_path), "HEAD~1", "HEAD")

    assert len(changes) == 1
    assert changes[0]["path"] == new_path
    assert classify_changed_path(changes[0]["path"])["category"] == expected
