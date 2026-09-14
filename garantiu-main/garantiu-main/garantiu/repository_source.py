"""Resolve local repositories and temporarily clone GitHub HTTPS sources."""

import os
import re
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import git


def repository_key(source: str) -> str:
    """Stable history identity; never includes credentials or a temporary path."""
    source = source.strip()
    if not source:
        raise ValueError("Informe uma pasta local ou um link de repositório GitHub.")
    if "://" not in source and not source.startswith("git@"):
        return os.path.normcase(str(Path(source).resolve()))
    url = urlsplit(source)
    parts = url.path.strip("/").split("/")
    if (
        url.scheme != "https" or url.netloc.lower() != "github.com"
        or url.query or url.fragment or len(parts) != 2
    ):
        raise ValueError(
            "Use o link HTTPS da raiz: https://github.com/usuario/repositorio "
            "(sem credenciais, /tree/branch ou /blob/arquivo)."
        )
    owner, name = parts
    if name.endswith(".git"):
        name = name[:-4]
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", owner)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
            or name in {".", ".."}):
        raise ValueError("Link de repositório GitHub inválido.")
    return f"https://github.com/{owner.lower()}/{name.lower()}"


@dataclass(frozen=True)
class RepositorySource:
    path: str
    key: str


@contextmanager
def prepare_repository(source: str):
    """Yield a local path and stable identity; remove remote clone on exit.

    Bare clones retain every branch and full history without checking out or
    running repository code. Separate temporary directories isolate sessions.
    Git may use an already configured credential helper for private repos.
    """
    key = repository_key(source)
    if not key.startswith("https://github.com/"):
        with git.Repo(key) as repo:
            path = os.path.normcase(str(Path(repo.working_dir).resolve()))
        yield RepositorySource(path, path)
        return
    with TemporaryDirectory(prefix="garantiu-github-") as directory:
        path = str(Path(directory) / "repository.git")
        try:
            subprocess.run(
                [git.Git.GIT_PYTHON_GIT_EXECUTABLE,
                 "-c", "http.followRedirects=false",
                 "clone", "--bare", "--", key + ".git", path],
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                     "GCM_INTERACTIVE": "never"},
                capture_output=True, check=True, timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(
                "O download do GitHub excedeu 120 segundos. "
                "Tente novamente ou clone o projeto e informe a pasta local."
            ) from exc
        except (subprocess.CalledProcessError, OSError) as exc:
            raise ValueError(
                "Não foi possível obter o repositório do GitHub. Confira o "
                "link, a conexão e o acesso. Para repositórios privados, "
                "configure previamente a autenticação HTTPS do Git no computador."
            ) from exc
        yield RepositorySource(path, key)
