import re

import git

_RENAME_BRACES_RE = re.compile(r"^(.*)\{.* => (.*)\}(.*)$")
AUTO_BASE_REF = "AUTO"
_DOCUMENTATION_SUFFIXES = {
    ".md", ".mdx", ".pdf", ".rst", ".txt", ".adoc",
}
PRODUCT_CODE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts",
    ".go", ".rs", ".rb", ".php", ".cs", ".c", ".h", ".cc", ".cpp",
    ".cxx", ".hpp", ".swift", ".dart", ".vue", ".svelte", ".html",
    ".htm", ".css", ".scss", ".sass", ".less", ".sql", ".sh", ".bash",
    ".zsh", ".ps1", ".bat", ".cmd",
}
TEST_DIRECTORIES = {"test", "tests", "__tests__", "spec", "specs"}
IGNORED_DIRECTORIES = {
    ".github": "repository_meta", ".gitlab": "repository_meta",
    ".circleci": "repository_meta", ".streamlit": "configuration",
    "docs": "documentation", "doc": "documentation",
    "sample_data": "quality_data", "examples": "generated_or_vendor",
    "fixtures": "quality_data", "dist": "generated_or_vendor",
    "build": "generated_or_vendor", "coverage": "quality_data",
    "htmlcov": "quality_data", "vendor": "generated_or_vendor",
    "node_modules": "generated_or_vendor", ".venv": "generated_or_vendor",
    "venv": "generated_or_vendor", "__pycache__": "generated_or_vendor",
    ".pytest_cache": "generated_or_vendor", ".mypy_cache": "generated_or_vendor",
}
SPECIAL_FILE_CATEGORIES = {
    ".gitignore": "repository_meta", ".gitattributes": "repository_meta",
    ".editorconfig": "repository_meta", ".dockerignore": "repository_meta",
    "package.json": "dependency_metadata", "package-lock.json": "dependency_metadata",
    "yarn.lock": "dependency_metadata", "pnpm-lock.yaml": "dependency_metadata",
    "pyproject.toml": "dependency_metadata", "poetry.lock": "dependency_metadata",
    "requirements.txt": "dependency_metadata", "pipfile": "dependency_metadata",
    "pipfile.lock": "dependency_metadata", "cargo.toml": "dependency_metadata",
    "cargo.lock": "dependency_metadata", "go.mod": "dependency_metadata",
    "go.sum": "dependency_metadata", "gemfile": "dependency_metadata",
    "gemfile.lock": "dependency_metadata", "composer.json": "dependency_metadata",
    "composer.lock": "dependency_metadata", "pom.xml": "dependency_metadata",
    "build.gradle": "dependency_metadata", "build.gradle.kts": "dependency_metadata",
    "dockerfile": "configuration", "makefile": "configuration",
}
ASSET_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp",
    ".woff", ".woff2", ".ttf", ".otf", ".mp3", ".wav", ".ogg", ".mp4",
    ".mov", ".avi", ".webm",
}
QUALITY_DATA_SUFFIXES = {".xml", ".csv", ".lcov"}
CONFIGURATION_SUFFIXES = {".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf"}
CATEGORY_REASONS = {
    "test_code": "Código de teste não representa diretamente código de produto.",
    "documentation": "Documentação não participa do cálculo de risco de código.",
    "repository_meta": "Metadado do repositório excluído do cálculo.",
    "configuration": "Arquivo de configuração excluído do cálculo.",
    "dependency_metadata": "Manifesto ou lockfile de dependência excluído.",
    "asset": "Asset binário ou visual excluído do cálculo.",
    "generated_or_vendor": "Arquivo gerado, cache ou código de terceiro excluído.",
    "quality_data": "Relatório ou dado de qualidade usado apenas como evidência.",
    "unknown": "Tipo de arquivo não reconhecido como código de produto.",
}


def _resolve_renamed_path(path: str) -> str:
    """
    git diff --numstat reports renames either as "{old => new}" with a
    shared prefix/suffix, or as "old/path => new/path" when nothing is
    shared. Resolve both forms to the file's current (new) path.
    """
    match = _RENAME_BRACES_RE.match(path)
    if match:
        prefix, new, suffix = match.groups()
        return f"{prefix}{new}{suffix}"
    if " => " in path:
        return path.split(" => ")[-1]
    return path


