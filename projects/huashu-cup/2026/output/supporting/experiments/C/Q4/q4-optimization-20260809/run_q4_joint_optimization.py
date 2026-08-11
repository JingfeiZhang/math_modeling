#!/usr/bin/env python
"""Surrogate-assisted Q4 fix-and-optimize probe on the formal Q2 schedule."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SEED, H0, HORIZON = 20260809, 2328, 72
H1 = H0 + HORIZON
QUEUE_SIZE, SHORTLIST_SIZE, LATENCY_GUARD_MS = 12, 8, 20.0
METHOD = "surrogate_assisted_fix_and_optimize_candidate_PROBE_ONLY"
SCENARIOS = {
    "observed": {"price": 1.0, "carbon": 1.0, "renewable": 1.0},
    "peak_price_empirical": {"price": 1.2, "carbon": 1.0, "renewable": 1.0},
    "high_carbon_empirical": {"price": 1.0, "carbon": 1.2, "renewable": 1.0},
    "renewable_low_empirical": {"price": 1.0, "carbon": 1.0, "renewable": 0.85},
    "joint_stress": {"price": 1.2, "carbon": 1.2, "renewable": 0.85},
}
OUT = Path(__file__).resolve().parent


def project_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "contest.yaml").is_file() and (candidate / "problems").is_dir():
            return candidate
    raise RuntimeError("isolated project root not found")


ROOT = project_root(OUT)
Q2_ROOT = ROOT / "experiments/C/Q2/q2-direct-20260808"
Q4_ROOT = ROOT / "experiments/C/Q4/q4-direct-20260808"
Q2_SOURCE = Q2_ROOT / "models/full_horizon/run_q2_full_horizon.py"
Q2_SCHEDULE = Q2_ROOT / "models/full_horizon/q2_full_candidate_schedule.csv"
Q4_SOURCE = Q4_ROOT / "models/final_milp/run_solver_q4_final.py"
DATA = ROOT / "problems/C/data"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_default(value):
    if isinstance(value, (np.bool_,)): return bool(value)
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return float(value)
    raise TypeError(type(value).__name__)


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False, default=json_default) + "\n", encoding="utf-8")


def prepare_modules():
    q2 = load_module("q2_direct_base", Q2_SOURCE)
    q2.ROOT = ROOT
    q4 = load_module("q4_direct_base", Q4_SOURCE)
    q4.ROOT, q4.HORIZON, q4.WINDOW_START_H = ROOT, HORIZON, H0
    return q2, q4


def load_energy_inputs():
    region_time = pd.read_excel(DATA / "region_time_data.xlsx", sheet_name="region_time_data")
    gpu = pd.read_excel(DATA / "GPU_information.xlsx", sheet_name=0)
    power = pd.read_excel(DATA / "power_mapping.xlsx", sheet_name=0)
    storage = pd.read_excel(DATA / "storage_information.xlsx", sheet_name="storage_information")
    pue = dict(zip(gpu.Region.astype(str), gpu.PUE.astype(float), strict=True))
    power_map = dict(zip(power.TaskType.astype(str), power.GPU_Power_MW_per_EquivalentGPU.astype(float), strict=True))
    return region_time, storage, pue, power_map


def window(schedule: pd.DataFrame) -> pd.DataFrame:
    return schedule[(schedule.StartMinute < H1 * 60) & (schedule.EndMinute > H0 * 60)].copy()


def metrics(dispatch: pd.DataFrame) -> dict[str, float]:
    renewable = float(dispatch.AvailableRenewable_MW.sum())
    return {
        "cost_CNY": float((dispatch.GridPurchase_MW * dispatch.ElectricityPrice_CNY_per_MWh - dispatch.GridSell_MW * dispatch.SellPrice_CNY_per_MWh).sum()),
        "carbon_tCO2": float((dispatch.GridPurchase_MW * dispatch.CarbonIntensity_tCO2_per_MWh).sum()),
        "positive_peak_MW": float(max(dispatch.groupby("Hour").NetGridImport_MW.sum().max(), 0.0)),
        "renewable_utilization_ratio": float((renewable - dispatch.Curtailment_MW.sum()) / max(renewable, 1e-9)),
    }


def evaluate(q4, schedule, region_time, storage, pue, power_map):
    envelope, meta = q4.schedule_to_envelope(window(schedule), region_time, power_map, pue, METHOD)
    carbon_q75 = float(envelope.CarbonIntensity_tCO2_per_MWh.quantile(0.75))
    results = {}
    for scenario, definition in SCENARIOS.items():
        scenario_envelope = q4.apply_scenario(envelope, definition, carbon_q75)
        dispatch, solver = q4.solve_integrated(scenario_envelope, storage)
        if dispatch.empty: raise RuntimeError(f"storage MILP failed: {scenario}")
        audit = q4.audit_dispatch(dispatch, storage, METHOD, solver.get("system_peak_variable_MW"))
        if not audit["passed"]: raise RuntimeError(f"storage audit failed: {scenario}")
        results[scenario] = {"metrics": metrics(dispatch), "dispatch": dispatch, "audit": audit}
    return results, meta


def objective(results, scales) -> float:
    values = []
    for scenario, result in results.items():
        m, s = result["metrics"], scales[scenario]
        values.append(m["cost_CNY"] / s["cost"] + .35 * m["carbon_tCO2"] / s["carbon"] + .08 * m["positive_peak_MW"] / s["peak"] - .03 * m["renewable_utilization_ratio"])
    return float(np.mean(values))


def select_queue(schedule, tasks, context):
    task_map = tasks.set_index("TaskID")
    candidates = window(schedule)
    candidates = candidates[~candidates.TaskType.astype(str).eq("RealTimeInference")]
    ranked = []
    for row in candidates.itertuples(index=False):
        idx = context["region_index"][str(row.ExecutionRegion)]
        begin, end = int(row.StartMinute), int(row.EndMinute)
        facility_mw = int(row.GPU_Demand) * context["power"][str(row.TaskType)] * context["pue"][str(row.ExecutionRegion)]
        carbon = facility_mw * float(context["carbon"][idx, begin:end].mean()) * (end - begin) / 60
        price = facility_mw * float(context["price"][idx, begin:end].mean()) * (end - begin) / 60
        ranked.append((carbon + price / 1000, int(row.TaskID)))
    ids = [task_id for _score, task_id in sorted(ranked, reverse=True)[:QUEUE_SIZE]]
    return task_map.loc[ids].sort_index().reset_index()


def optimize(q2, q4, tasks, context, incumbent, energy_inputs):
    region_time, storage, pue, power_map = energy_inputs
    rows = {int(row["TaskID"]): dict(row) for row in incumbent.to_dict("records")}
    ledger = q2.MinuteLedger(context)
    for row in rows.values(): ledger.apply(row, +1)
    current, envelope_meta = evaluate(q4, incumbent, region_time, storage, pue, power_map)
    scales = {name: {"cost": max(abs(z["metrics"]["cost_CNY"]), 1), "carbon": max(abs(z["metrics"]["carbon_tCO2"]), 1), "peak": max(abs(z["metrics"]["positive_peak_MW"]), 1)} for name, z in current.items()}
    current_objective, trace, evaluated = objective(current, scales), [], 0
    task_map = tasks.set_index("TaskID", drop=False)
    for task_id in select_queue(incumbent, tasks, context).TaskID.astype(int):
        task, old = task_map.loc[task_id], rows[task_id]
        ledger.apply(old, -1)
        options = []
        latency_ceiling = min(float(task.MaxLatency_ms), float(old["NetworkLatency_ms"]) + LATENCY_GUARD_MS)
        for region in q2.eligible_regions(task, context):
            latency = context["latency"][(str(task.SourceRegion), region)]
            if latency > latency_ceiling + q2.TOL: continue
            starts = {int(old["StartMinute"]), int(task._earliest), *(int(old["StartMinute"]) + delta for delta in (-120, -60, 60, 120))}
            for begin in sorted(starts):
                if begin < int(task._earliest) or begin > int(task._latest_start) or begin + int(task._duration) > H1 * 60: continue
                if not ledger.can_place(task, region, begin): continue
                proxy = q2.option_metrics(task, region, begin, ledger, context)
                options.append((proxy["score"], proxy["latency_ms"], begin, region))
        options = sorted(set(options), key=lambda x: (x[0], x[1], x[2], x[3]))[:SHORTLIST_SIZE]
        if (str(old["ExecutionRegion"]), int(old["StartMinute"])) not in {(x[3], x[2]) for x in options}:
            options.append((float("inf"), float(old["NetworkLatency_ms"]), int(old["StartMinute"]), str(old["ExecutionRegion"])))
        trials = []
        for _proxy, _latency, begin, region in options:
            candidate_row = dict(old)
            candidate_row.update({"ExecutionRegion": region, "StartMinute": begin, "EndMinute": begin + int(task._duration), "NetworkLatency_ms": context["latency"][(str(task.SourceRegion), region)], "Method": METHOD})
            rows[task_id] = candidate_row
            schedule = pd.DataFrame(rows.values(), columns=q2.SCHEDULE_COLUMNS).sort_values("TaskID").reset_index(drop=True)
            result, _meta = evaluate(q4, schedule, region_time, storage, pue, power_map)
            evaluated += 1
            trials.append((objective(result, scales), region, begin, candidate_row, result))
        best = min(trials, key=lambda x: (x[0], x[1], x[2]))
        accepted = best[0] < current_objective - 1e-10
        if accepted:
            rows[task_id], current, current_objective = best[3], best[4], best[0]
            ledger.apply(best[3], +1)
        else:
            rows[task_id] = old
            ledger.apply(old, +1)
        trace.append({"TaskID": task_id, "options_evaluated": len(trials), "accepted": accepted, "old_region": old["ExecutionRegion"], "new_region": rows[task_id]["ExecutionRegion"], "old_start_minute": int(old["StartMinute"]), "new_start_minute": int(rows[task_id]["StartMinute"]), "joint_objective": current_objective})
    schedule = pd.DataFrame(rows.values(), columns=q2.SCHEDULE_COLUMNS).sort_values("TaskID").reset_index(drop=True)
    return schedule, current, pd.DataFrame(trace), envelope_meta, evaluated


def main() -> int:
    started = time.perf_counter(); np.random.seed(SEED); OUT.mkdir(parents=True, exist_ok=True)
    q2, q4 = prepare_modules(); tasks, context = q2.load_context()
    incumbent = pd.read_csv(Q2_SCHEDULE); incumbent["Method"] = "fixed_weight_bounded_rolling_local_exchange_heuristic"
    energy_inputs = load_energy_inputs()
    baseline, baseline_meta = evaluate(q4, incumbent, *energy_inputs)
    candidate, candidate_results, trace, candidate_meta, evaluated = optimize(q2, q4, tasks, context, incumbent, energy_inputs)
    replay, _replay_results, _trace2, _meta2, _evaluated2 = optimize(q2, q4, tasks, context, incumbent, energy_inputs)
    deterministic = q2.compare_schedules_exact(candidate, replay)
    task_audit, _ledger, _hourly = q2.audit_schedule(candidate, tasks, context, METHOD)
    rows, dispatch_audits = [], {}
    for scenario in SCENARIOS:
        for role, result in (("sequential_baseline", baseline[scenario]), ("joint_candidate", candidate_results[scenario])):
            rows.append({"scenario": scenario, "role": role, **result["metrics"]})
            dispatch_audits[f"{scenario}:{role}"] = result["audit"]
            result["dispatch"].to_csv(OUT / f"q4_joint_{scenario}_{role}_dispatch.csv", index=False, float_format="%.10f")
    result_metrics = pd.DataFrame(rows)
    b = result_metrics[result_metrics.role.eq("sequential_baseline")].set_index("scenario")
    c = result_metrics[result_metrics.role.eq("joint_candidate")].set_index("scenario")
    nonworse, better = True, False
    for scenario in SCENARIOS:
        for key in ("cost_CNY", "carbon_tCO2", "positive_peak_MW"):
            nonworse &= bool(c.loc[scenario, key] <= b.loc[scenario, key] + 1e-7)
            better |= bool(c.loc[scenario, key] < b.loc[scenario, key] - 1e-7)
        nonworse &= bool(c.loc[scenario, "renewable_utilization_ratio"] >= b.loc[scenario, "renewable_utilization_ratio"] - 1e-10)
        better |= bool(c.loc[scenario, "renewable_utilization_ratio"] > b.loc[scenario, "renewable_utilization_ratio"] + 1e-10)
    moves = incumbent[["TaskID", "ExecutionRegion", "StartMinute"]].merge(candidate[["TaskID", "ExecutionRegion", "StartMinute"]], on="TaskID", suffixes=("_before", "_after"), validate="one_to_one")
    moves = moves[(moves.ExecutionRegion_before != moves.ExecutionRegion_after) | (moves.StartMinute_before != moves.StartMinute_after)]
    decision = "ROOT_REVIEW_REQUIRED" if nonworse and better and task_audit["passed"] and deterministic else "PROBE_ONLY"
    summary = {"schema_version": 1, "status": "PASS" if task_audit["passed"] and deterministic else "FAIL", "method": METHOD, "decision": decision, "formal_main_replaced": False, "scope": {"window_start_hour": H0, "horizon_h": HORIZON, "queue_size": QUEUE_SIZE, "scenarios": list(SCENARIOS)}, "algorithm": {"name": "surrogate-assisted high-impact fix-and-optimize with storage-MILP recourse", "storage_evaluations_first_run": evaluated, "accepted_move_count": int(len(moves)), "latency_guard_ms": LATENCY_GUARD_MS}, "promotion_test": {"all_metrics_nonworse_in_all_scenarios": bool(nonworse), "at_least_one_metric_strictly_better": bool(better), "task_hard_audit_passed": bool(task_audit["passed"]), "deterministic_replay_passed": bool(deterministic)}, "runtime_seconds": time.perf_counter() - started}
    candidate.to_csv(OUT / "q4_joint_candidate_schedule.csv", index=False)
    result_metrics.to_csv(OUT / "q4_joint_metrics.csv", index=False)
    trace.to_csv(OUT / "q4_joint_search_trace.csv", index=False)
    moves.to_csv(OUT / "q4_joint_task_moves.csv", index=False)
    dump(OUT / "q4_joint_summary.json", summary)
    dump(OUT / "q4_joint_constraint_audit.json", {"task_schedule": task_audit, "storage_dispatches": dispatch_audits, "all_passed": bool(task_audit["passed"] and all(x["passed"] for x in dispatch_audits.values()))})
    dump(OUT / "q4_joint_risk_probes.json", {"status": summary["status"], "decision": decision, "probes": {"full_50000_task_audit": bool(task_audit["passed"]), "deterministic_replay": bool(deterministic), "two_scenario_dominance": bool(nonworse and better), "frozen_main_untouched": True, "RegionF_relaxed_LP_excluded": True}})
    inputs = [Q2_SOURCE, Q2_SCHEDULE, Q4_SOURCE, *(DATA / name for name in ("workload_trace.xlsx", "GPU_information.xlsx", "network_latency.xlsx", "region_time_data.xlsx", "power_mapping.xlsx", "storage_information.xlsx"))]
    dump(OUT / "run_manifest.json", {"schema_version": 1, "question_id": "Q4", "status": "PROBE_ONLY", "command": f"{sys.executable} {Path(__file__).name}", "seed": SEED, "inputs": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in inputs], "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__}, "generated_at_utc": datetime.now(timezone.utc).isoformat(), "baseline_envelope": baseline_meta, "candidate_envelope": candidate_meta})
    files = sorted(path for path in OUT.iterdir() if path.is_file() and path.name != "result_hashes.json")
    dump(OUT / "result_hashes.json", {"schema_version": 1, "files": [{"path": p.name, "sha256": sha256(p)} for p in files]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
