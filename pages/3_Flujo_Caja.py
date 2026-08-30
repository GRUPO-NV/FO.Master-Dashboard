import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app_data import get_data
from src.theme import GREEN, NAVY, RED, SLATE_LIGHT, fmt_clp, format_display_df, inject_base_css, plotly_layout

st.set_page_config(page_title="Flujo de Caja — Family Office", layout="wide")
inject_base_css()
data = get_data()
fc = data.flujo_caja

st.markdown("## Explorador de Flujo de Caja")
st.markdown(
    '<span class="fo-muted">60 meses (ago-2026 a jul-2031). El Saldo Acumulado mensual fue reconstruido por el '
    "dashboard — la fila del Excel original venía vacía; ver nota más abajo y el panel de Datos Pendientes.</span>",
    unsafe_allow_html=True,
)
st.divider()

meses = fc.meses
fig1 = go.Figure()
fig1.add_bar(x=meses, y=fc.total_ingresos, name="Ingresos", marker_color=NAVY)
fig1.add_bar(x=meses, y=-fc.total_egresos, name="Egresos", marker_color=SLATE_LIGHT)
fig1.add_scatter(x=meses, y=fc.saldo_mensual, name="Saldo Mensual", mode="lines", line=dict(color=GREEN, width=2))
fig1.update_layout(barmode="relative", title="Ingresos, Egresos y Saldo Mensual")
fig1 = plotly_layout(fig1, height=380)
st.plotly_chart(fig1, use_container_width=True)

neg_months = [m for m, v in zip(meses, fc.saldo_acumulado) if v is not None and v < 0]
fig2 = go.Figure()
fig2.add_scatter(
    x=meses, y=fc.saldo_acumulado, name="Saldo Acumulado (reconstruido)",
    mode="lines", line=dict(color=NAVY, width=2), fill="tozeroy",
    fillcolor="rgba(15,35,64,0.08)",
)
if neg_months:
    neg_vals = [v for v in fc.saldo_acumulado if v is not None and v < 0]
    fig2.add_scatter(
        x=neg_months, y=neg_vals, name="Meses en rojo", mode="markers",
        marker=dict(color=RED, size=7, symbol="circle"),
    )
fig2.add_hline(y=0, line_color=SLATE_LIGHT, line_width=1)
fig2.update_layout(title="Saldo Acumulado proyectado")
fig2 = plotly_layout(fig2, height=340)
st.plotly_chart(fig2, use_container_width=True)

if neg_months:
    worst_idx = min(range(len(fc.saldo_acumulado)), key=lambda i: fc.saldo_acumulado.iloc[i])
    st.error(
        f"{len(neg_months)} meses proyectan Saldo Acumulado negativo. El peor punto es "
        f"{fmt_clp(fc.saldo_acumulado.iloc[worst_idx])} en {meses[worst_idx]:%b-%Y}. "
        "Revisar si corresponde a un compromiso de caja real (compra de propiedad, dividendo) o a un artefacto del modelo."
    )
else:
    st.success("No se proyectan meses con Saldo Acumulado negativo en la ventana de 60 meses.")

st.write("")
st.markdown("### Explorador por categoría")
all_items = pd.concat([
    pd.Series(fc.ingresos.index, name="item").to_frame().assign(Tipo="Ingreso"),
    pd.Series(fc.egresos.index, name="item").to_frame().assign(Tipo="Egreso"),
])
tipo_filter = st.radio("Tipo", ["Ingresos", "Egresos"], horizontal=True)
source_df = fc.ingresos if tipo_filter == "Ingresos" else fc.egresos
default_items = source_df.abs().sum(axis=1).sort_values(ascending=False).head(5).index.tolist()
selected = st.multiselect(f"Líneas de {tipo_filter.lower()} a graficar", options=list(source_df.index), default=default_items)

if selected:
    fig3 = go.Figure()
    for item in selected:
        fig3.add_scatter(x=meses, y=source_df.loc[item], name=item, mode="lines")
    fig3 = plotly_layout(fig3, height=380)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Selecciona al menos una línea para graficar su evolución mensual.")

st.write("")
st.markdown("### Resumen Anual — horizonte largo (para KPIs a 10 años)")
st.dataframe(
    format_display_df(
        fc.resumen_anual,
        currency_cols=("Total Ingresos", "Total Egresos", "Saldo Mensual", "Saldo Acumulado", "Activos Líquidos Totales (modelo)"),
    ),
    use_container_width=True, hide_index=True,
)
st.caption(
    "La grilla mensual solo cubre 5 años (60 meses); esta tabla del modelo 'Flujo General' original llega a 10 años "
    "y es la fuente de los KPIs de largo plazo."
)
