"""Recalculates FO_Master_Consolidado.xlsx with LibreOffice headless before it is read.

The source workbook can be edited by hand, which leaves formula cells without a
cached result (openpyxl with data_only=True would then read them as None). LibreOffice
headless opens the file, recalculates every formula, and re-saves it. We only pay that
cost when the source file's modification time has changed since the last recalculation.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

RAW_FILENAME = "FO_Master_Consolidado.xlsx"
RECALC_SUBDIR = "_recalculated"


class RecalcError(RuntimeError):
    pass


def _paths(data_dir: Path) -> tuple[Path, Path, Path]:
    raw_path = data_dir / RAW_FILENAME
    recalc_dir = data_dir / RECALC_SUBDIR
    recalc_path = recalc_dir / RAW_FILENAME
    return raw_path, recalc_dir, recalc_path


def is_recalculated_fresh(data_dir: Path) -> bool:
    raw_path, _recalc_dir, recalc_path = _paths(data_dir.resolve())
    if not recalc_path.exists():
        return False
    return recalc_path.stat().st_mtime >= raw_path.stat().st_mtime


def ensure_recalculated(data_dir: Path, force: bool = False) -> Path:
    """Return the path to a freshly-recalculated copy of the source workbook.

    Recalculation is skipped when the cached copy is already newer than the source
    file, so repeated calls (e.g. on every Streamlit rerun) are cheap.
    """
    raw_path, recalc_dir, recalc_path = _paths(data_dir.resolve())
    if not raw_path.exists():
        raise RecalcError(f"No se encontró el archivo fuente: {raw_path}")

    if not force and is_recalculated_fresh(data_dir):
        return recalc_path

    recalc_dir.mkdir(parents=True, exist_ok=True)
    if recalc_path.exists():
        recalc_path.unlink()

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        raise RecalcError(
            "No se encontró LibreOffice (soffice). Instálalo para poder recalcular "
            "fórmulas antes de leer el Excel: apt-get install libreoffice-calc"
        )

    profile_dir = (recalc_dir / ".lo_profile").resolve()
    cmd = [
        soffice,
        "--headless",
        "--norestore",
        f"-env:UserInstallation=file://{profile_dir.as_posix()}",
        "--convert-to",
        "xlsx",
        "--outdir",
        str(recalc_dir),
        str(raw_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 or not recalc_path.exists():
        raise RecalcError(
            "LibreOffice no pudo recalcular el archivo.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return recalc_path
