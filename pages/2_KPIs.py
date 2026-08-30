import streamlit as st

from src.app_data import get_data
from src.auth import require_password
from src.kpi_engine import cards_by_section
from src.theme import fmt_clp, inject_base_css, status_badge_html

st.set_page_config(page_title="KPIs — Family Office", layout="wide")
require_password()
inject_base_css()
data = get_data()

st.markdown("## Panel de KPIs")
st.markdown(
    '<span class="fo-muted">Horizontes 1/5/10 años · combina el Balance (foto actual) con la proyección de Flujo de Caja y los supuestos de retorno.</span>',
    unsafe_allow_html=True,
)
st.divider()

sections = cards_by_section(data)
section_order = ["Balance y Estructura", "Liquidez y Cobertura", "Rentabilidad y Crecimiento", "Riesgo y Concentración"]

for section in section_order:
    cards = sections.get(section, [])
    if not cards:
        continue
    st.markdown(f"#### {section}")
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="fo-card">
                    <div class="fo-metric-label">{card.label}</div>
                    <div class="fo-metric-value">{card.display}</div>
                    <div class="fo-muted">{status_badge_html(card.status)}</div>
                    <div class="fo-muted" style="margin-top:8px;">{card.note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.write("")

st.divider()
st.markdown("### Proyección de Patrimonio Neto y crecimiento")
c = data.kpis_raw["rentabilidad_crecimiento"]
row_pn = c[c["KPI"].str.contains("Patrimonio Neto proyectado", na=False)]
if not row_pn.empty:
    r = row_pn.iloc[0]
    cols = st.columns(3)
    for col, horiz, key in zip(cols, ["1 año", "5 años", "10 años"], ["1 año", "5 años", "10 años"]):
        with col:
            st.markdown(
                f"""
                <div class="fo-card">
                    <div class="fo-metric-label">Patrimonio Neto proyectado — {horiz}</div>
                    <div class="fo-metric-value">{fmt_clp(r[key])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
st.caption(
    "Retorno ponderado por peso de cada clase de activo × tasas de la pestaña Supuestos. "
    "Para modelar apalancamiento u otros escenarios, usa el Simulador."
)
st.page_link("pages/6_Simulador.py", label="Ir al Simulador de escenarios →")

st.write("")
with st.expander("Ver tablas de KPI completas (como en el Excel)"):
    for name, df in data.kpis_raw.items():
        st.markdown(f"**{name.replace('_', ' ').title()}**")
        st.dataframe(df, use_container_width=True, hide_index=True)
