"""Builds a one-page executive summary PDF. Uses fpdf2's built-in core fonts (latin-1)
rather than bundling a TTF, so text is sanitized to latin-1-safe characters first —
keeps the export dependency-free and portable across environments."""

from __future__ import annotations

import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from src.data_loader import FOData
from src.kpi_engine import build_kpi_cards
from src.pending_data import scan_pending_data
from src.theme import fmt_clp, fmt_pct

_REPLACEMENTS = {
    "—": "-", "–": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "→": "->",
    "•": "-",
}


def _clean(text: str) -> str:
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


_STATUS_LABEL = {"verde": "VERDE", "amarillo": "AMARILLO", "rojo": "ROJO"}


def build_executive_summary_pdf(data: FOData) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 35, 64)
    pdf.cell(0, 10, _clean("Family Office - Resumen Ejecutivo"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 100, 115)
    pdf.cell(0, 6, _clean(f"Perimetro: nucleo familiar + hijos. Datos al {data.fecha_carga}."), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_text_color(20, 27, 38)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _clean("Balance Consolidado"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    rows = [
        ("Total Activos", fmt_clp(data.balance.total_activos)),
        ("Total Pasivos", fmt_clp(data.balance.total_pasivos)),
        ("Patrimonio Neto", fmt_clp(data.balance.patrimonio_neto)),
        ("Patrimonio Neto Ajustado (con contingentes)", fmt_clp(data.balance.patrimonio_neto_ajustado)),
    ]
    for label, value in rows:
        pdf.cell(110, 6, _clean(label))
        pdf.cell(0, 6, _clean(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _clean("Distribucion de Activos"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    for _, row in data.balance.distribucion_activos.iterrows():
        pdf.cell(90, 6, _clean(str(row["Clase de Activo"])))
        pdf.cell(60, 6, _clean(fmt_clp(row["Monto (CLP)"])))
        pdf.cell(0, 6, _clean(fmt_pct(row["% del Total"])), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _clean("KPIs"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    for card in build_kpi_cards(data):
        status = _STATUS_LABEL[card.status]
        pdf.cell(0, 6, _clean(f"[{status}] {card.label}: {card.display}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _clean("Datos Pendientes"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pending = scan_pending_data(data)
    alta = [p for p in pending if p.priority == "Alta"]
    pdf.cell(0, 6, _clean(f"{len(pending)} items pendientes detectados ({len(alta)} de prioridad alta)."), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    for item in alta[:8]:
        pdf.multi_cell(0, 5.5, _clean(f"- [{item.category}] {item.item}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 130, 145)
    pdf.cell(0, 5, _clean(f"Generado {datetime.datetime.now():%Y-%m-%d %H:%M}."), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
