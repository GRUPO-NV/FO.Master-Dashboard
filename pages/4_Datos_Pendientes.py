import streamlit as st

from src.app_data import get_data
from src.pending_data import scan_pending_data
from src.theme import fmt_clp, inject_base_css, status_badge_html

st.set_page_config(page_title="Datos Pendientes — Family Office", layout="wide")
inject_base_css()
data = get_data()

st.markdown("## Datos Pendientes")
st.markdown(
    '<span class="fo-muted">Checklist accionable generado automáticamente a partir de celdas en blanco, '
    "titulares sin confirmar y valores proxy en el archivo maestro. El Excel marca estos casos en amarillo; "
    "este panel los detecta, prioriza y lista para que el family office los resuelva con el cliente.</span>",
    unsafe_allow_html=True,
)
st.divider()

items = scan_pending_data(data)
priority_to_status = {"Alta": "rojo", "Media": "amarillo", "Baja": "verde"}

col1, col2, col3 = st.columns(3)
counts = {"Alta": 0, "Media": 0, "Baja": 0}
for i in items:
    counts[i.priority] += 1
col1.markdown(status_badge_html("rojo", f"{counts['Alta']} prioridad alta"), unsafe_allow_html=True)
col2.markdown(status_badge_html("amarillo", f"{counts['Media']} prioridad media"), unsafe_allow_html=True)
col3.markdown(status_badge_html("verde", f"{counts['Baja']} prioridad baja"), unsafe_allow_html=True)

st.write("")
categories = sorted({i.category for i in items})
selected_categories = st.multiselect("Filtrar por categoría", categories, default=categories)

priority_filter = st.radio("Prioridad", ["Todas", "Alta", "Media", "Baja"], horizontal=True)

filtered = [
    i for i in items
    if i.category in selected_categories and (priority_filter == "Todas" or i.priority == priority_filter)
]

st.write("")
for item in filtered:
    status = priority_to_status[item.priority]
    amount = f" · {fmt_clp(item.amount_clp)}" if item.amount_clp is not None else ""
    st.markdown(
        f"""
        <div class="fo-card" style="margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong>{item.item}</strong>
                {status_badge_html(status, item.priority)}
            </div>
            <div class="fo-muted">{item.category}{amount}</div>
            <div style="margin-top:6px;">{item.detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if not filtered:
    st.info("No hay ítems pendientes para este filtro.")
