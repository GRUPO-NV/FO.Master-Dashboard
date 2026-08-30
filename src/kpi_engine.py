"""Turns the parsed KPI figures into semaphore-scored cards for the dashboard.

Thresholds are documented next to each rule so a CIO can audit or tune them; they are
not hidden inside formatting code. Values are read straight from FOData (which mirrors
the workbook's own KPIs sheet) so figures never drift from the source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.data_loader import FOData

Status = Literal["verde", "amarillo", "rojo"]


@dataclass
class KPICard:
    section: str
    label: str
    value: float | None
    display: str
    status: Status
    note: str


def _get(df, label_substr: str, col: str = "Valor"):
    match = df[df["KPI"].str.contains(label_substr, case=False, na=False, regex=False)]
    if match.empty:
        return None
    return match.iloc[0][col]


def _pct(v: float | None) -> str:
    return "s/d" if v is None else f"{v * 100:.1f}%"


def _clp(v: float | None) -> str:
    if v is None:
        return "s/d"
    return f"${v:,.0f}".replace(",", ".")


def _months(v: float | None) -> str:
    return "s/d" if v is None else f"{v:.1f} meses"


def _ratio(v: float | None) -> str:
    return "s/d" if v is None else f"{v:.2f}x"


def _threshold(value: float | None, green_if_below: float, red_if_above: float, invert: bool = False) -> Status:
    """green_if_below / red_if_above define an amarillo band between them.

    invert=True means higher is better (e.g. coverage ratios) instead of lower is
    better (e.g. leverage, concentration).
    """
    if value is None:
        return "amarillo"
    if invert:
        if value >= red_if_above:
            return "verde"
        if value <= green_if_below:
            return "rojo"
        return "amarillo"
    if value <= green_if_below:
        return "verde"
    if value >= red_if_above:
        return "rojo"
    return "amarillo"


def build_kpi_cards(data: FOData) -> list[KPICard]:
    kpis = data.kpis_raw
    a, b, c, d = kpis["balance_estructura"], kpis["liquidez_cobertura"], kpis["rentabilidad_crecimiento"], kpis["riesgo_concentracion"]

    cards: list[KPICard] = []

    apalancamiento = _get(a, "Apalancamiento")
    cards.append(KPICard(
        "Balance y Estructura", "Apalancamiento (Pasivos / Activos)", apalancamiento, _pct(apalancamiento),
        _threshold(apalancamiento, green_if_below=0.10, red_if_above=0.30),
        "Verde bajo 10%, rojo sobre 30% — patrimonio con deuda mínima hoy.",
    ))

    concentracion_inmobiliaria = _get(a, "concentración inmobiliaria")
    cards.append(KPICard(
        "Balance y Estructura", "Concentración en Bienes Raíces", concentracion_inmobiliaria, _pct(concentracion_inmobiliaria),
        _threshold(concentracion_inmobiliaria, green_if_below=0.60, red_if_above=0.80),
        "Umbral del cliente: sobre 60% se considera alta concentración para un family office.",
    ))

    concentracion_empresas = _get(a, "patrimonio en Empresas")
    cards.append(KPICard(
        "Balance y Estructura", "Concentración en Empresas (equity)", concentracion_empresas, _pct(concentracion_empresas),
        _threshold(concentracion_empresas, green_if_below=0.60, red_if_above=0.80),
        "Subestimado hoy: la mayoría de las 34 empresas no tienen EEFF cargados.",
    ))

    mayor_propiedad = _get(a, "mayor propiedad")
    cards.append(KPICard(
        "Balance y Estructura", "Concentración — mayor propiedad individual", mayor_propiedad, _pct(mayor_propiedad),
        _threshold(mayor_propiedad, green_if_below=0.10, red_if_above=0.25),
        "Peso de la propiedad más grande sobre el Total de Activos.",
    ))

    cobertura_gasto = _get(b, "Cobertura de gasto mensual")
    cards.append(KPICard(
        "Liquidez y Cobertura", "Cobertura de gasto mensual (Ingresos/Egresos)", cobertura_gasto, _ratio(cobertura_gasto),
        _threshold(cobertura_gasto, green_if_below=1.0, red_if_above=1.2, invert=True),
        "Bajo 1.0x el flujo operacional no cubre el gasto y se financia con activos.",
    ))

    meses_liquidez = _get(b, "Meses de gasto cubiertos")
    cards.append(KPICard(
        "Liquidez y Cobertura", "Meses de liquidez pura", meses_liquidez, _months(meses_liquidez),
        _threshold(meses_liquidez, green_if_below=3, red_if_above=3, invert=True),
        "Umbral del cliente: bajo 3 meses de cobertura es zona roja.",
    ))

    peor_saldo = _get(b, "Peor Saldo Acumulado")
    cards.append(KPICard(
        "Liquidez y Cobertura", "Peor Saldo Acumulado proyectado (10 años)", peor_saldo, _clp(peor_saldo),
        "rojo" if (peor_saldo or 0) < 0 else "verde",
        "Punto más bajo de caja acumulada proyectada — revisar si es un compromiso real o artefacto del modelo.",
    ))

    hhi = _get(d, "Índice de concentración")
    cards.append(KPICard(
        "Riesgo y Concentración", "Índice HHI (por clase de activo)", hhi, f"{hhi:.3f}" if hhi is not None else "s/d",
        _threshold(hhi, green_if_below=0.35, red_if_above=0.50),
        "1.0 = todo en una clase; 0.25 = perfectamente diversificado entre 4 clases.",
    ))

    contingentes_pct = _get(d, "Activos Contingentes")
    cards.append(KPICard(
        "Riesgo y Concentración", "Activos Contingentes / Patrimonio Neto", contingentes_pct, _pct(contingentes_pct),
        _threshold(contingentes_pct, green_if_below=0.05, red_if_above=0.15),
        "Cuentas por cobrar en disputa/litigio, fuera del Patrimonio Neto principal.",
    ))

    cagr = c[c["KPI"].str.contains("CAGR", case=False, na=False)]
    cagr_1y = float(cagr.iloc[0]["1 año"]) if not cagr.empty else None
    cards.append(KPICard(
        "Rentabilidad y Crecimiento", "CAGR implícito del patrimonio", cagr_1y, _pct(cagr_1y),
        _threshold(cagr_1y, green_if_below=0.03, red_if_above=0.06, invert=True),
        "Retorno ponderado por peso de cada clase de activo según Supuestos.",
    ))

    return cards


def cards_by_section(data: FOData) -> dict[str, list[KPICard]]:
    out: dict[str, list[KPICard]] = {}
    for card in build_kpi_cards(data):
        out.setdefault(card.section, []).append(card)
    return out
