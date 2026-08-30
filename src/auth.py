"""Minimal shared-password gate.

Streamlit Community Cloud's free tier has no built-in access control — any deployed
app is reachable by anyone with the URL. Since this dashboard shows a family's
patrimonial data, every page calls require_password() before rendering anything else.
The password lives in Streamlit secrets (dashboard_password), never in the repo.
"""

from __future__ import annotations

import streamlit as st


def require_password() -> None:
    if st.session_state.get("fo_authenticated"):
        return

    expected = st.secrets.get("dashboard_password")
    if not expected:
        # No password configured (e.g. local dev without secrets.toml) — don't lock
        # out local usage, but make it obvious this must be set before any shared
        # deployment.
        st.warning(
            "No hay `dashboard_password` configurado en `st.secrets` — el dashboard está "
            "abierto sin clave. Configúralo antes de compartir la URL.",
            icon="⚠️",
        )
        st.session_state["fo_authenticated"] = True
        return

    st.title("Family Office — Acceso")
    with st.form("fo_login"):
        entered = st.text_input("Clave de acceso", type="password")
        submitted = st.form_submit_button("Entrar")
    if submitted:
        if entered == expected:
            st.session_state["fo_authenticated"] = True
            st.rerun()
        else:
            st.error("Clave incorrecta.")
    st.stop()
