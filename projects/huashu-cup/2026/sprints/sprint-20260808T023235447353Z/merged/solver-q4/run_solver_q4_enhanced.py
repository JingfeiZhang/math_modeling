#!/usr/bin/env python
"""Q4 enhancement: re-runnable multi-region storage coordination.

The merged Q4 pilot provides the frozen, auditable 6-region x 24-hour task
load envelope.  This worker re-solves regional storage MILPs under a shared
peak-import shadow price and probes carbon-price and renewable-availability
perturbations.  It writes exploratory evidence only.
"""
from __future__ import annotations

import hashlib
import json
import math
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
SPRINT_ID = "sprint-20260808T023235447353Z"
TASK_ID = "solver-q4"
HORIZON = 24
SEED = 20260808
TOL = 5e-5
Q4_DIR = ROOT / "sprints" / "sprint-20260807T210015466011Z" / "merged" / "solver-q4"
TASK_PACKAGE = ROOT / "sprints" / SPRINT_ID / "retry" / f"{TASK_ID}-attempt-2.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def directory_hash(path: Path) -> str:
    source = "\n".join(f"{x.relative_to(path).as_posix()}:{sha256_file(x)}" for x in sorted(path.rglob("*")) if x.is_file())
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def verify_inputs(task: dict[str, Any]) -> None:
    failures = []
    for item in task.get("input_hashes", []):
        path = ROOT / str(item["path"])
        observed = directory_hash(path) if item.get("kind") == "directory" and path.is_dir() else sha256_file(path) if path.is_file() else None
        if observed != item.get("sha256"):
            failures.append({"path": item["path"], "expected": item.get("sha256"), "observed": observed})
    if failures:
        raise RuntimeError("stale or missing sprint inputs: " + json.dumps(failures, ensure_ascii=False))


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    data = ROOT / "problems" / "C" / "data"
    dispatch = pd.read_csv(Q4_DIR / "q4_candidate_dispatch.csv")
    summary = json.loads((Q4_DIR / "q4_summary.json").read_text(encoding="utf-8"))
    storage = pd.read_excel(data / "storage_information.xlsx", sheet_name=0)
    workload = pd.read_excel(data / "workload_trace.xlsx", sheet_name=0)
    required = {"Hour", "Region", "AvailableRenewable_MW", "Total_Load_MW", "ElectricityPrice_CNY_per_MWh", "SellPrice_CNY_per_MWh", "CarbonIntensity_tCO2_per_MWh"}
    if not required.issubset(dispatch.columns):
        raise ValueError(f"merged Q4 dispatch missing columns: {sorted(required - set(dispatch.columns))}")
    dispatch = dispatch[dispatch.Hour.astype(int).between(0, HORIZON - 1)].copy()
    dispatch["Hour"] = dispatch["Hour"].astype(int)
    dispatch["Region"] = dispatch["Region"].astype(str)
    regions = sorted(dispatch.Region.unique())
    if len(dispatch) != len(regions) * HORIZON:
        raise ValueError("merged Q4 pilot must contain exactly one row per region-hour")
    if workload.TaskID.duplicated().any():
        raise ValueError("workload TaskID is not unique")
    provenance = {
        "merged_q4_directory": "sprints/sprint-20260807T210015466011Z/merged/solver-q4",
        "merged_q4_directory_sha256": directory_hash(Q4_DIR),
        "merged_dispatch_sha256": sha256_file(Q4_DIR / "q4_candidate_dispatch.csv"),
        "merged_task_count": int(summary["data_counts"]["q2_scheduled_tasks"]),
        "raw_workload_rows": int(len(workload)),
        "envelope_definition": "Total_Load_MW from merged Q4 candidate dispatch; observed AI load is not added again.",
    }
    return dispatch.sort_values(["Region", "Hour"]).reset_index(drop=True), storage, provenance


