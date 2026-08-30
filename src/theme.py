"""Shared visual language: a sober family-office palette (navy / grays, semaphore
accents only for risk), one Plotly template, and small render helpers reused by every
page so the app reads as one tool, not a stack of separate scripts."""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

NAVY = "#0F2340"
NAVY_SOFT = "#1C3A5E"
SLATE = "#3E4C5E"
SLATE_LIGHT = "#6B7A8F"
BORDER = "#DCE2E8"
BG = "#F6F8FA"
CARD_BG = "#FFFFFF"
INK = "#141B26"

GREEN = "#1E7A4C"
GREEN_BG = "#E7F4ED"
AMBER = "#B7791F"
AMBER_BG = "#FBF2E1"
RED = "#B3261E"
RED_BG = "#FBE9E7"

STATUS_COLORS = {
    "verde": (GREEN, GREEN_BG),
    "amarillo": (AMBER, AMBER_BG),
    "rojo": (RED, RED_BG),
}

ASSET_CLASS_COLORS = {
    "Liquidez": "#8FA4BD",
    "Inversiones Financieras": "#4C6E91",
    "Bienes Raíces": NAVY,
    "Empresas (Equity)": "#2E5077",
    "Otros Activos (CxC + menores)": "#B7C3D0",
}

FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"


def inject_base_css() -> None:
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: {FONT_FAMILY};
        }}
        .stApp {{
            background-color: {BG};
        }}
        [data-testid="stSidebar"] {{
            background-color: {NAVY};
        }}
        [data-testid="stSidebar"] * {{
            color: #E7ECF2 !important;
        }}
        [data-testid="stSidebar"] a {{
            color: #C9D6E5 !important;
        }}
        h1, h2, h3 {{
            color: {INK};
            font-weight: 600;
        }}
        .fo-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 18px 20px;
        }}
        .fo-badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }}
        .fo-muted {{
            color: {SLATE_LIGHT};
            font-size: 0.85rem;
        }}
        .fo-metric-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: {INK};
        }}
        .fo-metric-label {{
            color: {SLATE};
            font-size: 0.85rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge_html(status: str, text: str | None = None) -> str:
    color, bg = STATUS_COLORS.get(status, (SLATE, "#EEE"))
    label = text or status.upper()
    return f'<span class="fo-badge" style="color:{color};background:{bg};">{label}</span>'


def plotly_layout(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        font=dict(family=FONT_FAMILY, color=INK, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        colorway=[NAVY, "#4C6E91", "#8FA4BD", "#2E5077", "#B7C3D0", SLATE_LIGHT],
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER)
    return fig


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def fmt_clp(value: float | None, decimals: int = 0) -> str:
    if _is_missing(value):
        return "s/d"
    sign = "-" if value < 0 else ""
    formatted = f"{abs(value):,.{decimals}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{sign}${formatted}"


def fmt_pct(value: float | None, decimals: int = 1) -> str:
    if _is_missing(value):
        return "s/d"
    return f"{value * 100:.{decimals}f}%"


def format_display_df(df: pd.DataFrame, currency_cols: tuple[str, ...] = (), pct_cols: tuple[str, ...] = ()) -> pd.DataFrame:
    """Returns a copy of df with the given columns replaced by already-formatted
    display strings (including 's/d' for missing values). st.dataframe's Arrow-based
    grid does not reliably apply pandas Styler formatters/na_rep to null cells, so
    pre-formatting to plain strings is the reliable way to control how blanks render."""
    out = df.copy()
    for col in currency_cols:
        out[col] = out[col].apply(fmt_clp)
    for col in pct_cols:
        out[col] = out[col].apply(fmt_pct)
    return out


def esc_dollar(text: str) -> str:
    """Streamlit's markdown renders $...$ as LaTeX (MathJax); a stray pair of dollar
    signs anywhere in one markdown call (e.g. two CLP amounts in the same block) gets
    silently re-styled as math. Swap the literal '$' for its HTML entity wherever text
    is going into st.markdown(unsafe_allow_html=True) so currency strings never form
    an accidental math delimiter pair."""
    return text.replace("$", "&#36;")


def metric_card(label: str, value: str, sublabel: str = "", status: str | None = None) -> None:
    badge = status_badge_html(status) if status else ""
    st.markdown(
        f"""
        <div class="fo-card">
            <div class="fo-metric-label">{label}</div>
            <div class="fo-metric-value">{esc_dollar(value)}</div>
            <div class="fo-muted">{esc_dollar(sublabel)} {badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
