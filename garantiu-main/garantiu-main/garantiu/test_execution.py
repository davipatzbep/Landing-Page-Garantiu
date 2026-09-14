"""Run local pytest suites and retain a fresh JUnit report for each analysis."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from garantiu.test_reports import parse_junit_report

PYTEST_TIMEOUT_SECONDS = 600


def generate_pytest_report(repo, ref: str, data_directory: str | Path) -> dict:
    """Execute the local working tree, retaining whether it has pending changes."""
    if repo.bare or not repo.working_tree_dir:
        raise ValueError("Para gerar JUnit, clone o projeto e informe sua pasta local.")
    if repo.head.commit.hexsha != repo.commit(ref).hexsha:
        raise ValueError("Para gerar JUnit, selecione o commit atualmente aberto na pasta local.")
    root = Path(repo.working_tree_dir).resolve()
    reports = Path(data_directory).resolve() / "garantiu-junit"
    working_tree_dirty = repo.is_dirty(untracked_files=False) or any(
        not (root / name).resolve().is_relative_to(reports)
        for name in repo.untracked_files
    )
    local_python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python = str(local_python) if local_python.is_file() else sys.executable
    identity = hashlib.sha256(str(root).encode()).hexdigest()[:16]
    output = reports / identity / uuid4().hex / "junit.xml"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        python, "-B", "-m", "pytest", "-q",
        "-o", f"cache_dir={output.parent / '.pytest_cache'}",
        f"--junitxml={output}",
    ]
    try:
        completed = subprocess.run(
            command, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            timeout=PYTEST_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output.unlink(missing_ok=True)
        raise ValueError(
            f"Os testes excederam {PYTEST_TIMEOUT_SECONDS} segundos. "
            "Execute-os no terminal e importe o JUnit para analisar."
        ) from exc
    except OSError as exc:
        output.unlink(missing_ok=True)
        raise ValueError("Não foi possível iniciar o Python do projeto. Confira o ambiente .venv.") from exc
    if completed.returncode not in {0, 1, 5} or not output.is_file():
        output.unlink(missing_ok=True)
        raise ValueError(
            f"O pytest não concluiu a geração do JUnit (saída {completed.returncode}). "
            "Confira pytest e dependências no ambiente do projeto. "
            "Execute python -m pytest no terminal para ver o diagnóstico."
        )
    try:
        results = parse_junit_report(str(output))
    except (OSError, ValueError) as exc:
        output.unlink(missing_ok=True)
        raise ValueError("O pytest não produziu um relatório JUnit válido.") from exc
    return {
        "path": str(output), "exit_code": completed.returncode,
        "results": results, "working_tree_dirty": working_tree_dirty,
    }
