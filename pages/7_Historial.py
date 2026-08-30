import plotly.graph_objects as go
import streamlit as st

from src.app_data import get_data
from src.pdf_export import build_executive_summary_pdf
from src.snapshots import load_snapshots
from src.theme import GREEN, NAVY, fmt_clp, format_display_df, inject_base_css, plotly_layout

st.set_page_config(page_title="Historial — Family Office", layout="wide")
inject_base_css()
data = get_data()

st.markdown("## Historial de Patrimonio Neto")
st.markdown(
    '<span class="fo-muted">Cada vez que se recalcula una nueva versión de FO_Master_Consolidado.xlsx, el dashboard '
    "guarda un snapshot con fecha. Con el tiempo esto arma una serie histórica real del patrimonio, algo que el "
    "Excel — una foto de un solo momento — no puede mostrar por sí solo.</span>",
    unsafe_allow_html=True,
)
st.divider()

snapshots = load_snapshots()

if len(snapshots) < 2:
    st.info(
        f"Hay {len(snapshots)} snapshot(s) guardado(s) hasta ahora. Se necesita al menos una segunda versión del "
        "Excel (con datos o fecha distintos) para poder graficar una evolución. Vuelve a abrir el dashboard después "
        "de actualizar el archivo fuente."
    )
    st.dataframe(snapshots, use_container_width=True, hide_index=True)
else:
    fig = go.Figure()
    fig.add_scatter(
        x=snapshots["fecha_carga"], y=snapshots["patrimonio_neto"], name="Patrimonio Neto",
        mode="lines+markers", line=dict(color=NAVY, width=2),
    )
    fig.add_scatter(
        x=snapshots["fecha_carga"], y=snapshots["patrimonio_neto_ajustado"], name="Patrimonio Neto Ajustado",
        mode="lines+markers", line=dict(color=GREEN, width=2, dash="dot"),
    )
    fig = plotly_layout(fig, height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(
        format_display_df(
            snapshots,
            currency_cols=("total_activos", "total_pasivos", "patrimonio_neto", "patrimonio_neto_ajustado"),
        ),
        use_container_width=True, hide_index=True,
    )

st.write("")
st.divider()
st.markdown("### Exportar resumen ejecutivo")
st.markdown('<span class="fo-muted">Genera un PDF de una página con el Balance, KPIs y Datos Pendientes del mes.</span>', unsafe_allow_html=True)
pdf_bytes = build_executive_summary_pdf(data)
st.download_button(
    "Descargar resumen ejecutivo (PDF)",
    data=pdf_bytes,
    file_name=f"resumen_ejecutivo_{data.fecha_carga.replace(':', '').replace(' ', '_')}.pdf",
    mime="application/pdf",
)
