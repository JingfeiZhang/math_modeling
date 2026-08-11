#!/usr/bin/env python
"""Audited Q3 rolling-window and terminal-SOC sensitivity experiment.

The script imports the frozen Q3 runner only for its model, metric, and audit
implementations. It writes all outputs to the current sprint staging folder.
No full-horizon relaxed LP probe is executed or used.
"""
from __future__ import annotations

import hashlib
import importlib.util
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
from scipy.sparse import lil_matrix, vstack


STAGING = Path(__file__).resolve().parent
ROOT = STAGING.parents[3]
SPRINT_ID = "sprint-20260808T101814701038Z"
TASK_ID = "solver-q3q4"
TASK_PATH = ROOT / "sprints" / SPRINT_ID / "tasks" / "solver-q2.json"
Q3_RUNNER = ROOT / "sprints" / "sprint-20260808T023236665505Z" / "merged" / "solver-q3" / "run_solver_q3.py"
SEED = 20260808
TOL = 5e-5
MAX_HOURS = 2407


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def load_module(path: Path) -> Any:
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("frozen_q3_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Q3 runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_inputs(task: dict[str, Any]) -> None:
    failures: list[dict[str, Any]] = []
    for item in task.get("input_hashes", []):
        path = ROOT / str(item["path"])
        observed = sha256_file(path) if path.is_file() else None
        if observed != item.get("sha256"):
            failures.append(
                {
                    "path": item["path"],
                    "expected": item.get("sha256"),
                    "observed": observed,
                }
            )
    if failures:
        raise RuntimeError("stale or missing inputs: " + json.dumps(failures, ensure_ascii=False))


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float], float]:
    data = ROOT / "problems" / "C" / "data"
    region = pd.read_excel(data / "region_time_data.xlsx", sheet_name="region_time_data", engine="openpyxl")
    storage = pd.read_excel(data / "storage_information.xlsx", sheet_name="storage_information", engine="openpyxl")
    region = region.sort_values(["Region", "Hour"]).reset_index(drop=True)
    storage["Region"] = storage.Region.astype(str)
    required = {"Baseline_AI_IT_Load_MW", "NonAI_IT_Load_MW", "Total_Load_MW", "IT_Load_MW"}
    missing = required - set(region.columns)
    if missing:
        raise ValueError(f"missing authoritative Q3 load columns: {sorted(missing)}")
    derived_it = region.Baseline_AI_IT_Load_MW.astype(float) + region.NonAI_IT_Load_MW.astype(float)
    region["Derived_IT_Load_MW"] = derived_it
    pue_by_region: dict[str, float] = {}
    for name, group in region.groupby("Region", sort=True):
        positive = group.loc[group.Derived_IT_Load_MW > 1e-9]
        pue_by_region[str(name)] = float(
            np.median(positive.Total_Load_MW.astype(float) / positive.Derived_IT_Load_MW.astype(float))
        )
    region["Inferred_PUE"] = region.Region.astype(str).map(pue_by_region)
    region["RecomputedTotalLoad_MW"] = region.Derived_IT_Load_MW * region.Inferred_PUE
    facility_residual = float(
        np.max(np.abs(region.Total_Load_MW.astype(float) - region.RecomputedTotalLoad_MW.astype(float)))
    )
    return region, storage, pue_by_region, facility_residual


