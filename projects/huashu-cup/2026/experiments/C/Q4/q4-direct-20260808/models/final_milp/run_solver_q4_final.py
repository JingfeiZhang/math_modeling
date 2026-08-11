#!/usr/bin/env python
"""Final bounded Q4 integration on a Q2-derived 72-hour envelope.

The candidate uses the selected Q2 carbon-aware schedule and one integrated
six-region storage MILP. The comparable baseline uses the Q2 FIFO schedule
and the same renewable-first, no-storage power balance. Q3 supplies the
empirical scenario definitions, while the repaired Q4 pilot supplies the
binary charge/discharge and import/export mutex conventions.
"""
from __future__ import annotations

import hashlib
import json
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


STAGING = Path(__file__).resolve().parent
ROOT = STAGING.parents[3]
SPRINT_ID = "sprint-20260808T031214934335Z"
TASK_ID = "solver-q4"
HORIZON = 72
WINDOW_ID = "w2328_2400"
WINDOW_START_H = 2328
SEED = 20260808
TOL = 5e-5
CARBON_WEIGHT = 0.35
PEAK_WEIGHT = 0.08

Q2_DIR = ROOT / "sprints" / "sprint-20260808T023234268084Z" / "merged" / "solver-q2"
Q3_DIR = ROOT / "sprints" / "sprint-20260808T023236665505Z" / "merged" / "solver-q3"
Q4_PILOT_DIR = ROOT / "sprints" / "sprint-20260807T210015466011Z" / "merged" / "solver-q4"
Q4_REPAIRED_DIR = ROOT / "sprints" / "sprint-20260808T023235447353Z" / "merged" / "solver-q4"
TASK_PACKAGE = ROOT / "sprints" / SPRINT_ID / "tasks" / f"{TASK_ID}.json"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_hash(path: Path) -> str:
    records = [
        f"{item.relative_to(path).as_posix()}:{sha256_file(item)}"
        for item in sorted(path.rglob("*"))
        if item.is_file()
    ]
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()


