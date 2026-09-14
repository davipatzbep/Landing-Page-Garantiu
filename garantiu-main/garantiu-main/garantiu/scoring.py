WEIGHTS = {
    "complexidade": 0.25,
    "bugs": 0.25,
    "saude_testes": 0.25,
    "incidentes": 0.25,
}

RISK_THRESHOLDS = {"alto": 70, "medio": 40}


def risk_label(score: float) -> str:
    """Returns 'alto' if score >= 70, 'medio' if score >= 40, else 'baixo'."""
    if score >= RISK_THRESHOLDS["alto"]:
        return "alto"
    if score >= RISK_THRESHOLDS["medio"]:
        return "medio"
    return "baixo"


def normalize_across_modules(raw_values: dict) -> dict:
    """
    Scales a {module: raw_value} dict to {module: 0-100} relative to the
    maximum raw_value present. Empty input or an all-zero input returns 0
    for every module (or an empty dict, for empty input).
    """
    if not raw_values:
        return {}
    max_value = max(raw_values.values())
    if max_value == 0:
        return {module: 0.0 for module in raw_values}
    return {
        module: round(100 * value / max_value, 1)
        for module, value in raw_values.items()
    }


def _group_by_module(changed_files: list) -> dict:
    grouped: dict = {}
    for f in changed_files:
        grouped.setdefault(f["module"], []).append(f)
    return grouped


def score_modules(changed_files: list, bug_history: dict, test_health: dict, incidents: dict, flakiness: dict) -> list:
    """
    Full scoring pipeline over the modules touched by changed_files. Returns
    a list of {"module": str, "score": float, "factors": {...}} sorted by
    score descending.

    complexidade, bugs and incidentes are normalized relative to the other
    changed modules in this release. saude_testes blends two already-0-100
    risk signals in equal parts: (100 - health%) from the current run and
    the historical flakiness rate. A module with no matching test/flakiness
    data gets 0 risk on that sub-signal, not 100, so missing data doesn't
    unfairly inflate the score.
    """
    grouped = _group_by_module(changed_files)

    complexidade_raw = {}
    bugs_raw = {}
    incidentes_raw = {}
    saude_testes = {}

    for module, files in grouped.items():
        complexidade_raw[module] = sum(f["lines_added"] + f["lines_removed"] for f in files)
        bugs_raw[module] = sum(bug_history.get(f["path"], 0) for f in files)
        incidentes_raw[module] = incidents.get(module, 0)
        health = test_health.get(module, 100.0)
        failure_risk = 100 - health
        flakiness_risk = flakiness.get(module, 0.0)
        saude_testes[module] = round(0.5 * failure_risk + 0.5 * flakiness_risk, 1)

    complexidade = normalize_across_modules(complexidade_raw)
    bugs = normalize_across_modules(bugs_raw)
    incidentes_scores = normalize_across_modules(incidentes_raw)

    results = []
    for module in grouped:
        factors = {
            "complexidade": complexidade[module],
            "bugs": bugs[module],
            "saude_testes": saude_testes[module],
            "incidentes": incidentes_scores[module],
        }
        score = round(sum(factors[name] * weight for name, weight in WEIGHTS.items()), 1)
        results.append({"module": module, "score": score, "factors": factors})

    return sorted(results, key=lambda r: r["score"], reverse=True)


def score_release(module_scores: list) -> dict:
    """
    Rolls per-module scores up to a release-level score using the
    "weakest link" rule: the release score is the highest module score.
    Returns {"score": float, "top_module": str | None, "factors": dict,
    "modulos_em_risco": {"alto": int, "medio": int}}.

    modulos_em_risco counts every changed module at "alto"/"medio" risk, not
    just the top one — the release score alone doesn't show whether risk is
    concentrated in one module or spread across many.
    """
    modulos_em_risco = {"alto": 0, "medio": 0}
    for m in module_scores:
        label = risk_label(m["score"])
        if label in modulos_em_risco:
            modulos_em_risco[label] += 1
    if not module_scores:
        return {
            "score": 0.0, "top_module": None, "factors": {},
            "modulos_em_risco": modulos_em_risco,
        }
    top = max(module_scores, key=lambda r: r["score"])
    return {
        "score": top["score"], "top_module": top["module"],
        "factors": top["factors"], "modulos_em_risco": modulos_em_risco,
    }
