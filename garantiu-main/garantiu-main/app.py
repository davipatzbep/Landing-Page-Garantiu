"""Local release risk dashboard. Run with python -m streamlit run app.py."""

import os
import sqlite3
from pathlib import Path

import git
import streamlit as st
from junitparser import JUnitXmlError

from garantiu.bug_history import (
    bug_evidence_for_files, bug_history_detail_by_module, build_bug_history,
)
from garantiu.decision_log import get_decision_history, record_decision
from garantiu.git_reader import (
    classify_changed_path, get_changed_files, resolve_comparison_base,
)
from garantiu.incidents import (
    load_project_incident_details, load_project_incidents,
)
from garantiu.manual_test_guide import build_module_card
from garantiu.module_detail import build_module_detail
from garantiu.release_history import (
    BUG_EXPORT_FIELDS, INCIDENT_EXPORT_FIELDS, RELEASE_EXPORT_FIELDS,
    get_release_bug_evidence, get_release_export_rows, get_release_history,
    get_release_incident_evidence, record_release_analysis,
    record_release_outcome, rows_to_csv,
)
from garantiu.scoring import score_modules, score_release
from garantiu.repository_source import prepare_repository, repository_key
from garantiu.quality_sources import (
    TEMPLATE_NAMES, create_missing_quality_templates,
    discover_quality_sources, discover_quality_sources_in_directory,
)
from garantiu.test_history import flakiness_by_module, record_test_run
from garantiu.test_execution import generate_pytest_report
from garantiu.test_prioritization import prioritize_tests
from garantiu.test_reports import load_project_test_report, test_health_by_module
from garantiu.ui import (
    BRAND_SYMBOL_PATH, format_date_br, format_datetime_br, format_percent,
    format_score, inject_design_system, render_brand, render_factor_heading,
    render_module_focus, render_page_header, render_release_context,
    render_risk_distribution, render_section_label, render_sidebar_footer,
    risk_level,
)

ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = Path(os.environ.get("GARANTIU_DATA_DIR", ROOT)).expanduser()
SCREENS = [
    "Conectar Release", "Visão Geral do Risco", "Roteiro de Teste Manual",
    "Suíte Automatizada Priorizada", "Detalhe do Módulo",
    "Decisão de Publicação", "Histórico & Tendências",
]
REPOSITORY_SOURCE_KEY = "repository_source"
DATA_DIRECTORY_KEY = "data_directory"
DATA_DIRECTORY_INPUT_KEY = "data_directory_input"
DATA_DIRECTORY_ERROR_KEY = "data_directory_error"
QUALITY_DISCOVERY_KEY = "quality_source_discovery"


