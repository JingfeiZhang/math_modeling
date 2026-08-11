from __future__ import annotations

"""Bounded CP-SAT fix-and-optimise neighbourhood probe for Q1."""

import hashlib
import importlib.util
import json
import time
from pathlib import Path

import pandas as pd
from ortools.sat.python import cp_model

SEED = 20260801
PROJECT_ROOT = Path(__file__).resolve().parents[6]
STAGING = Path(__file__).resolve().parent
SOURCE = STAGING / "run_scheduling_q1.py"
OUT_DIR = STAGING.parent / "cp_sat_fix_opt_probe"


def load_module():
    spec = importlib.util.spec_from_file_location("q1_sched_base", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {SOURCE}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = PROJECT_ROOT
    mod.DATA = PROJECT_ROOT / "problems" / "C" / "data"
    return mod


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def fixed_neighbour(mod, final_tasks: pd.DataFrame, context: dict, carry: pd.DataFrame, incumbent: pd.DataFrame, max_seconds: float = 20.0):
    chosen_ids = set(
        final_tasks[~final_tasks.TaskType.eq("RealTimeInference")]
        .assign(_work=lambda x: x.GPU_Demand * x.EstimatedDuration_min)
        .sort_values(["_work", "TaskID"], ascending=[False, True])
        .head(12).TaskID.astype(int)
    )
    model = cp_model.CpModel()
    resources = {r: {"gpu": [], "it": [], "facility": []} for r in context["regions"]}
    for r in context["regions"]:
        idx = context["index"][r]
        for hour in range(mod.Q1_START_H, mod.HORIZON_END_H):
            s, e = hour * 60, (hour + 1) * 60
            iv = model.NewIntervalVar(s, 60, e, f"bg_{r}_{hour}")
            bg = int(round(context["nonai"][idx, s] * 1000))
            resources[r]["it"].append((iv, bg)); resources[r]["facility"].append((iv, int(round(bg * context["pue"][r]))))
    for _, row in carry.iterrows():
        r = str(row.ExecutionRegion); s = max(mod.FINAL_START_M, int(row.StartMinute)); e = min(mod.FINAL_END_M, int(row.EndMinute))
        if e <= s: continue
        iv = model.NewIntervalVar(s, e - s, e, f"carry_{int(row.TaskID)}")
        d = int(row.GPU_Demand); p = context["power"][str(row.TaskType)]
        resources[r]["gpu"].append((iv, d)); resources[r]["it"].append((iv, int(round(d * p * 1000)))); resources[r]["facility"].append((iv, int(round(d * p * context["pue"][r] * 1000))))
    incumbent_map = incumbent.set_index("TaskID")
    choices = {}
    fixed_rows = []
    for _, task in final_tasks.iterrows():
        tid = int(task.TaskID); d = int(task.EstimatedDuration_min); p = context["power"][str(task.TaskType)]
        if tid not in chosen_ids:
            row = incumbent_map.loc[tid].to_dict(); row["TaskID"] = tid; fixed_rows.append(row)
            r = str(row["ExecutionRegion"]); s, e = int(row["StartMinute"]), int(row["EndMinute"])
            iv = model.NewIntervalVar(s, e - s, e, f"fixed_{tid}")
            resources[r]["gpu"].append((iv, int(task.GPU_Demand))); resources[r]["it"].append((iv, int(round(int(task.GPU_Demand) * p * 1000)))); resources[r]["facility"].append((iv, int(round(int(task.GPU_Demand) * p * context["pue"][r] * 1000))))
            continue
        arrival = max(mod.FINAL_START_M, int(task.ArrivalHour) * 60, int(task.EarliestStartHour) * 60); latest = min(mod.FINAL_END_M, int(task.LatestFinishHour) * 60)
        opts = []
        for r in mod.candidate_regions(task, context):
            if latest - d < arrival: continue
            su = arrival if str(task.TaskType) == "RealTimeInference" else latest - d
            sv = model.NewIntVar(arrival, su, f"start_{tid}_{r}"); ev = model.NewIntVar(arrival + d, latest, f"end_{tid}_{r}"); use = model.NewBoolVar(f"use_{tid}_{r}")
            model.Add(ev == sv + d); iv = model.NewOptionalIntervalVar(sv, d, ev, use, f"job_{tid}_{r}")
            resources[r]["gpu"].append((iv, int(task.GPU_Demand))); resources[r]["it"].append((iv, int(round(int(task.GPU_Demand) * p * 1000)))); resources[r]["facility"].append((iv, int(round(int(task.GPU_Demand) * p * context["pue"][r] * 1000))))
            opts.append((use, sv, ev, r))
        if not opts: return pd.DataFrame(), {"status": "INFEASIBLE_NO_OPTIONS", "selected_task_count": len(chosen_ids)}
        model.AddExactlyOne([o[0] for o in opts]); choices[tid] = opts
    for r in context["regions"]:
        model.AddCumulative([x[0] for x in resources[r]["gpu"]], [x[1] for x in resources[r]["gpu"]], context["gpu_capacity"][r])
        model.AddCumulative([x[0] for x in resources[r]["it"]], [x[1] for x in resources[r]["it"]], int(round(context["it_capacity"][r] * 1000)))
        model.AddCumulative([x[0] for x in resources[r]["facility"]], [x[1] for x in resources[r]["facility"]], int(round(context["facility_capacity"][r] * 1000)))
    objective = []
    for tid, opts in choices.items():
        task = final_tasks.loc[final_tasks.TaskID.astype(int).eq(tid)].iloc[0]; arrival = int(task.ArrivalHour) * 60
        for use, sv, _ev, r in opts:
            wait = model.NewIntVar(0, mod.FINAL_END_M - mod.FINAL_START_M, f"wait_{tid}_{r}")
            model.Add(wait == sv - arrival).OnlyEnforceIf(use); model.Add(wait == 0).OnlyEnforceIf(use.Not())
            objective.append(wait * 100 + context["latency"][(str(task.SourceRegion), r)] * use)
    model.Minimize(sum(objective))
    solver = cp_model.CpSolver(); solver.parameters.random_seed = SEED; solver.parameters.num_search_workers = 1; solver.parameters.max_time_in_seconds = max_seconds
    started = time.perf_counter(); status = solver.Solve(model)
    meta = {"status": solver.StatusName(status), "wall_time_seconds": time.perf_counter() - started, "selected_task_count": len(chosen_ids), "selected_task_ids": sorted(chosen_ids), "num_conflicts": solver.NumConflicts(), "num_branches": solver.NumBranches()}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return pd.DataFrame(), meta
    rows = fixed_rows[:]
    task_map = final_tasks.set_index("TaskID", drop=False)
    for tid, opts in choices.items():
        task = task_map.loc[tid]
        for use, sv, ev, r in opts:
            if solver.Value(use):
                rows.append(mod.row_for_task(task, r, solver.Value(sv), solver.Value(ev), context, "q1-fix-and-opt")); break
    out = pd.DataFrame(rows).sort_values("TaskID").reset_index(drop=True)
    meta.update({"objective": float(solver.ObjectiveValue()), "best_bound": float(solver.BestObjectiveBound()), "optimality_gap": float((solver.ObjectiveValue() - solver.BestObjectiveBound()) / max(1.0, abs(solver.ObjectiveValue())))})
    return out, meta


def main() -> int:
    started = time.perf_counter(); OUT_DIR.mkdir(parents=True, exist_ok=True); mod = load_module()
    tasks, context = mod.load_data(); carry, _, warm = mod.warmup(tasks, context); final_tasks = tasks[tasks.ArrivalHour >= mod.Q1_START_H].copy()
    incumbent_all = pd.read_csv(STAGING / "optimized_schedule.csv"); incumbent = incumbent_all[incumbent_all.SchedulePhase.astype(str).eq("q1-arrival")].copy()
    candidate, solver = fixed_neighbour(mod, final_tasks, context, carry, incumbent)
    audit = mod.audit_schedule(candidate, final_tasks, carry, context) if not candidate.empty else {"passed": False, "violations": ["empty_candidate"]}
    if "resource_rows" in audit:
        audit = {k: v for k, v in audit.items() if k != "resource_rows"}
    candidate.to_csv(OUT_DIR / "q1_fix_opt_schedule.csv", index=False)
    dump(OUT_DIR / "q1_fix_opt_solver.json", solver); dump(OUT_DIR / "q1_fix_opt_constraint_audit.json", audit)
    dump(OUT_DIR / "q1_fix_opt_summary.json", {"schema_version": 1, "status": "PASS" if audit.get("passed") else "FAIL", "method": "CP-SAT_fix_and_optimize_12_task_neighborhood", "baseline_schedule": "frozen optimized_schedule.csv", "selected_task_ids": solver.get("selected_task_ids", []), "solver": solver, "audit_passed": bool(audit.get("passed")), "decision": "PROBE_ONLY", "runtime_seconds": time.perf_counter() - started, "code_sha256": sha256(Path(__file__).resolve())})
    dump(OUT_DIR / "q1_fix_opt_risk_probes.json", {"status": "PASS" if audit.get("passed") else "FAIL", "checks": {"carry_in_reused": bool(warm["metadata"]["probe_passed"]), "all_final_tasks_once": bool(audit.get("passed")), "hard_constraints": bool(audit.get("passed")), "selected_neighborhood_bounded": len(solver.get("selected_task_ids", [])) <= 12}, "activation": "Only a bounded neighbourhood was released; incumbent remains the formal schedule."})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
