"""Scenario simulator — the dashboard's main value-add over the static Excel.

Models a simple, transparent leveraged-reallocation strategy: borrow against Bienes
Raíces at a given loan-to-value, redeploy the proceeds into a new position that
compounds at a chosen return, and pay the debt's interest out of cash flow each year
(interest-only, not capitalized). With leverage_pct = 0 this reduces exactly to the
weighted-return projection already used by the workbook's own KPI sheet — which is
also how the model is validated (see tests inline in load_fo_data usage / README).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.data_loader import FOData


@dataclass
class ScenarioInputs:
    leverage_pct: float  # 0..1, fraction of Bienes Raíces value drawn as new debt
    cost_of_debt: float  # annual interest rate on the new debt
    return_on_deployed_capital: float  # annual return earned by the redeployed capital
    horizon_years: int  # 1..10


@dataclass
class ScenarioResult:
    base_patrimonio_neto: float
    base_weighted_return: float
    debt_drawn: float
    path_base: list[float]  # patrimonio neto per year, no leverage, years 0..horizon
    path_leveraged: list[float]  # patrimonio neto per year, with leverage, years 0..horizon
    patrimonio_neto_final_base: float
    patrimonio_neto_final_leveraged: float
    cagr_base: float
    cagr_leveraged: float


def base_weighted_return(data: FOData) -> float:
    """Weighted-average expected return across return-bearing asset classes, using
    current balances and the rates in Supuestos. Reproduces the workbook's own
    'CAGR implícito del patrimonio' KPI exactly when nothing else changes."""
    b = data.balance
    total_activos = b.total_activos
    dist = b.distribucion_activos.set_index("Clase de Activo")["Monto (CLP)"]
    rates = {
        "Liquidez": data.supuestos["retorno_liquidez"],
        "Inversiones Financieras": data.supuestos["retorno_inversiones"],
        "Bienes Raíces": data.supuestos["retorno_bienes_raices"],
        "Empresas (Equity)": data.supuestos["retorno_empresas"],
    }
    weighted = sum(dist.get(cls, 0.0) * rate for cls, rate in rates.items())
    return weighted / total_activos


def run_scenario(data: FOData, inputs: ScenarioInputs) -> ScenarioResult:
    pn0 = data.balance.patrimonio_neto
    w = base_weighted_return(data)
    valor_br = data.balance.distribucion_activos.set_index("Clase de Activo")["Monto (CLP)"].get("Bienes Raíces", 0.0)
    debt = inputs.leverage_pct * valor_br

    path_base = [pn0 * (1 + w) ** t for t in range(inputs.horizon_years + 1)]
    path_leveraged = [
        pn0 * (1 + w) ** t
        + debt * ((1 + inputs.return_on_deployed_capital) ** t - 1)
        - debt * inputs.cost_of_debt * t
        for t in range(inputs.horizon_years + 1)
    ]

    pn_final_base = path_base[-1]
    pn_final_lev = path_leveraged[-1]
    cagr_base = (pn_final_base / pn0) ** (1 / inputs.horizon_years) - 1 if inputs.horizon_years else 0.0
    cagr_lev = (pn_final_lev / pn0) ** (1 / inputs.horizon_years) - 1 if inputs.horizon_years else 0.0

    return ScenarioResult(
        base_patrimonio_neto=pn0,
        base_weighted_return=w,
        debt_drawn=debt,
        path_base=path_base,
        path_leveraged=path_leveraged,
        patrimonio_neto_final_base=pn_final_base,
        patrimonio_neto_final_leveraged=pn_final_lev,
        cagr_base=cagr_base,
        cagr_leveraged=cagr_lev,
    )


def required_cagr_for_goal(multiple: float, horizon_years: int) -> float:
    """CAGR needed to multiply patrimonio neto by `multiple` over `horizon_years`."""
    if horizon_years <= 0:
        return 0.0
    return multiple ** (1 / horizon_years) - 1


def solve_leverage_for_target(
    data: FOData,
    target_cagr: float,
    cost_of_debt: float,
    return_on_deployed_capital: float,
    horizon_years: int,
    max_leverage: float = 0.8,
) -> float | None:
    """Bisects leverage_pct in [0, max_leverage] to hit target_cagr, holding the other
    scenario inputs fixed. Returns None if the target is unreachable within bounds
    (e.g. return_on_deployed_capital <= cost_of_debt makes leverage counterproductive)."""
    def cagr_at(leverage: float) -> float:
        result = run_scenario(data, ScenarioInputs(leverage, cost_of_debt, return_on_deployed_capital, horizon_years))
        return result.cagr_leveraged

    lo, hi = 0.0, max_leverage
    cagr_lo, cagr_hi = cagr_at(lo), cagr_at(hi)
    if target_cagr <= cagr_lo:
        return 0.0
    if cagr_hi < target_cagr:
        return None

    for _ in range(40):
        mid = (lo + hi) / 2
        if cagr_at(mid) < target_cagr:
            lo = mid
        else:
            hi = mid
    return hi
