import plotly.graph_objects as go
import streamlit as st

from src.app_data import get_data
from src.kpi_engine import build_kpi_cards
from src.pending_data import scan_pending_data
from src.theme import (
    ASSET_CLASS_COLORS,
    inject_base_css,
    metric_card,
    plotly_layout,
    status_badge_html,
    fmt_clp,
)

st.set_page_config(page_title="Family Office — Panel Consolidado", layout="wide")
inject_base_css()

data = get_data()

st.markdown("## Family Office — Panel Consolidado")
st.markdown(
    f'<span class="fo-muted">Perímetro: núcleo familiar + hijos · '
    f"Datos recalculados desde <code>FO_Master_Consolidado.xlsx</code> el {data.fecha_carga}</span>",
    unsafe_allow_html=True,
)
st.divider()

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Total Activos", fmt_clp(data.balance.total_activos))
with col2:
    metric_card("Total Pasivos", fmt_clp(data.balance.total_pasivos))
with col3:
    metric_card("Patrimonio Neto", fmt_clp(data.balance.patrimonio_neto))
with col4:
    metric_card(
        "Patrimonio Neto Ajustado",
        fmt_clp(data.balance.patrimonio_neto_ajustado),
        "incluye Activos Contingentes (memo)",
    )

st.write("")
left, right = st.columns([3, 2])

with left:
    st.markdown("#### Distribución de Activos")
    dist = data.balance.distribucion_activos
    fig = go.Figure(
        data=[
            go.Pie(
                labels=dist["Clase de Activo"],
                values=dist["Monto (CLP)"],
                hole=0.55,
                marker=dict(colors=[ASSET_CLASS_COLORS.get(c, "#999") for c in dist["Clase de Activo"]]),
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value:,.0f} CLP<extra></extra>",
            )
        ]
    )
    fig = plotly_layout(fig, height=380)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.page_link("pages/1_Balance.py", label="Ver detalle del Balance y drill-down por clase →")

with right:
    st.markdown("#### Semáforo de KPIs")
    cards = build_kpi_cards(data)
    counts = {"rojo": 0, "amarillo": 0, "verde": 0}
    for c in cards:
        counts[c.status] += 1
    b1, b2, b3 = st.columns(3)
    b1.markdown(status_badge_html("rojo", f"{counts['rojo']} en rojo"), unsafe_allow_html=True)
    b2.markdown(status_badge_html("amarillo", f"{counts['amarillo']} en amarillo"), unsafe_allow_html=True)
    b3.markdown(status_badge_html("verde", f"{counts['verde']} en verde"), unsafe_allow_html=True)
    st.write("")
    for c in sorted(cards, key=lambda x: {"rojo": 0, "amarillo": 1, "verde": 2}[x.status]):
        if c.status == "verde":
            continue
        st.markdown(
            f"{status_badge_html(c.status)} &nbsp; **{c.label}** — {c.display}",
            unsafe_allow_html=True,
        )
    st.page_link("pages/2_KPIs.py", label="Ver panel completo de KPIs →")

    st.write("")
    st.markdown("#### Datos Pendientes")
    pending = scan_pending_data(data)
    alta = sum(1 for p in pending if p.priority == "Alta")
    st.markdown(
        f'<div class="fo-card"><span class="fo-metric-value">{len(pending)}</span> '
        f'<span class="fo-muted">ítems pendientes detectados — {alta} de prioridad alta</span></div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_Datos_Pendientes.py", label="Ver checklist accionable →")

st.write("")
st.markdown("#### Navegación")
st.markdown(
    """
- **Balance** — activos/pasivos en vivo con drill-down por clase de activo.
- **KPIs** — estructura, liquidez, rentabilidad y riesgo con semáforos.
- **Flujo de Caja** — 60 meses de ingresos, egresos y saldo acumulado.
- **Datos Pendientes** — checklist de información que falta validar con el cliente.
- **Empresas** — las 34 sociedades vinculadas y su nivel de completitud de datos.
- **Simulador** — apalancamiento, costo de deuda y retorno reinvertido, en vivo.
- **Historial** — evolución del patrimonio neto entre snapshots del Excel.
"""
)
