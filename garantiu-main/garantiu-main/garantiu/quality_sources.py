"""Discover optional quality reports inside a repository without executing it."""

import csv
import os
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree

import git


IGNORED_DIRECTORIES = {
    ".git", ".hg", ".svn", ".pytest_cache", ".tox", ".venv",
    "__pycache__", "node_modules", "dist", "build", "coverage", "htmlcov",
    "vendor", "sample_data", "examples", "fixtures", "garantiu-junit",
}
MAX_CANDIDATE_BYTES = 25 * 1024 * 1024
MAX_SCANNED_FILES = 5_000
QUALITY_TEMPLATES = {
    "junit": ("modelo-junit.xml", '<!-- Modelo vazio: nao representa uma execucao de testes. -->\n<testsuites/>\n'),
    "incident_counts": ("modelo-incidents.csv", "module,incident_count\n"),
    "incident_details": ("modelo-incident_details.csv", "module,description,date\n"),
}
TEMPLATE_NAMES = {name for name, _ in QUALITY_TEMPLATES.values()}
PREFERRED_NAMES = {
    "junit": ("junit.xml", "test-results.xml", "results.xml", "report.xml"),
    "incident_counts": ("incidents.csv", "incidentes.csv"),
    "incident_details": (
        "incident_details.csv", "incident-details.csv", "detalhes-incidentes.csv",
    ),
}


def _classify(content: bytes, suffix: str) -> set[str]:
    if suffix == ".xml":
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return set()
        tag = root.tag.rsplit("}", 1)[-1]
        return {"junit"} if tag in {"testsuite", "testsuites"} else set()
    if suffix != ".csv":
        return set()
    try:
        header = next(csv.reader(StringIO(content.decode("utf-8-sig"))), [])
    except (UnicodeDecodeError, csv.Error):
        return set()
    columns = {column.strip() for column in header}
    kinds = set()
    if {"module", "incident_count"}.issubset(columns):
        kinds.add("incident_counts")
    if {"module", "description", "date"}.issubset(columns):
        kinds.add("incident_details")
    return kinds


def _candidate_sort_key(kind: str, location: str) -> tuple[int, int, str]:
    normalized = location[5:] if location.startswith("repo:") else location
    path = Path(normalized)
    name = path.name.lower()
    preferred = PREFERRED_NAMES[kind]
    rank = preferred.index(name) if name in preferred else len(preferred)
    return rank, len(path.parts), normalized.lower()


def _add_candidate(
    results: dict[str, list[str]], location: str, content: bytes,
) -> None:
    if Path(location.removeprefix("repo:")).name.lower() in TEMPLATE_NAMES:
        return
    suffix = Path(location).suffix.lower()
    for kind in _classify(content, suffix):
        results[kind].append(location)


def _discover_worktree(root: Path, results: dict[str, list[str]]) -> None:
    scanned = 0
    for directory, names, files in os.walk(root, followlinks=False):
        names[:] = [name for name in names if name not in IGNORED_DIRECTORIES]
        for name in files:
            path = Path(directory) / name
            if path.suffix.lower() not in {".xml", ".csv"} or path.is_symlink():
                continue
            scanned += 1
            if scanned > MAX_SCANNED_FILES:
                return
            try:
                if path.stat().st_size > MAX_CANDIDATE_BYTES:
                    continue
                content = path.read_bytes()
            except OSError:
                continue
            _add_candidate(results, str(path.resolve()), content)


def _discover_tree(repo: git.Repo, ref: str, results: dict[str, list[str]]) -> None:
    scanned = 0
    for item in repo.commit(ref).tree.traverse():
        path = Path(item.path)
        if (
            item.type != "blob"
            or path.suffix.lower() not in {".xml", ".csv"}
            or any(part in IGNORED_DIRECTORIES for part in path.parts[:-1])
        ):
            continue
        scanned += 1
        if (
            scanned > MAX_SCANNED_FILES
            or item.size > MAX_CANDIDATE_BYTES
        ):
            continue
        try:
            content = item.data_stream.read()
        except (OSError, ValueError):
            continue
        _add_candidate(results, f"repo:{item.path}", content)


def discover_quality_sources(
    repo_path: str, ref: str = "HEAD",
) -> dict[str, list[str]]:
    """Return JUnit and incident candidates found in a local or bare repository."""
    results = {"junit": [], "incident_counts": [], "incident_details": []}
    with git.Repo(repo_path) as repo:
        if repo.bare:
            _discover_tree(repo, ref, results)
        else:
            _discover_worktree(Path(repo.working_tree_dir), results)
    for kind, locations in results.items():
        results[kind] = sorted(
            set(locations), key=lambda item: _candidate_sort_key(kind, item),
        )
    return results


def discover_quality_sources_in_directory(
    directory: str | Path,
) -> dict[str, list[str]]:
    """Return quality reports stored in an arbitrary local directory."""
    results = {"junit": [], "incident_counts": [], "incident_details": []}
    root = Path(directory).expanduser().resolve()
    if not root.exists():
        return results
    if not root.is_dir():
        raise ValueError("O local de relatórios precisa ser uma pasta.")
    _discover_worktree(root, results)
    for kind, locations in results.items():
        results[kind] = sorted(
            set(locations), key=lambda item: _candidate_sort_key(kind, item),
        )
    return results


def create_missing_quality_templates(directory: str | Path) -> list[str]:
    """Create clearly named empty templates without replacing existing files."""
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    sources = discover_quality_sources_in_directory(root)
    created = []
    for kind, (name, content) in QUALITY_TEMPLATES.items():
        if sources[kind]:
            continue
        path = root / name
        try:
            with path.open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
        except FileExistsError:
            continue
        created.append(str(path))
    return created
