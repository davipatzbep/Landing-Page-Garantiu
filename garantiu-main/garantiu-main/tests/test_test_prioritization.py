from copy import deepcopy

from garantiu.test_prioritization import prioritize_tests


def test_prioritization_orders_risk_status_flakiness_and_name():
    results = [
        {"name": name, "classname": f"{module}.suite", "status": status,
         "time": 0.1}
        for name, module, status in [
            ("low_failed", "low", "failed"),
            ("a_passed", "high", "passed"),
            ("b_passed", "high", "passed"),
            ("skipped", "high", "skipped"),
            ("failed", "high", "failed"),
            ("z_flaky", "flaky", "passed"),
            ("unmapped", "other", "failed"),
        ]
    ]
    original = deepcopy(results)
    scores = [{"module": module, "score": score} for module, score in
              [("high", 90), ("flaky", 90), ("low", 10)]]
    ordered = prioritize_tests(results, scores, {"flaky": 50})
    assert [item["name"] for item in ordered] == [
        "failed", "skipped", "z_flaky", "a_passed", "b_passed",
        "low_failed", "unmapped",
    ]
    assert ordered[2]["flakiness"] == 50
    assert ordered[2]["module_score"] == 90
    assert ordered[-1]["module_score"] == 0
    assert ordered[-1]["flakiness"] == 0
    assert results == original


def test_prioritization_empty_suite():
    assert prioritize_tests([], [], {}) == []
