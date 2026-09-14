from garantiu.scoring import RISK_THRESHOLDS, risk_label  # noqa: F401  (re-exported)

FACTOR_MESSAGES = {
    "complexidade": (
        "Foi uma mudança grande nessa área — quanto mais código muda, maior "
        "a chance de algo passar despercebido na revisão."
    ),
    "bugs": (
        "Essa área já teve histórico de problema corrigido antes — isso é "
        "um dos sinais mais fortes de que pode dar problema de novo."
    ),
    "saude_testes": (
        "Os testes automatizados dessa área não estão saudáveis (falhando "
        "ou com pouca cobertura) — não dá pra confiar só neles."
    ),
    "incidentes": (
        "Essa área já causou incidente em produção antes — atenção redobrada."
    ),
}

GENERIC_SCENARIOS = [
    "Testar o fluxo principal de {module} do início ao fim",
    "Testar {module} com uma entrada inválida ou inesperada",
    "Testar o comportamento de {module} depois de uma falha (timeout, erro de rede, etc.)",
]


def build_module_card(module: str, score: float, factors: dict, changed_files: list) -> dict:
    """
    Builds the plain-language card for one module on the "Roteiro de Teste
    Manual" screen. Picks the highest-scoring factor to explain "por que
    testar isso".
    """
    file_names = [f["path"] for f in changed_files if f["module"] == module]
    preview = ", ".join(file_names[:3])
    if len(file_names) > 3:
        preview += ", ..."

    dominant_factor = max(factors, key=factors.get)

    return {
        "module": module,
        "score": score,
        "risk": risk_label(score),
        "o_que_mudou": f"{len(file_names)} arquivo(s) alterado(s) nesta área ({preview}).",
        "por_que_testar": FACTOR_MESSAGES[dominant_factor],
        "cenarios": [s.format(module=module) for s in GENERIC_SCENARIOS],
    }
