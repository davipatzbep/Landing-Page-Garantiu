from garantiu.manual_test_guide import build_module_card, risk_label


def test_risk_label_thresholds():
    assert risk_label(85) == "alto"
    assert risk_label(70) == "alto"
    assert risk_label(55) == "medio"
    assert risk_label(40) == "medio"
    assert risk_label(10) == "baixo"


def test_build_module_card_picks_dominant_factor():
    changed_files = [
        {"path": "checkout/gateway.py", "module": "checkout", "lines_added": 1, "lines_removed": 0},
    ]
    factors = {"complexidade": 20.0, "bugs": 90.0, "saude_testes": 10.0, "incidentes": 5.0}

    card = build_module_card("checkout", 85.0, factors, changed_files)

    assert card["risk"] == "alto"
    assert "histórico de problema" in card["por_que_testar"]
    assert "checkout/gateway.py" in card["o_que_mudou"]
    assert len(card["cenarios"]) == 3
    assert "checkout" in card["cenarios"][0]


def test_build_module_card_truncates_long_file_list():
    changed_files = [
        {"path": f"checkout/f{i}.py", "module": "checkout", "lines_added": 1, "lines_removed": 0}
        for i in range(5)
    ]
    factors = {"complexidade": 90.0, "bugs": 10.0, "saude_testes": 10.0, "incidentes": 5.0}

    card = build_module_card("checkout", 60.0, factors, changed_files)

    assert card["o_que_mudou"].startswith("5 arquivo(s)")
    assert "..." in card["o_que_mudou"]
