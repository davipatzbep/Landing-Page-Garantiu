import csv
from datetime import date
from io import StringIO
from pathlib import PurePosixPath


def _require_columns(reader: csv.DictReader, required: set[str]) -> None:
    missing = required.difference(reader.fieldnames or [])
    if missing:
        raise ValueError("CSV sem colunas obrigatórias: " + ", ".join(sorted(missing)))


def _load_incidents_stream(stream) -> dict:
    incidents = {}
    reader = csv.DictReader(stream)
    _require_columns(reader, {"module", "incident_count"})
    for row in reader:
        try:
            module = (row["module"] or "").strip()
            count = int(row["incident_count"])
            if module and count >= 0:
                incidents[module] = count
        except (KeyError, ValueError, TypeError):
            continue
    return incidents


def load_incidents(csv_path: str) -> dict:
    """Read module incident counts from a local UTF-8 CSV."""
    with open(csv_path, newline="", encoding="utf-8-sig") as stream:
        return _load_incidents_stream(stream)


def _load_incident_details_stream(stream) -> dict[str, list[dict]]:
    by_module = {}
    reader = csv.DictReader(stream)
    _require_columns(reader, {"module", "description", "date"})
    for row in reader:
        module = (row["module"] or "").strip()
        description = (row["description"] or "").strip()
        incident_date = (row["date"] or "").strip()
        if not module or not description:
            raise ValueError(
                f"CSV linha {reader.line_num}: módulo e descrição obrigatórios."
            )
        try:
            parsed_date = date.fromisoformat(incident_date)
            if parsed_date.isoformat() != incident_date:
                raise ValueError("non-canonical date")
        except ValueError as exc:
            raise ValueError(
                f"CSV linha {reader.line_num}: data inválida; use YYYY-MM-DD."
            ) from exc
        by_module.setdefault(module, []).append({
            "description": description,
            "date": incident_date,
        })
    for entries in by_module.values():
        entries.sort(key=lambda item: item["date"], reverse=True)
    return by_module


def load_incident_details(csv_path: str) -> dict[str, list[dict]]:
    """Read incident descriptions with YYYY-MM-DD dates, newest first."""
    with open(csv_path, newline="", encoding="utf-8-sig") as stream:
        return _load_incident_details_stream(stream)


def _repository_csv(repo, ref: str, location: str) -> StringIO:
    path = location[5:]
    parts = PurePosixPath(path)
    if not path or parts.is_absolute() or ".." in parts.parts or "\\" in path:
        raise ValueError("Use repo:pasta/arquivo.csv, relativo à raiz do projeto.")
    try:
        blob = repo.commit(ref).tree / path
    except KeyError as exc:
        raise ValueError("CSV não encontrado no commit selecionado.") from exc
    if blob.type != "blob" or blob.mode == 0o120000:
        raise ValueError("O CSV no repositório precisa ser um arquivo regular.")
    try:
        return StringIO(blob.data_stream.read().decode("utf-8-sig"), newline="")
    except UnicodeDecodeError as exc:
        raise ValueError("O CSV precisa usar codificação UTF-8.") from exc


def load_project_incidents(repo, ref: str, location: str) -> dict:
    """Read incident counts from a local path or repo: path."""
    location = location.strip()
    if location.startswith("repo:"):
        return _load_incidents_stream(_repository_csv(repo, ref, location))
    return load_incidents(location)


def load_project_incident_details(
    repo, ref: str, location: str,
) -> dict[str, list[dict]]:
    """Read incident details from a local path or repo: path."""
    location = location.strip()
    if location.startswith("repo:"):
        return _load_incident_details_stream(_repository_csv(repo, ref, location))
    return load_incident_details(location)
