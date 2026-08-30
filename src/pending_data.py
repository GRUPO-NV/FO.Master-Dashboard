"""Scans the parsed workbook for data-quality gaps and turns them into an actionable
checklist. This is one of the things the raw Excel cannot do for itself: the sheets
mark gaps in yellow for a human to notice, but nothing enumerates or prioritizes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from src.data_loader import FOData

Priority = Literal["Alta", "Media", "Baja"]
_PRIORITY_ORDER = {"Alta": 0, "Media": 1, "Baja": 2}


@dataclass
class PendingItem:
    priority: Priority
    category: str
    item: str
    detail: str
    amount_clp: float | None = None


def scan_pending_data(data: FOData) -> list[PendingItem]:
    items: list[PendingItem] = []

    if data.supuestos.get("tc_usd_clp") is None:
        items.append(PendingItem(
            "Alta", "Supuestos", "Tipo de cambio USD/CLP",
            "Falta cargar el tipo de cambio de referencia a la fecha de corte. Afecta cualquier posición valorizada en dólares.",
        ))

    liq = data.liquidez.detalle
    unconfirmed = liq[liq["Titular/Entidad"].astype(str).str.contains("verificar|sin identificar", case=False, na=False)]
    for _, row in unconfirmed.iterrows():
        items.append(PendingItem(
            "Alta", "Liquidez", f"Titular sin confirmar — {row['Cuenta/Instrumento']}",
            f"'{row['Titular/Entidad']}'. Monto CLP {row['Monto (CLP)']:,.0f}.".replace(",", "."),
            amount_clp=row["Monto (CLP)"],
        ))

    inv = data.inversiones.detalle
    unconfirmed_inv = inv[inv["Titular/Entidad"].astype(str).str.contains("verificar|asumido", case=False, na=False)]
    for _, row in unconfirmed_inv.iterrows():
        priority: Priority = "Alta" if (row["Monto (CLP)"] or 0) > 100_000_000 else "Media"
        items.append(PendingItem(
            priority, "Inversiones Financieras", f"Titular sin confirmar — {row['Cuenta/Instrumento']}",
            f"'{row['Titular/Entidad']}'. Monto CLP {row['Monto (CLP)']:,.0f}.".replace(",", "."),
            amount_clp=row["Monto (CLP)"],
        ))

    br = data.bienes_raices
    sin_dato = br[br["Fuente valor usado"] == "Sin dato (pendiente)"]
    for _, row in sin_dato.iterrows():
        items.append(PendingItem(
            "Alta", "Bienes Raíces", f"Sin Avalúo ni Tasación — {row['Dirección']}",
            "No hay Avalúo Fiscal ni Tasación Comercial cargados; el valor de esta propiedad no está incluido en ningún total.",
        ))

    proxy = br[br["Fuente valor usado"] == "Avalúo Fiscal x factor (proxy)"]
    if not proxy.empty:
        items.append(PendingItem(
            "Media", "Bienes Raíces", f"{len(proxy)} propiedades valorizadas con proxy (Avalúo Fiscal x {data.supuestos['factor_tasacion']:.2f})",
            "Usan Avalúo Fiscal × factor de Supuestos en vez de una Tasación Comercial real. Cargar tasaciones reales cuando estén disponibles.",
            amount_clp=proxy["Valor Balance (CLP)"].sum(),
        ))

    pct_sin_confirmar = br[~br["% Participación confirmado"]]
    for _, row in pct_sin_confirmar.iterrows():
        items.append(PendingItem(
            "Media", "Bienes Raíces", f"% Participación no confirmado — {row['Dirección']}",
            "Se asumió 100% de participación familiar por defecto; confirmar si es copropiedad.",
        ))

    completed_by_dashboard = br[br["Dirección"].isin(["Cementerio Zapallar", "Pichilemu av. Punta lobos"])]
    for _, row in completed_by_dashboard.iterrows():
        items.append(PendingItem(
            "Baja", "Bienes Raíces", f"Valor Atribuible completado automáticamente — {row['Dirección']}",
            f"El Excel original dejó 'Valor Balance'/'Valor Atribuible' en blanco; el dashboard lo calculó aplicando la misma fórmula del resto de la tabla (CLP {row['Valor Atribuible (CLP)']:,.0f}). Confirmar con el family office.".replace(",", "."),
            amount_clp=row["Valor Atribuible (CLP)"],
        ))

    emp = data.empresas
    no_rut = emp[~emp["RUT confirmado"]]
    if not no_rut.empty:
        items.append(PendingItem(
            "Media" if len(no_rut) <= 1 else "Alta", "Empresas", f"{len(no_rut)} empresa(s) con RUT sin confirmar",
            ", ".join(no_rut["Empresa"].tolist()),
        ))

    no_pct = emp[emp["% Participación (provisorio)"].isna()]
    if not no_pct.empty:
        items.append(PendingItem(
            "Alta", "Empresas", f"{len(no_pct)} empresas sin ningún % de participación (ni provisorio)",
            ", ".join(no_pct["Empresa"].tolist()),
        ))

    no_patrimonio = emp[emp["Patrimonio Contable (CLP)"].isna()]
    if not no_patrimonio.empty:
        items.append(PendingItem(
            "Alta", "Empresas", f"{len(no_patrimonio)} de {len(emp)} empresas sin Patrimonio Contable (EEFF no cargados)",
            "El Equity Value Estimado de estas empresas es $0 hasta que se carguen sus Estados Financieros. El Patrimonio Neto real del grupo es mayor a la cifra mostrada.",
        ))

    items.append(PendingItem(
        "Alta", "Flujo de Caja", "Saldo Acumulado mensual reconstruido",
        "La fila 'Saldo Acumulado' venía vacía en el archivo fuente para el detalle mensual. El dashboard la reconstruyó como suma acumulada del Saldo Mensual, anclada al valor conocido de la tabla Resumen Anual (oct-2026). Verificar contra el modelo original antes de tomar decisiones de caja.",
    ))

    egresos = data.flujo_caja.egresos
    materiality_floor = 50_000_000
    for concepto, serie in egresos.iterrows():
        if concepto.strip().lower() == "efecto inflacion":
            continue  # aggregate adjustment line, not a discrete expense — naturally trends up
        serie = serie.fillna(0)
        max_val = serie.max()
        if max_val < materiality_floor:
            continue
        baseline_vals = serie[(serie > 0) & (serie < max_val)]
        baseline = baseline_vals.median() if not baseline_vals.empty else 0.0
        if baseline > 0 and max_val < 5 * baseline:
            continue
        mes_pico = serie.idxmax()
        max_fmt = f"{max_val:,.0f}".replace(",", ".")
        baseline_fmt = f"{baseline:,.0f}".replace(",", ".")
        items.append(PendingItem(
            "Alta", "Flujo de Caja", f"Egreso atípico — '{concepto.strip()}' en {mes_pico:%b-%Y}",
            f"CLP {max_fmt} en un solo mes, muy por encima de los demás meses de esta misma línea "
            f"(resto de meses no nulos: mediana CLP {baseline_fmt}). Confirmar si es un compromiso de caja real "
            "(ej. compra de propiedad) o un error de carga antes de usarlo para decisiones de liquidez.",
            amount_clp=max_val,
        ))

    pasivos_extra = {"Interbodegas SPA", "Inversiones Meme Ltda"}
    empresas_set = set(emp["Empresa"].str.strip())
    faltantes = [p for p in data.pasivos["Empresa"] if p not in empresas_set]
    if faltantes:
        items.append(PendingItem(
            "Media", "Pasivos / Empresas", "Registro societario incompleto",
            f"{len(faltantes)} sociedades con deuda de patentes no figuran en el listado de {len(emp)} empresas: {', '.join(faltantes)}.",
        ))

    items.sort(key=lambda i: _PRIORITY_ORDER[i.priority])
    return items


def pending_data_df(data: FOData) -> pd.DataFrame:
    items = scan_pending_data(data)
    return pd.DataFrame([
        {
            "Prioridad": i.priority,
            "Categoría": i.category,
            "Ítem": i.item,
            "Detalle": i.detail,
            "Monto (CLP)": i.amount_clp,
        }
        for i in items
    ])
