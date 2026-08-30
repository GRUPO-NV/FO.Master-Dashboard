import plotly.graph_objects as go
import streamlit as st

from src.app_data import get_data
from src.theme import ASSET_CLASS_COLORS, esc_dollar, fmt_clp, format_display_df, inject_base_css, metric_card, plotly_layout

st.set_page_config(page_title="Balance — Family Office", layout="wide")
inject_base_css()
data = get_data()

st.markdown("## Balance en Vivo")
st.markdown(
    '<span class="fo-muted">Activos, pasivos y patrimonio neto consolidados — click en una clase de activo para ver el detalle.</span>',
    unsafe_allow_html=True,
)
st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    metric_card("Total Activos", fmt_clp(data.balance.total_activos))
with c2:
    metric_card("Total Pasivos", fmt_clp(data.balance.total_pasivos))
with c3:
    metric_card("Patrimonio Neto", fmt_clp(data.balance.patrimonio_neto))

st.write("")
left, right = st.columns([2, 3])

dist = data.balance.distribucion_activos
with left:
    fig = go.Figure(
        data=[
            go.Pie(
                labels=dist["Clase de Activo"],
                values=dist["Monto (CLP)"],
                hole=0.55,
                marker=dict(colors=[ASSET_CLASS_COLORS.get(c, "#999") for c in dist["Clase de Activo"]]),
                textinfo="percent",
                hovertemplate="%{label}<br>%{value:,.0f} CLP (%{percent})<extra></extra>",
            )
        ]
    )
    fig = plotly_layout(fig, height=360)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.dataframe(
        format_display_df(dist, currency_cols=("Monto (CLP)",), pct_cols=("% del Total",)),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("**Pasivos**")
    st.dataframe(
        format_display_df(data.balance.pasivos, currency_cols=("Monto (CLP)",)),
        use_container_width=True,
        hide_index=True,
    )
    st.markdown(
        esc_dollar(
            '<span class="fo-muted">Memo — Activos Contingentes (fuera del Patrimonio Neto principal): '
            f"{fmt_clp(data.balance.activos_contingentes_memo)}. Patrimonio Neto ajustado: "
            f"{fmt_clp(data.balance.patrimonio_neto_ajustado)}.</span>"
        ),
        unsafe_allow_html=True,
    )

st.write("")
st.markdown("### Drill-down por clase de activo")
clase = st.radio(
    "Clase de activo",
    ["Liquidez", "Inversiones Financieras", "Bienes Raíces", "Empresas", "Otras partidas"],
    horizontal=True,
    label_visibility="collapsed",
)

if clase == "Liquidez":
    st.markdown(
        esc_dollar(
            f"**{len(data.liquidez.detalle)} cuentas/plataformas** · Subtotal perímetro completo "
            f"{fmt_clp(data.liquidez.subtotal_perimetro_completo)} · Subtotal núcleo+hijos "
            f"{fmt_clp(data.liquidez.subtotal_nucleo)}"
        )
    )
    st.dataframe(
        format_display_df(data.liquidez.detalle, currency_cols=("Monto (CLP)",)),
        use_container_width=True, hide_index=True,
    )
    with st.expander(f"Referencia — FO.xlsx (jul-2026), no incluida en el total ({fmt_clp(data.liquidez.referencia_fo_total)})"):
        st.dataframe(
            format_display_df(data.liquidez.referencia_fo, currency_cols=("Monto (CLP)",)),
            use_container_width=True, hide_index=True,
        )

elif clase == "Inversiones Financieras":
    st.markdown(
        esc_dollar(
            f"**{len(data.inversiones.detalle)} instrumentos** · Subtotal perímetro completo "
            f"{fmt_clp(data.inversiones.subtotal_perimetro_completo)} · Subtotal núcleo+hijos "
            f"{fmt_clp(data.inversiones.subtotal_nucleo)}"
        )
    )
    st.dataframe(
        format_display_df(data.inversiones.detalle, currency_cols=("Monto (CLP)",)),
        use_container_width=True, hide_index=True,
    )
    with st.expander(f"Referencia — FO.xlsx (jul-2026), no incluida en el total ({fmt_clp(data.inversiones.referencia_fo_total)})"):
        st.dataframe(
            format_display_df(data.inversiones.referencia_fo, currency_cols=("Monto (CLP)",)),
            use_container_width=True, hide_index=True,
        )

elif clase == "Bienes Raíces":
    br = data.bienes_raices
    total_recalculado = br["Valor Atribuible (CLP)"].sum()
    total_oficial = dist.set_index("Clase de Activo")["Monto (CLP)"].get("Bienes Raíces", 0.0)
    diff = total_recalculado - total_oficial
    st.markdown(f"**{len(br)} propiedades** · Suma Valor Atribuible (recalculado) {fmt_clp(total_recalculado)}")
    if abs(diff) > 1:
        st.info(
            esc_dollar(
                f"El total recalculado difiere en {fmt_clp(diff)} del Balance_Consolidado oficial ({fmt_clp(total_oficial)}). "
                "La diferencia corresponde a propiedades cuyo 'Valor Balance'/'Valor Atribuible' venía en blanco en el Excel "
                "original y el dashboard completó aplicando la misma fórmula del resto de la tabla — ver Datos Pendientes."
            )
        )
    st.dataframe(
        format_display_df(
            br,
            currency_cols=("Avalúo Fiscal (CLP)", "Tasación Comercial (CLP)", "Valor Balance (CLP)", "Valor Atribuible (CLP)"),
            pct_cols=("% Participación",),
        ),
        use_container_width=True, hide_index=True, height=460,
    )

elif clase == "Empresas":
    emp = data.empresas
    st.markdown(
        f"**{len(emp)} sociedades** · Equity Value Estimado total {fmt_clp(emp['Equity Value Estimado (CLP)'].sum())} · "
        f"{(emp['Patrimonio Contable (CLP)'].isna()).sum()} sin Patrimonio Contable cargado (EEFF pendientes)"
    )
    st.dataframe(
        format_display_df(
            emp,
            currency_cols=("Patrimonio Contable (CLP)", "Equity Value Estimado (CLP)"),
            pct_cols=("% Participación (provisorio)",),
        ),
        use_container_width=True, hide_index=True, height=460,
    )
    st.page_link("pages/5_Empresas.py", label="Ver explorador de Empresas con semáforo de completitud →")

else:
    o = data.otras_partidas
    colA, colB, colC = st.columns(3)
    with colA:
        st.markdown(f"**Cuentas por Cobrar** (incluida en Activos) — {fmt_clp(o.cuentas_por_cobrar_subtotal)}")
        st.dataframe(format_display_df(o.cuentas_por_cobrar, currency_cols=("Monto (CLP)",)), use_container_width=True, hide_index=True)
    with colB:
        st.markdown(f"**Otros activos menores** (incluida en Activos) — {fmt_clp(o.otros_menores_subtotal)}")
        st.dataframe(format_display_df(o.otros_menores, currency_cols=("Monto (CLP)",)), use_container_width=True, hide_index=True)
    with colC:
        st.markdown(f"**Provisiones** (memo, NO incluida en Activos) — {fmt_clp(o.provisiones_subtotal_memo)}")
        st.dataframe(format_display_df(o.provisiones, currency_cols=("Monto (CLP)",)), use_container_width=True, hide_index=True)