def resolve_comparison_base(
    repo: git.Repo, base_ref: str, head_ref: str,
) -> tuple[str, str]:
    """Resolve an explicit base or choose a release-sized automatic range.

    Automatic mode compares from the latest tag reachable before the selected
    head. Repositories without tags fall back to the first commit reachable on
    the head's first-parent history. The returned tuple contains the full SHA
    and a human-readable label.
    """
    head = repo.commit(head_ref)
    requested = base_ref.strip()
    if requested and requested.upper() != AUTO_BASE_REF:
        return repo.commit(requested).hexsha, requested

    if head.parents:
        try:
            tag = repo.git.describe(
                head.parents[0].hexsha, tags=True, abbrev=0,
            ).strip()
        except git.GitCommandError:
            tag = ""
        if tag:
            return repo.commit(tag).hexsha, tag

    roots = repo.git.rev_list(
        "--first-parent", "--max-parents=0", head.hexsha,
    ).splitlines()
    if not roots:
        raise ValueError("Não foi possível localizar o primeiro commit do intervalo.")
    root_sha = roots[0]
    return root_sha, f"primeiro commit ({root_sha[:8]})"


def is_documentation_change(path: str) -> bool:
    """Legacy documentation-only filter; analysis uses classify_changed_path."""
    normalized = path.replace("\\", "/").lower()
    if normalized.startswith("docs/"):
        return True
    suffix = "." + normalized.rsplit(".", 1)[-1] if "." in normalized else ""
    return suffix in _DOCUMENTATION_SUFFIXES


def classify_changed_path(path: str) -> dict:
    """Classify a resolved Git path and decide whether it contributes to risk."""
    normalized = path.replace("\\", "/").strip("/")
    lowered = normalized.lower()
    parts = [part for part in lowered.split("/") if part]
    name = parts[-1] if parts else ""
    suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""

    for part in parts[:-1]:
        if part in IGNORED_DIRECTORIES:
            category = IGNORED_DIRECTORIES[part]
            return {
                "category": category, "include_in_risk": False,
                "reason": CATEGORY_REASONS[category],
            }
    if name in SPECIAL_FILE_CATEGORIES or (
        name.startswith("requirements") and suffix == ".txt"
    ):
        category = SPECIAL_FILE_CATEGORIES.get(name, "dependency_metadata")
    elif any(part in TEST_DIRECTORIES for part in parts[:-1]) or (
        name.startswith("test_") or name.endswith("_test" + suffix)
        or ".spec." in name or ".test." in name
    ):
        category = "test_code"
    elif suffix in _DOCUMENTATION_SUFFIXES:
        category = "documentation"
    elif suffix in ASSET_SUFFIXES:
        category = "asset"
    elif suffix in QUALITY_DATA_SUFFIXES or name in {".coverage", "coverage.json"}:
        category = "quality_data"
    elif suffix in CONFIGURATION_SUFFIXES or name.startswith(".env"):
        category = "configuration"
    elif suffix in PRODUCT_CODE_SUFFIXES:
        return {
            "category": "product_code", "include_in_risk": True,
            "reason": "Código de produto reconhecido.",
        }
    else:
        category = "unknown"
    return {
        "category": category, "include_in_risk": False,
        "reason": CATEGORY_REASONS[category],
    }


def get_changed_files(repo_path: str, base_ref: str, head_ref: str) -> list[dict]:
    """
    Returns changed files between base_ref and head_ref as a list of dicts:
    {"path": str, "module": str, "lines_added": int, "lines_removed": int}.
    module is the top-level directory of path, or the filename itself if the
    file lives at the repo root.
    """
    with git.Repo(repo_path) as repo:
        numstat = repo.git.diff(base_ref, head_ref, "--numstat", "-z")

    results = []
    records = numstat.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        added_str, removed_str, path = record.split("\t", 2)
        if not path:
            # With -z, a rename stores old and new paths as the next two
            # NUL-delimited fields instead of quoting or brace-compressing.
            if index + 1 >= len(records):
                raise ValueError("Saída Git incompleta ao ler um arquivo renomeado.")
            index += 1  # old path is intentionally ignored
            path = records[index]
            index += 1
        added = 0 if added_str == "-" else int(added_str)
        removed = 0 if removed_str == "-" else int(removed_str)
        path = _resolve_renamed_path(path)
        module = path.split("/")[0] if "/" in path else path
        results.append({
            "path": path,
            "module": module,
            "lines_added": added,
            "lines_removed": removed,
        })
    return results
