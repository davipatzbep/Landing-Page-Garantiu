def prioritize_tests(
    test_results: list[dict], module_scores: list[dict], flakiness: dict
) -> list[dict]:
    """Order tests by module risk, failed/skipped/passed, flakiness and name."""
    scores = {item["module"]: item["score"] for item in module_scores}
    enriched = []
    for result in test_results:
        module = result["classname"].split(".")[0]
        enriched.append({
            **result,
            "module": module,
            "module_score": scores.get(module, 0.0),
            "flakiness": flakiness.get(module, 0.0),
        })
    status_rank = {"failed": 0, "skipped": 1, "passed": 2}
    return sorted(enriched, key=lambda item: (
        -item["module_score"],
        status_rank.get(item["status"], 2),
        -item["flakiness"],
        item["name"],
    ))
