"""Presentation helpers for the Garantiu Streamlit interface."""

from __future__ import annotations

import base64
from datetime import date, datetime, timezone
from functools import lru_cache
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
BRAND_ASSET_DIR = ROOT / "garantiu" / "assets"
BRAND_SYMBOL_PATH = BRAND_ASSET_DIR / "garantiu-symbol.png"
BRAND_WORDMARK_PATH = BRAND_ASSET_DIR / "garantiu-wordmark.png"
FACTOR_LABELS = {
    "complexidade": "Complexidade da mudança",
    "bugs": "Histórico de bugs",
    "saude_testes": "Saúde dos testes",
    "incidentes": "Incidentes anteriores",
}


@lru_cache(maxsize=2)
def _asset_data_uri(path: Path) -> str:
    """Embed a local brand asset without depending on a static file server."""
    mime_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{payload}"


def format_score(value: float) -> str:
    """Format a numeric score for the Brazilian interface."""
    try:
        return f"{float(value):.1f}".replace(".", ",") + " / 100"
    except (TypeError, ValueError):
        return str(value)


def format_percent(value: float) -> str:
    """Format a numeric percentage without changing its stored value."""
    try:
        return f"{float(value):.1f}".replace(".", ",") + "%"
    except (TypeError, ValueError):
        return str(value)


def _parse_temporal(value: str | date | datetime) -> date | datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise TypeError("unsupported temporal value")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    if "T" in normalized or " " in normalized:
        return datetime.fromisoformat(normalized)
    return date.fromisoformat(normalized)


def format_date_br(value: str | date | datetime) -> str:
    """Format an ISO/date value as DD/MM/YYYY, preserving invalid legacy text."""
    try:
        parsed = _parse_temporal(value)
        return parsed.strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(value)


def format_datetime_br(
    value: str | datetime,
    timezone_name: str = "America/Sao_Paulo",
) -> str:
    """Convert an ISO timestamp from UTC to the requested display timezone."""
    try:
        parsed = _parse_temporal(value)
        if not isinstance(parsed, datetime):
            raise ValueError("datetime required")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        localized = parsed.astimezone(ZoneInfo(timezone_name))
        return localized.strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        return str(value)


def inject_design_system() -> None:
    """Load the shared visual system once per Streamlit render."""
    css = (ROOT / "garantiu" / "ui.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_brand() -> None:
    """Render the product signature and promise in the sidebar."""
    symbol = _asset_data_uri(BRAND_SYMBOL_PATH)
    wordmark = _asset_data_uri(BRAND_WORDMARK_PATH)
    st.sidebar.markdown(
        f"""
        <div class="brand-lockup">
          <div class="brand-logo" role="img" aria-label="Garantiu">
            <img class="brand-logo-symbol" src="{symbol}" alt="" />
            <img class="brand-logo-wordmark" src="{wordmark}" alt="" />
          </div>
          <p>Da evidência para entregas com segurança.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_footer() -> None:
    wordmark = _asset_data_uri(BRAND_WORDMARK_PATH)
    st.sidebar.markdown(
        f"""
        <div class="sidebar-footer">
          <img src="{wordmark}" alt="Garantiu" />
          <span>Engenharia de software<br>com mais confiança.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, description: str) -> None:
    symbol = _asset_data_uri(BRAND_SYMBOL_PATH)
    st.markdown(
        f"""
        <div class="page-brand-symbol" aria-hidden="true">
          <img src="{symbol}" alt="" />
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.title(title)
    st.markdown(
        f"<p class='page-description'>{escape(description)}</p>",
        unsafe_allow_html=True,
    )


def render_release_context(analysis: dict) -> None:
    """Keep the analyzed source visible without inventing unavailable data."""
    release_name = escape(str(analysis.get("release_name", "Release atual")))
    repo_path = escape(str(analysis.get("repo_path", "Repositório não informado")))
    changed = len(analysis.get("changed_files", []))
    modules = len(analysis.get("module_scores", []))
    st.markdown(
        f"""
        <section class="release-context" aria-label="Contexto da release">
          <div>
          <span class="context-label">Release analisada</span>
            <strong>{release_name}</strong>
            <small>{repo_path}</small>
          </div>
          <dl>
            <div><dt>Arquivos</dt><dd>{changed}</dd></div>
            <div><dt>Módulos</dt><dd>{modules}</dd></div>
            <div><dt>Status</dt><dd><span class="status-dot">Analisada</span></dd></div>
          </dl>
        </section>
        """,
        unsafe_allow_html=True,
    )


def risk_level(score: float) -> tuple[str, str]:
    if score >= 70:
        return "alto", "Alto risco"
    if score >= 40:
        return "medio", "Médio risco"
    return "baixo", "Baixo risco"


def render_risk_distribution(module_scores: list[dict]) -> None:
    counts = {"alto": 0, "medio": 0, "baixo": 0}
    for module in module_scores:
        counts[risk_level(float(module["score"]))[0]] += 1
    st.markdown(
        f"""
        <div class="risk-distribution" aria-label="Distribuição dos módulos por risco">
          <div><strong>{len(module_scores)}</strong><span>módulos impactados</span></div>
          <div class="risk-high"><strong>{counts['alto']}</strong><span>em alto risco</span></div>
          <div class="risk-medium"><strong>{counts['medio']}</strong><span>em médio risco</span></div>
          <div class="risk-low"><strong>{counts['baixo']}</strong><span>em baixo risco</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_factor_heading(factor: str, value: float) -> None:
    label = FACTOR_LABELS.get(factor, factor.replace("_", " ").title())
    level, level_label = risk_level(value)
    st.markdown(
        f"""
        <div class="factor-heading">
          <span>{escape(label)}</span>
          <strong class="risk-{level}">{format_score(value)}<small> · {level_label}</small></strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_label(title: str, description: str | None = None) -> None:
    detail = f"<span>{escape(description)}</span>" if description else ""
    st.markdown(
        f"<div class='section-label'><strong>{escape(title)}</strong>{detail}</div>",
        unsafe_allow_html=True,
    )


def render_module_focus(module: dict) -> None:
    level, label = risk_level(float(module["score"]))
    st.markdown(
        f"""
        <div class="module-focus">
          <span>Onde testar primeiro</span>
          <h3>{escape(str(module['module']))}</h3>
          <p>Este módulo concentra o maior risco desta release. Comece por ele e use as evidências abaixo para orientar o teste.</p>
          <strong class="risk-pill risk-{level}">{label} · {format_score(module['score'])}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
