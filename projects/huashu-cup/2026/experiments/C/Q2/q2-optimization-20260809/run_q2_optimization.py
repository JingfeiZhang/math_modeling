#!/usr/bin/env python
"""Q2 isolated epsilon-constraint/Pareto optimization probe.

This runner imports only the pinned Q2 full-horizon implementation, reuses its
input loader and minute-level auditor, and writes every artifact beneath this
candidate directory.  The two new policies are bounded deterministic rolling
exchanges with explicit absolute latency caps.  Local CP-SAT probes relax
capacity coupling, so their objective values are valid lower bounds for the
same latency-capped assignment problem (not feasible full-horizon schedules).
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
from ortools.sat.python import cp_model


STAGING = Path(__file__).resolve().parent
PROJECT_ROOT = STAGING.parents[3]
SOURCE = PROJECT_ROOT / "experiments" / "C" / "Q2" / "q2-direct-20260808" / "models" / "full_horizon" / "run_q2_full_horizon.py"
BASE_ARTIFACT_DIR = SOURCE.parent
SEED = 20260801
MAIN_METHOD = "fixed_weight_bounded_rolling_local_exchange_heuristic"
BASELINE_METHOD = "full_horizon_FIFO_latency_feasible_local_first"
GUARDED_METHOD = "epsilon_constraint_new_flexible_placement_cap_25ms"
CANDIDATE_METHOD = "epsilon_constraint_new_flexible_placement_cap_15ms"
TOL = 1e-7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=json_default) + "\n", encoding="utf-8")


def json_default(value: Any) -> Any:
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(type(value).__name__)


def artifact(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(PROJECT_ROOT).as_posix(), "sha256": sha256(path)}


def load_base():
    spec = importlib.util.spec_from_file_location("q2_full_horizon_pinned", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = PROJECT_ROOT
    return module


def input_hashes(mod) -> list[dict[str, Any]]:
    # The pinned runner owns the exact input list and hash semantics.
    return mod.direct_input_hashes()


def run_exchange(mod, tasks: pd.DataFrame, baseline: pd.DataFrame, context: dict[str, Any], method: str, cap_ms: float) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    """Bounded exchange with an absolute latency epsilon constraint."""
    started = time.perf_counter()
    rows = {int(row["TaskID"]): dict(row) for row in baseline.to_dict("records")}
    ledger = mod.MinuteLedger(context)
    for row in rows.values():
        ledger.apply(row, +1)
    accepted: list[dict[str, Any]] = []
    evaluated = 0
    moved = moved_region = moved_time = 0
    priority = {"BatchInference": 0, "AITraining": 1}
    for block_start in range(0, mod.MAIN_END_HOUR, mod.CHUNK_HOURS):
        block_end = min(mod.MAIN_END_HOUR, block_start + mod.CHUNK_HOURS)
        chunk = tasks[(~tasks.TaskType.eq("RealTimeInference")) & tasks.ArrivalHour.ge(block_start) & tasks.ArrivalHour.lt(block_end)].copy()
        if chunk.empty:
            continue
        chunk["_work"] = chunk.GPU_Demand * chunk._duration
        chunk["_slack"] = chunk._latest_start - chunk._earliest
        chunk["_priority"] = chunk.TaskType.map(priority)
        chunk = chunk.sort_values(["_work", "_slack", "_priority", "TaskID"], ascending=[False, False, True, True])
        for _, task in chunk.iterrows():
            tid = int(task.TaskID)
            old = rows[tid]
            ledger.apply(old, -1)
            old_metrics = mod.option_metrics(task, str(old["ExecutionRegion"]), int(old["StartMinute"]), ledger, context)
            options: list[tuple[float, str, int, dict[str, float]]] = []
            latency_limit = min(float(task.MaxLatency_ms), cap_ms)
            for region in mod.eligible_regions(task, context):
                if context["latency"][(str(task.SourceRegion), region)] > latency_limit + TOL:
                    continue
                for begin in mod.candidate_starts(task, region, old, context):
                    evaluated += 1
                    metrics = mod.option_metrics(task, region, begin, ledger, context)
                    options.append((metrics["score"], region, begin, metrics))
            chosen = None
            for option in sorted(options, key=lambda item: (item[0], item[3]["latency_ms"], item[2], item[1])):
                score, region, begin, metrics = option
                if score >= old_metrics["score"] - 1e-9:
                    continue
                if metrics["cost_CNY"] >= old_metrics["cost_CNY"] - TOL and metrics["carbon_tCO2"] >= old_metrics["carbon_tCO2"] - TOL:
                    continue
                if ledger.can_place(task, region, begin):
                    chosen = option
                    break
            if chosen is None:
                ledger.apply(old, +1)
                continue
            score, region, begin, metrics = chosen
            new_row = mod.schedule_row(task, region, begin, method, context, block_start // mod.CHUNK_HOURS)
            rows[tid] = new_row
            ledger.apply(new_row, +1)
            moved += 1
            moved_region += int(region != str(old["ExecutionRegion"]))
            moved_time += int(begin != int(old["StartMinute"]))
            accepted.append({"TaskID": tid, "OldLatency_ms": float(old["NetworkLatency_ms"]), "NewLatency_ms": float(metrics["latency_ms"]), "ObjectiveGain": float(old_metrics["score"] - score)})
    schedule = pd.DataFrame(rows.values(), columns=mod.SCHEDULE_COLUMNS).sort_values("TaskID").reset_index(drop=True)
    meta = {"method": method, "new_flexible_placement_latency_cap_ms": cap_ms, "incumbent_retention_rule": "retain the old feasible placement when no improving cap-compliant exchange exists", "runtime_seconds": time.perf_counter() - started, "moved_task_count": moved, "moved_region_count": moved_region, "moved_start_count": moved_time, "evaluated_options": evaluated, "accepted_exchange_count": len(accepted), "bounded_lookahead_hours": int(mod.LOOKAHEAD_HOURS), "chunk_hours": int(mod.CHUNK_HOURS)}
    return schedule, meta, pd.DataFrame(accepted)


def local_cpsat_lower_bound(mod, tasks: pd.DataFrame, context: dict[str, Any], start_hour: int, duration_hours: int, cap_ms: float) -> dict[str, Any]:
    """Relaxed CP-SAT assignment bound for a representative window.

    Capacity coupling is intentionally omitted; each task chooses one legal
    region/start option.  Therefore the optimum is a lower bound on any
    capacity-feasible schedule using the same options and latency cap.
    """
    end_hour = min(mod.MAIN_END_HOUR, start_hour + duration_hours)
    window = tasks[(tasks.ArrivalHour >= start_hour) & (tasks.ArrivalHour < end_hour) & (~tasks.TaskType.eq("RealTimeInference"))].copy()
    model = cp_model.CpModel()
    choices: list[tuple[int, str, int, int, float, float, float]] = []
    by_task: dict[int, list[int]] = {}
    scale = 1000
    for _, task in window.iterrows():
        tid = int(task.TaskID)
        indices: list[int] = []
        earliest = int(task._earliest)
        latest = int(task._latest_start)
        # Hourly starts match the production runner's bounded option granularity.
        for region in mod.eligible_regions(task, context):
            lat = float(context["latency"][(str(task.SourceRegion), region)])
            if lat > min(float(task.MaxLatency_ms), cap_ms) + TOL:
                continue
            for begin in range(max(earliest, start_hour * 60), min(latest, end_hour * 60 - int(task._duration)) + 1, 60):
                idx = len(choices)
                m = mod.option_metrics(task, region, begin, mod.MinuteLedger(context), context)
                indices.append(idx)
                choices.append((tid, region, begin, int(task._duration), float(m["cost_CNY"]), float(m["carbon_tCO2"]), lat))
        if indices:
            by_task[tid] = indices
    if not by_task:
        return {"start_hour": start_hour, "duration_hours": duration_hours, "latency_cap_ms": cap_ms, "task_count": 0, "status": "EMPTY", "lower_bound_cost_CNY": 0.0, "lower_bound_carbon_tCO2": 0.0}
    # Rebuild variables once so objective references the exact BoolVars.
    variables = [model.NewBoolVar(f"x_{i}") for i in range(len(choices))]
    for tid, indices in by_task.items():
        model.Add(sum(variables[i] for i in indices) == 1)
    objective = [int(round(item[4] * scale)) for item in choices]
    model.Minimize(sum(objective[i] * variables[i] for i in range(len(choices))))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20.0
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = SEED
    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"start_hour": start_hour, "duration_hours": duration_hours, "latency_cap_ms": cap_ms, "task_count": len(by_task), "status": status_name, "lower_bound_cost_CNY": None, "lower_bound_carbon_tCO2": None, "option_count": len(choices)}
    cost = sum(choices[i][4] for i in range(len(choices)) if solver.Value(variables[i]))
    carbon = sum(choices[i][5] for i in range(len(choices)) if solver.Value(variables[i]))
    return {"start_hour": start_hour, "duration_hours": duration_hours, "latency_cap_ms": cap_ms, "task_count": len(by_task), "option_count": len(choices), "status": status_name, "lower_bound_cost_CNY": float(cost), "lower_bound_carbon_tCO2": float(carbon), "objective_bound_gap": float(solver.ObjectiveValue() - solver.BestObjectiveBound()) / scale}


def metric_row(name: str, audit: dict[str, Any]) -> dict[str, Any]:
    return {"method": name, "cost_CNY": audit["cost_CNY"], "carbon_tCO2": audit["carbon_tCO2"], "mean_latency_ms": audit["mean_latency_ms"], "p95_latency_ms": audit["p95_latency_ms"], "renewable_utilization_ratio": audit["renewable_utilization_ratio"], "task_completion_rate": audit["task_completion_rate"], "SLA_violation_rate": audit["SLA_violation_rate"], "peak_facility_load_MW": audit["peak_facility_load_MW"], "hard_audit_passed": audit["passed"]}


def main() -> int:
    started = time.perf_counter()
    started_at = utcnow()
    STAGING.mkdir(parents=True, exist_ok=True)
    mod = load_base()
    np.random.seed(SEED)
    tasks, context = mod.load_context()
    baseline = pd.read_csv(BASE_ARTIFACT_DIR / "q2_full_baseline_schedule.csv")
    current = pd.read_csv(BASE_ARTIFACT_DIR / "q2_full_candidate_schedule.csv")
    baseline_audit, baseline_ledger, baseline_hourly = mod.audit_schedule(baseline, tasks, context, BASELINE_METHOD)
    current_audit, current_ledger, current_hourly = mod.audit_schedule(current, tasks, context, MAIN_METHOD)
    guarded, guarded_meta, guarded_log = run_exchange(mod, tasks, baseline, context, GUARDED_METHOD, 25.0)
    candidate, candidate_meta, candidate_log = run_exchange(mod, tasks, baseline, context, CANDIDATE_METHOD, 15.0)
    guarded_replay, guarded_replay_meta, _ = run_exchange(mod, tasks, baseline, context, GUARDED_METHOD, 25.0)
    candidate_replay, candidate_replay_meta, _ = run_exchange(mod, tasks, baseline, context, CANDIDATE_METHOD, 15.0)
    guarded_deterministic = mod.compare_schedules_exact(guarded, guarded_replay)
    candidate_deterministic = mod.compare_schedules_exact(candidate, candidate_replay)
    guarded_audit, guarded_ledger, guarded_hourly = mod.audit_schedule(guarded, tasks, context, GUARDED_METHOD)
    candidate_audit, candidate_ledger, candidate_hourly = mod.audit_schedule(candidate, tasks, context, CANDIDATE_METHOD)
    windows = []
    for duration in (6, 24, 72):
        for start_hour in (0, 600, 1200, 1800):
            if start_hour + duration <= mod.MAIN_END_HOUR:
                for cap in (25.0, 15.0):
                    windows.append(local_cpsat_lower_bound(mod, tasks, context, start_hour, duration, cap))
    schedules = {"fifo": baseline, "current": current, "latency_guarded": guarded, "candidate": candidate}
    audits = {"fifo": baseline_audit, "current": current_audit, "latency_guarded": guarded_audit, "candidate": candidate_audit}
    hourly = pd.concat([baseline_hourly, current_hourly, guarded_hourly, candidate_hourly], ignore_index=True)
    baseline.to_csv(STAGING / "q2_fifo_baseline_schedule.csv", index=False)
    current.to_csv(STAGING / "q2_current_schedule.csv", index=False)
    guarded.to_csv(STAGING / "q2_latency_guarded_schedule.csv", index=False)
    candidate.to_csv(STAGING / "q2_pareto_candidate_schedule.csv", index=False)
    guarded_log.to_csv(STAGING / "q2_latency_guarded_exchange_log.csv", index=False)
    candidate_log.to_csv(STAGING / "q2_pareto_candidate_exchange_log.csv", index=False)
    hourly.to_csv(STAGING / "q2_comparison_hourly_profiles.csv", index=False)
    pd.DataFrame([metric_row(k, v) for k, v in audits.items()]).to_csv(STAGING / "q2_pareto_metrics.csv", index=False)
    write_json(STAGING / "q2_local_cpsat_lower_bounds.json", {"schema_version": 1, "relaxation": "capacity coupling omitted; same release/deadline/latency-capped hourly options; values are task-marginal cost/carbon bounds and exclude fixed non-AI load", "probes": windows})
    all_hard = all(a["passed"] for a in audits.values())
    cap_pass = bool(candidate_audit["p95_latency_ms"] <= 15.0 + TOL and candidate_audit["mean_latency_ms"] <= current_audit["mean_latency_ms"] + TOL)
    deterministic = guarded_deterministic and candidate_deterministic
    promotion = bool(all_hard and deterministic and cap_pass and candidate_audit["cost_CNY"] <= current_audit["cost_CNY"] * 1.001 and candidate_audit["carbon_tCO2"] <= current_audit["carbon_tCO2"] * 1.001 and candidate_audit["mean_latency_ms"] <= current_audit["mean_latency_ms"] * 0.98)
    decision = "CANDIDATE" if promotion else "PROBE_ONLY"
    checks = {"all_methods_hard_audit": all_hard, "guarded_deterministic_replay": guarded_deterministic, "candidate_deterministic_replay": candidate_deterministic, "candidate_p95_latency_at_or_below_15ms_and_mean_nonworse": cap_pass, "candidate_cost_within_0_1pct_current": candidate_audit["cost_CNY"] <= current_audit["cost_CNY"] * 1.001, "candidate_carbon_within_0_1pct_current": candidate_audit["carbon_tCO2"] <= current_audit["carbon_tCO2"] * 1.001, "candidate_mean_latency_improvement_at_least_2pct": candidate_audit["mean_latency_ms"] <= current_audit["mean_latency_ms"] * 0.98}
    write_json(STAGING / "constraint_audit.json", {"schema_version": 1, "problem_id": "C", "question_id": "Q2", "status": "PASS" if all_hard and deterministic else "FAIL", "overall_passed": all_hard and deterministic, "hard_constraints": baseline_audit["checks"], "methods": {k: v for k, v in audits.items()}, "promotion_checks": checks, "local_lower_bound_count": len(windows), "input_hashes": input_hashes(mod)})
    summary = {"schema_version": 1, "run_id": "q2-optimization-20260809", "problem_id": "C", "question_id": "Q2", "status": "PASS" if all_hard and deterministic else "FAIL", "decision": decision, "formal_main_replaced": False, "comparison": [metric_row(k, v) for k, v in audits.items()], "policies": {"latency_guarded": {"new_flexible_placement_latency_cap_ms": 25.0, "epsilon_constraint": "each accepted flexible-task placement has network latency <= min(task MaxLatency_ms, 25ms); otherwise the feasible incumbent is retained"}, "candidate": {"new_flexible_placement_latency_cap_ms": 15.0, "epsilon_constraint": "each accepted flexible-task placement has network latency <= min(task MaxLatency_ms, 15ms); otherwise the feasible incumbent is retained"}}, "latency_cap_exceptions": {"guarded_tasks_above_25ms": int((guarded.NetworkLatency_ms > 25.0 + TOL).sum()), "candidate_tasks_above_15ms": int((candidate.NetworkLatency_ms > 15.0 + TOL).sum()), "candidate_tasks_above_25ms": int((candidate.NetworkLatency_ms > 25.0 + TOL).sum()), "interpretation": "retained feasible incumbents, not accepted cap-violating exchanges; supplied task MaxLatency_ms remains the hard SLA"}, "lower_bound_probe": {"path": "q2_local_cpsat_lower_bounds.json", "windows": windows}, "deterministic_replay": {"latency_guarded": guarded_deterministic, "candidate": candidate_deterministic, "guarded_runtime_seconds": guarded_meta["runtime_seconds"] + guarded_replay_meta["runtime_seconds"], "candidate_runtime_seconds": candidate_meta["runtime_seconds"] + candidate_replay_meta["runtime_seconds"]}, "promotion_gates": checks, "runtime_seconds": time.perf_counter() - started, "limitations": ["Full-horizon exchanges remain bounded one-pass heuristics.", "CP-SAT probes omit capacity coupling and are lower bounds, not feasible schedules.", "Placement caps are epsilon constraints on newly accepted flexible-task moves; hard-cap exceptions are retained incumbents required for feasibility.", "No global or joint power-system optimality claim."], "formal_claim_status": "PROBE_ONLY; root review and evidence freeze required"}
    write_json(STAGING / "summary.json", summary)
    manifest = {"schema_version": 1, "run_id": "q2-optimization-20260809", "problem_id": "C", "question_id": "Q2", "engine": "python", "command": [sys.executable, str(STAGING / "run_q2_optimization.py")], "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__, "ortools_module": getattr(cp_model, "__file__", "installed")}, "random_seed": SEED, "inputs": input_hashes(mod), "source_runner": artifact(SOURCE), "methods": {"baseline": BASELINE_METHOD, "current": MAIN_METHOD, "latency_guarded": GUARDED_METHOD, "candidate": CANDIDATE_METHOD}, "artifacts": [], "started_at_utc": started_at, "duration_seconds": time.perf_counter() - started, "status": "PASS" if all_hard and deterministic else "FAIL"}
    primary = ["q2_fifo_baseline_schedule.csv", "q2_current_schedule.csv", "q2_latency_guarded_schedule.csv", "q2_pareto_candidate_schedule.csv", "q2_latency_guarded_exchange_log.csv", "q2_pareto_candidate_exchange_log.csv", "q2_comparison_hourly_profiles.csv", "q2_pareto_metrics.csv", "q2_local_cpsat_lower_bounds.json", "constraint_audit.json", "summary.json"]
    manifest["artifacts"] = [artifact(STAGING / p) for p in primary]
    write_json(STAGING / "run_manifest.json", manifest)
    hash_targets = [STAGING / "run_q2_optimization.py", STAGING / "run_manifest.json", *[STAGING / p for p in primary]]
    result_hashes = {artifact(path)["path"]: artifact(path)["sha256"] for path in hash_targets}
    write_json(STAGING / "result_hashes.json", {"schema_version": 1, "run_id": manifest["run_id"], "artifacts": result_hashes})
    return 0 if all_hard and deterministic else 2


if __name__ == "__main__":
    raise SystemExit(main())
