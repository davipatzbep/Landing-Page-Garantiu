from garantiu.module_detail import build_module_detail


def test_module_detail_combines_only_selected_module_changes():
    files = [
        {"module": "checkout", "path": "checkout/pay.py",
         "lines_added": 10, "lines_removed": 2},
        {"module": "auth", "path": "auth/login.py",
         "lines_added": 1, "lines_removed": 0},
    ]
    bugs = [{"hash": "abc", "message": "fix", "date": "2026-03-05"}]
    incidents = [{"description": "outage", "date": "2026-02-10"}]
    detail = build_module_detail(
        "checkout", files, bugs, incidents, {"checkout": 60}, {"checkout": 20}
    )
    assert detail == {
        "module": "checkout", "files": [files[0]], "bugs": bugs,
        "incidents": incidents, "test_health": 60, "flakiness": 20,
    }


def test_module_detail_missing_data_has_no_added_test_risk():
    detail = build_module_detail("new", [], [], [], {}, {})
    assert detail["test_health"] == 100
    assert detail["flakiness"] == 0
    assert detail["files"] == detail["bugs"] == detail["incidents"] == []
