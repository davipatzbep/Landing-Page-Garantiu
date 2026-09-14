from garantiu.scoring import normalize_across_modules, score_modules, score_release


def test_normalize_across_modules_scales_relative_to_max():
    result = normalize_across_modules({"a": 10, "b": 5, "c": 0})
    assert result == {"a": 100.0, "b": 50.0, "c": 0.0}


def test_normalize_across_modules_handles_all_zero():
    result = normalize_across_modules({"a": 0, "b": 0})
    assert result == {"a": 0.0, "b": 0.0}


def test_normalize_across_modules_handles_empty():
    assert normalize_across_modules({}) == {}


def test_score_modules_combines_four_factors():
    changed_files = [
        {"path": "checkout/gateway.py", "module": "checkout", "lines_added": 100, "lines_removed": 20},
        {"path": "catalogo/busca.py", "module": "catalogo", "lines_added": 5, "lines_removed": 0},
    ]
    bug_history = {"checkout/gateway.py": 4}
    test_health = {"checkout": 60.0, "catalogo": 100.0}
    incidents = {"checkout": 2}
    flakiness = {"checkout": 20.0, "catalogo": 0.0}

    results = score_modules(changed_files, bug_history, test_health, incidents, flakiness)

    checkout = next(r for r in results if r["module"] == "checkout")
    catalogo = next(r for r in results if r["module"] == "catalogo")

    assert checkout["factors"]["complexidade"] == 100.0
    assert checkout["factors"]["bugs"] == 100.0
    # saude_testes = 0.5 * (100 - health) + 0.5 * flakiness = 0.5*40 + 0.5*20 = 30.0
    assert checkout["factors"]["saude_testes"] == 30.0
    assert checkout["factors"]["incidentes"] == 100.0
    assert checkout["score"] == 82.5
    assert catalogo["score"] < checkout["score"]


def test_score_modules_missing_test_data_means_zero_risk():
    changed_files = [
        {"path": "novo/modulo.py", "module": "novo", "lines_added": 1, "lines_removed": 0},
    ]
    results = score_modules(changed_files, bug_history={}, test_health={}, incidents={}, flakiness={})
    assert results[0]["factors"]["saude_testes"] == 0.0


def test_score_release_uses_max_module_score_regardless_of_order():
    module_scores = [
        {"module": "catalogo", "score": 20.0, "factors": {"complexidade": 10.0}},
        {"module": "checkout", "score": 85.0, "factors": {"complexidade": 100.0}},
    ]
    release = score_release(module_scores)
    assert release["score"] == 85.0
    assert release["top_module"] == "checkout"
    assert release["factors"] == {"complexidade": 100.0}


def test_score_release_counts_modules_by_risk_label():
    module_scores = [
        {"module": "catalogo", "score": 20.0, "factors": {}},
        {"module": "checkout", "score": 85.0, "factors": {}},
        {"module": "auth", "score": 55.0, "factors": {}},
    ]
    release = score_release(module_scores)
    assert release["modulos_em_risco"] == {"alto": 1, "medio": 1}


def test_score_release_handles_empty_list():
    release = score_release([])
    assert release == {
        "score": 0.0, "top_module": None, "factors": {},
        "modulos_em_risco": {"alto": 0, "medio": 0},
    }