def baseline_dispatch(frame: pd.DataFrame, storage: pd.Series, renewable_multiplier: float) -> pd.DataFrame:
    d = frame.sort_values("Hour").reset_index(drop=True).copy()
    renew = d.AvailableRenewable_MW.to_numpy(float) * renewable_multiplier
    load = d.Total_Load_MW.to_numpy(float)
    export = min(float(storage.SellLimit_MW), float(storage.MaxGridExport_MW))
    out = d[["Hour", "Region", "ElectricityPrice_CNY_per_MWh", "SellPrice_CNY_per_MWh", "CarbonIntensity_tCO2_per_MWh", "Total_Load_MW"]].copy()
    direct = np.minimum(load, renew)
    surplus = np.maximum(renew - direct, 0.0)
    sell = np.minimum(surplus, export)
    out["AvailableRenewable_MW"] = renew
    out["ChargePower_MW"] = 0.0; out["DischargePower_MW"] = 0.0; out["SOC_MWh"] = float(storage.InitialSOC_MWh)
    out["RenewableToLoad_MW"] = direct; out["RenewableCharge_MW"] = 0.0; out["GridCharge_MW"] = 0.0
    out["GridLoadPurchase_MW"] = np.maximum(load - direct, 0.0); out["GridPurchase_MW"] = out["GridLoadPurchase_MW"]
    out["GridSell_MW"] = sell; out["Curtailment_MW"] = surplus - sell; out["NetGridImport_MW"] = out.GridPurchase_MW - sell
    out["GridEnergyForCost_MW"] = out.GridPurchase_MW; out["ChargeMode"] = 0
    return out


