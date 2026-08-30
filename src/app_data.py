"""Streamlit-facing cache wrapper around data_loader.

The cache key is the source workbook's modification time: if someone edits
FO_Master_Consolidado.xlsx and drops a new copy in data/, the very next Streamlit
rerun (a widget interaction, or a manual browser refresh) sees a changed mtime,
misses the cache, and triggers a fresh LibreOffice recalculation automatically —
no separate watcher process needed.
"""

from __future__ import annotations

import streamlit as st

from src.data_loader import DATA_DIR, FOData, load_fo_data
from src.snapshots import record_snapshot


@st.cache_data(show_spinner="Recalculando fórmulas y cargando el archivo maestro...")
def _load_cached(_mtime: float) -> FOData:
    result = load_fo_data()
    record_snapshot(result)
    return result


def get_data() -> FOData:
    raw_path = DATA_DIR / "FO_Master_Consolidado.xlsx"
    if not raw_path.exists():
        st.error(
            f"No se encontró el archivo fuente en `{raw_path}`. "
            "Copia FO_Master_Consolidado.xlsx dentro de la carpeta `data/` del proyecto."
        )
        st.stop()
    return _load_cached(raw_path.stat().st_mtime)