def solve_with_terminal(
    q3: Any,
    frame: pd.DataFrame,
    storage: pd.Series,
    initial_soc: float,
    terminal_policy: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Solve the frozen model; add only an equality row for the sensitivity variant."""
    baseline = q3.build_baseline(frame, storage, initial_soc)
    objective, bounds, constraints, integrality, slices = q3.make_model(
        frame, storage, baseline, initial_soc, initial_soc
    )
    if terminal_policy == "equality":
        extra = lil_matrix((1, len(objective)), dtype=float)
        extra[0, slices["soc"].start + len(frame) - 1] = 1.0
        matrix = vstack([constraints.A, extra.tocsr()]).tocsr()
        lower = np.r_[constraints.lb, initial_soc]
        upper = np.r_[constraints.ub, initial_soc]
        constraints = LinearConstraint(matrix, lower, upper)
    elif terminal_policy != "lower_bound":
        raise ValueError(f"unknown terminal policy: {terminal_policy}")
    started = time.perf_counter()
    result = milp(
        c=objective,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options={"presolve": True, "time_limit": float(q3.TIME_LIMIT_S), "mip_rel_gap": 1e-7},
    )
    runtime_s = time.perf_counter() - started
    info: dict[str, Any] = {
        "status": str(result.message),
        "success": bool(result.success and result.x is not None),
        "runtime_s": float(runtime_s),
        "mip_gap": None if result.x is None else float(getattr(result, "mip_gap", 0.0) or 0.0),
        "objective": None if result.fun is None else float(result.fun),
        "mip_node_count": None if result.x is None else int(getattr(result, "mip_node_count", 0) or 0),
        "solver_mode": "binary_MILP_terminal_equality" if terminal_policy == "equality" else "binary_MILP",
    }
    if not info["success"]:
        return pd.DataFrame(), info
    data = frame.sort_values("Hour").reset_index(drop=True)
    x = result.x
    charge = x[slices["charge"]]
    discharge = x[slices["discharge"]]
    soc = x[slices["soc"]]
    ren_load = x[slices["renewable_to_load"]]
    ren_charge = x[slices["renewable_charge"]]
    grid_charge = x[slices["grid_charge"]]
    grid_load = x[slices["grid_load"]]
    sell = x[slices["sell"]]
    curtail = x[slices["curtail"]]
    dispatch = pd.DataFrame(
        {
            "Hour": data.Hour.astype(int),
            "Region": data.Region.astype(str),
            "AvailableRenewable_MW": data.AvailableRenewable_MW.astype(float),
            "Total_Load_MW": data.RecomputedTotalLoad_MW.astype(float),
            "ElectricityPrice_CNY_per_MWh": data.ElectricityPrice_CNY_per_MWh.astype(float),
            "SellPrice_CNY_per_MWh": data.SellPrice_CNY_per_MWh.astype(float),
            "CarbonIntensity_tCO2_per_MWh": data.CarbonIntensity_tCO2_per_MWh.astype(float),
            "ChargePower_MW": charge,
            "DischargePower_MW": discharge,
            "SOC_MWh": soc,
            "RenewableToLoad_MW": ren_load,
            "RenewableCharge_MW": ren_charge,
            "GridCharge_MW": grid_charge,
            "GridPurchase_MW": grid_load + grid_charge,
            "GridLoadPurchase_MW": grid_load,
            "GridSell_MW": sell,
            "Curtailment_MW": curtail,
            "NetGridImport_MW": grid_load + grid_charge - sell,
            "GridEnergyForCost_MW": grid_load + grid_charge,
            "ChargeMode": np.rint(x[slices["mode"]]).astype(int),
        }
    )
    return dispatch, info


def aggregate_setting(
    q3: Any,
    region: pd.DataFrame,
    storage: pd.DataFrame,
    setting: dict[str, Any],
    facility_residual_global: float,
) -> dict[str, Any]:
    block_h = int(setting["block_h"])
    terminal_policy = str(setting["terminal_policy"])
    regions = sorted(region.Region.astype(str).unique())
    candidate_parts: list[pd.DataFrame] = []
    block_audits: list[dict[str, Any]] = []
    solver_records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    start_time = time.perf_counter()
    for name in regions:
        st = storage.loc[storage.Region.astype(str) == name].iloc[0]
        all_rows = region.loc[region.Region.astype(str) == name].sort_values("Hour").reset_index(drop=True)
        if len(all_rows) != MAX_HOURS:
            raise ValueError(f"{name} has {len(all_rows)} rows instead of {MAX_HOURS}")
        current_soc = float(st.InitialSOC_MWh)
        start = 0
        while start < len(all_rows):
            horizon = min(block_h, len(all_rows) - start)
            frame = all_rows.iloc[start : start + horizon].copy()
            dispatch, solver = solve_with_terminal(q3, frame, st, current_soc, terminal_policy)
            record = {
                "setting_id": setting["setting_id"],
                "region": name,
                "window_start_h": int(start),
                "horizon_h": int(horizon),
                "block_h": block_h,
                "terminal_policy": terminal_policy,
                **solver,
            }
            solver_records.append(record)
            if dispatch.empty or not solver.get("success"):
                failures.append({**record, "reason": "solver_failed_or_infeasible"})
                break
            dispatch = dispatch.assign(
                Evaluation="sensitivity_block",
                Scenario="observed",
                WindowStart_h=int(start),
                SensitivitySetting=setting["setting_id"],
            )
            audit = q3.audit(
                dispatch,
                st,
                "q3_sensitivity_binary_MILP",
                horizon,
                current_soc,
                current_soc,
                "sensitivity_block",
                start,
                "observed",
            )
            terminal_error = abs(float(dispatch.SOC_MWh.iloc[-1]) - current_soc)
            audit["setting_id"] = setting["setting_id"]
            audit["terminal_policy"] = terminal_policy
            audit["terminal_equality_error_MWh"] = float(terminal_error)
            audit["passed"] = bool(audit["passed"] and (terminal_policy != "equality" or terminal_error <= TOL))
            block_audits.append(audit)
            if not audit["passed"]:
                failures.append({
                    **record,
                    "reason": "hard_audit_failed",
                    "audit": audit,
                })
                break
            candidate_parts.append(dispatch)
            current_soc = float(dispatch.SOC_MWh.iloc[-1])
            start += horizon
    elapsed = time.perf_counter() - start_time
    all_complete = not failures and len(solver_records) > 0 and all(bool(r.get("success")) for r in solver_records)
    candidate = pd.concat(candidate_parts, ignore_index=True) if all_complete else pd.DataFrame()
    candidate_aggregate_audit: dict[str, Any] | None = None
    baseline_aggregate_audits: list[dict[str, Any]] = []
    aggregate_metrics: list[dict[str, Any]] = []
    if all_complete:
        candidate = candidate.sort_values(["Region", "Hour"]).reset_index(drop=True)
        for name in regions:
            st = storage.loc[storage.Region.astype(str) == name].iloc[0]
            cand = candidate.loc[candidate.Region.astype(str) == name].sort_values("Hour").reset_index(drop=True)
            base = q3.build_baseline(cand.assign(RecomputedTotalLoad_MW=cand.Total_Load_MW), st, float(st.InitialSOC_MWh))
            c_audit = q3.audit(
                cand,
                st,
                "q3_sensitivity_binary_MILP",
                len(cand),
                float(st.InitialSOC_MWh),
                float(st.InitialSOC_MWh),
                "sensitivity_aggregate",
                0,
                "observed",
            )
            c_audit["setting_id"] = setting["setting_id"]
            c_audit["terminal_policy"] = terminal_policy
            c_audit["terminal_equality_error_MWh"] = float(abs(float(cand.SOC_MWh.iloc[-1]) - float(st.InitialSOC_MWh)))
            c_audit["passed"] = bool(c_audit["passed"] and (terminal_policy != "equality" or c_audit["terminal_equality_error_MWh"] <= TOL))
            candidate_aggregate_audit = candidate_aggregate_audit or {"audits": []}
            candidate_aggregate_audit["audits"].append(c_audit)
            b_audit = q3.audit(
                base,
                st,
                "no_storage_renewable_first",
                len(base),
                float(st.InitialSOC_MWh),
                float(st.InitialSOC_MWh),
                "sensitivity_aggregate",
                0,
                "observed",
            )
            b_audit["setting_id"] = setting["setting_id"]
            baseline_aggregate_audits.append(b_audit)
            c_info = {
                "status": "aggregate",
                "success": True,
                "runtime_s": float(sum(float(r.get("runtime_s") or 0.0) for r in solver_records if r["setting_id"] == setting["setting_id"])),
                "mip_gap": float(max(float(r.get("mip_gap") or 0.0) for r in solver_records if r["setting_id"] == setting["setting_id"])),
                "solver_mode": "rolling_binary_MILP_sensitivity",
            }
            cm = q3.metrics(cand, st, "q3_sensitivity_binary_MILP", len(cand), c_info, "sensitivity_aggregate", 0, "observed", float(st.InitialSOC_MWh))
            bm = q3.metrics(base, st, "no_storage_renewable_first", len(base), {"status": "baseline", "success": True, "runtime_s": 0.0, "mip_gap": None, "solver_mode": "baseline"}, "sensitivity_aggregate", 0, "observed", float(st.InitialSOC_MWh))
            aggregate_metrics.append({
                "setting_id": setting["setting_id"],
                "region": name,
                "block_h": block_h,
                "terminal_policy": terminal_policy,
                "candidate_cost_CNY": float(cm["cost_CNY"]),
                "baseline_cost_CNY": float(bm["cost_CNY"]),
                "candidate_carbon_tCO2": float(cm["carbon_tCO2"]),
                "baseline_carbon_tCO2": float(bm["carbon_tCO2"]),
                "candidate_peak_net_import_MW": float(cm["peak_net_import_MW"]),
                "baseline_peak_net_import_MW": float(bm["peak_net_import_MW"]),
                "candidate_renewable_utilization_ratio": float(cm["renewable_utilization_ratio"]),
                "baseline_renewable_utilization_ratio": float(bm["renewable_utilization_ratio"]),
                "candidate_terminal_SOC_MWh": float(cm["terminal_SOC_MWh"]),
                "baseline_terminal_SOC_MWh": float(bm["terminal_SOC_MWh"]),
                "cost_delta_candidate_minus_baseline_CNY": float(cm["cost_CNY"] - bm["cost_CNY"]),
                "carbon_delta_candidate_minus_baseline_tCO2": float(cm["carbon_tCO2"] - bm["carbon_tCO2"]),
                "peak_delta_candidate_minus_baseline_MW": float(cm["peak_net_import_MW"] - bm["peak_net_import_MW"]),
            })
    candidate_audits_pass = bool(candidate_aggregate_audit and all(a.get("passed") for a in candidate_aggregate_audit["audits"]) and all(a.get("passed") for a in block_audits))
    baseline_audits_pass = bool(all(a.get("passed") for a in baseline_aggregate_audits)) if all_complete else False
    max_simultaneous_cd = float(max((a.get("checks", {}).get("simultaneous_charge_discharge_MW", 0.0) for a in block_audits), default=0.0))
    max_simultaneous_buy_sell = float(max((a.get("checks", {}).get("simultaneous_grid_buy_sell_MW", 0.0) for a in block_audits), default=0.0))
    max_soc_violation = float(max((max(a.get("checks", {}).get("soc_min_violation_MWh", 0.0), a.get("checks", {}).get("soc_max_violation_MWh", 0.0)) for a in block_audits), default=0.0))
    terminal_eq_error = float(max((a.get("terminal_equality_error_MWh", 0.0) for a in block_audits), default=0.0))
    eligible = bool(all_complete and candidate_audits_pass and baseline_audits_pass and max_simultaneous_cd <= TOL and max_simultaneous_buy_sell <= TOL and max_soc_violation <= TOL)
    return {
        "setting": setting,
        "regions": regions,
        "hours_per_region": MAX_HOURS,
        "block_count_total": int(len(solver_records)),
        "successful_block_solves": int(sum(bool(r.get("success")) for r in solver_records)),
        "runtime_s": float(elapsed),
        "solver_records": solver_records,
        "block_audits": block_audits,
        "candidate_aggregate_audit": candidate_aggregate_audit,
        "baseline_aggregate_audits": baseline_aggregate_audits,
        "aggregate_metrics": aggregate_metrics,
        "failed_or_infeasible_cases": failures,
        "max_simultaneous_charge_discharge_MW": max_simultaneous_cd,
        "max_simultaneous_grid_buy_sell_MW": max_simultaneous_buy_sell,
        "max_soc_violation_MWh": max_soc_violation,
        "max_terminal_equality_error_MWh": terminal_eq_error,
        "candidate_audits_passed": candidate_audits_pass,
        "baseline_audits_passed": baseline_audits_pass,
        "complete_coverage": bool(all_complete and candidate.empty is False and len(candidate) == len(regions) * MAX_HOURS),
        "eligible_for_model_review": eligible,
        "eligibility_rule": "all blocks successful; exact six-region 0-2406 coverage; candidate and baseline audits pass; no simultaneous charge/discharge or grid buy/sell; SOC and grid bounds pass; terminal equality passes when requested",
        "facility_load_residual_boundary_MW": facility_residual_global,
    }


def main() -> int:
    STAGING.mkdir(parents=True, exist_ok=True)
    task = json.loads(TASK_PATH.read_text(encoding="utf-8"))
    verify_inputs(task)
    q3 = load_module(Q3_RUNNER)
    region, storage, pue, facility_residual_global = load_inputs()
    settings = [
        {"setting_id": "current_H168_lower_bound", "block_h": 168, "terminal_policy": "lower_bound"},
        {"setting_id": "near_H144_lower_bound", "block_h": 144, "terminal_policy": "lower_bound"},
        {"setting_id": "near_H192_lower_bound", "block_h": 192, "terminal_policy": "lower_bound"},
        {"setting_id": "near_H168_terminal_equality", "block_h": 168, "terminal_policy": "equality"},
    ]
    results = [aggregate_setting(q3, region, storage, setting, facility_residual_global) for setting in settings]
    rows = [row for result in results for row in result["aggregate_metrics"]]
    pd.DataFrame(rows).to_csv(STAGING / "q3_sensitivity.csv", index=False, float_format="%.12f")
    summary = {
        "schema_version": 1,
        "sprint_id": SPRINT_ID,
        "task_id": TASK_ID,
        "question_id": "Q3",
        "status": "SUCCESS" if all(r["eligible_for_model_review"] for r in results) else "PARTIAL",
        "method_source": "sprints/sprint-20260808T023236665505Z/merged/solver-q3/run_solver_q3.py",
        "method_source_sha256": sha256_file(Q3_RUNNER),
        "seed": SEED,
        "settings": results,
        "setting_count": len(results),
        "native_parameter_settings": [
            "current 168 h contiguous blocks with SOC_T >= SOC_start",
            "144 h contiguous blocks with SOC_T >= SOC_start",
            "192 h contiguous blocks with SOC_T >= SOC_start",
            "168 h contiguous blocks with SOC_T = SOC_start"
        ],
        "acceptance": {
            "all_six_regions": True,
            "exact_hours_per_region": MAX_HOURS,
            "no_full_horizon_relaxed_lp_run": True,
            "facility_load_residual_MW": facility_residual_global,
            "facility_load_exact_equality_claim_allowed": False,
            "current_269_of_270_boundary_preserved": True,
            "eligible_setting_ids": [r["setting"]["setting_id"] for r in results if r["eligible_for_model_review"]],
            "rejected_setting_ids": [r["setting"]["setting_id"] for r in results if not r["eligible_for_model_review"]],
        },
        "interpretation": {
            "primary_claim_eligible": False,
            "reason": "This is a sensitivity review. The existing frozen Q3 rolling policy remains the primary evidence until the root agent reviews this output and decides whether a variant merits a rerun and claim freeze.",
            "no_global_optimality": True,
            "no_causal_claim": True,
            "excluded_lp_probe": "RegionF full-horizon relaxed LP simultaneous charge/discharge remains permanently excluded."
        },
        "input_hashes": task["input_hashes"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    dump_json(STAGING / "q3_sensitivity_summary.json", summary)
    return 0


if __name__ == "__main__":
    main()
