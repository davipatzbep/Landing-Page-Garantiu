from xml.etree import ElementTree
from io import BytesIO
from pathlib import PurePosixPath

from junitparser import JUnitXml, Skipped


def load_project_test_report(repo, ref: str, location: str) -> list[dict]:
    """Read an explicit local JUnit or repo:path from the analyzed commit."""
    location = location.strip()
    if not location:
        return []
    if not location.startswith("repo:"):
        return parse_junit_report(location)
    path = location[5:]
    parts = PurePosixPath(path)
    if not path or parts.is_absolute() or ".." in parts.parts or "\\" in path:
        raise ValueError("Use repo:pasta/relatorio.xml, relativo à raiz do projeto.")
    try:
        blob = repo.commit(ref).tree / path
    except KeyError as exc:
        raise ValueError("Relatório não encontrado no commit selecionado.") from exc
    if blob.type != "blob" or blob.mode == 0o120000:
        raise ValueError("O relatório no repositório deve ser um arquivo XML.")
    return parse_junit_report(BytesIO(blob.data_stream.read()))


def parse_junit_report(xml_path: str) -> list[dict]:
    """
    Parses a JUnit XML report into a list of
    {"name": str, "classname": str, "status": "passed"|"failed"|"skipped", "time": float}.
    """
    try:
        tree = ElementTree.parse(xml_path)
    except ElementTree.ParseError as exc:
        raise ValueError("Relatório JUnit XML inválido.") from exc
    if tree.getroot().tag not in {"testsuite", "testsuites"}:
        raise ValueError("O XML deve conter testsuite ou testsuites.")
    xml = JUnitXml.fromfile(xml_path, parse_func=lambda _: tree)
    results = []
    for suite in xml:
        for case in suite:
            result = case.result
            if result and isinstance(result[0], Skipped):
                status = "skipped"
            elif result:
                status = "failed"
            else:
                status = "passed"
            results.append({
                "name": case.name or "sem_nome",
                "classname": case.classname or "sem_modulo",
                "status": status,
                "time": case.time or 0.0,
            })
    return results


def test_health_by_module(test_results: list) -> dict:
    """
    Groups results by module (first segment of classname, split on '.') and
    returns {module: health_score} where health_score = 100 * passed / total,
    rounded to 1 decimal place.
    """
    by_module: dict = {}
    for r in test_results:
        module = r["classname"].split(".")[0]
        by_module.setdefault(module, []).append(r)

    health = {}
    for module, cases in by_module.items():
        passed = sum(1 for c in cases if c["status"] == "passed")
        health[module] = round(100 * passed / len(cases), 1)
    return health
