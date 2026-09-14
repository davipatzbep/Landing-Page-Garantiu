def build_module_detail(
    module: str,
    changed_files: list[dict],
    bug_details: list[dict],
    incident_details: list[dict],
    test_health: dict,
    flakiness: dict,
) -> dict:
    """Aggregate the selected module's changes, history and test indicators."""
    return {
        "module": module,
        "files": [item for item in changed_files if item["module"] == module],
        "bugs": bug_details,
        "incidents": incident_details,
        "test_health": test_health.get(module, 100.0),
        "flakiness": flakiness.get(module, 0.0),
    }