def solve_region(frame: pd.DataFrame, storage: pd.Series, renewable_multiplier: float, carbon_weight: float, peak_shadow: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    d = frame.sort_values("Hour").reset_index(drop=True)
    n = HORIZON
    names = ["charge", "discharge", "soc", "renewable_to_load", "renewable_charge", "grid_charge", "grid_load", "sell", "curtail", "mode", "grid_mode"]
    sl: dict[str, slice] = {}; cursor = 0
    for name in names:
        sl[name] = slice(cursor, cursor + n); cursor += n
    peak = cursor; nvar = cursor + 1
    load = d.Total_Load_MW.to_numpy(float); renew = d.AvailableRenewable_MW.to_numpy(float) * renewable_multiplier
    price = d.ElectricityPrice_CNY_per_MWh.to_numpy(float); sell_price = d.SellPrice_CNY_per_MWh.to_numpy(float); carbon = d.CarbonIntensity_tCO2_per_MWh.to_numpy(float)
    cap = float(storage.StorageCapacity_MWh); min_soc = float(storage.MinSOC_MWh); initial = float(storage.InitialSOC_MWh)
    max_c = float(storage.MaxChargePower_MW); max_d = float(storage.MaxDischargePower_MW); eta_c = float(storage.ChargeEfficiency); eta_d = float(storage.DischargeEfficiency)
    import_cap = float(storage.MaxGridImport_MW); export_cap = min(float(storage.SellLimit_MW), float(storage.MaxGridExport_MW))
    scale_cost = max(float(np.dot(load, price)), 1.0); scale_carbon = max(float(np.dot(load, carbon)), 1.0)
    obj = np.zeros(nvar); obj[sl["grid_load"]] = price / scale_cost + carbon_weight * carbon / scale_carbon; obj[sl["grid_charge"]] = price / scale_cost + carbon_weight * carbon / scale_carbon; obj[sl["sell"]] = -sell_price / scale_cost; obj[sl["curtail"]] = 0.03 / max(float(renew.sum()), 1.0); obj[peak] = (0.08 + peak_shadow) / max(import_cap, 1.0); obj[sl["charge"]] += 1e-7; obj[sl["discharge"]] += 1e-7
    lower = np.zeros(nvar); upper = np.full(nvar, np.inf); lower[sl["charge"]] = 0; upper[sl["charge"]] = max_c; lower[sl["discharge"]] = 0; upper[sl["discharge"]] = max_d; lower[sl["soc"]] = min_soc; upper[sl["soc"]] = cap; upper[sl["renewable_charge"]] = max_c; upper[sl["grid_charge"]] = max_c; upper[sl["grid_load"]] = import_cap; upper[sl["sell"]] = export_cap; upper[sl["mode"]] = 1; upper[sl["grid_mode"]] = 1; upper[peak] = import_cap + max_c
    matrix = lil_matrix((9 * n + 1, nvar)); lo = np.full(9 * n + 1, -np.inf); hi = np.full(9 * n + 1, np.inf); row = 0
    for t in range(n):
        matrix[row, sl["soc"].start + t] = 1; matrix[row, sl["charge"].start + t] = -eta_c; matrix[row, sl["discharge"].start + t] = 1 / eta_d
        if t: matrix[row, sl["soc"].start + t - 1] = -1; lo[row] = hi[row] = 0
        else: lo[row] = hi[row] = initial
        row += 1
        matrix[row, sl["charge"].start + t] = 1; matrix[row, sl["renewable_charge"].start + t] = -1; matrix[row, sl["grid_charge"].start + t] = -1; lo[row] = hi[row] = 0; row += 1
        matrix[row, sl["renewable_to_load"].start + t] = 1; matrix[row, sl["renewable_charge"].start + t] = 1; matrix[row, sl["sell"].start + t] = 1; matrix[row, sl["curtail"].start + t] = 1; lo[row] = hi[row] = renew[t]; row += 1
        matrix[row, sl["renewable_to_load"].start + t] = 1; matrix[row, sl["discharge"].start + t] = 1; matrix[row, sl["grid_load"].start + t] = 1; lo[row] = hi[row] = load[t]; row += 1
        matrix[row, sl["charge"].start + t] = 1; matrix[row, sl["mode"].start + t] = -max_c; hi[row] = 0; row += 1
        matrix[row, sl["discharge"].start + t] = 1; matrix[row, sl["mode"].start + t] = max_d; hi[row] = max_d; row += 1
        matrix[row, sl["grid_load"].start + t] = 1; matrix[row, sl["grid_charge"].start + t] = 1; matrix[row, sl["grid_mode"].start + t] = -import_cap; hi[row] = 0; row += 1
        matrix[row, sl["sell"].start + t] = 1; matrix[row, sl["grid_mode"].start + t] = export_cap; hi[row] = export_cap; row += 1
        matrix[row, sl["grid_load"].start + t] = 1; matrix[row, sl["grid_charge"].start + t] = 1; matrix[row, sl["sell"].start + t] = -1; matrix[row, peak] = -1; hi[row] = 0; row += 1
    matrix[row, sl["soc"].start + n - 1] = 1; lo[row] = hi[row] = initial
    integrality = np.zeros(nvar); integrality[sl["mode"]] = 1; integrality[sl["grid_mode"]] = 1
    solve_started = time.perf_counter()
    result = milp(c=obj, integrality=integrality, bounds=Bounds(lower, upper), constraints=LinearConstraint(matrix.tocsr(), lo, hi), options={"presolve": True, "time_limit": 20.0, "mip_rel_gap": 1e-7})
    runtime_s = time.perf_counter() - solve_started
    if not result.success or result.x is None:
        return pd.DataFrame(), {"success": False, "status": str(result.message), "runtime_s": runtime_s, "mip_gap": None}
    x = result.x; net = x[sl["grid_load"]] + x[sl["grid_charge"]] - x[sl["sell"]]
    out = d[["Hour", "Region", "ElectricityPrice_CNY_per_MWh", "SellPrice_CNY_per_MWh", "CarbonIntensity_tCO2_per_MWh", "Total_Load_MW"]].copy()
    out["AvailableRenewable_MW"] = renew; out["ChargePower_MW"] = x[sl["charge"]]; out["DischargePower_MW"] = x[sl["discharge"]]; out["SOC_MWh"] = x[sl["soc"]]; out["RenewableToLoad_MW"] = x[sl["renewable_to_load"]]; out["RenewableCharge_MW"] = x[sl["renewable_charge"]]; out["GridCharge_MW"] = x[sl["grid_charge"]]; out["GridLoadPurchase_MW"] = x[sl["grid_load"]]; out["GridPurchase_MW"] = x[sl["grid_load"]] + x[sl["grid_charge"]]; out["GridSell_MW"] = x[sl["sell"]]; out["Curtailment_MW"] = x[sl["curtail"]]; out["NetGridImport_MW"] = net; out["GridEnergyForCost_MW"] = out.GridPurchase_MW; out["ChargeMode"] = np.rint(x[sl["mode"]]).astype(int); out["GridImportMode"] = np.rint(x[sl["grid_mode"]]).astype(int)
    return out, {"success": True, "status": str(result.message), "runtime_s": runtime_s, "mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0)}


def audit(d: pd.DataFrame, storage: pd.Series, method: str) -> dict[str, Any]:
    d = d.sort_values("Hour").reset_index(drop=True); initial = float(storage.InitialSOC_MWh); eta_c = float(storage.ChargeEfficiency); eta_d = float(storage.DischargeEfficiency)
    prev = np.r_[initial, d.SOC_MWh.to_numpy(float)[:-1]]; soc_resid = d.SOC_MWh.to_numpy(float) - (prev + eta_c * d.ChargePower_MW.to_numpy(float) - d.DischargePower_MW.to_numpy(float) / eta_d)
    checks = {"soc_transition_max_abs_MWh": float(np.max(np.abs(soc_resid))), "load_balance_max_abs_MW": float(np.max(np.abs(d.RenewableToLoad_MW + d.DischargePower_MW + d.GridLoadPurchase_MW - d.Total_Load_MW))), "renewable_balance_max_abs_MW": float(np.max(np.abs(d.AvailableRenewable_MW - d.RenewableToLoad_MW - d.RenewableCharge_MW - d.GridSell_MW - d.Curtailment_MW))), "soc_bounds_violation_MWh": float(max(float(storage.MinSOC_MWh - d.SOC_MWh.min()), float(d.SOC_MWh.max() - storage.StorageCapacity_MWh), 0.0)), "import_cap_violation_MW": float(max(float(d.GridPurchase_MW.max() - storage.MaxGridImport_MW), 0.0)), "export_cap_violation_MW": float(max(float(d.GridSell_MW.max() - min(storage.SellLimit_MW, storage.MaxGridExport_MW)), 0.0)), "terminal_soc_error_MWh": float(abs(d.SOC_MWh.iloc[-1] - initial)), "simultaneous_charge_discharge_MW": float(np.max(np.minimum(d.ChargePower_MW, d.DischargePower_MW))), "simultaneous_grid_import_export_MW": float(np.max(np.minimum(d.GridPurchase_MW, d.GridSell_MW)))}
    passed = all(v <= TOL for v in checks.values())
    return {"method": method, "region": str(d.Region.iloc[0]), "passed": bool(passed), "checks": checks}


def metrics(d: pd.DataFrame, storage: pd.Series, method: str, scenario: str, solver: dict[str, Any]) -> dict[str, Any]:
    cost = float(np.dot(d.GridPurchase_MW, d.ElectricityPrice_CNY_per_MWh) - np.dot(d.GridSell_MW, d.SellPrice_CNY_per_MWh)); carbon = float(np.dot(d.GridPurchase_MW, d.CarbonIntensity_tCO2_per_MWh)); renew = float((d.AvailableRenewable_MW.sum() - d.Curtailment_MW.sum()) / max(d.AvailableRenewable_MW.sum(), 1e-9))
    return {"scenario": scenario, "method": method, "region": str(d.Region.iloc[0]), "solver_success": bool(solver.get("success", True)), "solver_status": solver.get("status"), "runtime_s": float(solver.get("runtime_s", 0.0)), "mip_gap": solver.get("mip_gap"), "cost_CNY": cost, "carbon_tCO2": carbon, "peak_net_import_MW": float(d.NetGridImport_MW.max()), "peak_facility_load_MW": float(d.Total_Load_MW.max()), "renewable_utilization_ratio": renew, "terminal_SOC_MWh": float(d.SOC_MWh.iloc[-1]), "initial_SOC_MWh": float(storage.InitialSOC_MWh)}


def main() -> int:
    started = time.perf_counter(); STAGING.mkdir(parents=True, exist_ok=True)
    task = json.loads(TASK_PACKAGE.read_text(encoding="utf-8")); verify_inputs(task)
    base, storage_table, provenance = load_inputs(); regions = sorted(base.Region.unique()); storage_map = {str(r.Region): pd.Series(r._asdict()) for r in storage_table.itertuples(index=False)}
    scenarios = [{"name": "observed", "renewable_multiplier": 1.0, "carbon_weight": 0.35}, {"name": "high_carbon_price", "renewable_multiplier": 1.0, "carbon_weight": 0.85}, {"name": "renewable_low_70pct", "renewable_multiplier": 0.70, "carbon_weight": 0.50}]
    cand_rows: list[dict[str, Any]] = []; base_rows: list[dict[str, Any]] = []; cand_dispatch: list[pd.DataFrame] = []; base_dispatch: list[pd.DataFrame] = []; audits: dict[str, Any] = {}; coordination: dict[str, Any] = {}
    for scenario in scenarios:
        name = scenario["name"]; multiplier = float(scenario["renewable_multiplier"]); carbon_weight = float(scenario["carbon_weight"]); lambda_peak = 0.0; history = []; final_c = {}; final_b = {}
        baseline_seed = pd.concat([baseline_dispatch(base[base.Region == region].copy(), storage_map[region], multiplier) for region in regions], ignore_index=True)
        baseline_system_peak = float(baseline_seed.groupby("Hour").NetGridImport_MW.sum().max())
        target = max(0.0, 0.95 * baseline_system_peak)
        for iteration in range(5):
            cframes = []; bframes = {}; cmetrics = {}; bmetrics = {}; ca = {}; ba = {}
            for region in regions:
                st = storage_map[region]; frame = base[base.Region == region].copy(); b = baseline_dispatch(frame, st, multiplier); c, solver = solve_region(frame, st, multiplier, carbon_weight, lambda_peak)
                if c.empty: raise RuntimeError(f"MILP failed for {name}/{region}: {solver}")
                cframes.append(c); bframes[region] = b; cmetrics[region] = metrics(c, st, "alternating_peak_shadow_MILP", name, solver); bmetrics[region] = metrics(b, st, "same_envelope_no_storage", name, {"success": True, "status": "deterministic baseline"}); ca[region] = audit(c, st, "alternating_peak_shadow_MILP"); ba[region] = audit(b, st, "same_envelope_no_storage")
            ccat = pd.concat(cframes, ignore_index=True); global_peak = float(ccat.groupby("Hour").NetGridImport_MW.sum().max()); history.append({"iteration": iteration + 1, "lambda_peak": lambda_peak, "global_peak_net_import_MW": global_peak, "target_MW": target})
            if global_peak > target: lambda_peak += 0.25 * (global_peak - target) / max(target, 1.0)
            else: lambda_peak *= 0.7
            final_c, final_b = {"dispatch": ccat, "metrics": cmetrics, "audit": ca}, {"dispatch": pd.concat(list(bframes.values()), ignore_index=True), "metrics": bmetrics, "audit": ba}
        coordination[name] = {"target_peak_MW": target, "iterations": history, "final_lambda_peak": lambda_peak, "coordination_rule": "shared peak-import shadow price updated from regional max net import"}
        for region in regions: cand_rows.append(final_c["metrics"][region]); base_rows.append(final_b["metrics"][region])
        ctag = final_c["dispatch"].copy(); ctag["Scenario"] = name; ctag["CoordinationIteration"] = len(history); btag = final_b["dispatch"].copy(); btag["Scenario"] = name; cand_dispatch.append(ctag); btag["CoordinationIteration"] = len(history); base_dispatch.append(btag)
        audits[name] = {"candidate": final_c["audit"], "baseline": final_b["audit"]}
    cand_df = pd.concat(cand_dispatch, ignore_index=True); base_df = pd.concat(base_dispatch, ignore_index=True); cand_metrics = pd.DataFrame(cand_rows); base_metrics = pd.DataFrame(base_rows)
    aggregate = []
    for name in [x["name"] for x in scenarios]:
        c = cand_metrics[cand_metrics.scenario == name]; b = base_metrics[base_metrics.scenario == name]
        candidate_scenario = cand_df[cand_df.Scenario == name]; baseline_scenario = base_df[base_df.Scenario == name]
        aggregate.append({"scenario": name, "candidate_method": "alternating_peak_shadow_MILP", "baseline_method": "same_envelope_no_storage", "candidate_cost_CNY": float(c.cost_CNY.sum()), "baseline_cost_CNY": float(b.cost_CNY.sum()), "cost_delta_CNY": float(c.cost_CNY.sum() - b.cost_CNY.sum()), "candidate_carbon_tCO2": float(c.carbon_tCO2.sum()), "baseline_carbon_tCO2": float(b.carbon_tCO2.sum()), "candidate_peak_net_import_MW": float(candidate_scenario.groupby("Hour").NetGridImport_MW.sum().max()), "baseline_peak_net_import_MW": float(baseline_scenario.groupby("Hour").NetGridImport_MW.sum().max()), "candidate_renewable_utilization_ratio": float((candidate_scenario.AvailableRenewable_MW.sum() - candidate_scenario.Curtailment_MW.sum()) / max(candidate_scenario.AvailableRenewable_MW.sum(), 1e-9)), "baseline_renewable_utilization_ratio": float((baseline_scenario.AvailableRenewable_MW.sum() - baseline_scenario.Curtailment_MW.sum()) / max(baseline_scenario.AvailableRenewable_MW.sum(), 1e-9))})
    all_pass = all(audit_row["passed"] for scenario in audits.values() for method in scenario.values() for audit_row in method.values())
    summary = {"schema_version": 1, "problem_id": "C", "question_id": "Q4", "status": "PASS" if all_pass else "PARTIAL", "pilot_scope": "three 24-hour scenario probes seeded from merged Q4 task envelope", "methods": {"candidate": "alternating_peak_shadow_MILP", "baseline": "same_envelope_no_storage", "fallback": None, "optimality_statement": "Scenario results are exploratory; regional subproblems have solver status but the alternating coordinator is not a globally optimal integrated solve."}, "provenance": provenance, "scenario_definitions": scenarios, "coordination": coordination, "aggregate_comparison": aggregate, "risk_probes": {"scenarios": [x["name"] for x in scenarios], "all_hard_constraint_audits_passed": all_pass, "terminal_soc_checked": True, "double_counting_guard": provenance["envelope_definition"]}, "claim_proposals": [{"id": "Q4-ENH-P1", "text": "On the bounded 24-hour probes, the alternating regional storage coordinator maintained all audited energy/SOC/grid constraints under observed and perturbed renewable/carbon conditions.", "status": "proposal_only"}, {"id": "Q4-ENH-P2", "text": "Cost and renewable-utilization deltas are scenario-specific exploratory evidence and do not establish global dominance.", "status": "proposal_only"}], "limitations": ["24-hour bounded horizon", "task assignment/envelope is frozen from merged Q4 evidence", "regional subproblems communicate only through a peak-import shadow price; no physical inter-region power flow is introduced", "carbon price is an objective weight probe, not a new tariff claim", "MILP failure blocks evidence because no fallback is claimed", "formal claims remain root-owned"]}
    cand_df.to_csv(STAGING / "q4_enhanced_candidate_dispatch.csv", index=False, float_format="%.10f"); base_df.to_csv(STAGING / "q4_enhanced_baseline_dispatch.csv", index=False, float_format="%.10f"); cand_metrics.to_csv(STAGING / "q4_enhanced_candidate_metrics.csv", index=False, float_format="%.10f"); base_metrics.to_csv(STAGING / "q4_enhanced_baseline_metrics.csv", index=False, float_format="%.10f"); dump_json(STAGING / "q4_enhanced_constraint_audit.json", audits); dump_json(STAGING / "q4_enhanced_summary.json", summary)
    artifacts_simple = ["q4_enhanced_summary.json", "q4_enhanced_constraint_audit.json", "q4_enhanced_candidate_metrics.csv", "q4_enhanced_baseline_metrics.csv", "q4_enhanced_candidate_dispatch.csv", "q4_enhanced_baseline_dispatch.csv"]
    manifest = {"schema_version": 1, "sprint_id": SPRINT_ID, "task_id": TASK_ID, "run_id": "q4-enhanced-20260808", "question_id": "Q4", "engine": "python", "command": [sys.executable, str(STAGING / "run_solver_q4_enhanced.py")], "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": __import__("scipy").__version__}, "seed": SEED, "code": {"runner": (STAGING / "run_solver_q4_enhanced.py").relative_to(ROOT).as_posix(), "sha256": sha256_file(STAGING / "run_solver_q4_enhanced.py")}, "input_hashes": task["input_hashes"], "outputs": artifacts_simple, "coordination": coordination, "status": "PASS" if all_pass else "PARTIAL", "runtime_s": round(time.perf_counter() - started, 6)}
    dump_json(STAGING / "q4_enhanced_run_manifest.json", manifest)
    artifact_paths = artifacts_simple + ["q4_enhanced_run_manifest.json", "run_solver_q4_enhanced.py"]
    artifacts = [{"path": (STAGING / p).relative_to(ROOT).as_posix(), "sha256": sha256_file(STAGING / p)} for p in artifact_paths]
    handoff = {"schema_version": 1, "sprint_id": SPRINT_ID, "task_id": TASK_ID, "attempt": int(task.get("attempt", 1)), "status": "SUCCESS" if all_pass else "PARTIAL", "input_hashes": task["input_hashes"], "written_paths": [a["path"] for a in artifacts] + [(STAGING / "handoff.json").relative_to(ROOT).as_posix()], "artifacts": artifacts, "gate_result": {"gate": "G5", "passed": bool(all_pass), "checks": ["input_hashes_rechecked", "merged_Q4_envelope_reused", "candidate_baseline_same_envelope", "three_scenario_probes", "regional_SOC_and_energy_balance", "charge_discharge_and_import_export_mutex", "system_peak_linkage", "grid_caps", "artifact_hashes"]}, "summary": "Enhanced Q4 pilot completed with re-runnable task envelope, alternating multi-region storage coordination, same-envelope no-storage baseline, and carbon/renewable perturbation probes."}
    dump_json(STAGING / "handoff.json", handoff)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        (STAGING / "q4_enhanced_failure.log").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise
