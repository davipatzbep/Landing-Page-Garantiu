import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from garantiu.release_history import (
    get_release_bug_evidence, get_release_export_rows, get_release_history,
)
from garantiu.ui import BRAND_SYMBOL_PATH, BRAND_WORDMARK_PATH
from tests.conftest import init_repo
from tests.test_repository_source import remote_fixture


def select_fixture_reports(at):
    root = Path(__file__).resolve().parents[1] / "sample_data"
    at.text_input[3].set_value(str(root / "sample_junit.xml"))
    at.text_input[4].set_value(str(root / "incidents.csv"))
    at.text_input[5].set_value(str(root / "incident_details.csv"))


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("GARANTIU_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
def analyzed_app(tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    (repo_path / "checkout").mkdir()
    source = repo_path / "checkout/gateway.py"
    source.write_text("v1\n", encoding="utf-8")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("initial")
    source.write_text("v1\nv2\n", encoding="utf-8")
    repo.index.add(["checkout/gateway.py"])
    repo.index.commit("fix: gateway")
    repo.close()
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input[0].set_value(str(repo_path)).run()
    select_fixture_reports(at)
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert not at.error
    return at


def test_app_loads_without_exceptions():
    at = AppTest.from_file("../app.py", default_timeout=15)
    at.run()
    assert not at.exception
    assert at.text_input[0].value == ""
    assert at.session_state.repository_source == ""


def test_blank_repository_shows_specific_error_without_creating_history(tmp_path):
    at = AppTest.from_file("../app.py", default_timeout=15).run()

    at.button(key="analyze_release").click().run()

    assert not at.exception
    assert any("Informe a pasta local" in item.value for item in at.error)
    assert at.session_state.analysis is None
    assert not (tmp_path / "data/garantiu_release_history.db").exists()


def test_full_pipeline_runs_end_to_end_and_populates_risk_overview():
    """
    Exercises the real analysis pipeline exactly as app.py composes it:
    clicking "Analisar mudanças" on the default "Conectar Release" screen
    (with its default input values, which point at this actual git repo and
    the real sample JUnit/incidents files) must run get_changed_files ->
    build_bug_history -> parse_junit_report -> test_health_by_module ->
    load_incidents -> score_modules -> score_release without raising, store
    the result in session_state, and make it visible on the "Visão Geral do
    Risco" screen. No mocking: this is the only test that runs the modules
    wired together the way the app actually wires them.
    """
    at = AppTest.from_file("../app.py", default_timeout=15)
    at.run()
    assert not at.exception

    # Exercise explicit repository/report ingestion; nothing is prefilled.
    at.text_input[0].set_value(str(Path(__file__).resolve().parents[1])).run()
    select_fixture_reports(at)
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert at.session_state.analysis is not None
    assert at.session_state.analysis["release"]["top_module"] is not None
    source_html = "\n".join(item.value for item in at.markdown)
    assert "Fontes desta análise" in source_html
    assert "JUnit XML</strong> — Utilizada" in source_html
    assert "Contagem de incidentes</strong> — Utilizada" in source_html

    at.sidebar.radio[0].set_value("Visão Geral do Risco").run()
    assert not at.exception
    assert len(at.metric) == 1
    assert at.metric[0].value != ""
    assert at.metric[0].value.endswith("/ 100")


def test_risk_overview_primary_action_opens_manual_guide(analyzed_app):
    at = analyzed_app
    at.sidebar.radio[0].set_value("Visão Geral do Risco").run()
    assert at.button(key="open_manual_guide").label == "Preparar teste manual"

    at.button(key="open_manual_guide").click().run()

    assert at.sidebar.radio[0].value == "Roteiro de Teste Manual"
    assert at.title[0].value == "Roteiro de teste manual"


def test_all_seven_screens_without_analysis():
    at = AppTest.from_file("../app.py").run()
    screens = list(at.sidebar.radio[0].options)
    assert len(screens) == 7
    assert at.sidebar.radio[0].label == "Etapas da release"
    rendered_html = []
    for screen in screens:
        at.sidebar.radio[0].set_value(screen).run()
        assert not at.exception
        assert not at.error
        rendered_html.extend(item.value for item in at.markdown)
    combined = "\n".join(rendered_html)
    assert not re.search(r"\b0[1-7]\s*·", combined)
    assert "FLUXO DA RELEASE" not in combined


def test_populated_screens_decision_and_outcome_persist(analyzed_app, tmp_path):
    at = analyzed_app
    analysis = at.session_state.analysis
    assert analysis["module_scores"][0]["module"] == "checkout"
    for screen in list(at.sidebar.radio[0].options)[1:]:
        at.sidebar.radio[0].set_value(screen).run()
        assert not at.exception
        assert not at.error
        assert at.title

    at.sidebar.radio[0].set_value("Suíte Automatizada Priorizada").run()
    assert at.table[0].value.iloc[0]["Teste"] == "test_pagamento_recusado"
    at.sidebar.radio[0].set_value("Detalhe do Módulo").run()
    assert at.selectbox[0].value == "checkout"
    assert at.table[1].value.iloc[0]["Mensagem"] == "fix: gateway"
    assert len(at.table[2].value) == 2

    at.sidebar.radio[0].set_value("Decisão de Publicação").run()
    assert at.button(key="publish_release").disabled
    at.text_input[0].set_value("   ").run()
    assert at.button(key="publish_release").disabled
    at.text_input[0].set_value("Pessoa de teste").run()
    at.button(key="publish_release").click().run()
    assert not at.exception
    assert at.table[0].value.iloc[0]["Decisão"] == "publicar"
    at.button(key="cancel_release").click().run()
    assert at.table[0].value.iloc[0]["Decisão"] == "cancelar"

    at.sidebar.radio[0].set_value("Histórico & Tendências").run()
    at.radio(key="outcome").set_value("falhou")
    at.button(key="record_release_outcome").click().run()
    assert not at.exception
    assert at.table[0].value.iloc[0]["Resultado"] == "falhou"
    history = get_release_history(
        str(tmp_path / "data/garantiu_release_history.db"),
        repo_key=analysis["repo_path"],
    )
    assert len(history) == 1
    assert history[0]["outcome"] == "falhou"
    # A new browser session can read the same persisted history.
    fresh = AppTest.from_file("../app.py").run()
    fresh.sidebar.radio[0].set_value("Histórico & Tendências").run()
    fresh.text_input[0].set_value(analysis["repo_path"]).run()
    assert fresh.table[0].value.iloc[0]["Resultado"] == "falhou"


def test_manual_guide_note_field_is_session_only(analyzed_app):
    at = analyzed_app
    at.sidebar.radio[0].set_value("Roteiro de Teste Manual").run()
    assert len(at.text_area) == 1
    at.text_area[0].set_value("Atenção ao fluxo de desconto.").run()
    assert at.session_state["nota_dev_checkout"] == "Atenção ao fluxo de desconto."

    fresh = AppTest.from_file("../app.py", default_timeout=15).run()
    assert "nota_dev_checkout" not in fresh.session_state


def test_repeated_analysis_uses_real_test_flips(analyzed_app, tmp_path):
    at = analyzed_app
    repo_path = at.session_state.analysis["repo_path"]
    initial_score = at.session_state.analysis["release"]["score"]
    root = Path(__file__).resolve().parents[1]
    report = tmp_path / "next.xml"
    report.write_text(
        (root / "sample_data/sample_junit.xml").read_text(encoding="utf-8")
        .replace('<testcase classname="checkout.test_gateway" '
                 'name="test_pagamento_aprovado" time="0.01"/>',
                 '<testcase classname="checkout.test_gateway" '
                 'name="test_pagamento_aprovado" time="0.01">'
                 '<failure/></testcase>'),
        encoding="utf-8",
    )
    at.text_input[3].set_value(str(report))
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert not at.error
    assert at.session_state.analysis["flakiness"]["checkout"] == 50.0
    assert at.session_state.analysis["release"]["score"] > initial_score
    history = get_release_history(
        str(tmp_path / "data/garantiu_release_history.db"), repo_key=repo_path,
    )
    assert len(history) == 1


def test_empty_diff_and_empty_report_are_navigable(analyzed_app, tmp_path):
    at = analyzed_app
    original_release = at.session_state.analysis["release_name"]
    report = tmp_path / "empty.xml"
    report.write_text("<testsuites/>", encoding="utf-8")
    at.text_input[1].set_value("HEAD")
    at.text_input[3].set_value(str(report))
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert at.session_state.analysis["module_scores"] == []
    assert at.session_state.analysis["release_name"] != original_release
    history = get_release_history(
        str(tmp_path / "data/garantiu_release_history.db"),
        repo_key=at.session_state.analysis["repo_path"],
    )
    assert len(history) == 2
    for screen in list(at.sidebar.radio[0].options)[1:]:
        at.sidebar.radio[0].set_value(screen).run()
        assert not at.exception
        assert not at.error


@pytest.mark.parametrize("field,value", [
    (0, "missing-repository"), (1, "missing-ref"),
    (3, "missing-report.xml"), (4, "missing-incidents.csv"),
    (5, "missing-details.csv"),
])
def test_invalid_inputs_show_error_without_recording(field, value, tmp_path):
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input[field].set_value(value)
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert at.error
    assert at.session_state.analysis is None
    assert not (tmp_path / "data/garantiu_test_history.db").exists()


def test_failed_reanalysis_clears_stale_analysis(analyzed_app):
    at = analyzed_app
    at.text_input[3].set_value("missing-report.xml")
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert at.error
    assert at.session_state.analysis is None


def test_default_analysis_has_no_fictitious_test_results(tmp_path):
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input[0].set_value(str(Path(__file__).resolve().parents[1])).run()
    assert all(not field.value for field in at.text_input[3:6])
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert not at.error
    assert at.session_state.analysis["test_results"] == []
    assert at.session_state.analysis["flakiness"] == {}
    assert not (tmp_path / "data/garantiu_test_history.db").exists()
    at.sidebar.radio[0].set_value("Suíte Automatizada Priorizada").run()
    assert not at.table
    assert "Nenhum relatório" in at.info[0].value


def test_brand_assets_are_present_and_rendered_in_all_three_variants():
    assert BRAND_SYMBOL_PATH.is_file()
    assert BRAND_WORDMARK_PATH.is_file()

    at = AppTest.from_file("../app.py", default_timeout=15).run()

    assert not at.exception
    html = "\n".join(item.value for item in at.markdown)
    sidebar_html = "\n".join(item.value for item in at.sidebar.markdown)
    assert 'class="page-brand-symbol"' in html
    assert 'class="brand-logo"' in sidebar_html
    assert 'class="sidebar-footer"' in sidebar_html
    assert "data:image/png;base64" in sidebar_html
    assert "data:image/jpeg" not in sidebar_html
    assert not at.error


def test_quality_inputs_explain_sources_and_embed_storage_configuration():
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    captions = "\n".join(item.value for item in at.caption)

    assert "não representa cobertura" in captions
    assert "histórico operacional" in captions
    assert "extraído automaticamente" in captions
    assert "ausência de uma fonte não significa ausência de risco" in captions
    assert not at.download_button
    assert at.text_input(key="data_directory_input").label == (
        "Pasta para salvar e localizar os dados"
    )
    assert at.button(key="apply_data_directory").label == "Usar esta pasta"
    assert all(not field.value for field in at.text_input[3:6])


def test_quality_files_are_discovered_and_prefilled_from_local_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with init_repo(project) as repo:
        (project / "src.py").write_text("value = 1\n", encoding="utf-8")
        repo.index.add(["src.py"])
        repo.index.commit("initial")
    reports = project / "reports"
    reports.mkdir()
    junit = reports / "junit.xml"
    counts = reports / "incidents.csv"
    details = reports / "incident_details.csv"
    junit.write_text("<testsuite/>", encoding="utf-8")
    counts.write_text("module,incident_count\ncheckout,1\n", encoding="utf-8")
    details.write_text(
        "module,description,date\ncheckout,outage,2026-09-10\n",
        encoding="utf-8",
    )

    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input(key="_connect_repository_input").set_value(str(project)).run()

    assert not at.exception
    assert not at.error
    assert at.text_input(key=f"junit_path:{project}").value == str(junit.resolve())
    assert at.text_input(key=f"incidents_path:{project}").value == str(counts.resolve())
    assert at.text_input(key=f"incident_details_path:{project}").value == str(
        details.resolve()
    )
    assert any("3 arquivo(s)" in item.value for item in at.success)


def test_multiple_discovered_reports_can_be_selected(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    with init_repo(project) as repo:
        (project / "src.py").write_text("value = 1\n", encoding="utf-8")
        repo.index.add(["src.py"])
        repo.index.commit("initial")
    first = project / "junit.xml"
    second = project / "reports" / "other.xml"
    second.parent.mkdir()
    first.write_text("<testsuite/>", encoding="utf-8")
    second.write_text("<testsuites/>", encoding="utf-8")

    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input(key="_connect_repository_input").set_value(str(project)).run()
    input_key = f"junit_path:{project}"
    selection_key = f"{input_key}:candidate"

    assert at.text_input(key=input_key).value == ""
    assert set(at.selectbox(key=selection_key).options) == {
        str(first.resolve()), str(second.resolve()),
    }

    at.selectbox(key=selection_key).set_value(str(second.resolve())).run()

    assert at.text_input(key=input_key).value == str(second.resolve())


def test_user_can_choose_the_local_storage_folder(tmp_path):
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    chosen_directory = tmp_path / "dados-da-release"
    repository_path = tmp_path / "projeto"
    repository_path.mkdir()
    repository = init_repo(repository_path)
    source = repository_path / "checkout" / "gateway.py"
    source.parent.mkdir()
    source.write_text("primeira versão\n", encoding="utf-8")
    repository.index.add(["checkout/gateway.py"])
    repository.index.commit("initial")
    source.write_text("segunda versão\n", encoding="utf-8")
    repository.index.add(["checkout/gateway.py"])
    repository.index.commit("fix: gateway")
    repository.close()
    chosen_directory.mkdir()
    stored_report = chosen_directory / "junit.xml"
    stored_report.write_text("<testsuite/>", encoding="utf-8")

    at.text_input(key="data_directory_input").set_value(
        str(chosen_directory),
    )
    at.button(key="apply_data_directory").click().run()

    assert not at.exception
    assert not at.error
    assert chosen_directory.is_dir()
    assert at.session_state.data_directory == str(chosen_directory.resolve())
    assert str(chosen_directory.resolve()) in at.code[0].value

    at.text_input(key="_connect_repository_input").set_value(
        str(repository_path),
    ).run()
    assert at.text_input(key=f"junit_path:{repository_path}").value == str(
        stored_report.resolve()
    )
    at.button(key="analyze_release").click().run()

    assert not at.exception
    assert (chosen_directory / "garantiu_release_history.db").is_file()


@pytest.mark.parametrize("pending_changes", [False, True])
def test_analysis_generates_and_consumes_junit_in_selected_folder(tmp_path, pending_changes):
    project = tmp_path / "pytest-project"
    project.mkdir()
    with init_repo(project) as repo:
        (project / "checkout").mkdir()
        (project / "checkout/__init__.py").write_text("", encoding="utf-8")
        (project / "checkout/test_pay.py").write_text(
            "def test_payment():\n    assert False\n", encoding="utf-8",
        )
        (project / "checkout/pay.py").write_text("value = 1\n", encoding="utf-8")
        repo.index.add(["checkout/__init__.py", "checkout/test_pay.py", "checkout/pay.py"])
        repo.index.commit("initial")
        (project / "checkout/pay.py").write_text("value = 2\n", encoding="utf-8")
        repo.index.add(["checkout/pay.py"])
        repo.index.commit("change")
        if pending_changes:
            (project / "checkout/pay.py").write_text("value = 3\n", encoding="utf-8")
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    at.text_input[0].set_value(str(project)).run()
    at.checkbox(key=f"generate_junit:{project}").check().run()
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert not at.error
    analysis = at.session_state.analysis
    report = Path(analysis["junit_source"])
    assert report.is_file()
    assert report.is_relative_to(tmp_path / "data")
    assert analysis["test_results"][0]["status"] == "failed"
    assert analysis["test_health"] == {"checkout": 0.0}
    assert analysis["sources"]["junit"] is True
    assert analysis["test_working_tree_dirty"] is pending_changes
    assert ("testes com alterações locais" in analysis["release_name"]) is pending_changes
    assert at.download_button(key="download_generated_junit").label == "Baixar JUnit gerado"
    assert (tmp_path / "data/garantiu_test_history.db").is_file()
    assert any("reprovados" in item.value for item in at.warning)
    at.sidebar.radio[0].set_value("Suíte Automatizada Priorizada").run()
    assert at.table[0].value.iloc[0]["Status"] == "failed"
    at.sidebar.radio[0].set_value("Conectar Release").run()
    assert at.checkbox(key=f"generate_junit:{project}").value
    at.button(key="analyze_release").click().run()
    assert not at.error
    assert at.session_state.analysis["junit_source"] != str(report)
    assert report.is_file()


def test_choosing_empty_storage_creates_models_and_does_not_import_them(tmp_path):
    from garantiu.quality_sources import TEMPLATE_NAMES

    folder = tmp_path / "empty-storage"
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input(key="data_directory_input").set_value(str(folder))
    at.button(key="apply_data_directory").click().run()
    assert not at.exception
    assert not at.error
    assert {p.name for p in folder.iterdir()} == TEMPLATE_NAMES
    assert all(not field.value for field in at.text_input[3:6])
    at.button(key="apply_data_directory").click().run()
    assert not at.error


def test_junit_execution_error_clears_analysis_without_new_snapshot(analyzed_app, tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError("Falha na execução de teste")

    monkeypatch.setattr("garantiu.test_execution.generate_pytest_report", fail)
    at = analyzed_app
    repo_path = at.session_state.analysis["repo_path"]
    history_path = str(tmp_path / "data/garantiu_release_history.db")
    before = get_release_history(history_path, repo_key=repo_path)
    at.checkbox(key=f"generate_junit:{at.text_input[0].value}").check().run()
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert any("Falha na execução" in item.value for item in at.error)
    assert at.session_state.analysis is None
    assert get_release_history(history_path, repo_key=repo_path) == before


def test_documentation_only_interval_does_not_inflate_release_risk(tmp_path):
    repo_path = tmp_path / "docs-only"
    repo_path.mkdir()
    repo = init_repo(repo_path)
    readme = repo_path / "README.md"
    readme.write_text("initial\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    readme.write_text("initial\nmore docs\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("docs: update readme")
    repo.close()

    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input[0].set_value(str(repo_path)).run()
    at.button(key="analyze_release").click().run()

    assert not at.exception
    assert not at.error
    assert at.session_state.analysis["changed_files"] == []
    assert at.session_state.analysis["excluded_files"][0]["category"] == "documentation"
    assert at.session_state.analysis["release"]["score"] == 0
    assert any("ignorados no cálculo" in item.label for item in at.expander)
    assert any("não contém mudanças de código de produto" in item.value for item in at.warning)


@pytest.mark.parametrize("include_product", [False, True])
def test_support_files_are_auditable_and_excluded_from_pipeline(tmp_path, include_product):
    repo_path = tmp_path / "mixed"
    repo_path.mkdir()
    support = {
        ".gitignore": "repository_meta",
        ".github/workflows/ci.yml": "repository_meta",
        ".streamlit/config.toml": "configuration",
        "logo.png": "asset", "guide.pdf": "documentation",
        "reports/junit.xml": "quality_data", "reports/data.csv": "quality_data",
        "checkout/tests/test_pay.py": "test_code",
        "checkout/README.md": "documentation", "unknown.xyz": "unknown",
    }
    with init_repo(repo_path) as repo:
        (repo_path / "README.md").write_text("initial\n", encoding="utf-8")
        repo.index.add(["README.md"])
        repo.index.commit("initial")
        for name in support:
            path = repo_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("support\n", encoding="utf-8")
        repo.index.add(list(support))
        repo.index.commit("fix: support only")
        if include_product:
            for name in ["checkout/pay.py", "checkout/style.css"]:
                (repo_path / name).write_text("product\n", encoding="utf-8")
            repo.index.add(["checkout/pay.py", "checkout/style.css"])
            repo.index.commit("fix: product")

    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input[0].set_value(str(repo_path)).run()
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert not at.error
    analysis = at.session_state.analysis
    assert len(analysis["all_changed_files"]) == len(support) + (2 if include_product else 0)
    assert {f["path"]: f["category"] for f in analysis["excluded_files"]} == support
    assert all(f["reason"] for f in analysis["excluded_files"])
    assert analysis["changed_files"] == analysis["changed_code_files"]
    assert {f["path"] for f in analysis["changed_code_files"]} == (
        {"checkout/pay.py", "checkout/style.css"} if include_product else set()
    )
    db = str(tmp_path / "data/garantiu_release_history.db")
    rows = get_release_export_rows(db, repo_key=analysis["repo_path"])
    assert {r["module"] for r in rows if r["module"]} == (
        {"checkout"} if include_product else set()
    )
    evidence = get_release_bug_evidence(db, repo_key=analysis["repo_path"])
    assert {r["file_path"] for r in evidence} == (
        {"checkout/pay.py", "checkout/style.css"} if include_product else set()
    )
    if include_product:
        assert [d["message"] for d in analysis["bug_details"]["checkout"]] == ["fix: product"]
        assert analysis["module_scores"][0]["factors"]["complexidade"] == 100
    else:
        assert analysis["module_scores"] == []
        assert analysis["release"]["top_module"] is None
    at.sidebar.radio[0].set_value("Visão Geral do Risco").run()
    assert not at.exception
    audit = next(e for e in at.expander if "ignorados no cálculo" in e.label)
    assert set(audit.table[0].value["Arquivo"]) == set(support)
    if not include_product:
        assert not at.metric
    at.sidebar.radio[0].set_value("Roteiro de Teste Manual").run()
    assert not at.exception
    text = "\n".join(m.value for m in at.markdown)
    assert "unknown.xyz" not in text
    assert "checkout/README.md" not in text
    at.sidebar.radio[0].set_value("Conectar Release").run()
    assert any("ignorados no cálculo" in e.label for e in at.expander)


def test_switching_repository_clears_report_and_stale_analysis(analyzed_app):
    at = analyzed_app
    assert at.text_input[3].value
    at.text_input[0].set_value("https://github.com/other/project").run()
    assert at.session_state.analysis is None
    assert not at.text_input[3].value
    assert not at.text_input[4].value
    at.sidebar.radio[0].set_value("Suíte Automatizada Priorizada").run()
    assert not at.table


def test_repository_input_survives_navigation_between_screens():
    at = AppTest.from_file("../app.py").run()
    repository = "https://github.com/owner/persistent-project"
    at.text_input[0].set_value(repository).run()

    at.sidebar.radio[0].set_value("Visão Geral do Risco").run()
    assert at.session_state.repository_source == repository

    at.sidebar.radio[0].set_value("Histórico & Tendências").run()
    assert at.text_input[0].value == repository

    at.sidebar.radio[0].set_value("Conectar Release").run()
    assert at.text_input[0].value == repository


def test_report_in_github_commit_populates_actual_suite(remote_fixture):
    upstream, _ = remote_fixture
    from git import Repo
    with Repo(upstream) as repo:
        (upstream / "results.xml").write_text(
            '<testsuite><testcase classname="checkout.pay" name="test_real" '
            'time="0.25"><failure/></testcase></testsuite>', encoding="utf-8",
        )
        repo.index.add(["results.xml"])
        repo.index.commit("test report")
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input[0].set_value("https://github.com/owner/project").run()
    assert at.text_input(
        key="junit_path:https://github.com/owner/project",
    ).value == "repo:results.xml"
    at.text_input[1].set_value("v1")
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert not at.error
    at.sidebar.radio[0].set_value("Suíte Automatizada Priorizada").run()
    assert at.table[0].value["Teste"].tolist() == ["test_real"]
    assert at.table[0].value.iloc[0]["Status"] == "failed"
    assert any("repo:results.xml" in caption.value for caption in at.caption)


def test_github_analysis_all_screens_and_persistent_url_history(remote_fixture):
    _, calls = remote_fixture
    at = AppTest.from_file("../app.py", default_timeout=15).run()
    at.text_input[0].set_value("https://github.com/Owner/Project.git")
    at.text_input[1].set_value("v1")
    at.text_input[2].set_value("release/test")
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert not at.error
    assert at.session_state.analysis["repo_path"] == "https://github.com/owner/project"
    assert at.session_state.analysis["changed_files"][0]["path"] == "checkout/pay.py"
    for screen in list(at.sidebar.radio[0].options)[1:]:
        at.sidebar.radio[0].set_value(screen).run()
        assert not at.exception
        assert not at.error
    at.radio(key="outcome").set_value("ok")
    at.button(key="record_release_outcome").click().run()
    assert at.table[0].value.iloc[0]["Resultado"] == "ok"
    fresh = AppTest.from_file("../app.py").run()
    fresh.sidebar.radio[0].set_value("Histórico & Tendências").run()
    fresh.text_input[0].set_value("https://github.com/OWNER/PROJECT.git/").run()
    assert not fresh.error
    assert fresh.table[0].value.iloc[0]["Resultado"] == "ok"
    assert len(calls) == 2  # Discovery + analysis; history reading does not download.


def test_invalid_github_url_shows_error_without_analysis():
    at = AppTest.from_file("../app.py").run()
    at.text_input[0].set_value("https://github.com/owner/project/tree/main")
    at.button(key="analyze_release").click().run()
    assert not at.exception
    assert at.error
    assert at.session_state.analysis is None