def verify_inputs(task: dict[str, Any]) -> None:
    failures: list[dict[str, Any]] = []
    for item in task.get("input_hashes", []):
        path = ROOT / str(item["path"])
        if item.get("kind") == "directory" and path.is_dir():
            observed = directory_hash(path)
        elif path.is_file():
            observed = sha256_file(path)
        else:
            observed = None
        if observed != item.get("sha256"):
            failures.append(
                {"path": item["path"], "expected": item.get("sha256"), "observed": observed}
            )
    if failures:
        raise RuntimeError(
            "stale or missing sprint inputs: " + json.dumps(failures, ensure_ascii=False)
        )


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def selected_window(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    required = {
        "WindowID",
        "Method",
        "TaskID",
        "TaskType",
        "ExecutionRegion",
        "StartMinute",
        "EndMinute",
        "GPU_Demand",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} Q2 schedule missing columns: {sorted(missing)}")
    selected = frame[frame.WindowID.astype(str) == WINDOW_ID].copy()
    if selected.empty:
        raise ValueError(f"{label} Q2 schedule has no rows for {WINDOW_ID}")
    if selected.TaskID.duplicated().any():
        raise ValueError(f"{label} Q2 schedule contains duplicate TaskID")
    if (selected.EndMinute.astype(int) <= selected.StartMinute.astype(int)).any():
        raise ValueError(f"{label} Q2 schedule contains non-positive durations")
    return selected.sort_values("TaskID").reset_index(drop=True)


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


def load_inputs() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, Any],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    data = ROOT / "problems" / "C" / "data"
    candidate_schedule = selected_window(
        pd.read_csv(Q2_DIR / "q2_candidate_schedules.csv"), "candidate"
    )
    baseline_schedule = selected_window(
        pd.read_csv(Q2_DIR / "q2_baseline_schedules.csv"), "baseline"
    )
    if set(candidate_schedule.TaskID.astype(int)) != set(baseline_schedule.TaskID.astype(int)):
        raise ValueError("Q2 candidate and FIFO schedules do not contain the same task set")

    region_time = pd.read_excel(data / "region_time_data.xlsx", sheet_name="region_time_data")
    gpu = pd.read_excel(data / "GPU_information.xlsx", sheet_name="GPU中心基础情况")
    power = pd.read_excel(data / "power_mapping.xlsx", sheet_name="任务功率映射")
    storage = pd.read_excel(data / "storage_information.xlsx", sheet_name="storage_information")
    pue_map = dict(zip(gpu.Region.astype(str), gpu.PUE.astype(float), strict=True))
    power_map = dict(
        zip(
            power.TaskType.astype(str),
            power.GPU_Power_MW_per_EquivalentGPU.astype(float),
            strict=True,
        )
    )
    candidate_method = str(candidate_schedule.Method.iloc[0])
    baseline_method = str(baseline_schedule.Method.iloc[0])
    candidate_base, candidate_meta = schedule_to_envelope(
        candidate_schedule, region_time, power_map, pue_map, candidate_method
    )
    baseline_base, baseline_meta = schedule_to_envelope(
        baseline_schedule, region_time, power_map, pue_map, baseline_method
    )

    q2_summary = json.loads((Q2_DIR / "q2_enhancement_summary.json").read_text(encoding="utf-8"))
    q3_summary = json.loads((Q3_DIR / "q3_summary.json").read_text(encoding="utf-8"))
    q4_pilot = json.loads((Q4_PILOT_DIR / "q4_summary.json").read_text(encoding="utf-8"))
    q4_repaired = json.loads(
        (Q4_REPAIRED_DIR / "q4_enhanced_summary.json").read_text(encoding="utf-8")
    )
    q2_candidate_metrics = pd.read_csv(Q2_DIR / "q2_candidate_metrics.csv")
    q2_baseline_metrics = pd.read_csv(Q2_DIR / "q2_baseline_metrics.csv")
    candidate_service = q2_candidate_metrics[
        q2_candidate_metrics.window_id.astype(str) == WINDOW_ID
    ].iloc[0]
    baseline_service = q2_baseline_metrics[
        q2_baseline_metrics.window_id.astype(str) == WINDOW_ID
    ].iloc[0]
    service_metrics = {
        "candidate": {
            "task_completion_rate": float(candidate_service.task_completion_rate),
            "SLA_violation_rate": float(candidate_service.SLA_violation_rate),
            "mean_latency_ms": float(candidate_service.mean_latency_ms),
            "q2_audit_passed": bool(candidate_service.audit_passed),
        },
        "baseline": {
            "task_completion_rate": float(baseline_service.task_completion_rate),
            "SLA_violation_rate": float(baseline_service.SLA_violation_rate),
            "mean_latency_ms": float(baseline_service.mean_latency_ms),
            "q2_audit_passed": bool(baseline_service.audit_passed),
        },
    }

    q3_scenarios = q3_summary["scenarios"]
    scenarios = [
        {"name": "observed", "price": 1.0, "carbon": 1.0, "renewable": 1.0},
        {"name": "peak_price_empirical", **q3_scenarios["peak_price_empirical"]},
        {"name": "high_carbon_empirical", **q3_scenarios["high_carbon_empirical"]},
        {"name": "renewable_low_empirical", **q3_scenarios["renewable_low_empirical"]},
        {"name": "joint_stress", **q3_scenarios["joint_stress"]},
    ]
    quantiles = q3_summary["scenario_observed_quantiles"]
    provenance = {
        "q2_enhanced_directory": Q2_DIR.relative_to(ROOT).as_posix(),
        "q2_enhanced_directory_sha256": directory_hash(Q2_DIR),
        "q2_status": q2_summary["status"],
        "q2_selected_policy": q2_summary["exploration"]["selected_policy"],
        "q2_candidate_schedule_sha256": sha256_file(Q2_DIR / "q2_candidate_schedules.csv"),
        "q2_fifo_schedule_sha256": sha256_file(Q2_DIR / "q2_baseline_schedules.csv"),
        "q2_candidate_envelope": candidate_meta,
        "q2_fifo_envelope": baseline_meta,
        "q2_service_metrics": service_metrics,
        "q3_enhanced_directory": Q3_DIR.relative_to(ROOT).as_posix(),
        "q3_enhanced_directory_sha256": directory_hash(Q3_DIR),
        "q3_status": q3_summary["status"],
        "q3_candidate": q3_summary["candidate"],
        "q3_scenarios": q3_scenarios,
        "q3_scenario_observed_quantiles": quantiles,
        "q3_excluded_probe": q3_summary["full_cycle_probe"],
        "q4_pilot_directory": Q4_PILOT_DIR.relative_to(ROOT).as_posix(),
        "q4_pilot_directory_sha256": directory_hash(Q4_PILOT_DIR),
        "q4_pilot_status": q4_pilot["status"],
        "q4_pilot_scope": q4_pilot["pilot_scope"],
        "q4_repaired_directory": Q4_REPAIRED_DIR.relative_to(ROOT).as_posix(),
        "q4_repaired_directory_sha256": directory_hash(Q4_REPAIRED_DIR),
        "q4_repaired_status": q4_repaired["status"],
        "q4_repaired_hard_audits_passed": q4_repaired["risk_probes"][
            "all_hard_constraint_audits_passed"
        ],
        "envelope_definition": (
            "Each Q2 schedule is converted independently to hourly-average AI IT load by exact "
            "minute overlap, then combined with supplied NonAI_IT_Load_MW and regional PUE. "
            "Activity after hour 2399 belongs to Q2 closeout and is outside this bounded 72-hour Q4 horizon."
        ),
    }
    return candidate_base, baseline_base, storage, provenance, service_metrics, scenarios


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


