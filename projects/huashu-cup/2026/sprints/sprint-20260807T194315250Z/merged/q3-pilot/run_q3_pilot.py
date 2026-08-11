"""Q3 storage-dispatch pilot on the supplied HuaShu Cup C data.

The script is deliberately self-contained and writes only beside this file. It
uses a deterministic MILP for short and full-cycle windows, with a no-storage
renewable-first dispatch as the same-class baseline. Formal claims are owned by
the root agent; this directory is exploratory evidence only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


SPRINT_ID = "sprint-20260807T194315250Z"
TASK_ID = "q3-pilot"
ATTEMPT = 1
SEED = 20260801
TOL = 1e-6
# Bounded 24-hour MILP evidence. Longer configurations remain deferred
# scalability probes and are not part of this frozen pilot.
HORIZONS = (24,)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dir_fingerprint(path: Path) -> str:
    source = "\n".join(
        f"{item.relative_to(path).as_posix()}:{sha256_file(item)}"
        for item in sorted(path.rglob("*"))
        if item.is_file()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def fingerprint(root: Path, value: str) -> dict[str, Any]:
    path = root / value
    if path.is_file():
        return {"path": value, "kind": "file", "exists": True, "sha256": sha256_file(path)}
    if path.is_dir():
        return {"path": value, "kind": "directory", "exists": True, "sha256": dir_fingerprint(path)}
    return {"path": value, "kind": "missing", "exists": False, "sha256": None}


def json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def finite(value: float | int | np.number | None) -> float | None:
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def build_baseline(region_df: pd.DataFrame, storage: pd.Series) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    export_limit = float(min(storage["SellLimit_MW"], storage["MaxGridExport_MW"]))
    import_limit = float(storage["MaxGridImport_MW"])
    initial_soc = float(storage["InitialSOC_MWh"])
    for row in region_df.sort_values("Hour").itertuples(index=False):
        load = float(row.Total_Load_MW)
        renewable = float(row.AvailableRenewable_MW)
        # Comparable no-storage baseline: allocate all physically available
        # renewable generation to load first. Observed UsedRenewable_MW is an
        # upstream operating outcome and must not create a policy mismatch.
        renewable_to_load = min(load, renewable)
        grid_load = max(load - renewable_to_load, 0.0)
        surplus = max(renewable - renewable_to_load, 0.0)
        sell = min(surplus, export_limit)
        curtail = max(surplus - sell, 0.0)
        rows.append(
            {
                "Hour": int(row.Hour),
                "Region": str(row.Region),
                "AvailableRenewable_MW": renewable,
                "Total_Load_MW": load,
                "ElectricityPrice_CNY_per_MWh": float(row.ElectricityPrice_CNY_per_MWh),
                "SellPrice_CNY_per_MWh": float(row.SellPrice_CNY_per_MWh),
                "CarbonIntensity_tCO2_per_MWh": float(row.CarbonIntensity_tCO2_per_MWh),
                "ChargePower_MW": 0.0,
                "DischargePower_MW": 0.0,
                "SOC_MWh": initial_soc,
                "RenewableToLoad_MW": renewable_to_load,
                "RenewableCharge_MW": 0.0,
                "GridCharge_MW": 0.0,
                # GridPurchase is total grid purchase; keep the load-side
                # component separately for the energy-balance audit.
                "GridPurchase_MW": grid_load,
                "GridLoadPurchase_MW": grid_load,
                "GridSell_MW": sell,
                "Curtailment_MW": curtail,
                "NetGridImport_MW": grid_load - sell,
                "GridEnergyForCost_MW": grid_load,
            }
        )
        if grid_load > import_limit + 1e-5:
            raise ValueError(f"baseline import cap infeasible at hour {row.Hour}, {row.Region}")
    return pd.DataFrame(rows)


def make_model(region_df: pd.DataFrame, storage: pd.Series, baseline: pd.DataFrame) -> tuple[np.ndarray, Bounds, LinearConstraint, np.ndarray, dict[str, slice]]:
    data = region_df.sort_values("Hour").reset_index(drop=True)
    horizon = len(data)
    max_charge = float(storage["MaxChargePower_MW"])
    max_discharge = float(storage["MaxDischargePower_MW"])
    capacity = float(storage["StorageCapacity_MWh"])
    min_soc = float(storage["MinSOC_MWh"])
    initial_soc = float(storage["InitialSOC_MWh"])
    import_limit = float(storage["MaxGridImport_MW"])
    export_limit = float(min(storage["SellLimit_MW"], storage["MaxGridExport_MW"]))
    eta_c = float(storage["ChargeEfficiency"])
    eta_d = float(storage["DischargeEfficiency"])

    # c,d,soc,renewable-to-load,renewable-charge,grid-charge,grid-load,sell,curtail,z plus peak.
    names = ["charge", "discharge", "soc", "renewable_to_load", "renewable_charge", "grid_charge", "grid_load", "sell", "curtail", "mode"]
    slices: dict[str, slice] = {}
    cursor = 0
    for name in names:
        slices[name] = slice(cursor, cursor + horizon)
        cursor += horizon
    peak_index = cursor
    nvar = cursor + 1

    prices = data["ElectricityPrice_CNY_per_MWh"].to_numpy(float)
    sell_prices = data["SellPrice_CNY_per_MWh"].to_numpy(float)
    carbon_intensity = data["CarbonIntensity_tCO2_per_MWh"].to_numpy(float)
    loads = data["Total_Load_MW"].to_numpy(float)
    renewables = data["AvailableRenewable_MW"].to_numpy(float)

    # Normalized objective: carbon-aware dispatch with a small peak/import term.
    base_cost = max(float(baseline["GridEnergyForCost_MW"].to_numpy().dot(prices) - baseline["GridSell_MW"].to_numpy().dot(sell_prices)), 1.0)
    base_carbon = max(float(baseline["GridEnergyForCost_MW"].to_numpy().dot(carbon_intensity)), 1.0)
    base_peak = max(float(baseline["NetGridImport_MW"].max()), 1.0)
    cvec = np.zeros(nvar)
    cvec[slices["grid_load"]] = prices / base_cost
    cvec[slices["grid_charge"]] = prices / base_cost
    cvec[slices["sell"]] = -sell_prices / base_cost
    cvec[slices["grid_load"]] += 0.35 * carbon_intensity / base_carbon
    cvec[slices["grid_charge"]] += 0.35 * carbon_intensity / base_carbon
    cvec[peak_index] = 0.08 / base_peak
    cvec[slices["curtail"]] = 0.03 / max(float(renewables.sum()), 1.0)
    # Prevent the full-cycle LP scalability probe from consuming renewable
    # energy through artificial same-hour cycling. The coefficient is small
    # relative to cost/carbon terms and is recorded in the manifest.
    cvec[slices["charge"]] += 1e-7
    cvec[slices["discharge"]] += 1e-7

    lower = np.zeros(nvar)
    upper = np.full(nvar, np.inf)
    for name, lo, hi in [
        ("charge", 0.0, max_charge),
        ("discharge", 0.0, max_discharge),
        ("soc", min_soc, capacity),
        ("renewable_to_load", 0.0, np.inf),
        ("renewable_charge", 0.0, max_charge),
        ("grid_charge", 0.0, max_charge),
        ("grid_load", 0.0, import_limit),
        ("sell", 0.0, export_limit),
        ("curtail", 0.0, np.inf),
        ("mode", 0.0, 1.0),
    ]:
        lower[slices[name]] = lo
        upper[slices[name]] = hi
    lower[peak_index] = 0.0
    upper[peak_index] = import_limit + max_charge
    bounds = Bounds(lower, upper)

    # Equality rows: SOC transition, split charge, renewable balance, load balance.
    eq_rows = 4 * horizon
    ub_rows = 3 * horizon + 1
    matrix = lil_matrix((eq_rows + ub_rows, nvar), dtype=float)
    row_lower = np.empty(eq_rows + ub_rows)
    row_upper = np.empty(eq_rows + ub_rows)
    row = 0
    for t in range(horizon):
        # soc[t] - eta_c*c[t] + d[t]/eta_d = initial_soc (t=0), 0 otherwise.
        matrix[row, slices["soc"].start + t] = 1.0
        matrix[row, slices["charge"].start + t] = -eta_c
        matrix[row, slices["discharge"].start + t] = 1.0 / eta_d
        rhs = initial_soc if t == 0 else 0.0
        if t > 0:
            matrix[row, slices["soc"].start + t - 1] = -1.0
        row_lower[row] = rhs
        row_upper[row] = rhs
        row += 1

        matrix[row, slices["charge"].start + t] = 1.0
        matrix[row, slices["renewable_charge"].start + t] = -1.0
        matrix[row, slices["grid_charge"].start + t] = -1.0
        row_lower[row] = 0.0
        row_upper[row] = 0.0
        row += 1

        matrix[row, slices["renewable_to_load"].start + t] = 1.0
        matrix[row, slices["renewable_charge"].start + t] = 1.0
        matrix[row, slices["sell"].start + t] = 1.0
        matrix[row, slices["curtail"].start + t] = 1.0
        row_lower[row] = renewables[t]
        row_upper[row] = renewables[t]
        row += 1

        # Charging has its own renewable/grid source split above. Facility
        # demand is met only by direct renewable, storage discharge and grid.
        matrix[row, slices["renewable_to_load"].start + t] = 1.0
        matrix[row, slices["discharge"].start + t] = 1.0
        matrix[row, slices["grid_load"].start + t] = 1.0
        row_lower[row] = loads[t]
        row_upper[row] = loads[t]
        row += 1

    for t in range(horizon):
        # Peak epigraph for net grid import (grid-to-load + grid-to-storage - export).
        matrix[row, slices["grid_load"].start + t] = 1.0
        matrix[row, slices["grid_charge"].start + t] = 1.0
        matrix[row, slices["sell"].start + t] = -1.0
        matrix[row, peak_index] = -1.0
        row_lower[row] = -np.inf
        row_upper[row] = 0.0
        row += 1

        # Charge/discharge mode disjunction.
        matrix[row, slices["charge"].start + t] = 1.0
        matrix[row, slices["mode"].start + t] = -max_charge
        row_lower[row] = -np.inf
        row_upper[row] = 0.0
        row += 1

        matrix[row, slices["discharge"].start + t] = 1.0
        matrix[row, slices["mode"].start + t] = max_discharge
        row_lower[row] = -np.inf
        row_upper[row] = max_discharge
        row += 1

    # Use a cyclic terminal boundary so the comparison is not rewarded or
    # penalized for leaving energy in storage after the window.
    matrix[row, slices["soc"].start + horizon - 1] = 1.0
    row_lower[row] = initial_soc
    row_upper[row] = initial_soc

    constraints = LinearConstraint(matrix.tocsr(), row_lower, row_upper)
    integrality = np.zeros(nvar)
    integrality[slices["mode"]] = 1.0
    return cvec, bounds, constraints, integrality, slices


def solve_region(region_df: pd.DataFrame, storage: pd.Series, horizon: int, baseline: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    window = region_df.sort_values("Hour").head(horizon).reset_index(drop=True)
    base_window = baseline.head(horizon).reset_index(drop=True)
    objective, bounds, constraints, integrality, slices = make_model(window, storage, base_window)
    started = time.perf_counter()
    full_cycle_relaxation = horizon >= 2407
    solver_integrality = np.zeros_like(integrality) if full_cycle_relaxation else integrality
    result = milp(
        c=objective,
        integrality=solver_integrality,
        bounds=bounds,
        constraints=constraints,
        options={"presolve": True, "time_limit": 20.0, "mip_rel_gap": 1e-7},
    )
    runtime = time.perf_counter() - started
    if not result.success or result.x is None:
        return pd.DataFrame(), {
            "status": str(result.message),
            "success": False,
            "runtime_s": runtime,
            "mip_gap": finite(getattr(result, "mip_gap", None)),
            "objective": finite(getattr(result, "fun", None)),
            "solver_mode": "LP_full_cycle_scalability_probe" if full_cycle_relaxation else "binary_MILP",
        }
    x = result.x
    data = window
    charge = x[slices["charge"]]
    discharge = x[slices["discharge"]]
    soc = x[slices["soc"]]
    renewable_to_load = x[slices["renewable_to_load"]]
    renewable_charge = x[slices["renewable_charge"]]
    grid_charge = x[slices["grid_charge"]]
    grid_load = x[slices["grid_load"]]
    sell = x[slices["sell"]]
    curtail = x[slices["curtail"]]
    net_import = grid_load + grid_charge - sell
    out = pd.DataFrame(
        {
            "Hour": data["Hour"].astype(int),
            "Region": data["Region"].astype(str),
            "AvailableRenewable_MW": data["AvailableRenewable_MW"].astype(float),
            "Total_Load_MW": data["Total_Load_MW"].astype(float),
            "ElectricityPrice_CNY_per_MWh": data["ElectricityPrice_CNY_per_MWh"].astype(float),
            "SellPrice_CNY_per_MWh": data["SellPrice_CNY_per_MWh"].astype(float),
            "CarbonIntensity_tCO2_per_MWh": data["CarbonIntensity_tCO2_per_MWh"].astype(float),
            "ChargePower_MW": charge,
            "DischargePower_MW": discharge,
            "SOC_MWh": soc,
            "RenewableToLoad_MW": renewable_to_load,
            "RenewableCharge_MW": renewable_charge,
            "GridCharge_MW": grid_charge,
            "GridPurchase_MW": grid_load + grid_charge,
            "GridLoadPurchase_MW": grid_load,
            "GridSell_MW": sell,
            "Curtailment_MW": curtail,
            "NetGridImport_MW": net_import,
            "GridEnergyForCost_MW": grid_load + grid_charge,
            "ChargeMode": np.rint(x[slices["mode"]]).astype(int),
        }
    )
    return out, {
        "status": str(result.message),
        "success": True,
        "runtime_s": runtime,
        "mip_gap": finite(getattr(result, "mip_gap", None)),
        "objective": finite(getattr(result, "fun", None)),
        "mip_node_count": int(getattr(result, "mip_node_count", 0) or 0),
        "solver_mode": "LP_full_cycle_scalability_probe" if full_cycle_relaxation else "binary_MILP",
    }


def metrics(dispatch: pd.DataFrame, storage: pd.Series, method: str, horizon: int, solver: dict[str, Any]) -> dict[str, Any]:
    price = dispatch["ElectricityPrice_CNY_per_MWh"].to_numpy(float)
    sell_price = dispatch["SellPrice_CNY_per_MWh"].to_numpy(float)
    ci = dispatch["CarbonIntensity_tCO2_per_MWh"].to_numpy(float)
    grid = dispatch["GridPurchase_MW"].to_numpy(float)
    sell = dispatch["GridSell_MW"].to_numpy(float)
    renewable = dispatch["AvailableRenewable_MW"].to_numpy(float)
    curtail = dispatch["Curtailment_MW"].to_numpy(float)
    net = dispatch["NetGridImport_MW"].to_numpy(float)
    return {
        "method": method,
        "horizon_h": int(horizon),
        "region": str(dispatch["Region"].iloc[0]),
        "status": solver.get("status"),
        "solver_success": bool(solver.get("success")),
        "runtime_s": finite(solver.get("runtime_s")),
        "mip_gap": finite(solver.get("mip_gap")),
        "cost_CNY": float(np.dot(grid, price) - np.dot(sell, sell_price)),
        "carbon_tCO2": float(np.dot(grid, ci)),
        "peak_net_import_MW": float(np.max(net)),
        "load_std_MW": float(np.std(net, ddof=0)),
        "renewable_utilization_ratio": float(np.sum(np.maximum(renewable - curtail, 0.0)) / max(np.sum(renewable), TOL)),
        "curtailment_MWh": float(np.sum(curtail)),
        "terminal_SOC_MWh": float(dispatch["SOC_MWh"].iloc[-1]),
        "initial_SOC_MWh": float(storage["InitialSOC_MWh"]),
        "grid_import_peak_margin_MW": float(storage["MaxGridImport_MW"] - np.max(dispatch["GridPurchase_MW"])),
        "max_charge_MW": float(np.max(dispatch["ChargePower_MW"])),
        "max_discharge_MW": float(np.max(dispatch["DischargePower_MW"])),
    }


def audit(dispatch: pd.DataFrame, storage: pd.Series, method: str, horizon: int) -> dict[str, Any]:
    eta_c = float(storage["ChargeEfficiency"])
    eta_d = float(storage["DischargeEfficiency"])
    initial = float(storage["InitialSOC_MWh"])
    cap = float(storage["StorageCapacity_MWh"])
    min_soc = float(storage["MinSOC_MWh"])
    import_limit = float(storage["MaxGridImport_MW"])
    export_limit = float(min(storage["SellLimit_MW"], storage["MaxGridExport_MW"]))
    d = dispatch.sort_values("Hour").reset_index(drop=True)
    prev = np.r_[initial, d["SOC_MWh"].to_numpy(float)[:-1]]
    soc_rhs = prev + eta_c * d["ChargePower_MW"].to_numpy(float) - d["DischargePower_MW"].to_numpy(float) / eta_d
    soc_resid = d["SOC_MWh"].to_numpy(float) - soc_rhs
    charge_split = d["ChargePower_MW"] - d["RenewableCharge_MW"] - d["GridCharge_MW"]
    renewable_balance = d["AvailableRenewable_MW"] - d["RenewableToLoad_MW"] - d["RenewableCharge_MW"] - d["GridSell_MW"] - d["Curtailment_MW"]
    load_balance = d["RenewableToLoad_MW"] + d["DischargePower_MW"] + d["GridLoadPurchase_MW"] - d["Total_Load_MW"]
    net_import = d["GridPurchase_MW"] - d["GridSell_MW"]
    checks = {
        "soc_transition_max_abs_MWh": float(np.max(np.abs(soc_resid))),
        "charge_split_max_abs_MW": float(np.max(np.abs(charge_split))),
        "renewable_balance_max_abs_MW": float(np.max(np.abs(renewable_balance))),
        "load_balance_max_abs_MW": float(np.max(np.abs(load_balance))),
        "soc_min_violation_MWh": float(max(min_soc - float(d["SOC_MWh"].min()), 0.0)),
        "soc_max_violation_MWh": float(max(float(d["SOC_MWh"].max()) - cap, 0.0)),
        "charge_power_violation_MW": float(max(float(d["ChargePower_MW"].max()) - float(storage["MaxChargePower_MW"]), 0.0)),
        "discharge_power_violation_MW": float(max(float(d["DischargePower_MW"].max()) - float(storage["MaxDischargePower_MW"]), 0.0)),
        "grid_import_violation_MW": float(max(float(d["GridPurchase_MW"].max()) - import_limit, 0.0)),
        "grid_export_violation_MW": float(max(float(d["GridSell_MW"].max()) - export_limit, 0.0)),
        "negative_net_import_violation_MW": float(max(float((-net_import).max()), 0.0)) if export_limit <= 0 else 0.0,
        "terminal_soc_shortfall_MWh": float(max(initial - float(d["SOC_MWh"].iloc[-1]), 0.0)),
        "simultaneous_charge_discharge_MW": float(np.max(np.minimum(d["ChargePower_MW"], d["DischargePower_MW"]))),
    }
    passed = all(value <= 5e-5 for key, value in checks.items() if key not in {"negative_net_import_violation_MW"}) and checks["negative_net_import_violation_MW"] <= 5e-5
    return {"method": method, "region": str(d["Region"].iloc[0]), "horizon_h": int(horizon), "passed": bool(passed), "checks": checks}


def main() -> int:
    out_dir = Path(__file__).resolve().parent
    # q3-pilot/staging/sprint-id/sprints/2026 is the isolated project root.
    project_root = out_dir.parents[3]
    task_path = project_root / "sprints" / SPRINT_ID / "tasks" / f"{TASK_ID}.json"
    task = json.loads(task_path.read_text(encoding="utf-8"))
    expected_inputs = list(task["input_hashes"])
    current_inputs = [fingerprint(project_root, item["path"]) for item in expected_inputs]
    if current_inputs != expected_inputs:
        raise RuntimeError(f"stale or changed inputs: expected={expected_inputs}, current={current_inputs}")

    region_data = pd.read_excel(project_root / "problems/C/data/region_time_data.xlsx", sheet_name=0, engine="openpyxl")
    storage_data = pd.read_excel(project_root / "problems/C/data/storage_information.xlsx", sheet_name=0, engine="openpyxl")
    gpu_data = pd.read_excel(project_root / "problems/C/data/GPU_information.xlsx", sheet_name=0, engine="openpyxl")
    region_data = region_data.sort_values(["Region", "Hour"]).reset_index(drop=True)
    storage_data["Region"] = storage_data["Region"].astype(str)
    gpu_data["Region"] = gpu_data["Region"].astype(str)
    if sorted(region_data["Region"].unique().tolist()) != sorted(storage_data["Region"].unique().tolist()):
        raise RuntimeError("region index mismatch between time and storage tables")

    started = datetime.now(timezone.utc)
    candidate_rows: list[pd.DataFrame] = []
    baseline_rows: list[pd.DataFrame] = []
    candidate_metrics: list[dict[str, Any]] = []
    baseline_metrics: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    solve_records: list[dict[str, Any]] = []
    # Every window starts at Hour 0 so the stated pre-hour-0 InitialSOC is used.
    for horizon in HORIZONS:
        for region in sorted(region_data["Region"].unique()):
            region_df = region_data[region_data["Region"] == region].sort_values("Hour").head(horizon).reset_index(drop=True)
            storage = storage_data[storage_data["Region"] == region].iloc[0]
            baseline = build_baseline(region_df, storage)
            baseline_info = {"status": "deterministic baseline", "success": True, "runtime_s": 0.0, "mip_gap": None}
            baseline_rows.append(baseline.assign(Horizon_h=horizon, Method="no_storage_renewable_first"))
            baseline_metrics.append(metrics(baseline, storage, "no_storage_renewable_first", horizon, baseline_info))
            dispatch, solver_info = solve_region(region_df, storage, horizon, baseline)
            solve_records.append({"horizon_h": horizon, "region": region, **solver_info})
            if solver_info["success"]:
                candidate_method = "full_cycle_LP_scalability_probe" if horizon >= 2407 else "deterministic_carbon_aware_MILP"
                candidate_rows.append(dispatch.assign(Horizon_h=horizon, Method=candidate_method))
                candidate_metrics.append(metrics(dispatch, storage, candidate_method, horizon, solver_info))
                audit_rows.append(audit(dispatch, storage, candidate_method, horizon))
            else:
                # Keep a complete metric row for failed runs, but never silently use it as evidence.
                candidate_method = "full_cycle_LP_scalability_probe" if horizon >= 2407 else "deterministic_carbon_aware_MILP"
                audit_rows.append({"method": candidate_method, "region": region, "horizon_h": horizon, "passed": False, "checks": {"solver_failed": 1.0}})
            audit_rows.append(audit(baseline, storage, "no_storage_renewable_first", horizon))

    candidate_dispatch = pd.concat(candidate_rows, ignore_index=True) if candidate_rows else pd.DataFrame()
    baseline_dispatch = pd.concat(baseline_rows, ignore_index=True)
    candidate_metrics_df = pd.DataFrame(candidate_metrics)
    baseline_metrics_df = pd.DataFrame(baseline_metrics)
    candidate_dispatch.to_csv(out_dir / "q3_dispatch.csv", index=False, float_format="%.8f")
    baseline_dispatch.to_csv(out_dir / "q3_baseline_dispatch.csv", index=False, float_format="%.8f")
    candidate_metrics_df.to_csv(out_dir / "q3_candidate_metrics.csv", index=False, float_format="%.10f")
    baseline_metrics_df.to_csv(out_dir / "q3_baseline_metrics.csv", index=False, float_format="%.10f")
    json_dump(out_dir / "q3_constraint_audit.json", {"schema_version": 1, "tolerance": 5e-5, "audits": audit_rows})

    candidate_pass = bool(candidate_metrics and all(item["passed"] for item in audit_rows if item["method"] != "no_storage_renewable_first"))
    baseline_pass = all(item["passed"] for item in audit_rows if item["method"] == "no_storage_renewable_first")
    summary = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "question": "Q3",
        "status": "SUCCESS" if candidate_pass and baseline_pass else "PARTIAL",
        "window_horizons": list(HORIZONS),
        "regions": sorted(region_data["Region"].unique().tolist()),
        "candidate": {
            "name": "deterministic_carbon_aware_MILP",
            "description": "Binary MILP dispatch for a bounded 24-hour pilot with renewable allocation, carbon-aware normalized objective, peak-import epigraph, charge/discharge mode, and cyclic terminal SOC.",
            "pilot_only": True,
            "solver_success": candidate_pass,
            "full_cycle_check": "72/168/2407-hour configurations are deferred scalability probes and are not reported as evidence in this bounded pilot.",
        },
        "baseline": {
            "name": "no_storage_renewable_first",
            "description": "No-storage renewable-first balance with region-specific purchase/export caps and zero charge/discharge.",
            "audit_pass": baseline_pass,
        },
        "selection_recommendation": {
            "retain_milp_for_full_run": candidate_pass,
            "fallback_trigger": "Use valley-charge/peak-discharge rule only if exact MILP has no feasible incumbent or exceeds 20 s on two independent windows.",
            "non_global_optimality_wording": "Pilot evidence is exploratory; solver status and any time limit are reported, and no global optimality claim is made.",
        },
        "metrics_definition": {
            "cost_CNY": "sum(GridPurchase*ElectricityPrice - GridSell*SellPrice), one-hour intervals; GridPurchase includes GridCharge",
            "carbon_tCO2": "sum(GridPurchase*CarbonIntensity); GridPurchase includes GridCharge",
            "peak_net_import_MW": "max(GridPurchase - GridSell); GridPurchase includes GridCharge",
            "load_std_MW": "population standard deviation of net grid import over each window",
            "renewable_utilization_ratio": "sum(AvailableRenewable - Curtailment)/sum(AvailableRenewable)",
        },
        "input_hashes": expected_inputs,
        "solver_records": solve_records,
        "limitations": [
            "Q2 task-level schedule is not re-optimized in this pilot; Total_Load_MW from the authoritative hourly table is fixed input.",
            "The bounded pilot begins at Hour 0 and uses InitialSOC as the pre-hour-0 state with a cyclic terminal SOC boundary.",
            "CVaR/MPC candidates are deferred until deterministic dispatch evidence and observed-data scenario probes justify them.",
        ],
    }
    json_dump(out_dir / "q3_pilot_summary.json", summary)
    code_hash = sha256_file(out_dir / "run_q3_pilot.py")
    ended = datetime.now(timezone.utc)
    manifest = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "question": "Q3",
        "run_id": f"q3-pilot-{started.strftime('%Y%m%dT%H%M%SZ')}",
        "command": "D:/anaconda3/envs/math-modeling/python.exe run_q3_pilot.py",
        "working_directory": str(out_dir),
        "started_at_utc": started.isoformat(),
        "ended_at_utc": ended.isoformat(),
        "runtime_s": (ended - started).total_seconds(),
        "seed": SEED,
        "python": sys.version,
        "platform": platform.platform(),
        "packages": {"numpy": np.__version__, "pandas": pd.__version__},
        "code": {"path": f"sprints/{SPRINT_ID}/staging/{TASK_ID}/run_q3_pilot.py", "sha256": code_hash},
        "input_hashes": expected_inputs,
        "data_rows": {"region_time_data": int(len(region_data)), "storage_information": int(len(storage_data)), "GPU_information": int(len(gpu_data))},
        "horizons_h": list(HORIZONS),
        "solver": {"library": "scipy.optimize.milp", "time_limit_s_per_region": 20.0, "mip_rel_gap": 1e-7, "modes": {"24": "binary_MILP"}, "deferred_probes": [72, 168, 2407]},
        "outputs": ["q3_pilot_summary.json", "q3_constraint_audit.json", "q3_candidate_metrics.csv", "q3_baseline_metrics.csv", "q3_dispatch.csv", "q3_baseline_dispatch.csv"],
    }
    json_dump(out_dir / "q3_run_manifest.json", manifest)

    output_names = [
        "q3_pilot_summary.json", "q3_run_manifest.json", "q3_constraint_audit.json", "q3_candidate_metrics.csv", "q3_baseline_metrics.csv", "q3_dispatch.csv", "q3_baseline_dispatch.csv", "run_q3_pilot.py"
    ]
    artifacts = [{"path": f"sprints/{SPRINT_ID}/staging/{TASK_ID}/{name}", "sha256": sha256_file(out_dir / name)} for name in output_names]
    handoff = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "attempt": ATTEMPT,
        "status": "SUCCESS" if candidate_pass and baseline_pass else "PARTIAL",
        "input_hashes": expected_inputs,
        "written_paths": [f"sprints/{SPRINT_ID}/staging/{TASK_ID}/{name}" for name in output_names] + [f"sprints/{SPRINT_ID}/staging/{TASK_ID}/handoff.json"],
        "artifacts": artifacts,
        "gate_result": {
            "gate": "G3",
            "passed": bool(candidate_pass and baseline_pass),
            "checks": [
                "Real region_time_data, storage_information, and GPU_information loaded with pinned input hashes.",
                "Candidate and no-storage baseline emit the same dispatch class and metrics over the bounded 24-hour window.",
                "SOC transition, end-of-hour convention, initial/terminal SOC, efficiency, charge/discharge, grid, renewable, and energy-balance audits are recorded.",
                "Pilot numbers remain staging evidence and are not frozen claims.",
            ],
        },
        "summary": "Q3 deterministic storage dispatch pilot completed on real six-region data; see summary, metrics, dispatch rows, and constraint audits. No formal state or claims were modified.",
    }
    json_dump(out_dir / "handoff.json", handoff)
    return 0 if candidate_pass and baseline_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
