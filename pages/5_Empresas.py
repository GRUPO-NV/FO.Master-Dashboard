import streamlit as st

from src.app_data import get_data
from src.theme import fmt_clp, fmt_pct, format_display_df, inject_base_css, status_badge_html

st.set_page_config(page_title="Empresas — Family Office", layout="wide")
inject_base_css()
data = get_data()

st.markdown("## Explorador de Empresas")
st.markdown(
    '<span class="fo-muted">34 sociedades vinculadas al grupo familiar. Semáforo de completitud: RUT confirmado, '
    "% de participación verificado y Estados Financieros (Patrimonio Contable) cargados.</span>",
    unsafe_allow_html=True,
)
st.divider()

emp = data.empresas.copy()
emp["% verificado"] = emp["% Participación (provisorio)"].notna()
emp["EEFF cargados"] = emp["Patrimonio Contable (CLP)"].notna()
emp["Completitud"] = emp["RUT confirmado"].astype(int) + emp["% verificado"].astype(int) + emp["EEFF cargados"].astype(int)


def status_for(score: int) -> str:
    if score == 3:
        return "verde"
    if score == 0:
        return "rojo"
    return "amarillo"


emp["Estado"] = emp["Completitud"].apply(status_for)

c1, c2, c3 = st.columns(3)
c1.markdown(status_badge_html("verde", f"{(emp['Estado'] == 'verde').sum()} completas"), unsafe_allow_html=True)
c2.markdown(status_badge_html("amarillo", f"{(emp['Estado'] == 'amarillo').sum()} parciales"), unsafe_allow_html=True)
c3.markdown(status_badge_html("rojo", f"{(emp['Estado'] == 'rojo').sum()} sin ningún dato"), unsafe_allow_html=True)

st.write("")
search = st.text_input("Buscar empresa o RUT")
estado_filter = st.multiselect("Filtrar por estado", ["verde", "amarillo", "rojo"], default=["verde", "amarillo", "rojo"])

view = emp[emp["Estado"].isin(estado_filter)]
if search:
    mask = view["Empresa"].str.contains(search, case=False, na=False) | view["RUT"].astype(str).str.contains(search, case=False, na=False)
    view = view[mask]

display_cols = [
    "Empresa", "RUT", "RUT confirmado", "% Participación (provisorio)", "% verificado",
    "Patrimonio Contable (CLP)", "EEFF cargados", "Equity Value Estimado (CLP)", "Estado",
]
st.dataframe(
    format_display_df(
        view[display_cols],
        currency_cols=("Patrimonio Contable (CLP)", "Equity Value Estimado (CLP)"),
        pct_cols=("% Participación (provisorio)",),
    ),
    use_container_width=True, hide_index=True, height=520,
)

st.caption(
    f"Equity Value Estimado total: {fmt_clp(emp['Equity Value Estimado (CLP)'].sum())}. "
    f"{(~emp['EEFF cargados']).sum()} de {len(emp)} empresas aún en $0 por falta de Estados Financieros — "
    "el Patrimonio Neto real del grupo es mayor a la cifra del Balance mientras esto no se resuelva."
)