def _parse_data_directory(value: object) -> Path:
    """Return a valid local folder selected for persisted Garantiu data."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Informe uma pasta para armazenar os dados locais.")
    directory = Path(value.strip()).expanduser().resolve()
    if directory.exists() and not directory.is_dir():
        raise ValueError("O local de armazenamento precisa ser uma pasta.")
    return directory


def _active_data_directory() -> Path:
    if DATA_DIRECTORY_KEY not in st.session_state:
        st.session_state[DATA_DIRECTORY_KEY] = str(DEFAULT_DATA_DIR)
    return _parse_data_directory(st.session_state[DATA_DIRECTORY_KEY])


def _database_paths() -> tuple[Path, str, str, str]:
    directory = _active_data_directory()
    return (
        directory,
        str(directory / "garantiu.db"),
        str(directory / "garantiu_test_history.db"),
        str(directory / "garantiu_release_history.db"),
    )


def _apply_data_directory() -> None:
    """Persist the chosen folder for the current app session after validation."""
    try:
        directory = _parse_data_directory(st.session_state[DATA_DIRECTORY_INPUT_KEY])
        directory.mkdir(parents=True, exist_ok=True)
        create_missing_quality_templates(directory)
    except (OSError, ValueError) as exc:
        st.session_state[DATA_DIRECTORY_ERROR_KEY] = str(exc)
        return
    st.session_state[DATA_DIRECTORY_KEY] = str(directory)
    st.session_state.pop(DATA_DIRECTORY_ERROR_KEY, None)
    st.session_state.pop(QUALITY_DISCOVERY_KEY, None)
    st.session_state.analysis = None


def render_storage_location() -> None:
    """Render storage selection in the optional quality-data area."""
    active_directory = _active_data_directory()
    if DATA_DIRECTORY_INPUT_KEY not in st.session_state:
        st.session_state[DATA_DIRECTORY_INPUT_KEY] = str(active_directory)
    st.markdown("#### Armazenamento local")
    st.caption(
        "Escolha onde os bancos e os JUnit gerados serão gravados. Relatórios JUnit e CSVs "
        "colocados nessa pasta também são localizados automaticamente."
    )
    st.text_input(
        "Pasta para salvar e localizar os dados", key=DATA_DIRECTORY_INPUT_KEY,
        help="Cole o caminho de uma pasta existente ou nova.",
    )
    st.button(
        "Usar esta pasta", key="apply_data_directory",
        on_click=_apply_data_directory, use_container_width=True,
    )
    if DATA_DIRECTORY_ERROR_KEY in st.session_state:
        st.error(
            "Não foi possível usar essa pasta: "
            f"{st.session_state[DATA_DIRECTORY_ERROR_KEY]}"
        )
    st.caption("Pasta em uso nesta sessão:")
    st.code(str(active_directory), language=None)
    st.caption(
        "Quando houver dados, os bancos garantiu.db, garantiu_test_history.db "
        "e garantiu_release_history.db serão salvos aqui."
    )
    st.caption(
        "Ao usar a pasta, criamos os modelos JUnit e CSV que estiverem faltando, "
        "com nomes iniciados por modelo-. Eles são vazios e não entram na análise. "
        "Para usar um CSV, preencha dados reais e salve uma cópia sem o prefixo modelo-."
    )


def _discover_repository_quality_sources(repo_source: str, ref: str) -> dict:
    """Discover reports in the repository and selected local data folder."""
    empty = {"junit": [], "incident_counts": [], "incident_details": []}
    data_directory = _active_data_directory()
    identity = (repo_source.strip(), ref.strip(), str(data_directory))
    cached = st.session_state.get(QUALITY_DISCOVERY_KEY)
    if cached and cached.get("identity") == identity:
        return cached
    try:
        with st.spinner("Procurando relatórios no projeto..."):
            sources = discover_quality_sources_in_directory(data_directory)
            if repo_source.strip() and ref.strip():
                with prepare_repository(repo_source.strip()) as source:
                    repository_sources = discover_quality_sources(
                        source.path, ref.strip(),
                    )
                for kind, candidates in repository_sources.items():
                    sources[kind] = list(dict.fromkeys([*sources[kind], *candidates]))
        result = {"identity": identity, "sources": sources, "error": None}
    except (OSError, ValueError, git.GitError, git.BadName, git.BadObject) as exc:
        result = {"identity": identity, "sources": empty, "error": str(exc)}
    st.session_state[QUALITY_DISCOVERY_KEY] = result
    return result


def _select_discovered_source(selection_key: str, input_key: str) -> None:
    selected = st.session_state.get(selection_key)
    if selected:
        st.session_state[input_key] = selected


def _quality_source_input(
    label: str, input_key: str, candidates: list[str], *, help_text: str | None = None,
) -> str:
    """Render an editable path, auto-filling or offering discovered candidates."""
    if input_key not in st.session_state:
        st.session_state[input_key] = candidates[0] if len(candidates) == 1 else ""
    if len(candidates) == 1:
        st.caption(f"Encontrado automaticamente: {candidates[0]}")
    elif len(candidates) > 1:
        selection_key = f"{input_key}:candidate"
        st.selectbox(
            f"Escolher {label.lower()} encontrado",
            candidates,
            index=None,
            placeholder="Selecione um dos arquivos encontrados",
            key=selection_key,
            on_change=_select_discovered_source,
            args=(selection_key, input_key),
        )
        st.caption(
            f"Foram encontrados {len(candidates)} arquivos compatíveis. "
            "Escolha um deles ou informe outro caminho abaixo."
        )
    return st.text_input(label, key=input_key, help=help_text)


def _refresh_quality_discovery(*input_keys: str) -> None:
    st.session_state.pop(QUALITY_DISCOVERY_KEY, None)
    for key in input_keys:
        st.session_state.pop(key, None)


def _repository_input(label: str, widget_key: str, **kwargs) -> str:
    """Render a repository field backed by durable, non-widget session state."""
    if REPOSITORY_SOURCE_KEY not in st.session_state:
        st.session_state[REPOSITORY_SOURCE_KEY] = ""
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[REPOSITORY_SOURCE_KEY]
    return st.text_input(
        label, key=widget_key, on_change=_persist_repository_input,
        args=(widget_key,), **kwargs,
    )


def _persist_repository_input(widget_key: str) -> None:
    """Copy a transient widget value before Streamlit cleans hidden widgets."""
    value = st.session_state[widget_key]
    if value == st.session_state.get(REPOSITORY_SOURCE_KEY):
        return
    st.session_state[REPOSITORY_SOURCE_KEY] = value
    st.session_state.analysis = None


def _render_analysis_sources(analysis: dict) -> None:
    if analysis.get("junit_generated"):
        st.caption("JUnit gerado nesta análise:")
        st.code(analysis["junit_source"], language=None)
        if analysis.get("test_working_tree_dirty"):
            st.warning(
                "Os testes incluem alterações locais ainda não commitadas. "
                "O diff e o score de mudanças continuam usando o intervalo Git selecionado."
            )
        report = Path(analysis["junit_source"])
        if report.is_file():
            st.download_button(
                "Baixar JUnit gerado", data=report.read_bytes(),
                file_name="junit.xml", mime="application/xml",
                key="download_generated_junit",
            )
    sources = analysis.get("sources", {})
    render_section_label(
        "Fontes desta análise",
        "A ausência de uma fonte opcional não significa ausência de risco.",
    )
    labels = (
        ("JUnit XML", sources.get("junit"), "opcional"),
        ("Contagem de incidentes", sources.get("incident_counts"), "opcional"),
        ("Detalhes de incidentes", sources.get("incident_details"), "opcional"),
        ("Histórico de bugs pelo Git", True, "automática"),
    )
    st.markdown(
        "<div class='source-statuses'>" + "".join(
            f"<span><strong>{label}</strong> — "
            f"{'Utilizada' if used else 'Não informada'} ({kind})</span>"
            for label, used, kind in labels
        ) + "</div>",
        unsafe_allow_html=True,
    )


def _render_excluded_files(analysis: dict) -> None:
    excluded = analysis.get("excluded_files", [])
    if excluded:
        with st.expander(
            f"{len(excluded)} arquivo(s) de suporte foram ignorados no cálculo."
        ):
            st.table([
                {"Arquivo": item["path"], "Categoria": item["category"],
                 "Motivo": item["reason"]}
                for item in excluded
            ])


def connect_release():
    render_page_header(
        "Conectar release",
        "Escolha o código e o intervalo que serão avaliados antes de calcular o risco.",
    )
    render_section_label(
        "Origem da análise",
        "O Garantiu lê as mudanças do Git e pode executar testes locais com pytest.",
    )
    repo_input = _repository_input(
        "Pasta local ou link do GitHub", "_connect_repository_input",
        help="Ex.: C:\\Projetos\\meu-sistema ou https://github.com/usuario/projeto",
    )
    base_ref = st.text_input(
        "Comparar desde", value="AUTO",
        help="AUTO usa a última tag anterior à branch escolhida. Sem tags, "
             "usa o primeiro commit alcançável.",
    )
    head_ref = st.text_input("Branch do release", value="HEAD")
    discovery = _discover_repository_quality_sources(repo_input, head_ref)
    discovered = discovery["sources"]
    junit_key = f"junit_path:{repo_input}"
    incidents_key = f"incidents_path:{repo_input}"
    incident_details_key = f"incident_details_path:{repo_input}"
    with st.expander("Resultados de testes e incidentes — opcional"):
        st.caption(
            "Enriqueça a análise com resultados reais de testes e incidentes. "
            "A ausência de uma fonte não significa ausência de risco."
        )
        if discovery["error"]:
            st.warning(
                "A busca automática não encontrou o projeto. Você ainda pode "
                f"informar os arquivos manualmente. Detalhe: {discovery['error']}"
            )
        elif repo_input.strip():
            total_found = sum(len(items) for items in discovered.values())
            if total_found:
                st.success(f"{total_found} arquivo(s) de qualidade encontrado(s) no projeto.")
            else:
                st.info("Nenhum relatório JUnit ou CSV de incidentes foi encontrado no projeto.")
        junit_path = _quality_source_input(
            "Relatório de testes (JUnit XML)",
            junit_key, discovered["junit"],
            help_text="Informe um arquivo local ou repo:reports/junit.xml para ler "
                      "um XML do commit selecionado. Deixe vazio se não houver relatório.",
        )
        st.caption(
            "Informa o status dos testes já executados no terminal ou na CI. "
            "JUnit não representa cobertura de código."
        )
        generation_key = f"generate_junit:{repo_input}"
        preference_key = f"junit_generation_preference:{repo_input}"
        if generation_key not in st.session_state:
            st.session_state[generation_key] = st.session_state.get(preference_key, False)
        generate_junit = st.checkbox(
            "Gerar JUnit com pytest ao analisar", key=generation_key,
            help="Executa os testes da pasta local ao clicar em Analisar mudanças. "
                 "Usa .venv do projeto, quando existente, e exige dependências instaladas. "
                 "O novo resultado substitui o relatório informado nesta análise.",
        )
        st.session_state[preference_key] = generate_junit
        if generate_junit:
            st.caption(
                "Os testes serão executados no computador, com limite de 10 minutos. "
                "A pasta precisa estar no commit escolhido; alterações locais entram nos testes. "
                "O XML será salvo na pasta de armazenamento local."
            )
        incidents_path = _quality_source_input(
            "Arquivo de incidentes (CSV)",
            incidents_key, discovered["incident_counts"],
            help_text="Aceita um arquivo local ou repo:caminho/incidents.csv.",
        )
        st.caption(
            "Quantidade de incidentes por módulo, obtida do histórico operacional da equipe."
        )
        incident_details_path = _quality_source_input(
            "Arquivo de detalhe de incidentes (CSV, opcional)",
            incident_details_key, discovered["incident_details"],
            help_text="Aceita um arquivo local ou repo:caminho/incident_details.csv.",
        )
        st.caption(
            "Descrição e data dos incidentes, obtidas do histórico operacional da equipe."
        )
        render_storage_location()
        st.caption(
            "O histórico de bugs não exige arquivo: ele é extraído automaticamente "
            "das mensagens de commit do Git, como fix, bug e corrige."
        )
        st.button(
            "Procurar novamente", key="refresh_quality_sources",
            on_click=_refresh_quality_discovery,
            args=(junit_key, incidents_key, incident_details_key),
        )
    st.caption(
        "A busca considera XMLs JUnit e CSVs com os cabeçalhos esperados. Em links "
        "GitHub, os arquivos encontrados usam repo:caminho/arquivo."
    )
    if not st.button(
        "Analisar mudanças", type="primary", use_container_width=True,
        key="analyze_release",
    ):
        if st.session_state.analysis:
            _render_analysis_sources(st.session_state.analysis)
            _render_excluded_files(st.session_state.analysis)
        return
    st.session_state.analysis = None
    test_working_tree_dirty = False
    repo_path = repo_input.strip()
    if not repo_path:
        st.error("Informe a pasta local ou o link do GitHub antes de analisar.")
        return
    if not base_ref.strip() or not head_ref.strip():
        st.error("Informe as duas referências Git da comparação.")
        return
    with st.spinner("Lendo mudanças, testes e histórico..."):
        for location in (incidents_path, incident_details_path, "" if generate_junit else junit_path):
            if Path(location.removeprefix("repo:")).name.lower() in TEMPLATE_NAMES:
                raise ValueError(
                    "Arquivos modelo- são apenas modelos vazios. Preencha dados reais "
                    "e salve com outro nome, ou ative a geração do JUnit."
                )
        with prepare_repository(repo_path) as source:
            repo_key = source.key
            with git.Repo(source.path) as repo:
                head_sha = repo.commit(head_ref.strip()).hexsha
                base_sha, base_label = resolve_comparison_base(
                    repo, base_ref, head_ref.strip(),
                )
                incidents = (
                    load_project_incidents(repo, head_sha, incidents_path)
                    if incidents_path.strip() else {}
                )
                incident_details = (
                    load_project_incident_details(
                        repo, head_sha, incident_details_path,
                    )
                    if incident_details_path.strip() else {}
                )
                if generate_junit:
                    with st.spinner("Executando pytest e salvando JUnit..."):
                        execution = generate_pytest_report(repo, head_sha, _active_data_directory())
                    junit_path = execution["path"]
                    test_results = execution["results"]
                    test_working_tree_dirty = execution["working_tree_dirty"]
                    st.session_state.pop(QUALITY_DISCOVERY_KEY, None)
                    if execution["exit_code"] == 1:
                        st.warning("Há testes reprovados. O resultado foi incluído na análise.")
                    elif execution["exit_code"] == 5:
                        st.warning("O pytest não encontrou testes. O JUnit salvo está vazio.")
                    st.success(f"JUnit gerado e salvo em: {junit_path}")
                else:
                    test_results = load_project_test_report(repo, head_sha, junit_path)
            all_changed_files = get_changed_files(
                source.path, base_sha, head_sha,
            )
            changed_code_files = []
            excluded_files = []
            for change in all_changed_files:
                classification = classify_changed_path(change["path"])
                if classification["include_in_risk"]:
                    changed_code_files.append(change)
                else:
                    excluded_files.append({**change, **classification})
            # Compatibility alias: every downstream consumer receives product code only.
            changed_files = changed_code_files
            bug_history = build_bug_history(source.path, ref=head_sha)
            bug_details = {
                module: bug_history_detail_by_module(
                    source.path, module, ref=head_sha,
                )
                for module in {f["module"] for f in changed_files}
            }
            bug_evidence = bug_evidence_for_files(
                source.path, {f["path"] for f in changed_files}, ref=head_sha,
            )
        test_health = test_health_by_module(test_results)
        data_dir, _, test_history_db, release_history_db = _database_paths()
        data_dir.mkdir(parents=True, exist_ok=True)
        if test_results:
            record_test_run(test_history_db, test_results, repo_key=repo_key)
        flakiness = (
            flakiness_by_module(test_history_db, repo_key=repo_key)
            if test_results else {}
        )
        module_scores = score_modules(
            changed_files, bug_history, test_health, incidents, flakiness,
        )
        release = score_release(module_scores)
        release_name = f"{head_ref.strip()} @ {base_label}..{head_sha[:8]}"
        if test_working_tree_dirty:
            release_name += " · testes com alterações locais"
        analysis_id = record_release_analysis(
            release_history_db, release_name, release["score"], module_scores,
            bug_evidence, incidents, incident_details,
            repo_key=repo_key,
        )
        st.session_state.analysis = {
            "analysis_id": analysis_id,
            "release_name": release_name, "repo_path": repo_key,
            "comparison_base": base_label,
            "all_changed_files": all_changed_files,
            "excluded_files": excluded_files,
            "changed_code_files": changed_code_files,
            "changed_files": changed_files, "module_scores": module_scores,
            "release": release, "test_results": test_results,
            "junit_source": junit_path.strip(),
            "junit_generated": generate_junit,
            "test_working_tree_dirty": test_working_tree_dirty,
            "test_health": test_health, "flakiness": flakiness,
            "bug_details": bug_details, "incident_details": incident_details,
            "sources": {
                "junit": bool(junit_path.strip()),
                "incident_counts": bool(incidents_path.strip()),
                "incident_details": bool(incident_details_path.strip()),
            },
        }
    st.success(
        f"{len(changed_files)} arquivo(s) de produto analisado(s) "
        f"em {len(module_scores)} módulo(s), dentro de "
        f"{len(all_changed_files)} alteração(ões) no intervalo."
    )
    _render_excluded_files(st.session_state.analysis)
    if not changed_files:
        st.warning(
            "O intervalo não contém mudanças de código de produto para analisar. "
            "Houve alterações, mas nenhuma foi classificada como código de produto."
            if all_changed_files else "Nenhum arquivo mudou no intervalo Git selecionado."
        )
    _render_analysis_sources(st.session_state.analysis)


def risk_overview(analysis):
    render_page_header(
        "Visão geral do risco",
        "Entenda o impacto, encontre o foco do teste e avance com evidências.",
    )
    render_release_context(analysis)
    release = analysis["release"]
    _render_excluded_files(analysis)
    if not analysis["module_scores"]:
        st.info("Nenhuma mudança de código de produto para calcular o risco neste intervalo.")
        return
    with st.container(border=True):
        score_col, distribution_col = st.columns([1.15, 1])
        with score_col:
            st.metric("Score de risco da release", format_score(release["score"]))
            level, label = risk_level(release["score"])
            st.markdown(
                f"<strong class='risk-pill risk-{level}'>{label}</strong>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"O módulo {release['top_module']} concentra o maior risco desta release."
            )
        with distribution_col:
            render_risk_distribution(analysis["module_scores"])
    risco = release["modulos_em_risco"]
    outros = risco["alto"] + risco["medio"] - 1
    if outros > 0:
        st.caption(
            f"O score do release é o do módulo mais arriscado, mas há mais "
            f"{outros} módulo(s) em risco alto/médio nesta mudança "
            f"({risco['alto']} em risco alto, {risco['medio']} em risco médio)."
        )
    render_section_label(
        f"Por que {release['top_module']} está em risco?",
        "Quatro sinais objetivos compõem o score do módulo mais crítico.",
    )
    factor_columns = st.columns(2)
    for index, (factor, value) in enumerate(release["factors"].items()):
        with factor_columns[index % 2]:
            render_factor_heading(factor, value)
            st.progress(min(value, 100) / 100)
    render_section_label(
        "Módulos por nível de risco",
        "Ordenados por risco e impacto para indicar onde testar primeiro.",
    )
    table_col, focus_col = st.columns([1.7, 1])
    with table_col:
        st.table([
            {"Módulo": m["module"], "Score": format_score(m["score"]),
             "Nível": risk_level(m["score"])[1]}
            for m in analysis["module_scores"]
        ])
    with focus_col:
        render_module_focus(analysis["module_scores"][0])
        st.button(
            "Preparar teste manual", type="primary", use_container_width=True,
            key="open_manual_guide",
            on_click=lambda: st.session_state.update(screen=SCREENS[2]),
        )
    if any(m["module"] not in analysis["test_health"]
           for m in analysis["module_scores"]):
        st.info(
            "Há módulos sem testes correspondentes no relatório. A ausência "
            "de dados não aumenta o score, mas não comprova que estão testados."
        )


def manual_guide(analysis):
    render_page_header(
        "Roteiro de teste manual",
        "Transforme evidências técnicas em cenários claros para quem vai testar.",
    )
    render_release_context(analysis)
    if not analysis["module_scores"]:
        st.info("Nenhum módulo alterado para gerar um roteiro.")
    for module in analysis["module_scores"]:
        card = build_module_card(
            module["module"], module["score"], module["factors"],
            analysis["changed_files"],
        )
        with st.container(border=True):
            st.subheader(f"{card['module']} — risco {card['risk']}")
            st.caption(f"Score do módulo: {format_score(card['score'])}")
            st.write("**O que mudou**")
            st.write(card["o_que_mudou"])
            st.write("**Por que testar isso**")
            st.write(card["por_que_testar"])
            st.write("**Cenários sugeridos**")
            for scenario in card["cenarios"]:
                st.write(f"- {scenario}")
            st.text_area(
                "Nota do dev pro QA (opcional)",
                key=f"nota_dev_{module['module']}",
                placeholder="Ex.: mexi na validação de cupom, atenção ao fluxo de desconto.",
            )


def automated_suite(analysis):
    render_page_header(
        "Suíte automatizada priorizada",
        "Consulte os testes importados na ordem que mais reduz o risco da release.",
    )
    render_release_context(analysis)
    st.caption(f"Repositório analisado: {analysis['repo_path']}")
    st.caption(f"Release: {analysis['release_name']}")
    if not analysis.get("junit_source"):
        st.info(
            "Nenhum relatório de testes foi fornecido para este projeto. "
            "Em Conectar Release, ative Gerar JUnit com pytest ao analisar "
            "ou informe um relatório e clique em Analisar mudanças."
        )
        st.caption(
            "Também é possível gerar o relatório no terminal ou CI. Com pytest: "
            "python -m pytest --junitxml=relatorio.xml."
        )
        return
    st.caption(f"Relatório utilizado: {analysis['junit_source']}")
    ordered = prioritize_tests(
        analysis["test_results"], analysis["module_scores"],
        analysis["flakiness"],
    )
    st.caption(
        "Ordem recomendada a partir do relatório utilizado na análise. "
        "Para executar novamente com pytest, volte a Conectar Release."
    )
    if not ordered:
        st.info("O relatório não contém testes.")
        return
    changed_modules = {m["module"] for m in analysis["module_scores"]}
    unmatched = sorted({t["module"] for t in ordered} - changed_modules)
    if unmatched:
        st.warning(
            "Há testes sem associação aos módulos alterados: "
            + ", ".join(unmatched)
            + ". Podem ser de áreas não alteradas ou usar nomes diferentes. "
            "Eles não recebem prioridade por risco. Confira o relatório "
            "e a correspondência entre classname e as pastas do projeto."
        )
    st.table([
        {"Teste": t["name"], "Módulo": t["module"], "Status": t["status"],
         "Tempo (s)": t["time"],
         "Flakiness do módulo": format_percent(t["flakiness"]),
         "Score do módulo": (format_score(t["module_score"])
                             if t["module"] in changed_modules else "—")}
        for t in ordered
    ])


def module_detail(analysis):
    render_page_header(
        "Detalhe do módulo",
        "Veja as evidências que sustentam o risco de cada área alterada.",
    )
    render_release_context(analysis)
    modules = [m["module"] for m in analysis["module_scores"]]
    if not modules:
        st.info("Nenhum módulo alterado para detalhar.")
        return
    selected = st.selectbox("Módulo", modules)
    detail = build_module_detail(
        selected, analysis["changed_files"],
        analysis["bug_details"].get(selected, []),
        analysis["incident_details"].get(selected, []),
        analysis["test_health"], analysis["flakiness"],
    )
    st.subheader("O que mudou")
    st.table([
        {"Arquivo": f["path"], "+": f["lines_added"], "-": f["lines_removed"]}
        for f in detail["files"]
    ])
    st.subheader("Histórico de bugs")
    if detail["bugs"]:
        st.table([{
            "Commit": item["hash"], "Mensagem": item["message"],
            "Data": format_date_br(item["date"]),
        } for item in detail["bugs"]])
    else:
        st.caption("Nenhum bug histórico registrado para esse módulo.")
    st.subheader("Incidentes em produção")
    if detail["incidents"]:
        st.table([{
            "Descrição": item["description"],
            "Data": format_date_br(item["date"]),
        } for item in detail["incidents"]])
    else:
        st.caption("Nenhum detalhe de incidente informado para esse módulo.")
    st.subheader("Saúde dos testes")
    if selected in analysis["test_health"]:
        st.write(
            "Taxa de aprovação na última rodada: "
            f"{format_percent(detail['test_health'])}"
        )
    else:
        st.info("Sem testes correspondentes no relatório atual.")
    st.write(f"Flakiness histórica: {format_percent(detail['flakiness'])}")


def publication_decision(analysis):
    render_page_header(
        "Decisão de publicação",
        "Registre uma decisão humana consciente; o Garantiu não executa o deploy.",
    )
    render_release_context(analysis)
    release = analysis["release"]
    with st.container(border=True):
        score_col, decision_col = st.columns([.8, 1.6])
        with score_col:
            st.metric("Score atual", format_score(release["score"]))
            level, label = risk_level(release["score"])
            st.markdown(
                f"<strong class='risk-pill risk-{level}'>{label}</strong>",
                unsafe_allow_html=True,
            )
        with decision_col:
            st.subheader("Responsável pela decisão")
            st.caption(
                "Seu nome identifica o registro de auditoria. Isto não substitui autenticação."
            )
            decided_by = st.text_input("Seu nome").strip()
            decision_key = f"{analysis['repo_path']} :: {analysis['release_name']}"
            col1, col2 = st.columns(2)
            publish = col1.button(
                "Publicar mesmo assim", disabled=not decided_by,
                type="primary", use_container_width=True, key="publish_release",
            )
            cancel = col2.button(
                "Cancelar publicação", disabled=not decided_by,
                use_container_width=True, key="cancel_release",
            )
    _, decisions_db, _, _ = _database_paths()
    if publish or cancel:
        decision = "publicar" if publish else "cancelar"
        record_decision(
            decisions_db, decision_key, release["score"], decided_by, decision,
        )
        st.success(f"Decisão registrada: {decision}.")
    render_section_label(
        "Registro de auditoria",
        "Decisões anteriores desta mesma release, em ordem cronológica.",
    )
    history = get_decision_history(decisions_db, decision_key)
    if history:
        st.table([{
            "Release": item["release"],
            "Score": format_score(item["score"]),
            "Responsável": item["decided_by"],
            "Decisão": item["decision"],
            "Decidido em": format_datetime_br(item["decided_at"]),
        } for item in history])
    else:
        st.info("Nenhuma decisão registrada para este release.")


def release_trends():
    render_page_header(
        "Histórico & tendências",
        "Compare risco previsto e resultado real para construir confiança no score.",
    )
    repo_path = _repository_input(
        "Repositório do histórico (pasta ou link do GitHub)",
        "_history_repository_input",
    )
    if not repo_path.strip():
        st.info("Informe um repositório para consultar o histórico e as evidências.")
        return
    repo_key = repository_key(repo_path)
    data_dir, _, _, release_history_db = _database_paths()
    data_dir.mkdir(parents=True, exist_ok=True)
    history = get_release_history(release_history_db, repo_key=repo_key)
    all_release_rows = get_release_export_rows(
        release_history_db, repo_key=repo_key,
    )
    all_bug_rows = get_release_bug_evidence(
        release_history_db, repo_key=repo_key,
    )
    all_incident_rows = get_release_incident_evidence(
        release_history_db, repo_key=repo_key,
    )
    releases = [item["release"] for item in history]
    modules = sorted({
        row["module"] for row in
        (all_release_rows + all_bug_rows + all_incident_rows)
        if row.get("module")
    })
    filter_col, module_col = st.columns(2)
    selected_release = filter_col.selectbox(
        "Filtrar por release", ["Todas", *releases], key="history_release_filter",
    )
    selected_module = module_col.selectbox(
        "Filtrar por módulo", ["Todos", *modules], key="history_module_filter",
    )
    release_filter = None if selected_release == "Todas" else selected_release
    module_filter = None if selected_module == "Todos" else selected_module

    release_rows = get_release_export_rows(
        release_history_db, repo_key=repo_key, release=release_filter,
        module=module_filter,
    )
    bug_rows = get_release_bug_evidence(
        release_history_db, repo_key=repo_key, release=release_filter,
        module=module_filter,
    )
    incident_rows = get_release_incident_evidence(
        release_history_db, repo_key=repo_key, release=release_filter,
        module=module_filter,
    )
    allowed_releases = {row["release"] for row in release_rows}
    filtered_history = [
        item for item in history
        if (release_filter is None or item["release"] == release_filter)
        and (module_filter is None or item["release"] in allowed_releases)
    ]

    render_section_label(
        "Releases", "Último snapshot de cada release para o repositório selecionado.",
    )
    if filtered_history:
        st.table([{
            "Release": item["release"],
            "Score": format_score(item["score"]),
            "Analisado em": format_datetime_br(item["computed_at"]),
            "Resultado": item["outcome"] or "Não informado",
        } for item in filtered_history])
        st.subheader("Evolução do score previsto")
        st.line_chart([
            {"Analisado em": item["computed_at"], "Score": item["score"]}
            for item in reversed(filtered_history)
        ], x="Analisado em", y="Score")
        st.caption(
            "O score é um indicador relativo, não uma probabilidade de falha."
        )
    else:
        st.info("Nenhuma release encontrada para os filtros selecionados.")
    st.download_button(
        "Baixar CSV de releases",
        data=rows_to_csv(release_rows, RELEASE_EXPORT_FIELDS),
        file_name="historico-releases.csv", mime="text/csv; charset=utf-8",
        key="download_release_history",
    )

    render_section_label(
        "Bugs encontrados", "Correções anteriores relacionadas aos arquivos analisados.",
    )
    if bug_rows:
        st.table([{
            "Release": row["release"], "Módulo": row["module"],
            "Arquivo": row["file_path"], "Commit": row["commit_hash"][:8],
            "Mensagem": row["message"], "Ocorrido em": format_date_br(row["occurred_on"]),
            "Analisado em": format_datetime_br(row["computed_at"]),
        } for row in bug_rows])
    else:
        st.info("Nenhuma evidência de bug encontrada para os filtros selecionados.")
    st.download_button(
        "Baixar CSV de bugs", data=rows_to_csv(bug_rows, BUG_EXPORT_FIELDS),
        file_name="historico-bugs.csv", mime="text/csv; charset=utf-8",
        key="download_bug_history",
    )

    render_section_label(
        "Incidentes importados", "Contagens e detalhes preservados em registros distintos.",
    )
    if incident_rows:
        st.table([{
            "Release": row["release"],
            "Tipo": "Contagem" if row["record_type"] == "count" else "Detalhe",
            "Módulo": row["module"],
            "Quantidade": (row["incident_count"]
                           if row["incident_count"] is not None else "—"),
            "Descrição": row["description"] or "—",
            "Ocorrido em": (format_date_br(row["occurred_on"])
                            if row["occurred_on"] else "—"),
            "Analisado em": format_datetime_br(row["computed_at"]),
        } for row in incident_rows])
    else:
        st.info("Nenhum incidente importado para os filtros selecionados.")
    st.download_button(
        "Baixar CSV de incidentes",
        data=rows_to_csv(incident_rows, INCIDENT_EXPORT_FIELDS),
        file_name="historico-incidentes.csv", mime="text/csv; charset=utf-8",
        key="download_incident_history",
    )

    if history:
        st.subheader("Marcar resultado real de uma release")
        release_to_mark = st.selectbox(
            "Release", releases, key="release_outcome_target",
        )
        outcome = st.radio(
            "Resultado", ["ok", "falhou"], horizontal=True, key="outcome",
        )
        if st.button("Registrar resultado", key="record_release_outcome"):
            record_release_outcome(
                release_history_db, release_to_mark, outcome, repo_key=repo_key,
            )
            st.rerun()


st.set_page_config(
    page_title="garantiu", page_icon=str(BRAND_SYMBOL_PATH), layout="wide",
)
inject_design_system()
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "screen" not in st.session_state:
    st.session_state.screen = SCREENS[0]
render_brand()
screen = st.sidebar.radio("Etapas da release", SCREENS, key="screen")
render_sidebar_footer()
try:
    if screen == SCREENS[0]:
        connect_release()
    elif screen == SCREENS[6]:
        release_trends()
    elif not st.session_state.analysis:
        render_page_header(
            screen,
            "Conecte e analise uma release para liberar esta etapa.",
        )
        st.info("Analise um release na tela 'Conectar Release' primeiro.")
    else:
        renderers = {
            SCREENS[1]: risk_overview, SCREENS[2]: manual_guide,
            SCREENS[3]: automated_suite, SCREENS[4]: module_detail,
            SCREENS[5]: publication_decision,
        }
        renderers[screen](st.session_state.analysis)
except (OSError, ValueError, git.GitError, git.BadName,
        git.BadObject, JUnitXmlError) as exc:
    st.error(f"Não foi possível concluir a operação. Confira os dados: {exc}")
except sqlite3.Error:
    st.error(
        "Não foi possível acessar ou gravar o histórico local. "
        "Confira a permissão da pasta de dados e tente novamente."
    )
