import plotly.graph_objects as go
import streamlit as st

from src.app_data import get_data
from src.auth import require_password
from src.simulator import (
    ScenarioInputs,
    required_cagr_for_goal,
    run_scenario,
    solve_leverage_for_target,
)
from src.theme import GREEN, NAVY, fmt_clp, fmt_pct, inject_base_css, metric_card, plotly_layout

st.set_page_config(page_title="Simulador — Family Office", layout="wide")
require_password()
inject_base_css()
data = get_data()

st.markdown("## Simulador de Escenarios")
st.markdown(
    '<span class="fo-muted">Modela apalancar Bienes Raíces para reinvertir el capital a una tasa distinta, y compara '
    "contra el crecimiento orgánico del portafolio. Recalcula en vivo al mover los controles.</span>",
    unsafe_allow_html=True,
)
st.divider()

st.markdown("#### Supuestos del escenario")
s1, s2, s3, s4 = st.columns(4)
with s1:
    leverage_pct = st.slider("Apalancamiento sobre Bienes Raíces (LTV)", 0, 80, 20, step=5, format="%d%%") / 100
with s2:
    cost_of_debt = st.slider("Costo de la deuda (anual)", 0.0, 15.0, 7.0, step=0.5, format="%.1f%%") / 100
with s3:
    return_on_deployed = st.slider("Retorno del capital reasignado (anual)", 0.0, 20.0, 8.0, step=0.5, format="%.1f%%") / 100
with s4:
    horizon = st.slider("Horizonte (años)", 1, 10, 5)

result = run_scenario(data, ScenarioInputs(leverage_pct, cost_of_debt, return_on_deployed, horizon))

st.write("")
c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Deuda nueva tomada", fmt_clp(result.debt_drawn), f"{fmt_pct(leverage_pct)} del valor de Bienes Raíces")
with c2:
    metric_card("Patrimonio Neto hoy", fmt_clp(result.base_patrimonio_neto))
with c3:
    metric_card(
        f"Patrimonio Neto proyectado — {horizon} años",
        fmt_clp(result.patrimonio_neto_final_leveraged),
        f"sin apalancar: {fmt_clp(result.patrimonio_neto_final_base)}",
    )
with c4:
    metric_card(
        "CAGR resultante",
        fmt_pct(result.cagr_leveraged),
        f"sin apalancar: {fmt_pct(result.cagr_base)} (retorno ponderado del portafolio)",
    )

years = list(range(horizon + 1))
fig = go.Figure()
fig.add_scatter(x=years, y=result.path_base, name="Sin apalancamiento", mode="lines+markers", line=dict(color=NAVY, dash="dot"))
fig.add_scatter(x=years, y=result.path_leveraged, name="Con apalancamiento", mode="lines+markers", line=dict(color=GREEN))
fig.update_layout(title="Patrimonio Neto proyectado", xaxis_title="Años desde hoy", yaxis_title="CLP")
fig = plotly_layout(fig, height=380)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Modelo simplificado: la deuda se toma una vez al año 0, el interés se paga de flujo de caja cada año (no se "
    "capitaliza) y el capital reasignado compone a la tasa elegida. No considera impuestos, amortización de capital "
    "ni costos de transacción. Con apalancamiento 0% este escenario reproduce exactamente el KPI "
    "'Patrimonio Neto proyectado' del Excel."
)

st.divider()
st.markdown("#### Tracker de objetivo")
g1, g2 = st.columns([1, 2])
with g1:
    multiple = st.number_input("Meta: multiplicar el patrimonio por", min_value=1.1, max_value=10.0, value=2.0, step=0.1)
    st.markdown(f'<span class="fo-muted">en {horizon} años (usa el horizonte del simulador)</span>', unsafe_allow_html=True)

required = required_cagr_for_goal(multiple, horizon)
gap = required - result.cagr_leveraged

with g2:
    m1, m2, m3 = st.columns(3)
    with m1:
        metric_card("CAGR requerido", fmt_pct(required), f"para llegar a {multiple:.1f}x en {horizon} años")
    with m2:
        metric_card("CAGR del escenario actual", fmt_pct(result.cagr_leveraged))
    with m3:
        status = "verde" if gap <= 0 else ("amarillo" if gap < 0.03 else "rojo")
        metric_card("Brecha", fmt_pct(gap), status=status)

if gap <= 0:
    st.success(f"El escenario actual ya alcanza la meta de {multiple:.1f}x en {horizon} años.")
else:
    needed_leverage = solve_leverage_for_target(data, required, cost_of_debt, return_on_deployed, horizon)
    if needed_leverage is None:
        st.warning(
            f"Con el costo de deuda ({fmt_pct(cost_of_debt)}) y retorno reinvertido ({fmt_pct(return_on_deployed)}) "
            "actuales, ningún nivel de apalancamiento sobre Bienes Raíces (hasta 80% LTV) alcanza la meta. "
            "Sube el retorno del capital reasignado o el horizonte, o baja la meta."
        )
    else:
        valor_br = data.balance.distribucion_activos.set_index("Clase de Activo")["Monto (CLP)"].get("Bienes Raíces", 0.0)
        st.info(
            f"Para cerrar la brecha solo con apalancamiento (mismo costo de deuda y retorno reinvertido), "
            f"se necesitaría un LTV de aproximadamente {fmt_pct(needed_leverage)} sobre Bienes Raíces "
            f"(deuda de {fmt_clp(needed_leverage * valor_br)})."
        )
