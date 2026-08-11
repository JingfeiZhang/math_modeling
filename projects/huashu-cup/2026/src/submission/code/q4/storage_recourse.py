#!/usr/bin/env python
"""Final bounded Q4 integration on a Q2-derived 72-hour envelope.

The candidate uses the selected Q2 carbon-aware schedule and one integrated
six-region storage MILP. The comparable baseline uses the Q2 FIFO schedule
and the same renewable-first, no-storage power balance. Q3 supplies the
empirical scenario definitions, while the repaired Q4 pilot supplies the
binary charge/discharge and import/export mutex conventions.
"""
from __future__ import annotations

# 本程序及代码是在 AI 工具辅助下完成的。
# AI 工具名称：OpenAI Codex，版本/型号：GPT-5，开发机构/公司：OpenAI，版本发布日期：2025-08-07。

import hashlib
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


HORIZON = 72
WINDOW_ID = "w2328_2400"
WINDOW_START_H = 2328
SEED = 20260808
TOL = 5e-5
CARBON_WEIGHT = 0.35
PEAK_WEIGHT = 0.08


def schedule_to_envelope(
    schedule: pd.DataFrame,
    region_time: pd.DataFrame,
    power_map: dict[str, float],
    pue_map: dict[str, float],
    method: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    hours = region_time[
        region_time.Hour.astype(int).between(WINDOW_START_H, WINDOW_START_H + HORIZON - 1)
    ].copy()
    required = {
        "Hour",
        "Region",
        "PricePeriod",
        "ElectricityPrice_CNY_per_MWh",
        "SellPrice_CNY_per_MWh",
        "CarbonIntensity_tCO2_per_MWh",
        "AvailableRenewable_MW",
        "NonAI_IT_Load_MW",
    }
    missing = required - set(hours.columns)
    if missing:
        raise ValueError(f"region_time_data missing columns: {sorted(missing)}")
    regions = sorted(hours.Region.astype(str).unique())
    if set(regions) != set(pue_map):
        raise ValueError("PUE regions do not match region_time_data regions")
    if len(hours) != len(regions) * HORIZON:
        raise ValueError("region_time_data must contain one row per region-hour in the 72-hour window")
    if hours.duplicated(["Region", "Hour"]).any():
        raise ValueError("region_time_data contains duplicate region-hour rows")

    out = hours[
        [
            "Hour",
            "Region",
            "PricePeriod",
            "ElectricityPrice_CNY_per_MWh",
            "SellPrice_CNY_per_MWh",
            "CarbonIntensity_tCO2_per_MWh",
            "AvailableRenewable_MW",
            "NonAI_IT_Load_MW",
        ]
    ].copy()
    out["Hour"] = out.Hour.astype(int) - WINDOW_START_H
    out["AbsoluteHour"] = out.Hour.astype(int) + WINDOW_START_H
    out["Region"] = out.Region.astype(str)
    out["AI_IT_Load_MW"] = 0.0
    row_index = {
        (str(row.Region), int(row.AbsoluteHour)): idx
        for idx, row in out.iterrows()
    }

    missing_types = sorted(set(schedule.TaskType.astype(str)) - set(power_map))
    if missing_types:
        raise ValueError(f"power_mapping has no entries for task types: {missing_types}")
    unknown_regions = sorted(set(schedule.ExecutionRegion.astype(str)) - set(regions))
    if unknown_regions:
        raise ValueError(f"Q2 schedule contains unknown execution regions: {unknown_regions}")

    excluded_minutes = 0
    excluded_ai_energy_mwh = 0.0
    spill_tasks = 0
    horizon_start_m = WINDOW_START_H * 60
    horizon_end_m = (WINDOW_START_H + HORIZON) * 60
    for row in schedule.itertuples(index=False):
        start = int(row.StartMinute)
        end = int(row.EndMinute)
        inside = max(0, min(end, horizon_end_m) - max(start, horizon_start_m))
        excluded_minutes += (end - start) - inside
        spill_tasks += int(end > horizon_end_m)
        task_power_mw = power_map[str(row.TaskType)] * float(row.GPU_Demand)
        excluded_ai_energy_mwh += task_power_mw * ((end - start) - inside) / 60.0
        for absolute_hour in range(WINDOW_START_H, WINDOW_START_H + HORIZON):
            hour_start = absolute_hour * 60
            overlap = max(0, min(end, hour_start + 60) - max(start, hour_start))
            if overlap:
                idx = row_index[(str(row.ExecutionRegion), absolute_hour)]
                out.loc[idx, "AI_IT_Load_MW"] += task_power_mw * overlap / 60.0

    out["IT_Load_MW"] = out.NonAI_IT_Load_MW + out.AI_IT_Load_MW
    out["PUE"] = out.Region.map(pue_map).astype(float)
    out["Total_Load_MW"] = out.IT_Load_MW * out.PUE
    out["Q2Method"] = method
    out = out.sort_values(["Region", "Hour"]).reset_index(drop=True)
    meta = {
        "task_count": int(len(schedule)),
        "task_id_sha256": hashlib.sha256(
            ",".join(str(value) for value in sorted(schedule.TaskID.astype(int))).encode("utf-8")
        ).hexdigest(),
        "spill_task_count": int(spill_tasks),
        "excluded_closeout_task_minutes": int(excluded_minutes),
        "excluded_closeout_ai_energy_MWh": float(excluded_ai_energy_mwh),
        "ai_energy_within_72h_MWh": float(out.AI_IT_Load_MW.sum()),
        "facility_energy_within_72h_MWh": float(out.Total_Load_MW.sum()),
        "region_hour_rows": int(len(out)),
    }
    return out, meta


def apply_scenario(
    frame: pd.DataFrame,
    scenario: dict[str, Any],
    carbon_q75: float,
) -> pd.DataFrame:
    out = frame.copy()
    out["ObservedElectricityPrice_CNY_per_MWh"] = out.ElectricityPrice_CNY_per_MWh
    out["ObservedCarbonIntensity_tCO2_per_MWh"] = out.CarbonIntensity_tCO2_per_MWh
    out["ObservedAvailableRenewable_MW"] = out.AvailableRenewable_MW
    price_factor = np.ones(len(out), dtype=float)
    if float(scenario.get("price", 1.0)) != 1.0:
        price_factor[out.PricePeriod.astype(str).eq("Peak").to_numpy()] = float(scenario["price"])
    carbon_factor = np.ones(len(out), dtype=float)
    if float(scenario.get("carbon", 1.0)) != 1.0:
        mask = out.CarbonIntensity_tCO2_per_MWh.to_numpy(float) >= carbon_q75
        carbon_factor[mask] = float(scenario["carbon"])
    renewable_factor = float(scenario.get("renewable", 1.0))
    out["ScenarioPriceMultiplier"] = price_factor
    out["ScenarioCarbonMultiplier"] = carbon_factor
    out["ScenarioRenewableMultiplier"] = renewable_factor
    out["ElectricityPrice_CNY_per_MWh"] = (
        out.ElectricityPrice_CNY_per_MWh.to_numpy(float) * price_factor
    )
    out["CarbonIntensity_tCO2_per_MWh"] = (
        out.CarbonIntensity_tCO2_per_MWh.to_numpy(float) * carbon_factor
    )
    out["AvailableRenewable_MW"] = (
        out.AvailableRenewable_MW.to_numpy(float) * renewable_factor
    )
    return out


def storage_map(storage_table: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        str(row.Region): pd.Series(row._asdict())
        for row in storage_table.itertuples(index=False)
    }


def baseline_dispatch(frame: pd.DataFrame, storage_table: pd.DataFrame) -> pd.DataFrame:
    stores = storage_map(storage_table)
    pieces: list[pd.DataFrame] = []
    for region, group in frame.groupby("Region", sort=True):
        st = stores[str(region)]
        out = group.sort_values("Hour").reset_index(drop=True).copy()
        renew = out.AvailableRenewable_MW.to_numpy(float)
        load = out.Total_Load_MW.to_numpy(float)
        direct = np.minimum(load, renew)
        surplus = np.maximum(renew - direct, 0.0)
        export_cap = min(float(st.SellLimit_MW), float(st.MaxGridExport_MW))
        sell = np.minimum(surplus, export_cap)
        purchase = np.maximum(load - direct, 0.0)
        out["ChargePower_MW"] = 0.0
        out["DischargePower_MW"] = 0.0
        out["SOC_MWh"] = float(st.InitialSOC_MWh)
        out["RenewableToLoad_MW"] = direct
        out["RenewableCharge_MW"] = 0.0
        out["GridCharge_MW"] = 0.0
        out["GridLoadPurchase_MW"] = purchase
        out["GridPurchase_MW"] = purchase
        out["GridSell_MW"] = sell
        out["Curtailment_MW"] = surplus - sell
        out["NetGridImport_MW"] = purchase - sell
        out["ChargeMode"] = 0
        out["GridImportMode"] = (purchase > TOL).astype(int)
        out["Method"] = "Q2_FIFO_plus_no_storage_renewable_first"
        pieces.append(out)
    return pd.concat(pieces, ignore_index=True).sort_values(["Region", "Hour"]).reset_index(drop=True)


# BEGIN APPENDIX_Q4_STORAGE_RECOURSE
def solve_integrated(
    frame: pd.DataFrame,
    storage_table: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    data = frame.sort_values(["Region", "Hour"]).reset_index(drop=True)
    regions = sorted(data.Region.astype(str).unique())
    stores = storage_map(storage_table)
    region_frames = {
        region: data[data.Region.astype(str) == region].sort_values("Hour").reset_index(drop=True)
        for region in regions
    }
    if any(len(region_frames[region]) != HORIZON for region in regions):
        raise ValueError("candidate envelope must contain 72 rows for every region")

    region_count = len(regions)
    n_rt = region_count * HORIZON
    variable_names = [
        "charge",
        "discharge",
        "soc",
        "renewable_to_load",
        "renewable_charge",
        "grid_charge",
        "grid_load",
        "sell",
        "curtail",
        "charge_mode",
        "grid_mode",
    ]
    slices: dict[str, slice] = {}
    cursor = 0
    for name in variable_names:
        slices[name] = slice(cursor, cursor + n_rt)
        cursor += n_rt
    system_peak = cursor
    nvar = cursor + 1

    def at(name: str, region_index: int, hour: int) -> int:
        return slices[name].start + region_index * HORIZON + hour

    objective = np.zeros(nvar)
    lower = np.zeros(nvar)
    upper = np.full(nvar, np.inf)
    integrality = np.zeros(nvar)
    total_nominal_cost = 0.0
    total_nominal_carbon = 0.0
    total_renewable = 0.0
    total_import_cap = 0.0
    for region in regions:
        d = region_frames[region]
        total_nominal_cost += float(np.dot(d.Total_Load_MW, d.ElectricityPrice_CNY_per_MWh))
        total_nominal_carbon += float(np.dot(d.Total_Load_MW, d.CarbonIntensity_tCO2_per_MWh))
        total_renewable += float(d.AvailableRenewable_MW.sum())
        total_import_cap += float(stores[region].MaxGridImport_MW)
    cost_scale = max(total_nominal_cost, 1.0)
    carbon_scale = max(total_nominal_carbon, 1.0)
    renewable_scale = max(total_renewable, 1.0)

    for ri, region in enumerate(regions):
        d = region_frames[region]
        st = stores[region]
        max_charge = float(st.MaxChargePower_MW)
        max_discharge = float(st.MaxDischargePower_MW)
        import_cap = float(st.MaxGridImport_MW)
        export_cap = min(float(st.SellLimit_MW), float(st.MaxGridExport_MW))
        for hour in range(HORIZON):
            charge = at("charge", ri, hour)
            discharge = at("discharge", ri, hour)
            objective[at("grid_load", ri, hour)] = (
                float(d.ElectricityPrice_CNY_per_MWh.iloc[hour]) / cost_scale
                + CARBON_WEIGHT
                * float(d.CarbonIntensity_tCO2_per_MWh.iloc[hour])
                / carbon_scale
            )
            objective[at("grid_charge", ri, hour)] = objective[at("grid_load", ri, hour)]
            objective[at("sell", ri, hour)] = -float(d.SellPrice_CNY_per_MWh.iloc[hour]) / cost_scale
            objective[at("curtail", ri, hour)] = 0.03 / renewable_scale
            objective[charge] += 1e-7
            objective[discharge] += 1e-7
            upper[charge] = max_charge
            upper[discharge] = max_discharge
            lower[at("soc", ri, hour)] = float(st.MinSOC_MWh)
            upper[at("soc", ri, hour)] = float(st.StorageCapacity_MWh)
            upper[at("renewable_charge", ri, hour)] = max_charge
            upper[at("grid_charge", ri, hour)] = max_charge
            upper[at("grid_load", ri, hour)] = import_cap
            upper[at("sell", ri, hour)] = export_cap
            upper[at("charge_mode", ri, hour)] = 1.0
            upper[at("grid_mode", ri, hour)] = 1.0
            integrality[at("charge_mode", ri, hour)] = 1
            integrality[at("grid_mode", ri, hour)] = 1
    objective[system_peak] = PEAK_WEIGHT / max(total_import_cap, 1.0)
    lower[system_peak] = 0.0
    upper[system_peak] = total_import_cap

    constraint_count = 8 * n_rt + region_count + HORIZON
    matrix = lil_matrix((constraint_count, nvar))
    lo = np.full(constraint_count, -np.inf)
    hi = np.full(constraint_count, np.inf)
    row = 0
    for ri, region in enumerate(regions):
        d = region_frames[region]
        st = stores[region]
        initial = float(st.InitialSOC_MWh)
        eta_charge = float(st.ChargeEfficiency)
        eta_discharge = float(st.DischargeEfficiency)
        max_charge = float(st.MaxChargePower_MW)
        max_discharge = float(st.MaxDischargePower_MW)
        import_cap = float(st.MaxGridImport_MW)
        export_cap = min(float(st.SellLimit_MW), float(st.MaxGridExport_MW))
        for hour in range(HORIZON):
            matrix[row, at("soc", ri, hour)] = 1
            matrix[row, at("charge", ri, hour)] = -eta_charge
            matrix[row, at("discharge", ri, hour)] = 1 / eta_discharge
            if hour:
                matrix[row, at("soc", ri, hour - 1)] = -1
                lo[row] = hi[row] = 0.0
            else:
                lo[row] = hi[row] = initial
            row += 1

            matrix[row, at("charge", ri, hour)] = 1
            matrix[row, at("renewable_charge", ri, hour)] = -1
            matrix[row, at("grid_charge", ri, hour)] = -1
            lo[row] = hi[row] = 0.0
            row += 1

            matrix[row, at("renewable_to_load", ri, hour)] = 1
            matrix[row, at("renewable_charge", ri, hour)] = 1
            matrix[row, at("sell", ri, hour)] = 1
            matrix[row, at("curtail", ri, hour)] = 1
            lo[row] = hi[row] = float(d.AvailableRenewable_MW.iloc[hour])
            row += 1

            matrix[row, at("renewable_to_load", ri, hour)] = 1
            matrix[row, at("discharge", ri, hour)] = 1
            matrix[row, at("grid_load", ri, hour)] = 1
            lo[row] = hi[row] = float(d.Total_Load_MW.iloc[hour])
            row += 1

            matrix[row, at("charge", ri, hour)] = 1
            matrix[row, at("charge_mode", ri, hour)] = -max_charge
            hi[row] = 0.0
            row += 1

            matrix[row, at("discharge", ri, hour)] = 1
            matrix[row, at("charge_mode", ri, hour)] = max_discharge
            hi[row] = max_discharge
            row += 1

            matrix[row, at("grid_load", ri, hour)] = 1
            matrix[row, at("grid_charge", ri, hour)] = 1
            matrix[row, at("grid_mode", ri, hour)] = -import_cap
            hi[row] = 0.0
            row += 1

            matrix[row, at("sell", ri, hour)] = 1
            matrix[row, at("grid_mode", ri, hour)] = export_cap
            hi[row] = export_cap
            row += 1

        matrix[row, at("soc", ri, HORIZON - 1)] = 1
        lo[row] = hi[row] = initial
        row += 1

    for hour in range(HORIZON):
        for ri in range(region_count):
            matrix[row, at("grid_load", ri, hour)] = 1
            matrix[row, at("grid_charge", ri, hour)] = 1
            matrix[row, at("sell", ri, hour)] = -1
        matrix[row, system_peak] = -1
        hi[row] = 0.0
        row += 1
    if row != constraint_count:
        raise RuntimeError(f"constraint assembly mismatch: expected={constraint_count}, actual={row}")

    started = time.perf_counter()
    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(matrix.tocsr(), lo, hi),
        options={"presolve": True, "time_limit": 60.0, "mip_rel_gap": 1e-7},
    )
    runtime_s = time.perf_counter() - started
    solver = {
        "success": bool(result.success and result.x is not None),
        "status": str(result.message),
        "runtime_s": runtime_s,
        "mip_gap": None if result.x is None else float(getattr(result, "mip_gap", 0.0) or 0.0),
        "mip_node_count": None
        if result.x is None
        else int(getattr(result, "mip_node_count", 0) or 0),
        "objective": None if result.fun is None else float(result.fun),
        "solver_mode": "integrated_binary_MILP",
    }
    if not solver["success"]:
        return pd.DataFrame(), solver

    x = result.x
    pieces: list[pd.DataFrame] = []
    for ri, region in enumerate(regions):
        out = region_frames[region].copy()
        out["ChargePower_MW"] = x[slices["charge"]][ri * HORIZON : (ri + 1) * HORIZON]
        out["DischargePower_MW"] = x[slices["discharge"]][ri * HORIZON : (ri + 1) * HORIZON]
        out["SOC_MWh"] = x[slices["soc"]][ri * HORIZON : (ri + 1) * HORIZON]
        out["RenewableToLoad_MW"] = x[slices["renewable_to_load"]][
            ri * HORIZON : (ri + 1) * HORIZON
        ]
        out["RenewableCharge_MW"] = x[slices["renewable_charge"]][
            ri * HORIZON : (ri + 1) * HORIZON
        ]
        out["GridCharge_MW"] = x[slices["grid_charge"]][ri * HORIZON : (ri + 1) * HORIZON]
        out["GridLoadPurchase_MW"] = x[slices["grid_load"]][
            ri * HORIZON : (ri + 1) * HORIZON
        ]
        out["GridPurchase_MW"] = out.GridLoadPurchase_MW + out.GridCharge_MW
        out["GridSell_MW"] = x[slices["sell"]][ri * HORIZON : (ri + 1) * HORIZON]
        out["Curtailment_MW"] = x[slices["curtail"]][ri * HORIZON : (ri + 1) * HORIZON]
        out["NetGridImport_MW"] = out.GridPurchase_MW - out.GridSell_MW
        out["ChargeMode"] = np.rint(
            x[slices["charge_mode"]][ri * HORIZON : (ri + 1) * HORIZON]
        ).astype(int)
        out["GridImportMode"] = np.rint(
            x[slices["grid_mode"]][ri * HORIZON : (ri + 1) * HORIZON]
        ).astype(int)
        out["Method"] = "Q2_candidate_plus_integrated_storage_MILP"
        pieces.append(out)
    dispatch = pd.concat(pieces, ignore_index=True).sort_values(["Region", "Hour"]).reset_index(drop=True)
    solver["system_peak_variable_MW"] = float(x[system_peak])
    solver["system_peak_net_import_MW"] = float(
        dispatch.groupby("Hour").NetGridImport_MW.sum().max()
    )
    return dispatch, solver


# END APPENDIX_Q4_STORAGE_RECOURSE


def audit_dispatch(
    dispatch: pd.DataFrame,
    storage_table: pd.DataFrame,
    method: str,
    reported_peak_mw: float | None,
) -> dict[str, Any]:
    stores = storage_map(storage_table)
    regional: dict[str, Any] = {}
    for region, group in dispatch.groupby("Region", sort=True):
        d = group.sort_values("Hour").reset_index(drop=True)
        st = stores[str(region)]
        initial = float(st.InitialSOC_MWh)
        eta_charge = float(st.ChargeEfficiency)
        eta_discharge = float(st.DischargeEfficiency)
        previous = np.r_[initial, d.SOC_MWh.to_numpy(float)[:-1]]
        soc_residual = d.SOC_MWh.to_numpy(float) - (
            previous
            + eta_charge * d.ChargePower_MW.to_numpy(float)
            - d.DischargePower_MW.to_numpy(float) / eta_discharge
        )
        checks = {
            "soc_transition_max_abs_MWh": float(np.max(np.abs(soc_residual))),
            "charge_split_max_abs_MW": float(
                np.max(np.abs(d.ChargePower_MW - d.RenewableCharge_MW - d.GridCharge_MW))
            ),
            "load_balance_max_abs_MW": float(
                np.max(
                    np.abs(
                        d.RenewableToLoad_MW
                        + d.DischargePower_MW
                        + d.GridLoadPurchase_MW
                        - d.Total_Load_MW
                    )
                )
            ),
            "renewable_balance_max_abs_MW": float(
                np.max(
                    np.abs(
                        d.AvailableRenewable_MW
                        - d.RenewableToLoad_MW
                        - d.RenewableCharge_MW
                        - d.GridSell_MW
                        - d.Curtailment_MW
                    )
                )
            ),
            "soc_bounds_violation_MWh": float(
                max(
                    float(st.MinSOC_MWh - d.SOC_MWh.min()),
                    float(d.SOC_MWh.max() - st.StorageCapacity_MWh),
                    0.0,
                )
            ),
            "charge_power_violation_MW": float(
                max(float(d.ChargePower_MW.max() - st.MaxChargePower_MW), 0.0)
            ),
            "discharge_power_violation_MW": float(
                max(float(d.DischargePower_MW.max() - st.MaxDischargePower_MW), 0.0)
            ),
            "import_cap_violation_MW": float(
                max(float(d.GridPurchase_MW.max() - st.MaxGridImport_MW), 0.0)
            ),
            "export_cap_violation_MW": float(
                max(
                    float(
                        d.GridSell_MW.max()
                        - min(float(st.SellLimit_MW), float(st.MaxGridExport_MW))
                    ),
                    0.0,
                )
            ),
            "terminal_soc_error_MWh": float(abs(d.SOC_MWh.iloc[-1] - initial)),
            "simultaneous_charge_discharge_MW": float(
                np.max(np.minimum(d.ChargePower_MW, d.DischargePower_MW))
            ),
            "simultaneous_grid_import_export_MW": float(
                np.max(np.minimum(d.GridPurchase_MW, d.GridSell_MW))
            ),
            "charge_mode_integrality_error": float(
                np.max(np.abs(d.ChargeMode - np.rint(d.ChargeMode)))
            ),
            "grid_mode_integrality_error": float(
                np.max(np.abs(d.GridImportMode - np.rint(d.GridImportMode)))
            ),
        }
        regional[str(region)] = {
            "passed": bool(all(value <= TOL for value in checks.values())),
            "checks": checks,
        }

    system_hourly = dispatch.groupby("Hour", as_index=False).agg(
        SystemNetGridImport_MW=("NetGridImport_MW", "sum")
    )
    observed_peak = float(system_hourly.SystemNetGridImport_MW.max())
    positive_peak = max(observed_peak, 0.0)
    linked_peak = positive_peak if reported_peak_mw is None else float(reported_peak_mw)
    expected_rows = int(dispatch.Region.nunique()) * HORIZON
    exact_hour_coverage = all(
        len(group) == HORIZON and set(group.Hour.astype(int)) == set(range(HORIZON))
        for _, group in dispatch.groupby("Region")
    )
    system_checks = {
        "region_hour_row_count_error": float(abs(len(dispatch) - expected_rows)),
        "exact_72h_coverage_error": 0.0 if exact_hour_coverage else 1.0,
        "system_peak_linkage_violation_MW": float(
            max(float((system_hourly.SystemNetGridImport_MW - linked_peak).max()), 0.0)
        ),
        "system_peak_identity_error_MW": float(abs(linked_peak - positive_peak)),
    }
    system = {
        "passed": bool(all(value <= TOL for value in system_checks.values())),
        "reported_peak_variable_MW": linked_peak,
        "observed_peak_net_import_MW": observed_peak,
        "positive_part_peak_MW": positive_peak,
        "checks": system_checks,
    }
    return {
        "method": method,
        "passed": bool(system["passed"] and all(row["passed"] for row in regional.values())),
        "regional": regional,
        "system": system,
    }