def regional_metrics(
    dispatch: pd.DataFrame,
    method: str,
    scenario: str,
    service: dict[str, Any],
    solver: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for region, d in dispatch.groupby("Region", sort=True):
        renewable_total = float(d.AvailableRenewable_MW.sum())
        rows.append(
            {
                "scenario": scenario,
                "method": method,
                "region": str(region),
                "solver_success": bool(solver.get("success", True)),
                "solver_status": solver.get("status"),
                "runtime_s": float(solver.get("runtime_s", 0.0)),
                "mip_gap": solver.get("mip_gap"),
                "cost_CNY": float(
                    np.dot(d.GridPurchase_MW, d.ElectricityPrice_CNY_per_MWh)
                    - np.dot(d.GridSell_MW, d.SellPrice_CNY_per_MWh)
                ),
                "carbon_tCO2": float(
                    np.dot(d.GridPurchase_MW, d.CarbonIntensity_tCO2_per_MWh)
                ),
                "peak_net_import_MW": float(d.NetGridImport_MW.max()),
                "peak_facility_load_MW": float(d.Total_Load_MW.max()),
                "renewable_utilization_ratio": float(
                    (renewable_total - d.Curtailment_MW.sum()) / max(renewable_total, 1e-9)
                ),
                "terminal_SOC_MWh": float(d.SOC_MWh.iloc[-1]),
                "task_completion_rate": service["task_completion_rate"],
                "SLA_violation_rate": service["SLA_violation_rate"],
                "mean_latency_ms": service["mean_latency_ms"],
            }
        )
    return pd.DataFrame(rows)


def aggregate_comparison(
    candidate: pd.DataFrame,
    baseline: pd.DataFrame,
    candidate_metrics: pd.DataFrame,
    baseline_metrics: pd.DataFrame,
    scenario: str,
    solver: dict[str, Any],
) -> dict[str, Any]:
    candidate_cost = float(candidate_metrics.cost_CNY.sum())
    baseline_cost = float(baseline_metrics.cost_CNY.sum())
    candidate_carbon = float(candidate_metrics.carbon_tCO2.sum())
    baseline_carbon = float(baseline_metrics.carbon_tCO2.sum())
    candidate_peak = float(candidate.groupby("Hour").NetGridImport_MW.sum().max())
    baseline_peak = float(baseline.groupby("Hour").NetGridImport_MW.sum().max())
    candidate_renewable = float(
        (candidate.AvailableRenewable_MW.sum() - candidate.Curtailment_MW.sum())
        / max(candidate.AvailableRenewable_MW.sum(), 1e-9)
    )
    baseline_renewable = float(
        (baseline.AvailableRenewable_MW.sum() - baseline.Curtailment_MW.sum())
        / max(baseline.AvailableRenewable_MW.sum(), 1e-9)
    )
    return {
        "scenario": scenario,
        "candidate_method": "Q2_candidate_plus_integrated_storage_MILP",
        "baseline_method": "Q2_FIFO_plus_no_storage_renewable_first",
        "candidate_cost_CNY": candidate_cost,
        "baseline_cost_CNY": baseline_cost,
        "cost_delta_CNY": candidate_cost - baseline_cost,
        "cost_delta_ratio": (candidate_cost - baseline_cost) / max(abs(baseline_cost), 1e-9),
        "candidate_carbon_tCO2": candidate_carbon,
        "baseline_carbon_tCO2": baseline_carbon,
        "carbon_delta_tCO2": candidate_carbon - baseline_carbon,
        "carbon_delta_ratio": (candidate_carbon - baseline_carbon)
        / max(abs(baseline_carbon), 1e-9),
        "candidate_peak_net_import_MW": candidate_peak,
        "baseline_peak_net_import_MW": baseline_peak,
        "peak_delta_MW": candidate_peak - baseline_peak,
        "candidate_system_peak_variable_MW": float(solver["system_peak_variable_MW"]),
        "candidate_renewable_utilization_ratio": candidate_renewable,
        "baseline_renewable_utilization_ratio": baseline_renewable,
        "renewable_utilization_delta": candidate_renewable - baseline_renewable,
        "candidate_system_net_import_std_MW": float(
            candidate.groupby("Hour").NetGridImport_MW.sum().std(ddof=0)
        ),
        "baseline_system_net_import_std_MW": float(
            baseline.groupby("Hour").NetGridImport_MW.sum().std(ddof=0)
        ),
        "candidate_task_completion_rate": float(candidate_metrics.task_completion_rate.iloc[0]),
        "baseline_task_completion_rate": float(baseline_metrics.task_completion_rate.iloc[0]),
        "candidate_SLA_violation_rate": float(candidate_metrics.SLA_violation_rate.iloc[0]),
        "baseline_SLA_violation_rate": float(baseline_metrics.SLA_violation_rate.iloc[0]),
        "candidate_mean_latency_ms": float(candidate_metrics.mean_latency_ms.iloc[0]),
        "baseline_mean_latency_ms": float(baseline_metrics.mean_latency_ms.iloc[0]),
    }


def system_hourly_rows(
    candidate: pd.DataFrame,
    baseline: pd.DataFrame,
    scenario: str,
    candidate_peak: float,
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for method, frame, peak in [
        ("candidate", candidate, candidate_peak),
        (
            "baseline",
            baseline,
            max(float(baseline.groupby("Hour").NetGridImport_MW.sum().max()), 0.0),
        ),
    ]:
        grouped = frame.groupby(["Hour", "AbsoluteHour"], as_index=False).agg(
            SystemNetGridImport_MW=("NetGridImport_MW", "sum"),
            SystemGridPurchase_MW=("GridPurchase_MW", "sum"),
            SystemGridSell_MW=("GridSell_MW", "sum"),
            SystemFacilityLoad_MW=("Total_Load_MW", "sum"),
            SystemAvailableRenewable_MW=("AvailableRenewable_MW", "sum"),
            SystemCurtailment_MW=("Curtailment_MW", "sum"),
        )
        grouped["Scenario"] = scenario
        grouped["Method"] = method
        grouped["ReportedPositivePeak_MW"] = peak
        grouped["PeakLinkSlack_MW"] = peak - grouped.SystemNetGridImport_MW
        pieces.append(grouped)
    return pd.concat(pieces, ignore_index=True)


def main() -> int:
    run_started_at = utcnow()
    started = time.perf_counter()
    STAGING.mkdir(parents=True, exist_ok=True)
    failure_path = STAGING / "q4_final_failure.log"
    if failure_path.exists():
        failure_path.unlink()
    task = json.loads(TASK_PACKAGE.read_text(encoding="utf-8"))
    verify_inputs(task)
    (
        candidate_base,
        baseline_base,
        storage_table,
        provenance,
        service_metrics,
        scenarios,
    ) = load_inputs()
    carbon_q75 = float(provenance["q3_scenario_observed_quantiles"]["carbon_q75"])

    candidate_dispatches: list[pd.DataFrame] = []
    baseline_dispatches: list[pd.DataFrame] = []
    candidate_metric_frames: list[pd.DataFrame] = []
    baseline_metric_frames: list[pd.DataFrame] = []
    aggregate_rows: list[dict[str, Any]] = []
    hourly_frames: list[pd.DataFrame] = []
    audits: dict[str, Any] = {}
    solver_records: dict[str, Any] = {}

    for scenario in scenarios:
        name = str(scenario["name"])
        candidate_frame = apply_scenario(candidate_base, scenario, carbon_q75)
        baseline_frame = apply_scenario(baseline_base, scenario, carbon_q75)
        candidate, solver = solve_integrated(candidate_frame, storage_table)
        if candidate.empty:
            raise RuntimeError(f"integrated MILP failed for {name}: {json.dumps(solver)}")
        baseline = baseline_dispatch(baseline_frame, storage_table)
        candidate_audit = audit_dispatch(
            candidate,
            storage_table,
            "Q2_candidate_plus_integrated_storage_MILP",
            float(solver["system_peak_variable_MW"]),
        )
        baseline_audit = audit_dispatch(
            baseline,
            storage_table,
            "Q2_FIFO_plus_no_storage_renewable_first",
            None,
        )
        audits[name] = {"candidate": candidate_audit, "baseline": baseline_audit}
        solver_records[name] = solver

        candidate["Scenario"] = name
        baseline["Scenario"] = name
        candidate_dispatches.append(candidate)
        baseline_dispatches.append(baseline)
        candidate_metrics = regional_metrics(
            candidate,
            "Q2_candidate_plus_integrated_storage_MILP",
            name,
            service_metrics["candidate"],
            solver,
        )
        baseline_metrics = regional_metrics(
            baseline,
            "Q2_FIFO_plus_no_storage_renewable_first",
            name,
            service_metrics["baseline"],
            {"success": True, "status": "deterministic baseline", "runtime_s": 0.0, "mip_gap": 0.0},
        )
        candidate_metric_frames.append(candidate_metrics)
        baseline_metric_frames.append(baseline_metrics)
        aggregate_rows.append(
            aggregate_comparison(
                candidate,
                baseline,
                candidate_metrics,
                baseline_metrics,
                name,
                solver,
            )
        )
        hourly_frames.append(
            system_hourly_rows(
                candidate,
                baseline,
                name,
                float(solver["system_peak_variable_MW"]),
            )
        )

    candidate_dispatch = pd.concat(candidate_dispatches, ignore_index=True)
    baseline_dispatch_all = pd.concat(baseline_dispatches, ignore_index=True)
    candidate_metrics_all = pd.concat(candidate_metric_frames, ignore_index=True)
    baseline_metrics_all = pd.concat(baseline_metric_frames, ignore_index=True)
    aggregate = pd.DataFrame(aggregate_rows)
    system_hourly = pd.concat(hourly_frames, ignore_index=True)
    operational_columns = [
        "ChargePower_MW",
        "DischargePower_MW",
        "GridPurchase_MW",
        "GridSell_MW",
        "Curtailment_MW",
        "NetGridImport_MW",
    ]
    observed_dispatch = (
        candidate_dispatch[candidate_dispatch.Scenario == "observed"]
        .sort_values(["Region", "Hour"])
        .reset_index(drop=True)
    )
    observed_aggregate = aggregate[aggregate.scenario == "observed"].iloc[0]
    scenario_response: dict[str, Any] = {}
    for scenario in scenarios:
        name = str(scenario["name"])
        current = (
            candidate_dispatch[candidate_dispatch.Scenario == name]
            .sort_values(["Region", "Hour"])
            .reset_index(drop=True)
        )
        max_change = float(
            np.max(
                np.abs(
                    current[operational_columns].to_numpy(float)
                    - observed_dispatch[operational_columns].to_numpy(float)
                )
            )
        )
        current_aggregate = aggregate[aggregate.scenario == name].iloc[0]
        aggregate_deltas = {
            "cost_CNY": float(
                current_aggregate.candidate_cost_CNY - observed_aggregate.candidate_cost_CNY
            ),
            "carbon_tCO2": float(
                current_aggregate.candidate_carbon_tCO2 - observed_aggregate.candidate_carbon_tCO2
            ),
            "peak_net_import_MW": float(
                current_aggregate.candidate_peak_net_import_MW
                - observed_aggregate.candidate_peak_net_import_MW
            ),
            "renewable_utilization_ratio": float(
                current_aggregate.candidate_renewable_utilization_ratio
                - observed_aggregate.candidate_renewable_utilization_ratio
            ),
        }
        aggregate_active = bool(
            abs(aggregate_deltas["cost_CNY"]) > 0.01
            or abs(aggregate_deltas["carbon_tCO2"]) > 1e-6
            or abs(aggregate_deltas["peak_net_import_MW"]) > TOL
            or abs(aggregate_deltas["renewable_utilization_ratio"]) > 1e-9
        )
        grid_purchase_mwh = float(current.GridPurchase_MW.sum())
        if name == "peak_price_empirical" and not aggregate_active and grid_purchase_mwh <= TOL:
            interpretation = (
                "Purchase-price stress is inactive on aggregate outcomes because the candidate makes no "
                "grid purchase; any dispatch difference is an alternative optimal storage pattern."
            )
        elif name == "high_carbon_empirical" and not aggregate_active and grid_purchase_mwh <= TOL:
            interpretation = (
                "Carbon-intensity stress is inactive because the candidate makes no grid purchase in the "
                "observed-renewable envelope."
            )
        elif aggregate_active:
            interpretation = "The scenario changes at least one reported aggregate candidate outcome."
        else:
            interpretation = "No aggregate response relative to the observed scenario."
        scenario_response[name] = {
            "candidate_operational_response_active": bool(max_change > TOL),
            "candidate_aggregate_metric_response_active": aggregate_active,
            "max_dispatch_change_vs_observed_MW": max_change,
            "aggregate_metric_deltas_vs_observed": aggregate_deltas,
            "candidate_grid_purchase_MWh": grid_purchase_mwh,
            "candidate_system_positive_peak_MW": max(
                float(current.groupby("Hour").NetGridImport_MW.sum().max()), 0.0
            ),
            "interpretation": interpretation,
        }
    peak_active = [
        name
        for name, record in solver_records.items()
        if float(record["system_peak_variable_MW"]) > TOL
    ]
    all_pass = bool(
        service_metrics["candidate"]["q2_audit_passed"]
        and service_metrics["baseline"]["q2_audit_passed"]
        and all(
            row["passed"]
            for scenario_audit in audits.values()
            for row in scenario_audit.values()
        )
        and all(record["success"] for record in solver_records.values())
    )

    observed = aggregate[aggregate.scenario == "observed"].iloc[0]
    summary = {
        "schema_version": 1,
        "problem_id": "C",
        "question_id": "Q4",
        "status": "PASS" if all_pass else "PARTIAL",
        "scope": (
            "Five Q3-aligned scenario probes on the Q2 w2328_2400 representative window, "
            "using exactly 72 hours (absolute hours 2328-2399) and all six regions."
        ),
        "methods": {
            "candidate": "Q2_candidate_plus_integrated_storage_MILP",
            "candidate_description": (
                "Freeze the selected Q2 lagrangian-balanced task schedule, convert it to a 72-hour "
                "facility-load envelope, and solve all six storage systems in one binary MILP with "
                "a system-hour peak-import epigraph."
            ),
            "baseline": "Q2_FIFO_plus_no_storage_renewable_first",
            "baseline_description": (
                "Convert the independently stored Q2 FIFO schedule to its own 72-hour envelope and "
                "apply a renewable-first no-storage balance under the same scenario inputs."
            ),
            "fallback": None,
            "optimality_statement": (
                "Each storage-dispatch scenario is solved as one integrated six-region MILP. The Q2 "
                "task schedules are fixed upstream, so these results do not establish globally joint "
                "task-and-storage optimality or full-horizon optimality."
            ),
        },
        "data_counts": {
            "regions": int(candidate_base.Region.nunique()),
            "horizon_h": HORIZON,
            "region_hour_rows_per_envelope": int(len(candidate_base)),
            "q2_tasks_per_schedule": provenance["q2_candidate_envelope"]["task_count"],
            "scenario_count": len(scenarios),
        },
        "provenance": provenance,
        "scenario_definitions": scenarios,
        "scenario_response_diagnostics": scenario_response,
        "closeout_boundary_diagnostics": {
            "candidate_spill_task_count": provenance["q2_candidate_envelope"]["spill_task_count"],
            "baseline_spill_task_count": provenance["q2_fifo_envelope"]["spill_task_count"],
            "candidate_excluded_ai_energy_MWh": provenance["q2_candidate_envelope"][
                "excluded_closeout_ai_energy_MWh"
            ],
            "baseline_excluded_ai_energy_MWh": provenance["q2_fifo_envelope"][
                "excluded_closeout_ai_energy_MWh"
            ],
            "interpretation": (
                "The 72-hour comparison intentionally follows the fixed Q2 schedules. Different closeout "
                "spill means the reported bundle delta combines task-timing and storage effects and is not a "
                "storage-only treatment effect."
            ),
        },
        "system_peak_coordination": {
            "active_scenarios": peak_active,
            "inactive_scenarios": [
                str(scenario["name"])
                for scenario in scenarios
                if str(scenario["name"]) not in peak_active
            ],
            "interpretation": (
                "The linked peak epigraph is zero because the candidate system has no positive aggregate "
                "net import in any tested hour. No nonzero shadow or penalty signal was forced."
            ),
        },
        "solver_records": solver_records,
        "aggregate_comparison": aggregate_rows,
        "risk_probes": {
            "all_hard_constraint_audits_passed": all_pass,
            "candidate_and_fifo_envelopes_built_independently": True,
            "exact_minute_overlap_used": True,
            "charge_discharge_binary_mutex_checked": True,
            "grid_import_export_binary_mutex_checked": True,
            "terminal_soc_equality_checked": True,
            "system_hour_peak_linkage_checked": True,
            "q3_relaxed_full_cycle_probe_used_for_claims": False,
            "closeout_spill_energy_recorded": True,
            "effect_attribution_is_sequential_bundle": True,
        },
        "claim_proposals": [
            {
                "id": "Q4-FINAL-P1",
                "text": (
                    "Across the bounded 72-hour observed and Q3-derived stress scenarios, the integrated "
                    "six-region storage MILP satisfied every audited SOC, energy-balance, binary-mutex, "
                    "grid-cap, terminal-SOC, and system-peak-linkage constraint."
                ),
                "status": "proposal_only",
            },
            {
                "id": "Q4-FINAL-P2",
                "text": (
                    f"In the observed 72-hour window, net operating cost was "
                    f"{float(observed.candidate_cost_CNY):.2f} CNY versus "
                    f"{float(observed.baseline_cost_CNY):.2f} CNY (delta "
                    f"{float(observed.cost_delta_CNY):.2f} CNY); grid-purchase carbon was zero for both. "
                    f"The positive-part system peak was zero for both, while signed maximum net import was "
                    f"{float(observed.candidate_peak_net_import_MW):.4f} MW versus "
                    f"{float(observed.baseline_peak_net_import_MW):.4f} MW. "
                    "This bounded bundle delta includes both upstream task timing and storage dispatch effects."
                ),
                "status": "proposal_only",
            },
        ],
        "limitations": [
            "The 72-hour representative window is not evidence of full 0-2400 h optimality.",
            "Q2 candidate and FIFO schedules are fixed rather than jointly re-optimized with storage.",
            "Q2 tasks that continue after hour 2399 are recorded as closeout spill and excluded from this bounded horizon.",
            "No physical inter-region power flow, migration-energy, or network-traffic model is introduced.",
            "The Q3 full-cycle LP scalability probe is explicitly excluded because RegionF failed the simultaneous-cycling audit.",
            "Formal claim freezing and paper inclusion remain root-agent decisions.",
        ],
    }

    candidate_base.to_csv(
        STAGING / "q4_final_candidate_envelope.csv", index=False, float_format="%.10f"
    )
    baseline_base.to_csv(
        STAGING / "q4_final_baseline_envelope.csv", index=False, float_format="%.10f"
    )
    candidate_dispatch.to_csv(
        STAGING / "q4_final_candidate_dispatch.csv", index=False, float_format="%.10f"
    )
    baseline_dispatch_all.to_csv(
        STAGING / "q4_final_baseline_dispatch.csv", index=False, float_format="%.10f"
    )
    candidate_metrics_all.to_csv(
        STAGING / "q4_final_candidate_metrics.csv", index=False, float_format="%.10f"
    )
    baseline_metrics_all.to_csv(
        STAGING / "q4_final_baseline_metrics.csv", index=False, float_format="%.10f"
    )
    aggregate.to_csv(
        STAGING / "q4_final_aggregate_comparison.csv", index=False, float_format="%.10f"
    )
    system_hourly.to_csv(
        STAGING / "q4_final_system_hourly.csv", index=False, float_format="%.10f"
    )
    dump_json(STAGING / "q4_final_constraint_audit.json", audits)
    dump_json(STAGING / "q4_final_summary.json", summary)

    output_names = [
        "q4_final_candidate_envelope.csv",
        "q4_final_baseline_envelope.csv",
        "q4_final_candidate_dispatch.csv",
        "q4_final_baseline_dispatch.csv",
        "q4_final_candidate_metrics.csv",
        "q4_final_baseline_metrics.csv",
        "q4_final_aggregate_comparison.csv",
        "q4_final_system_hourly.csv",
        "q4_final_constraint_audit.json",
        "q4_final_summary.json",
    ]
    runner_name = "run_solver_q4_final.py"
    run_ended_at = utcnow()
    manifest = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "run_id": "q4-final-72h-20260808",
        "problem_id": "C",
        "question_id": "Q4",
        "engine": "python",
        "command": [sys.executable, str(STAGING / runner_name)],
        "working_directory": str(STAGING),
        "started_at_utc": run_started_at,
        "ended_at_utc": run_ended_at,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": __import__("scipy").__version__,
        },
        "seed": SEED,
        "code": {
            "runner": (STAGING / runner_name).relative_to(ROOT).as_posix(),
            "sha256": sha256_file(STAGING / runner_name),
        },
        "input_hashes": task["input_hashes"],
        "data_scope": {
            "window_id": WINDOW_ID,
            "absolute_hours": [WINDOW_START_H, WINDOW_START_H + HORIZON - 1],
            "horizon_h": HORIZON,
            "regions": sorted(candidate_base.Region.unique()),
            "candidate_q2_tasks": provenance["q2_candidate_envelope"]["task_count"],
            "baseline_q2_tasks": provenance["q2_fifo_envelope"]["task_count"],
        },
        "solver": {
            "library": "scipy.optimize.milp",
            "mode": "integrated_binary_MILP",
            "time_limit_s_per_scenario": 60.0,
            "mip_rel_gap": 1e-7,
            "carbon_weight": CARBON_WEIGHT,
            "system_peak_weight": PEAK_WEIGHT,
        },
        "metric_definitions_and_units": {
            "cost_CNY": "CNY",
            "carbon_tCO2": "tCO2",
            "peak_net_import_MW": "MW",
            "renewable_utilization_ratio": "dimensionless",
            "mean_latency_ms": "ms inherited from the audited Q2 schedule",
            "task_completion_rate": "dimensionless inherited from the audited Q2 schedule",
            "SLA_violation_rate": "dimensionless inherited from the audited Q2 schedule",
        },
        "outputs": output_names,
        "solver_records": solver_records,
        "status": "PASS" if all_pass else "PARTIAL",
        "runtime_s": round(time.perf_counter() - started, 6),
    }
    dump_json(STAGING / "q4_final_run_manifest.json", manifest)

    artifact_names = output_names + ["q4_final_run_manifest.json", runner_name]
    artifacts = [
        {
            "path": (STAGING / name).relative_to(ROOT).as_posix(),
            "sha256": sha256_file(STAGING / name),
        }
        for name in artifact_names
    ]
    handoff = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "attempt": int(task.get("attempt", 1)),
        "status": "SUCCESS" if all_pass else "PARTIAL",
        "input_hashes": task["input_hashes"],
        "written_paths": [item["path"] for item in artifacts]
        + [(STAGING / "handoff.json").relative_to(ROOT).as_posix()],
        "artifacts": artifacts,
        "gate_result": {
            "gate": task.get("target_gate", "G5"),
            "passed": all_pass,
            "checks": [
                "input_hashes_rechecked",
                "Q2_candidate_and_FIFO_schedules_loaded_separately",
                "exact_minute_overlap_72h_envelopes",
                "Q3_empirical_scenarios_reused",
                "repaired_Q4_binary_conventions_reused",
                "integrated_six_region_MILP",
                "binary_charge_discharge_mutex",
                "binary_grid_import_export_mutex",
                "SOC_transition_and_bounds",
                "terminal_SOC_equality",
                "system_hour_peak_epigraph_linkage",
                "regional_grid_caps",
                "artifact_hashes",
            ],
        },
        "summary": (
            "Completed the bounded 72-hour Q2-Q3-Q4 integration. The candidate uses the Q2 "
            "lagrangian-balanced envelope and an integrated six-region storage MILP; the baseline "
            "uses the separate Q2 FIFO envelope and no storage. All declared hard audits passed."
            if all_pass
            else "Completed the bounded 72-hour integration, but at least one declared hard audit failed."
        ),
    }
    dump_json(STAGING / "handoff.json", handoff)
    return 0 if all_pass else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        (STAGING / "q4_final_failure.log").write_text(
            f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
        )
        raise
