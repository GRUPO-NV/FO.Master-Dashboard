"""Persists one row per distinct version of FO_Master_Consolidado.xlsx so the
dashboard can chart how Patrimonio Neto evolves over time, not just show today's
snapshot. A new row is appended automatically whenever the workbook is reloaded with
a modification time not already recorded — no manual step required."""

from __future__ import annotations

import csv
import datetime
from pathlib import Path

import pandas as pd

from src.data_loader import DATA_DIR, FOData

SNAPSHOT_PATH = DATA_DIR / "snapshots.csv"
_COLUMNS = ["fecha_carga", "total_activos", "total_pasivos", "patrimonio_neto", "patrimonio_neto_ajustado"]


def record_snapshot(data: FOData) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = load_snapshots()
    if not existing.empty and data.fecha_carga in existing["fecha_carga"].astype(str).values:
        return
    is_new_file = not SNAPSHOT_PATH.exists()
    with open(SNAPSHOT_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(_COLUMNS)
        writer.writerow([
            data.fecha_carga,
            data.balance.total_activos,
            data.balance.total_pasivos,
            data.balance.patrimonio_neto,
            data.balance.patrimonio_neto_ajustado,
        ])


def load_snapshots() -> pd.DataFrame:
    if not SNAPSHOT_PATH.exists():
        return pd.DataFrame(columns=_COLUMNS)
    df = pd.read_csv(SNAPSHOT_PATH)
    df["fecha_carga"] = pd.to_datetime(df["fecha_carga"])
    return df.sort_values("fecha_carga")
